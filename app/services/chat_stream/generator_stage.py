"""
Generator & Tool Execution Stage (Issue #23)
============================================
Handles SSE streaming generation via LiNeP and Ollama-HTTP, reasoning/task/factcheck/artifact
splitters, token pacing, multi-iteration agent tool dispatch, and graceful fallback.
"""

import sys
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict

import httpx

from core.database import SessionLocal
from core.mirko_logger import get_mirko_logger, should_log_for_user
from liara_engine.memory.mood_system import MoodSystem
from services.config_service import get_config_service
from services.factcheck_splitter import FactCheckBlockExtractor, parse_factcheck_items
from services.linep_provider import get_linep_provider, linep_enabled, LinepUnavailableError
from services.ollama_capabilities import model_supports_tools, get_model_num_predict
from services.task_splitter import TaskBlockExtractor, parse_task_items
from services.thinking_splitter import ThinkingSplitter
from services.tool_executor import get_tool_executor
from services.tool_parser import ToolCall, get_tool_parser
from services.tool_registry import get_tool_registry
from services.toolcall_splitter import ToolCallBlockExtractor
from services.workspace_artifact_splitter import WorkspaceArtifactBlockExtractor, parse_workspace_artifact
from services.workspace_artifacts import save_artifact

from services.chat_stream.lock_guard import (
    SessionLockLostError,
    SessionLockTimeoutError,
    SessionLockUnavailableError,
    _acquire_session_lock,
    _race_with_lock_lost,
    _release_session_lock,
    _session_lock_watchdog,
    _with_lock_lost_guard,
)
from services.chat_stream.prompt_stage import (
    _build_agent_step_label,
    assemble_streaming_system_prompt,
    load_canonical_history,
)
from services.chat_stream.persistence_stage import (
    persist_user_turn_under_lock,
    persist_assistant_turn,
)
from services.chat_persistence import persist_assistant_message
from services.chat_stream.generator_helpers import (
    _resolve_symbol,
    _flatten_messages_for_linep,
    _append_linep_tool_call,
)

logger = logging.getLogger(__name__)
mlogger = get_mirko_logger()


async def _handle_workspace_artifact_blocks(raw_blocks: List[str], user_id: Optional[int], session_id: Optional[int]):
    """Saves each completed <workspace_artifact> block and yields its SSE line."""
    for raw_block in raw_blocks:
        title, content = parse_workspace_artifact(raw_block)
        filename = None
        if user_id is not None and session_id is not None:
            filename = await asyncio.to_thread(save_artifact, user_id, session_id, title, content, "Plan")
        payload = {"type": "workspace_artifact", "title": title, "filename": filename}
        if filename is None:
            payload["content"] = content
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_ollama_response(
    message: str,
    model: str = "llama3.2:3b",
    temperature: float = 0.7,
    context: Optional[str] = None,
    web_search_intent: Optional[str] = None,
    web_search_type: Optional[str] = None,
    web_search_data: Optional[Dict] = None,
    web_search_risk_score: Optional[int] = None,
    action_result: Optional[Dict] = None,
    memory_context: Optional[List[Dict]] = None,
    session_id: Optional[int] = None,
    user_id: int = None,
    username: Optional[str] = None,
    personality: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    user_message_id: Optional[int] = None,
    memory_enabled: bool = True,
    used_tools: bool = False,
    conversation_history: Optional[List[Dict]] = None,
    session_lock=None,
    images: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """Streame Ollama-Response via Server-Sent Events."""
    lock_watchdog_task = None
    lock_lost_event = asyncio.Event()

    def _check_lock_held():
        if lock_lost_event.is_set():
            raise SessionLockLostError("Sitzungskoordination wurde während der Anfrage unterbrochen (Lease-Verlust).")

    acquire_fn = _resolve_symbol("_acquire_session_lock", _acquire_session_lock)
    watchdog_fn = _resolve_symbol("_session_lock_watchdog", _session_lock_watchdog)
    mood_cls = _resolve_symbol("MoodSystem", MoodSystem)
    cfg_fn = _resolve_symbol("get_config_service", get_config_service)
    num_predict_fn = _resolve_symbol("get_model_num_predict", get_model_num_predict)
    httpx_mod = _resolve_symbol("httpx", httpx)

    if session_lock is None and session_id is not None:
        try:
            session_lock = await asyncio.to_thread(acquire_fn, session_id)
        except SessionLockTimeoutError:
            logger.error("Session generation lock acquisition timed out for session %s", session_id)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Die vorherige Anfrage in dieser Sitzung läuft noch oder hat das Zeitlimit überschritten.'})}\n\n"
            return
        except SessionLockUnavailableError as ex:
            logger.error("Session generation lock unavailable for session %s (%s)", session_id, ex)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Sitzungskoordination momentan nicht verfügbar. Bitte versuche es in Kürze erneut.'})}\n\n"
            return
        except Exception as ex:
            logger.error("Unexpected error acquiring session lock for session %s: %s", session_id, ex)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Sitzungsfehler aufgetreten. Bitte versuche es erneut.'})}\n\n"
            return

    if session_lock is not None:
        lock_watchdog_task = asyncio.create_task(watchdog_fn(session_lock, lock_lost_event))

    mood_system = mood_cls(user_id)
    interaction_type = mood_cls.detect_interaction_type(message)
    mood_snapshot = mood_system.get_snapshot()
    mood_modifier = mood_snapshot["modifier"]

    if user_id is not None and session_id is not None:
        db_turn = SessionLocal()
        try:
            if conversation_history is None:
                conversation_history = load_canonical_history(db_turn, session_id)
            if user_message_id is None:
                user_message_id = persist_user_turn_under_lock(
                    user_id=user_id,
                    session_id=session_id,
                    message=message,
                    model=model,
                    mood_snapshot=mood_snapshot,
                    memory_enabled=memory_enabled,
                    used_tools=used_tools,
                )
        except Exception as e:
            logger.error(f"Turn history read and user turn persistence failed: {e}")
        finally:
            db_turn.close()

    vision_context = ""
    if images and len(images) > 0:
        try:
            from services.vision_service import analyze_image_with_gemma, format_vision_context_block
            logger.info("Analyzing %d image(s) via Gemma Vision worker...", len(images))
            yield f"data: {json.dumps({'type': 'thinking', 'text': 'Analysiere Bild(er) mit Gemma Vision in der Cloud...\\n'})}\n\n"
            for img in images:
                analysis = await asyncio.to_thread(analyze_image_with_gemma, img, message)
                if analysis:
                    vision_context += format_vision_context_block(analysis)
        except Exception as vis_err:
            logger.error("Gemma Vision analysis error: %s", vis_err)

    supports_tools = await model_supports_tools(model)
    system_prompt = assemble_streaming_system_prompt(
        username=username,
        personality=personality,
        custom_instructions=custom_instructions,
        mood_modifier=mood_modifier,
        model=model,
        supports_tools=supports_tools,
        memory_context=memory_context,
        custom_context=context,
        action_result=action_result,
        web_search_data=web_search_data,
        user_id=user_id,
        session_id=session_id,
        vision_context=vision_context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *(conversation_history or []),
        {"role": "user", "content": message}
    ]

    ollama_tools = None
    if supports_tools:
        ollama_tools = get_tool_registry().get_tools_for_ollama()
        logger.info("Native tools enabled for model '%s' (%d tools, user_id=%s, session_id=%s)", model, len(ollama_tools), user_id, session_id)

    full_response_text = ""
    full_thinking_text = ""
    persisted_attempted = False

    def _persist_turn(interrupted: bool = False) -> bool:
        return persist_assistant_turn(
            user_id=user_id,
            session_id=session_id,
            full_response_text=full_response_text,
            full_thinking_text=full_thinking_text,
            model=model,
            mood_snapshot=mood_snapshot,
            user_message_id=user_message_id,
            personality=personality,
            memory_enabled=memory_enabled,
            used_tools=used_tools,
            interrupted=interrupted,
        )

    try:
        metadata = {'type': 'metadata', 'model': model, 'mood': mood_snapshot["mood"]}
        if session_id:
            metadata['session_id'] = session_id
        yield f"data: {json.dumps(metadata)}\n\n"

        if memory_context:
            yield f"data: {json.dumps({'type': 'memory_context', 'data': memory_context})}\n\n"

        if action_result:
            yield f"data: {json.dumps({'type': 'action_result', 'result': action_result})}\n\n"
            if action_result.get('success'):
                confirmation_text = action_result.get('message', 'Aktion erfolgreich ausgeführt')
                if user_id and session_id:
                    db_shortcut = SessionLocal()
                    try:
                        persist_assistant_message(db_shortcut, session_id, user_id, confirmation_text)
                    finally:
                        db_shortcut.close()
                yield f"data: {json.dumps({'type': 'content', 'text': confirmation_text})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'action_executed': True})}\n\n"
                return

        if web_search_intent:
            yield f"data: {json.dumps({'type': 'web_search', 'intent': web_search_intent, 'search_type': web_search_type})}\n\n"
            if web_search_type == 'web' and web_search_data:
                web_source_items = [
                    {
                        "id": f"source-{i}",
                        "title": s.get("title", ""),
                        "url": s.get("url", ""),
                        "domain": s.get("domain", ""),
                        "published_at": s.get("published_at"),
                        "dated": s.get("dated", False)
                    }
                    for i, s in enumerate(web_search_data.get("sources", []))
                ]
                yield f"data: {json.dumps({'type': 'web_sources', 'items': web_source_items})}\n\n"
            elif web_search_data:
                yield f"data: {json.dumps({'type': 'web_results', 'results': web_search_data, 'search_type': web_search_type, 'risk_score': web_search_risk_score or 0})}\n\n"

        MAX_AGENT_ITERATIONS = 3
        agent_tool_used = False
        agent_steps: List[Dict] = []

        db_config = SessionLocal()
        try:
            configured_max_tokens = cfg_fn(db_config).get_max_tokens()
        finally:
            db_config.close()
        num_predict = await num_predict_fn(model, configured_max_tokens)

        transport = "ollama"
        if linep_enabled():
            if await get_linep_provider().health():
                transport = "linep"
                logger.info("[LiNeP-Switch] Chat turn (session=%s) using LiNeP transport", session_id)
            else:
                logger.warning("[LiNeP-Switch] LINEP_ENABLED, but linep-server unreachable -> fallback to Ollama-HTTP (session=%s)", session_id)

        for iteration in range(MAX_AGENT_ITERATIONS + 1):
            _check_lock_held()
            iteration_tools = ollama_tools if iteration < MAX_AGENT_ITERATIONS else None

            if iteration_tools is None and ollama_tools:
                messages.append({
                    "role": "user",
                    "content": "Es sind keine weiteren Tool-Aufrufe mehr möglich. Bitte beantworte die ursprüngliche Frage jetzt direkt mit den bisher erhaltenen Informationen."
                })

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict,
                    "repeat_penalty": 1.1
                }
            }
            if iteration_tools:
                payload["tools"] = iteration_tools

            thinking_splitter = ThinkingSplitter()
            task_extractor = TaskBlockExtractor()
            factcheck_extractor = FactCheckBlockExtractor()
            artifact_extractor = WorkspaceArtifactBlockExtractor()
            toolcall_extractor = ToolCallBlockExtractor() if transport == "linep" else None
            turn_content = ""
            turn_tool_calls = []

            if transport == "linep":
                prompt_text = _flatten_messages_for_linep(messages, bool(iteration_tools))
                async for event_kind, event_payload in _with_lock_lost_guard(
                    get_linep_provider().generate_stream(prompt_text, model, num_predict),
                    lock_lost_event
                ):
                    _check_lock_held()
                    if event_kind == "thinking":
                        full_thinking_text += event_payload
                        yield f"data: {json.dumps({'type': 'thinking', 'text': event_payload})}\n\n"
                        continue

                    if event_kind == "tool_call":
                        try:
                            native_call = json.loads(event_payload)
                        except json.JSONDecodeError:
                            native_call = None
                        if isinstance(native_call, dict) and native_call.get("function"):
                            turn_tool_calls.append(native_call)
                        continue

                    content = event_payload
                    thinking_part, content_part = thinking_splitter.feed(content)
                    if thinking_part:
                        full_thinking_text += thinking_part
                        yield f"data: {json.dumps({'type': 'thinking', 'text': thinking_part})}\n\n"

                    if content_part:
                        content_part, completed_task_blocks = task_extractor.feed(content_part)
                        for raw_block in completed_task_blocks:
                            yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"

                    if content_part:
                        content_part, completed_factcheck_blocks = factcheck_extractor.feed(content_part)
                        for raw_block in completed_factcheck_blocks:
                            yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"

                    if content_part:
                        content_part, completed_artifact_blocks = artifact_extractor.feed(content_part)
                        async for sse_line in _handle_workspace_artifact_blocks(completed_artifact_blocks, user_id, session_id):
                            yield sse_line

                    if content_part:
                        content_part, completed_toolcall_blocks = toolcall_extractor.feed(content_part)
                        for raw_block in completed_toolcall_blocks:
                            _append_linep_tool_call(turn_tool_calls, raw_block)

                    if content_part:
                        turn_content += content_part
                        full_response_text += content_part
                        try:
                            if username and should_log_for_user(username):
                                mlogger.log_sse_chunk("content", content=content_part)
                        except:
                            pass
                        yield f"data: {json.dumps({'type': 'content', 'text': content_part})}\n\n"

                leftover_thinking, leftover_content = thinking_splitter.flush()
                if leftover_thinking:
                    full_thinking_text += leftover_thinking
                    yield f"data: {json.dumps({'type': 'thinking', 'text': leftover_thinking})}\n\n"
                if leftover_content:
                    leftover_content, leftover_task_blocks = task_extractor.feed(leftover_content)
                    for raw_block in leftover_task_blocks:
                        yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"
                    if leftover_content:
                        leftover_content, leftover_factcheck_blocks = factcheck_extractor.feed(leftover_content)
                        for raw_block in leftover_factcheck_blocks:
                            yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                        if leftover_content:
                            leftover_content, leftover_artifact_blocks = artifact_extractor.feed(leftover_content)
                            async for sse_line in _handle_workspace_artifact_blocks(leftover_artifact_blocks, user_id, session_id):
                                yield sse_line
                        if leftover_content:
                            leftover_content, leftover_toolcall_blocks = toolcall_extractor.feed(leftover_content)
                            for raw_block in leftover_toolcall_blocks:
                                _append_linep_tool_call(turn_tool_calls, raw_block)
                            if leftover_content:
                                turn_content += leftover_content
                                full_response_text += leftover_content
                                yield f"data: {json.dumps({'type': 'content', 'text': leftover_content})}\n\n"

                final_task_content = task_extractor.flush()
                if final_task_content:
                    final_task_content, final_task_factcheck_blocks = factcheck_extractor.feed(final_task_content)
                    for raw_block in final_task_factcheck_blocks:
                        yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                    if final_task_content:
                        final_task_content, final_task_artifact_blocks = artifact_extractor.feed(final_task_content)
                        async for sse_line in _handle_workspace_artifact_blocks(final_task_artifact_blocks, user_id, session_id):
                            yield sse_line
                    if final_task_content:
                        final_task_content, final_task_toolcall_blocks = toolcall_extractor.feed(final_task_content)
                        for raw_block in final_task_toolcall_blocks:
                            _append_linep_tool_call(turn_tool_calls, raw_block)
                        if final_task_content:
                            turn_content += final_task_content
                            full_response_text += final_task_content
                            yield f"data: {json.dumps({'type': 'content', 'text': final_task_content})}\n\n"

                final_factcheck_content = factcheck_extractor.flush()
                if final_factcheck_content:
                    final_factcheck_content, final_fc_artifact_blocks = artifact_extractor.feed(final_factcheck_content)
                    async for sse_line in _handle_workspace_artifact_blocks(final_fc_artifact_blocks, user_id, session_id):
                        yield sse_line
                if final_factcheck_content:
                    final_factcheck_content, final_fc_toolcall_blocks = toolcall_extractor.feed(final_factcheck_content)
                    for raw_block in final_fc_toolcall_blocks:
                        _append_linep_tool_call(turn_tool_calls, raw_block)
                    if final_factcheck_content:
                        turn_content += final_factcheck_content
                        full_response_text += final_factcheck_content
                        yield f"data: {json.dumps({'type': 'content', 'text': final_factcheck_content})}\n\n"

                final_artifact_content = artifact_extractor.flush()
                if final_artifact_content:
                    final_artifact_content, final_artifact_toolcall_blocks = toolcall_extractor.feed(final_artifact_content)
                    for raw_block in final_artifact_toolcall_blocks:
                        _append_linep_tool_call(turn_tool_calls, raw_block)
                    if final_artifact_content:
                        turn_content += final_artifact_content
                        full_response_text += final_artifact_content
                        yield f"data: {json.dumps({'type': 'content', 'text': final_artifact_content})}\n\n"

                final_toolcall_content = toolcall_extractor.flush()
                if final_toolcall_content:
                    turn_content += final_toolcall_content
                    full_response_text += final_toolcall_content
                    yield f"data: {json.dumps({'type': 'content', 'text': final_toolcall_content})}\n\n"

                if not turn_tool_calls and iteration_tools:
                    fallback_call = get_tool_parser().extract_tool_call(turn_content)
                    if fallback_call:
                        turn_tool_calls.append({
                            "function": {"name": fallback_call.tool_name, "arguments": fallback_call.parameters}
                        })

            else:
                ollama_timeout = httpx_mod.Timeout(connect=10.0, read=280.0, write=10.0, pool=10.0)
                async with httpx_mod.AsyncClient(timeout=ollama_timeout) as client:
                    async with client.stream("POST", "http://localhost:11434/api/chat", json=payload) as response:
                        response.raise_for_status()
                        async for line in _with_lock_lost_guard(response.aiter_lines(), lock_lost_event):
                            _check_lock_held()
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    if "message" in chunk:
                                        if chunk["message"].get("tool_calls"):
                                            turn_tool_calls.extend(chunk["message"]["tool_calls"])

                                        native_thinking = chunk["message"].get("thinking", "")
                                        if native_thinking:
                                            full_thinking_text += native_thinking
                                            yield f"data: {json.dumps({'type': 'thinking', 'text': native_thinking})}\n\n"

                                        content = chunk["message"].get("content", "")
                                        if content:
                                            thinking_part, content_part = thinking_splitter.feed(content)
                                            if thinking_part:
                                                full_thinking_text += thinking_part
                                                yield f"data: {json.dumps({'type': 'thinking', 'text': thinking_part})}\n\n"

                                            if content_part:
                                                content_part, completed_task_blocks = task_extractor.feed(content_part)
                                                for raw_block in completed_task_blocks:
                                                    yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"

                                            if content_part:
                                                content_part, completed_factcheck_blocks = factcheck_extractor.feed(content_part)
                                                for raw_block in completed_factcheck_blocks:
                                                    yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"

                                            if content_part:
                                                content_part, completed_artifact_blocks = artifact_extractor.feed(content_part)
                                                async for sse_line in _handle_workspace_artifact_blocks(completed_artifact_blocks, user_id, session_id):
                                                    yield sse_line

                                            if content_part:
                                                turn_content += content_part
                                                full_response_text += content_part
                                                try:
                                                    if username and should_log_for_user(username):
                                                        mlogger.log_sse_chunk("content", content=content_part)
                                                except:
                                                    pass
                                                yield f"data: {json.dumps({'type': 'content', 'text': content_part})}\n\n"

                                    if chunk.get("done", False):
                                        leftover_thinking, leftover_content = thinking_splitter.flush()
                                        if leftover_thinking:
                                            full_thinking_text += leftover_thinking
                                            yield f"data: {json.dumps({'type': 'thinking', 'text': leftover_thinking})}\n\n"
                                        if leftover_content:
                                            leftover_content, leftover_task_blocks = task_extractor.feed(leftover_content)
                                            for raw_block in leftover_task_blocks:
                                                yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"
                                            if leftover_content:
                                                leftover_content, leftover_factcheck_blocks = factcheck_extractor.feed(leftover_content)
                                                for raw_block in leftover_factcheck_blocks:
                                                    yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                                                if leftover_content:
                                                    leftover_content, leftover_artifact_blocks = artifact_extractor.feed(leftover_content)
                                                    async for sse_line in _handle_workspace_artifact_blocks(leftover_artifact_blocks, user_id, session_id):
                                                        yield sse_line
                                                if leftover_content:
                                                    turn_content += leftover_content
                                                    full_response_text += leftover_content
                                                    yield f"data: {json.dumps({'type': 'content', 'text': leftover_content})}\n\n"

                                        final_task_content = task_extractor.flush()
                                        if final_task_content:
                                            final_task_content, final_task_factcheck_blocks = factcheck_extractor.feed(final_task_content)
                                            for raw_block in final_task_factcheck_blocks:
                                                yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                                            if final_task_content:
                                                final_task_content, final_task_artifact_blocks = artifact_extractor.feed(final_task_content)
                                                async for sse_line in _handle_workspace_artifact_blocks(final_task_artifact_blocks, user_id, session_id):
                                                    yield sse_line
                                            if final_task_content:
                                                turn_content += final_task_content
                                                full_response_text += final_task_content
                                                yield f"data: {json.dumps({'type': 'content', 'text': final_task_content})}\n\n"
                                        final_factcheck_content = factcheck_extractor.flush()
                                        if final_factcheck_content:
                                            final_factcheck_content, final_fc_artifact_blocks = artifact_extractor.feed(final_factcheck_content)
                                            async for sse_line in _handle_workspace_artifact_blocks(final_fc_artifact_blocks, user_id, session_id):
                                                yield sse_line
                                        if final_factcheck_content:
                                            turn_content += final_factcheck_content
                                            full_response_text += final_factcheck_content
                                            yield f"data: {json.dumps({'type': 'content', 'text': final_factcheck_content})}\n\n"
                                        final_artifact_content = artifact_extractor.flush()
                                        if final_artifact_content:
                                            turn_content += final_artifact_content
                                            full_response_text += final_artifact_content
                                            yield f"data: {json.dumps({'type': 'content', 'text': final_artifact_content})}\n\n"
                                        break

                                except json.JSONDecodeError:
                                    continue

            if turn_tool_calls and iteration < MAX_AGENT_ITERATIONS:
                agent_tool_used = True
                messages.append({
                    "role": "assistant",
                    "content": turn_content,
                    "tool_calls": turn_tool_calls
                })

                tool_executor = get_tool_executor()
                for tc in turn_tool_calls:
                    _check_lock_held()
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    arguments = fn.get("arguments") or {}

                    agent_steps.append({
                        "id": f"step-{len(agent_steps)}",
                        "label": _build_agent_step_label(tool_name, arguments),
                        "status": "running"
                    })
                    yield f"data: {json.dumps({'type': 'agent_steps', 'items': agent_steps})}\n\n"

                    tool_call = ToolCall(tool_name=tool_name, parameters=arguments, raw_text="", confidence=1.0)
                    try:
                        tool_result = await _race_with_lock_lost(
                            tool_executor.execute(tool_call, user_id or 0, session_id=session_id),
                            lock_lost_event
                        )
                    except SessionLockLostError:
                        raise
                    except Exception as e:
                        logger.error(f"Agent tool execution failed: {tool_name}: {e}")
                        tool_result = {"success": False, "error": str(e)}

                    _check_lock_held()

                    agent_steps[-1]["status"] = "done" if tool_result.get("success") else "error"
                    yield f"data: {json.dumps({'type': 'agent_steps', 'items': agent_steps})}\n\n"

                    inner_result = tool_result.get("result") or {}
                    if tool_result.get("success") and inner_result.get("type") == "web":
                        web_source_items = [
                            {
                                "id": f"source-{i}",
                                "title": s.get("title", ""),
                                "url": s.get("url", ""),
                                "domain": s.get("domain", ""),
                                "published_at": s.get("published_at"),
                                "dated": s.get("dated", False)
                            }
                            for i, s in enumerate(inner_result.get("sources", []))
                        ]
                        yield f"data: {json.dumps({'type': 'web_sources', 'items': web_source_items})}\n\n"

                    if tool_name == "workspace_propose_change" and tool_result.get("success") and inner_result.get("proposed"):
                        yield f"data: {json.dumps({'type': 'workspace_proposal', 'proposal_id': inner_result.get('proposal_id'), 'filename': inner_result.get('filename'), 'action': inner_result.get('action'), 'session_id': session_id})}\n\n"

                    if tool_name == "workspace_propose_dependency_change" and tool_result.get("success") and inner_result.get("proposed"):
                        yield f"data: {json.dumps({'type': 'workspace_proposal', 'proposal_id': inner_result.get('proposal_id'), 'filename': inner_result.get('package'), 'action': inner_result.get('action'), 'session_id': session_id})}\n\n"

                    tool_message = {"role": "tool", "content": json.dumps(tool_result)}
                    if tc.get("id"):
                        tool_message["tool_call_id"] = tc["id"]
                    messages.append(tool_message)

                continue

            break

        try:
            if username and should_log_for_user(username):
                mlogger.log_sse_chunk("done", metadata={"mood_updated": True})
        except:
            pass

        if user_id is not None:
            mood_system.update_mood(interaction_type, intensity=0.5)

        if user_id is not None and session_id is not None and full_response_text:
            _check_lock_held()
            persisted_attempted = True
            yield f"data: {json.dumps({'type': 'done', 'mood_updated': True})}\n\n"

            persisted_ok = False
            try:
                persisted_ok = await asyncio.to_thread(_persist_turn, False)
            except Exception as e:
                logger.error(f"Assistant message persistence task failed: {e}")
            yield f"data: {json.dumps({'type': 'persisted', 'success': persisted_ok})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done', 'mood_updated': True})}\n\n"

    except SessionLockLostError as e:
        logger.error("Turn aborted due to lock lease loss (session=%s): %s", session_id, e)
        persisted_attempted = True
        yield f"data: {json.dumps({'type': 'error', 'error': 'Sitzungskoordination wurde während der Anfrage unterbrochen.'})}\n\n"

    except httpx_mod.TimeoutException:
        yield f"data: {json.dumps({'type': 'error', 'error': {'error_type': 'timeout', 'message': 'Ollama antwortet nicht (Timeout nach 280s)', 'timestamp': datetime.now().isoformat(), 'recoverable': True, 'suggestion': 'Versuche es mit einem schnelleren Modell'}})}\n\n"

    except httpx_mod.ConnectError:
        yield f"data: {json.dumps({'type': 'error', 'error': {'error_type': 'connection_error', 'message': 'Kann nicht mit Ollama verbinden', 'timestamp': datetime.now().isoformat(), 'recoverable': True, 'suggestion': 'Prüfe ob Ollama läuft: systemctl status ollama'}})}\n\n"

    except LinepUnavailableError as e:
        logger.error(f"LiNeP transport failed mid-stream: {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': {'error_type': 'linep_error', 'message': 'LiNeP-Transport nicht erreichbar (experimentell)', 'timestamp': datetime.now().isoformat(), 'recoverable': True, 'suggestion': 'Erneut versuchen - fällt bei Bedarf auf Ollama-HTTP zurück'}})}\n\n"

    except httpx_mod.HTTPStatusError as e:
        yield f"data: {json.dumps({'type': 'error', 'error': {'error_type': 'http_error', 'message': f'Ollama HTTP Error: {e.response.status_code}', 'timestamp': datetime.now().isoformat(), 'recoverable': False, 'suggestion': 'Model existiert möglicherweise nicht.'}})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': {'error_type': 'unknown_error', 'message': f'Unbekannter Fehler: {str(e)}', 'timestamp': datetime.now().isoformat(), 'recoverable': False, 'suggestion': 'Kontaktiere System-Admin'}})}\n\n"

    finally:
        if not lock_lost_event.is_set() and not persisted_attempted and full_response_text and user_id is not None and session_id is not None:
            try:
                await asyncio.to_thread(_persist_turn, True)
            except Exception as e:
                logger.error(f"Interrupted-turn persistence failed: {e}")

        if lock_watchdog_task is not None:
            lock_watchdog_task.cancel()
            try:
                await asyncio.gather(lock_watchdog_task, return_exceptions=True)
            except Exception:
                pass

        if not lock_lost_event.is_set():
            _release_session_lock(session_lock)
