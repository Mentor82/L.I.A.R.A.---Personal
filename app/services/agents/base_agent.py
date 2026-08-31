"""
Base Agent Engine für L.I.A.R.A.
Implementiert den autonomen ReAct-Loop (Thought -> Action -> Observation).
"""
import os
import json
import re
import logging
import asyncio
import requests
from typing import Dict, List, Any, Optional, Callable, Awaitable

from services.ollama_capabilities import model_supports_tools

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")


class BaseAgent:
    """
    Abstrakte Basisklasse für alle spezialisierten Liara-Agenten.
    """

    def __init__(
        self,
        name: str,
        role_description: str,
        system_prompt: str,
        model: str = "qwen2.5:7b",
        max_steps: int = 12,
        ollama_url: str = OLLAMA_BASE_URL
    ):
        self.name = name
        self.role_description = role_description
        self.system_prompt = system_prompt
        self.model = model
        self.max_steps = max_steps
        self.ollama_url = ollama_url
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any]
    ):
        """Registriert ein Werkzeug mit Schema und Handler-Funktion."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }

    def _build_tools_prompt(self) -> str:
        """Erzeugt die Tool-Definitionen für den System-Prompt."""
        if not self.tools:
            return "Du hast keine externen Tools registriert."

        lines = ["Du hast Zugriff auf folgende Werkzeuge:\n"]
        for t in self.tools.values():
            params_json = json.dumps(t["parameters"], ensure_ascii=False, indent=2)
            lines.append(
                f"### Tool: `{t['name']}`\n"
                f"{t['description']}\n"
                f"Parameter Schema:\n```json\n{params_json}\n```\n"
            )

        lines.append(
            "\n### Formatierungs-Regeln:\n"
            "Wenn du ein Tool aufrufen möchtest, antworte GENAU in diesem Format:\n"
            "Gedanke: <Deine Analyse und der nächste logische Schritt>\n"
            "<tool_call>\n"
            "{\n"
            '  "name": "tool_name",\n'
            '  "arguments": { ... }\n'
            "}\n"
            "</tool_call>\n\n"
            "Wenn du die Aufgabe vollständig erledigt hast oder keine weiteren Tools benötigst:\n"
            "Gedanke: <Zusammenfassung>\n"
            "<final_answer>\n"
            "Deine ausführliche finale Antwort an den Benutzer.\n"
            "</final_answer>\n"
        )
        return "\n".join(lines)

    def _build_native_tools_schema(self) -> List[Dict[str, Any]]:
        """Same tool definitions as _build_tools_prompt(), but as Ollama's
        native tool-calling schema instead of prompt text - register_tool()'s
        `parameters` are already plain JSON Schema, so no conversion needed."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in self.tools.values()
        ]

    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Extrahiert Gedanke, Tool-Aufruf oder finale Antwort aus der Modell-Ausgabe."""
        thought_match = re.search(r"Gedanke:\s*(.*?)(?=<tool_call>|<final_answer>|$)", text, re.DOTALL | re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else ""

        # Tool Call suchen
        tool_match = re.search(r"<tool_call>\s*({.*?})\s*</tool_call>", text, re.DOTALL)
        if tool_match:
            try:
                call_json = json.loads(tool_match.group(1))
                return {
                    "type": "tool_call",
                    "thought": thought,
                    "tool_name": call_json.get("name"),
                    "arguments": call_json.get("arguments", {})
                }
            except json.JSONDecodeError as e:
                return {
                    "type": "parse_error",
                    "thought": thought,
                    "error": f"Tool-Call JSON ungültig: {str(e)}",
                    "raw": tool_match.group(1)
                }

        # Final Answer suchen
        final_match = re.search(r"<final_answer>\s*(.*?)\s*</final_answer>", text, re.DOTALL)
        if final_match:
            return {
                "type": "final_answer",
                "thought": thought,
                "answer": final_match.group(1).strip()
            }

        # Fallback wenn keine Tags verwendet wurden
        return {
            "type": "final_answer",
            "thought": thought,
            "answer": text.strip()
        }

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Führt das angeforderte Tool synchron oder asynchron aus."""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' existiert nicht. Verfügbare Tools: {list(self.tools.keys())}"}

        handler = self.tools[tool_name]["handler"]
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**arguments)
            else:
                return await asyncio.to_thread(handler, **arguments)
        except TypeError as e:
            return {"error": f"Falsche Parameter für {tool_name}: {str(e)}"}
        except Exception as e:
            logger.exception(f"Fehler bei Ausführung von {tool_name}")
            return {"error": f"Fehler bei Tool-Ausführung ({tool_name}): {str(e)}"}

    async def call_llm(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Sendet Chat-Nachrichten an Ollama. Gibt das komplette message-Objekt
        zurück (nicht nur .content) - der native Tool-Pfad in run() braucht
        auch .tool_calls, die reine Text-Konvention liest nur .content.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Niedrige Temperatur für präzise Tool-Nutzung
            }
        }
        if tools:
            payload["tools"] = tools

        def _request():
            res = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=90)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {})

        try:
            return await asyncio.to_thread(_request)
        except Exception as e:
            logger.error(f"Ollama API Fehler: {e}")
            raise RuntimeError(f"Ollama Verbindung fehlgeschlagen ({self.model}): {str(e)}")

    async def run(
        self,
        task: str,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        is_cancelled: Optional[Callable[[], Awaitable[bool]]] = None
    ) -> Dict[str, Any]:
        """
        Haupt-Ausführungsschleife (ReAct Loop).
        """
        async def emit(event_type: str, data: Any):
            if callback:
                try:
                    await callback({"event": event_type, "agent": self.name, "data": data})
                except Exception as e:
                    logger.warning(f"Callback Fehler: {e}")

        # Prefer Ollama's native tool-calling for models that support it
        # (checked once via /api/show, see ollama_capabilities.py) - a
        # thinking/"harmony"-style model like gpt-oss doesn't reliably follow
        # a freeform "emit a literal <tool_call> tag" prompt convention (its
        # `content` can come back as just a restated thought with no tags at
        # all, which the text parser below has no choice but to treat as a
        # final answer - confirmed live with gpt-oss:120b-cloud). Models
        # without native tool support keep the existing text convention.
        use_native_tools = bool(self.tools) and await model_supports_tools(self.model)
        native_tools_schema = self._build_native_tools_schema() if use_native_tools else None

        full_system = self.system_prompt if use_native_tools else f"{self.system_prompt}\n\n{self._build_tools_prompt()}"
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": f"Aufgabe:\n{task}"}
        ]

        await emit("start", {"task": task, "model": self.model, "max_steps": self.max_steps, "native_tools": use_native_tools})

        step = 0
        history_log = []

        while step < self.max_steps:
            step += 1

            # Cooperative cancellation: the caller (agent_router.py) checks a
            # cross-worker Redis flag here since a cancel POST can land on a
            # different gunicorn worker than the one running this loop, so
            # there's no local asyncio.Task handle to just .cancel().
            if is_cancelled and await is_cancelled():
                await emit("cancelled", {"step": step})
                return {
                    "success": False,
                    "error": "Task durch Benutzer abgebrochen",
                    "steps": step,
                    "history": history_log,
                    "cancelled": True
                }

            await emit("step_start", {"step": step})

            # LLM anfragen
            try:
                message = await self.call_llm(messages, tools=native_tools_schema)
            except Exception as e:
                await emit("error", {"error": str(e), "step": step})
                return {
                    "success": False,
                    "error": str(e),
                    "steps": step,
                    "history": history_log
                }

            if use_native_tools:
                content = (message.get("content") or "").strip()
                native_tool_calls = message.get("tool_calls") or []

                if content:
                    await emit("thought", {"thought": content, "step": step})

                if native_tool_calls:
                    history_log.append({"type": "tool_call", "step": step, "tool_calls": native_tool_calls})
                    messages.append({"role": "assistant", "content": content, "tool_calls": native_tool_calls})

                    # Ollama can return more than one tool call in a single
                    # turn - execute all of them before the next LLM call,
                    # same as chat_streaming.py's native-tool loop.
                    for tc in native_tool_calls:
                        fn = tc.get("function", {})
                        t_name = fn.get("name")
                        t_args = fn.get("arguments") or {}

                        await emit("tool_call", {"tool": t_name, "arguments": t_args, "step": step})
                        observation = await self.execute_tool(t_name, t_args)
                        await emit("tool_result", {"tool": t_name, "result": observation, "step": step})

                        obs_str = json.dumps(observation, ensure_ascii=False) if not isinstance(observation, str) else observation
                        tool_message = {"role": "tool", "content": obs_str}
                        if tc.get("id"):
                            tool_message["tool_call_id"] = tc["id"]
                        messages.append(tool_message)

                    continue

                # No tool call this turn - the model's content is its answer.
                history_log.append({"type": "final_answer", "step": step, "answer": content})
                await emit("done", {"answer": content, "steps": step})
                return {
                    "success": True,
                    "answer": content,
                    "steps": step,
                    "history": history_log
                }

            # --- Prompt-based <tool_call>/<final_answer> convention (models without native tool support) ---
            raw_response = message.get("content", "")
            parsed = self._parse_llm_response(raw_response)
            parsed["step"] = step
            history_log.append(parsed)

            if parsed.get("thought"):
                await emit("thought", {"thought": parsed["thought"], "step": step})

            # Wenn Final Answer erreicht
            if parsed["type"] == "final_answer":
                await emit("done", {"answer": parsed["answer"], "steps": step})
                return {
                    "success": True,
                    "answer": parsed["answer"],
                    "steps": step,
                    "history": history_log
                }

            # Wenn Tool Call
            if parsed["type"] == "tool_call":
                t_name = parsed["tool_name"]
                t_args = parsed["arguments"]

                await emit("tool_call", {"tool": t_name, "arguments": t_args, "step": step})

                # Tool ausführen
                observation = await self.execute_tool(t_name, t_args)

                await emit("tool_result", {"tool": t_name, "result": observation, "step": step})

                # Observation zurück in Konversationshistorie einspeisen
                obs_str = json.dumps(observation, ensure_ascii=False) if not isinstance(observation, str) else observation
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": f"Observation aus {t_name}:\n{obs_str}"})

            elif parsed["type"] == "parse_error":
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": f"Fehler beim Parsen deines Tool-Calls: {parsed['error']}. Bitte korrigiere das Format."
                })

        # Max Steps erreicht
        timeout_msg = f"Maximale Schrittanzahl ({self.max_steps}) erreicht, bevor die Aufgabe abgeschlossen werden konnte."
        await emit("timeout", {"message": timeout_msg})
        return {
            "success": False,
            "error": timeout_msg,
            "steps": step,
            "history": history_log
        }
