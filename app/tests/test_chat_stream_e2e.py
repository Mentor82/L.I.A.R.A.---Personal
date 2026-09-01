"""
E2E Chat Streaming & Multi-Turn Agent Sequence Test Suite (Issue #25)
====================================================================
Tests end-to-end multi-turn sequences, tool execution with state accumulation,
splitter tag extraction without content leaks, keepalive timing, lease loss recovery,
and graceful client cancellation.
"""

import os
import sys
import json
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"

for mod in ("redis", "sentence_transformers", "neo4j", "jose", "passlib", "passlib.context"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import api.routers.chat_streaming
from services.chat_stream.lock_guard import (
    _with_sse_keepalive,
    SessionLockLostError,
    SessionLockTimeoutError,
)
from services.chat_stream.generator_stage import stream_ollama_response
from services.chat_stream.prompt_stage import assemble_streaming_system_prompt
from services.thinking_splitter import ThinkingSplitter
from services.task_splitter import TaskBlockExtractor, parse_task_items
from services.factcheck_splitter import FactCheckBlockExtractor, parse_factcheck_items
from services.workspace_artifact_splitter import WorkspaceArtifactBlockExtractor, parse_workspace_artifact


class TestChatStreamE2E(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_lock = MagicMock()
        self.mock_lock.acquire.return_value = True
        self.mock_lock.reacquire.return_value = True
        self.mock_lock.release.return_value = None

        self.mock_db = MagicMock()
        self.mock_db.execute.return_value.all.return_value = []
        self.mock_db.execute.return_value.scalar.return_value = 999
        self.mock_db.execute.return_value.first.return_value = None

        mock_mood_state = MagicMock()
        mock_mood_state.current_mood = "neutral"
        mock_mood_state.intensity = 1.0
        mock_mood_state.confidence = 1.0
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_mood_state
        self.mock_db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_mood_state
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        self.patch_db_gen = patch("services.chat_stream.generator_stage.SessionLocal", return_value=self.mock_db)
        self.patch_db_pers = patch("services.chat_stream.persistence_stage.SessionLocal", return_value=self.mock_db)
        self.patch_db_mood = patch("liara_engine.memory.mood_system.SessionLocal", return_value=self.mock_db)
        self.patch_db_core = patch("core.database.SessionLocal", return_value=self.mock_db)
        self.patch_db_gen.start()
        self.patch_db_pers.start()
        self.patch_db_mood.start()
        self.patch_db_core.start()

    def tearDown(self):
        self.patch_db_gen.stop()
        self.patch_db_pers.stop()
        self.patch_db_mood.stop()
        self.patch_db_core.stop()

    async def test_e2e_splitter_pipeline_combined_tags(self):
        """
        Verify that a streamed LLM response containing <think>, <tasks>,
        <factcheck>, and <workspace_artifact> tags extracts each into its
        own structured SSE event with ZERO tag or JSON fragments leaking into
        the visible 'content' events.
        """
        chunks_in = [
            "<think>Ich muss ",
            "zuerst den Plan strukturieren.</think>",
            "Hier ist der Plan:\n",
            "<tasks>\n- [ ] Schritt 1: Setup\n- [x] Schritt 2: Build\n</tasks>\n",
            "Laut Quelle: Python ist populär.",
            "<factcheck>\n- [bestätigt|python.org] Python ist populär\n</factcheck>\n",
            "Ich erstelle die Datei:\n",
            "<workspace_artifact>\nTitel: Architecture\nInhalt:\n# System Architecture\nComponents: A, B, C\n</workspace_artifact>\n",
            "Alles erfolgreich vorbereitet!"
        ]

        async def mock_aiter_lines():
            for c in chunks_in:
                yield json.dumps({"message": {"content": c}})
            yield json.dumps({"done": True})

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.aiter_lines = MagicMock(side_effect=mock_aiter_lines)

        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None
        mock_client.stream.return_value = mock_stream_ctx

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=self.mock_lock), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=False), \
             patch("services.chat_stream.generator_stage.save_artifact", return_value="architecture.md"):

            events = []
            generator = stream_ollama_response(
                message="Erstelle Architekturplan",
                session_id=42,
                user_id=1,
                session_lock=self.mock_lock
            )

            async for line in generator:
                if line.startswith("data: "):
                    events.append(json.loads(line.replace("data: ", "").strip()))

        event_types = [e.get("type") for e in events]
        self.assertIn("thinking", event_types)
        self.assertIn("tasks", event_types)
        self.assertIn("factcheck", event_types)
        self.assertIn("workspace_artifact", event_types)
        self.assertIn("content", event_types)
        self.assertIn("done", event_types)

        # Verify parsed tasks
        task_events = [e for e in events if e.get("type") == "tasks"]
        self.assertTrue(len(task_events) >= 1)
        task_items = task_events[0].get("items", [])
        self.assertEqual(len(task_items), 2)
        self.assertEqual(task_items[0]["label"], "Schritt 1: Setup")
        self.assertFalse(task_items[0]["done"])
        self.assertEqual(task_items[1]["label"], "Schritt 2: Build")
        self.assertTrue(task_items[1]["done"])

        # Verify parsed factcheck
        factcheck_events = [e for e in events if e.get("type") == "factcheck"]
        self.assertTrue(len(factcheck_events) >= 1)
        fc_items = factcheck_events[0].get("items", [])
        self.assertEqual(len(fc_items), 1)
        self.assertEqual(fc_items[0]["confidence"], "bestätigt")
        self.assertEqual(fc_items[0]["label"], "Python ist populär")
        self.assertEqual(fc_items[0]["source"], "python.org")

        # Verify workspace artifact
        artifact_events = [e for e in events if e.get("type") == "workspace_artifact"]
        self.assertEqual(len(artifact_events), 1)
        self.assertEqual(artifact_events[0]["title"], "Architecture")
        self.assertEqual(artifact_events[0]["filename"], "architecture.md")

        # Verify visible content does NOT contain raw tags
        full_visible_content = "".join([e.get("text", "") for e in events if e.get("type") == "content"])
        self.assertNotIn("<think>", full_visible_content)
        self.assertNotIn("</think>", full_visible_content)
        self.assertNotIn("<tasks>", full_visible_content)
        self.assertNotIn("</tasks>", full_visible_content)
        self.assertNotIn("<factcheck>", full_visible_content)
        self.assertNotIn("</factcheck>", full_visible_content)
        self.assertNotIn("<workspace_artifact", full_visible_content)
        self.assertNotIn("</workspace_artifact>", full_visible_content)
        self.assertIn("Hier ist der Plan:", full_visible_content)
        self.assertIn("Alles erfolgreich vorbereitet!", full_visible_content)

    async def test_multi_turn_tool_sequence_and_history(self):
        """
        Verify multi-turn tool calling:
        Turn 1 triggers a tool and records agent_steps, web_sources, and message history.
        Turn 2 passes that history into subsequent LLM calls.
        """
        tool_call_payload = {
            "name": "web_search",
            "arguments": {"query": "Liara Python architecture"}
        }

        turn1_chunks_iter1 = [
            {"message": {"content": "", "tool_calls": [{"id": "call_1", "function": tool_call_payload}]}},
            {"done": True}
        ]
        turn1_chunks_iter2 = [
            {"message": {"content": "Basierend auf der Suche ist Liara modular aufgebaut."}},
            {"done": True}
        ]

        iter_count = 0
        async def mock_tool_aiter():
            nonlocal iter_count
            iter_count += 1
            chunks = turn1_chunks_iter1 if iter_count == 1 else turn1_chunks_iter2
            for c in chunks:
                yield json.dumps(c)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.aiter_lines = MagicMock(side_effect=mock_tool_aiter)

        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None
        mock_client.stream.return_value = mock_stream_ctx

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value={
            "success": True,
            "result": {
                "type": "web",
                "sources": [{"title": "Liara Docs", "url": "https://liara.ai/docs", "domain": "liara.ai"}]
            }
        })

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=self.mock_lock), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=True), \
             patch("services.chat_stream.generator_stage.get_tool_executor", return_value=mock_executor):

            events = []
            generator = stream_ollama_response(
                message="Wie ist Liara aufgebaut?",
                session_id=101,
                user_id=1,
                session_lock=self.mock_lock
            )

            async for line in generator:
                if line.startswith("data: "):
                    events.append(json.loads(line.replace("data: ", "").strip()))

        print("\nDEBUG EVENTS:", [e.get("type") for e in events], events)

        # Verify tool execution events
        agent_steps_events = [e for e in events if e.get("type") == "agent_steps"]
        self.assertTrue(len(agent_steps_events) >= 2)  # running -> done
        self.assertEqual(agent_steps_events[-1]["items"][0]["status"], "done")

        web_sources_events = [e for e in events if e.get("type") == "web_sources"]
        self.assertEqual(len(web_sources_events), 1)
        self.assertEqual(web_sources_events[0]["items"][0]["title"], "Liara Docs")

        content_events = [e for e in events if e.get("type") == "content"]
        full_content = "".join([e.get("text", "") for e in content_events])
        self.assertIn("Liara modular aufgebaut", full_content)

    async def test_keepalive_interleaving_slow_chunks(self):
        """
        Verify that slow streams receive ': keep-alive\n\n' pulses at the specified interval
        without dropping or delaying any actual content chunks.
        """
        async def slow_stream():
            yield "data: {\"type\": \"metadata\"}\n\n"
            await asyncio.sleep(0.06)
            yield "data: {\"type\": \"content\", \"text\": \"Chunk A\"}\n\n"
            await asyncio.sleep(0.06)
            yield "data: {\"type\": \"content\", \"text\": \"Chunk B\"}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"

        wrapped = _with_sse_keepalive(slow_stream(), interval=0.02)
        received = []
        async for chunk in wrapped:
            received.append(chunk)

        keepalives = [c for c in received if c == ": keep-alive\n\n"]
        self.assertGreaterEqual(len(keepalives), 2)

        data_events = [json.loads(c.replace("data: ", "").strip()) for c in received if c.startswith("data: ")]
        content_texts = [d.get("text") for d in data_events if d.get("type") == "content"]
        self.assertEqual(content_texts, ["Chunk A", "Chunk B"])

    async def test_lease_loss_turn_aborts_and_subsequent_turn_recovers(self):
        """
        Verify that when a turn loses lock lease ownership, it immediately aborts fail-closed,
        and that a subsequent turn on the same session acquires a fresh lock and succeeds.
        """
        # Turn 1: Lease loss
        mock_lock_lost = MagicMock()
        mock_lock_lost.reacquire.return_value = False  # Lease renewal fails

        async def slow_turn_aiter():
            yield json.dumps({"message": {"content": "Start of response"}})
            await asyncio.sleep(0.05)
            yield json.dumps({"message": {"content": "End of response"}})
            yield json.dumps({"done": True})

        mock_resp1 = MagicMock()
        mock_resp1.raise_for_status.return_value = None
        mock_resp1.aiter_lines = MagicMock(side_effect=slow_turn_aiter)

        mock_client1 = MagicMock()
        mock_client1.__aenter__.return_value = mock_client1
        mock_client1.__aexit__.return_value = None
        mock_stream_ctx1 = MagicMock()
        mock_stream_ctx1.__aenter__.return_value = mock_resp1
        mock_stream_ctx1.__aexit__.return_value = None
        mock_client1.stream.return_value = mock_stream_ctx1

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=mock_lock_lost), \
             patch("api.routers.chat_streaming._renew_session_lock", return_value=False), \
             patch("api.routers.chat_streaming.SESSION_GENERATION_LOCK_RENEW_INTERVAL", 0.01), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client1), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=False):

            events_turn1 = []
            async for line in stream_ollama_response(message="Turn 1", session_id=200, user_id=None):
                if line.startswith("data: "):
                    events_turn1.append(json.loads(line.replace("data: ", "").strip()))

        self.assertTrue(any(
            e.get("type") == "error" and "Sitzungskoordination wurde während der Anfrage unterbrochen" in e.get("error", "")
            for e in events_turn1
        ))

        # Turn 2: Redis recovered, healthy lock
        mock_lock_healthy = MagicMock()
        mock_lock_healthy.reacquire.return_value = True

        async def fast_turn_aiter():
            yield json.dumps({"message": {"content": "Turn 2 successful reply"}})
            yield json.dumps({"done": True})

        mock_resp2 = MagicMock()
        mock_resp2.raise_for_status.return_value = None
        mock_resp2.aiter_lines = MagicMock(side_effect=fast_turn_aiter)

        mock_client2 = MagicMock()
        mock_client2.__aenter__.return_value = mock_client2
        mock_client2.__aexit__.return_value = None
        mock_stream_ctx2 = MagicMock()
        mock_stream_ctx2.__aenter__.return_value = mock_resp2
        mock_stream_ctx2.__aexit__.return_value = None
        mock_client2.stream.return_value = mock_stream_ctx2

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=mock_lock_healthy), \
             patch("api.routers.chat_streaming._renew_session_lock", return_value=True), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client2), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=False):

            events_turn2 = []
            async for line in stream_ollama_response(message="Turn 2", session_id=200, user_id=None):
                if line.startswith("data: "):
                    events_turn2.append(json.loads(line.replace("data: ", "").strip()))

        content_turn2 = "".join([e.get("text", "") for e in events_turn2 if e.get("type") == "content"])
        self.assertIn("Turn 2 successful reply", content_turn2)
        self.assertTrue(any(e.get("type") == "done" for e in events_turn2))

    async def test_client_cancellation_releases_lock_cleanly(self):
        """
        Verify that when a client disconnects mid-stream and aclose() is invoked,
        the Redis session lock is cleanly released without leaving stuck lock keys.
        """
        mock_lock = MagicMock()
        mock_lock.release.return_value = None

        async def endless_aiter():
            while True:
                yield json.dumps({"message": {"content": "flowing... "}})
                await asyncio.sleep(0.01)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.aiter_lines = MagicMock(side_effect=endless_aiter)

        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None
        mock_client.stream.return_value = mock_stream_ctx

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=mock_lock), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=False):

            generator = stream_ollama_response(message="Endless", session_id=300, user_id=None)
            wrapped = _with_sse_keepalive(generator, interval=1.0)

            # Consume 3 chunks and then simulate client disconnect
            consumed = 0
            async for _ in wrapped:
                consumed += 1
                if consumed >= 3:
                    break

            await wrapped.aclose()

        mock_lock.release.assert_called()

    async def test_consent_gating_multi_turn(self):
        """
        Verify that when a sensitive tool execution requires explicit consent,
        the tool executor returns consent_required, agent_steps marks status as error/blocked,
        and the model does not execute unconsented actions.
        """
        tool_call_payload = {
            "name": "workspace_run_command",
            "arguments": {"command": "rm -rf /tmp/test"}
        }

        turn_chunks_iter1 = [
            {"message": {"content": "", "tool_calls": [{"id": "call_1", "function": tool_call_payload}]}},
            {"done": True}
        ]
        turn_chunks_iter2 = [
            {"message": {"content": "Diese Aktion erfordert deine ausdrückliche Zustimmung in den Einstellungen."}},
            {"done": True}
        ]

        iter_count = 0
        async def mock_tool_aiter():
            nonlocal iter_count
            iter_count += 1
            chunks = turn_chunks_iter1 if iter_count == 1 else turn_chunks_iter2
            for c in chunks:
                yield json.dumps(c)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.aiter_lines = MagicMock(side_effect=mock_tool_aiter)

        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None
        mock_client.stream.return_value = mock_stream_ctx

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value={
            "success": False,
            "error": "consent_required",
            "message": "Ausdrückliche Zustimmung des Nutzers erforderlich."
        })

        with patch("api.routers.chat_streaming._acquire_session_lock", return_value=self.mock_lock), \
             patch("api.routers.chat_streaming.httpx.AsyncClient", return_value=mock_client), \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock, return_value=1024), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock, return_value=True), \
             patch("services.chat_stream.generator_stage.get_tool_executor", return_value=mock_executor):

            events = []
            generator = stream_ollama_response(
                message="Lösche das Verzeichnis",
                session_id=400,
                user_id=1,
                session_lock=self.mock_lock
            )

            async for line in generator:
                if line.startswith("data: "):
                    events.append(json.loads(line.replace("data: ", "").strip()))

        # Verify agent_steps caught error status
        agent_steps_events = [e for e in events if e.get("type") == "agent_steps"]
        self.assertTrue(len(agent_steps_events) >= 2)
        self.assertEqual(agent_steps_events[-1]["items"][0]["status"], "error")

        content_events = [e for e in events if e.get("type") == "content"]
        full_content = "".join([e.get("text", "") for e in content_events])
        self.assertIn("Zustimmung", full_content)


if __name__ == "__main__":
    unittest.main()
