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

    async def call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Sendet Chat-Nachrichten an Ollama."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Niedrige Temperatur für präzise Tool-Nutzung
            }
        }
        
        def _request():
            res = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=90)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "")

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

        full_system = f"{self.system_prompt}\n\n{self._build_tools_prompt()}"
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": f"Aufgabe:\n{task}"}
        ]

        await emit("start", {"task": task, "model": self.model, "max_steps": self.max_steps})

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
                raw_response = await self.call_llm(messages)
            except Exception as e:
                await emit("error", {"error": str(e), "step": step})
                return {
                    "success": False,
                    "error": str(e),
                    "steps": step,
                    "history": history_log
                }

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
