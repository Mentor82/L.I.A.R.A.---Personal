"""
⚙️ Tool Executor
Automatische Ausführung von Tool-Calls mit Privacy-Checks
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from sqlalchemy import text

from core.database import SessionLocal
from services.tool_registry import get_tool_registry, ToolDefinition
from services.tool_parser import ToolCall
from services.web_search_service import get_web_search_service
from services.location_service import get_location_service
from services.search_broker import get_search_broker
from services.web_safety.proxy_sandbox import get_proxy_sandbox
from services import session_workspace
from services.productivity_tools import execute_productivity_tool

WORKSPACE_AGENT_TOOLS = (
    "workspace_list_files", "workspace_read_file", "workspace_propose_change",
    "workspace_propose_dependency_change",
)

# How many top SearXNG results get a real fetch-and-extract enrichment pass
# via the (SSRF-hardened) ProxySandbox - each one is a real HTTP request with
# its own timeout, not just a cheap snippet lookup, but they run concurrently
# (see asyncio.gather below) so this costs ~one fetch's wall-clock time
# regardless of N.
WEB_SEARCH_ENRICH_TOP_N = 10
WEB_SEARCH_SOURCE_TEXT_CAP = 2000

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Tool-Ausführungs-Fehler"""
    pass


class ToolExecutor:
    """Führt Tool-Calls automatisch aus"""
    
    def __init__(self):
        self.registry = get_tool_registry()
        self.web_search = get_web_search_service()
        self.location_service = get_location_service()
        self.search_broker = get_search_broker()
        self.proxy_sandbox = get_proxy_sandbox()
    
    async def execute(
        self,
        tool_call: ToolCall,
        user_id: int,
        check_consent: bool = True,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Führt Tool-Call aus

        Args:
            tool_call: Der auszuführende Tool-Call
            user_id: User-ID für Privacy-Checks
            check_consent: Ob Consent geprüft werden soll
            session_id: Aktuelle Chat-Session, nötig für die workspace_*-Tools.
                Kommt ausschließlich vom Aufrufer (chat_streaming.py's eigener,
                serverseitig bekannter session_id) - das Modell selbst liefert
                das nie als Tool-Parameter, damit es nie eine fremde Session
                ansprechen kann.

        Returns:
            Tool-Execution Result

        Raises:
            ToolExecutionError: Bei Ausführungsfehlern

        Note (issue #13 item 6): this used to also accept an optional `db`
        for the handful of tools needing a real consent/data lookup
        (detect_location, web_search, workspace_*) - callers (chat.py,
        chat_streaming.py's SSE agent loop) would thread their own
        request-scoped session through. For chat_streaming.py that session
        stays open for the entire multi-minute SSE stream, so a tool call
        deep into a long generation was reading through a connection that
        had already been idle-but-open for however long the model had been
        generating. Every DB touch below now opens and closes its own
        short-lived SessionLocal() instead, same pattern this file's
        persist_assistant_turn()/store_memory_async() already use for
        the same reason.
        """
        # Tool aus Registry holen
        tool_def = self.registry.get_tool(tool_call.tool_name)

        if not tool_def:
            return self._error_result(
                tool_call.tool_name,
                f"Unknown tool: {tool_call.tool_name}"
            )

        # Privacy-Check
        if check_consent and tool_def.requires_consent:
            has_consent = await self._check_user_consent(user_id, tool_def)
            logger.info("Consent check for tool '%s' (user_id=%s): granted=%s", tool_call.tool_name, user_id, has_consent)
            if not has_consent:
                logger.warning("Tool execution blocked by consent policy: '%s' (user_id=%s)", tool_call.tool_name, user_id)
                return self._error_result(
                    tool_call.tool_name,
                    "User consent required but not granted",
                    consent_required=True
                )

        # Parameter-Validierung
        validation_error = self._validate_parameters(tool_call, tool_def)
        if validation_error:
            logger.warning("Tool validation failed for '%s': %s (parameters: %s)", tool_call.tool_name, validation_error, tool_call.parameters)
            return self._error_result(
                tool_call.tool_name,
                validation_error
            )

        if tool_def.name in WORKSPACE_AGENT_TOOLS and session_id is None:
            logger.warning("Workspace tool '%s' called without active session_id", tool_call.tool_name)
            return self._error_result(
                tool_call.tool_name,
                "Kein aktiver Workspace (keine Chat-Session)"
            )

        # Tool ausführen
        try:
            logger.info("Executing tool '%s' for user_id=%s, session_id=%s with params: %s", tool_call.tool_name, user_id, session_id, tool_call.parameters)

            start = time.monotonic()
            result = await self._execute_tool(tool_def, tool_call.parameters, user_id, session_id)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Normalize inner-error-as-outer-success (issue #14): several
            # tool implementations signal a normal (non-exception) failure
            # by returning a dict with a top-level "error" key (weather,
            # location, current-time, workspace proposals) rather than
            # raising. Without this check, every one of those was wrapped
            # as success=True below - the Agent loop, agent_steps status,
            # and structured UI gating all key off the outer "success"
            # field, so a tool could fail while its execution trace said it
            # completed fine.
            if isinstance(result, dict) and "error" in result:
                logger.warning("Tool '%s' returned inner error in %dms: %s", tool_call.tool_name, elapsed_ms, result["error"])
                return self._error_result(
                    tool_call.tool_name,
                    result["error"],
                    result=result,
                    execution_time_ms=elapsed_ms,
                )

            logger.info("Tool '%s' completed successfully in %dms", tool_call.tool_name, elapsed_ms)
            return {
                "success": True,
                "tool": tool_call.tool_name,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": elapsed_ms
            }

        except Exception as e:
            logger.error("Tool '%s' execution raised exception: %s", tool_call.tool_name, e, exc_info=True)
            return self._error_result(
                tool_call.tool_name,
                str(e)
            )
    
    async def _execute_tool(
        self,
        tool_def: ToolDefinition,
        parameters: Dict[str, Any],
        user_id: int,
        session_id: Optional[int] = None
    ) -> Any:
        """
        Routing zu echten Tool-Implementierungen
        """
        # Web Search
        if tool_def.name == "web_search":
            return await self._execute_web_search(parameters)

        # 🌐 Web Page Fetch (direct URL reading)
        elif tool_def.name == "fetch_web_page":
            from services.web_search_service import fetch_web_page_safe
            return await fetch_web_page_safe(parameters.get("url", ""))

        # Weather
        elif tool_def.name == "get_weather":
            return await self._execute_weather(parameters)

        # Location Detection
        elif tool_def.name == "detect_location":
            return await self._execute_location(user_id)

        # Wikipedia
        elif tool_def.name == "wikipedia_search":
            return await self._execute_wikipedia(parameters)

        # 🔍 Delegate to the specialized Research Agent (multi-agent
        # orchestration, mirrors base_agent.py's delegate_research tool)
        elif tool_def.name == "delegate_research":
            return await self._execute_delegate_research(parameters)

        # 🐙 GitHub Search
        elif tool_def.name == "github_search":
            from services.github_service import get_github_service
            return await get_github_service().search_repositories(**parameters)

        # 🐙 GitHub Readme
        elif tool_def.name == "github_repo_readme":
            from services.github_service import get_github_service
            return await get_github_service().get_repository_readme(**parameters)

        # Current Time
        elif tool_def.name == "get_current_time":
            return await self._execute_current_time(parameters)

        # 🩺 System Health & Metrics
        elif tool_def.name == "get_system_health":
            from services.system_health_service import get_full_system_health
            scope = parameters.get("scope", "summary")
            return await asyncio.to_thread(get_full_system_health, scope=scope)

        # Workspace: inspect
        elif tool_def.name == "workspace_list_files":
            return self._execute_workspace_list(user_id, session_id)

        elif tool_def.name == "workspace_read_file":
            return self._execute_workspace_read(user_id, session_id, parameters)

        # Workspace: propose (never mutates directly - see session_workspace.create_proposal)
        elif tool_def.name == "workspace_propose_change":
            return self._execute_workspace_propose(user_id, session_id, parameters)

        # Workspace: propose a dependency change (issue #5) - never calls pip
        # itself, only session_workspace.create_package_proposal; same
        # approve/reject-by-the-user gate as a file proposal.
        elif tool_def.name == "workspace_propose_dependency_change":
            return self._execute_workspace_propose_dependency(user_id, session_id, parameters)

        # 📅 Productivity & Memory Tools (Notes, Tasks, Calendar, 4D Memory)
        prod_res = execute_productivity_tool(tool_def.name, user_id, parameters)
        if prod_res is not None:
            return prod_res

        # Fallback to stub function
        else:
            return await tool_def.function(**parameters)

    def _execute_workspace_list(self, user_id: int, session_id: int) -> Dict:
        files = session_workspace.list_session_files(user_id, session_id)
        return {"files": files}

    def _execute_workspace_read(self, user_id: int, session_id: int, params: Dict[str, Any]) -> Dict:
        filename = params.get("filename", "")
        return session_workspace.read_session_file(user_id, session_id, filename)

    def _execute_workspace_propose(self, user_id: int, session_id: int, params: Dict[str, Any]) -> Dict:
        result = session_workspace.create_proposal(
            user_id,
            session_id,
            filename=params.get("filename", ""),
            action=params.get("action", ""),
            new_content=params.get("content"),
            description=params.get("description", ""),
        )
        if not result.get("ok"):
            return {"error": result.get("error", "Vorschlag fehlgeschlagen")}
        return {
            "proposed": True,
            "proposal_id": result["proposal_id"],
            "filename": params.get("filename", ""),
            "action": params.get("action", ""),
            "message": "Vorschlag wurde erstellt. Der Nutzer muss ihn im Workspace-Tab annehmen, bevor er wirksam wird.",
        }

    def _execute_workspace_propose_dependency(self, user_id: int, session_id: int, params: Dict[str, Any]) -> Dict:
        result = session_workspace.create_package_proposal(
            user_id,
            session_id,
            action=params.get("action", ""),
            package_spec=params.get("package", ""),
            description=params.get("description", ""),
        )
        if not result.get("ok"):
            return {"error": result.get("error", "Vorschlag fehlgeschlagen")}
        return {
            "proposed": True,
            "proposal_id": result["proposal_id"],
            "package": params.get("package", ""),
            "action": params.get("action", ""),
            "message": "Vorschlag wurde erstellt. Der Nutzer muss ihn im Workspace-Tab annehmen, bevor das Paket tatsächlich installiert/entfernt wird.",
        }

    async def _execute_web_search(self, params: Dict[str, Any]) -> Dict:
        """Führt Web-Suche aus"""
        query = params.get("query")
        search_type = params.get("search_type", "instant")
        language = params.get("language", "de")

        if search_type == "web":
            policy = params.get("policy", "general")
            return await self._execute_web_search_general(query, language, policy)

        if search_type == "wikipedia":
            result = await self.web_search.search_wikipedia(query, language)
        else:
            result = await self.web_search.search_instant_answer(query)

        # Formatiere für LLM-Konsum
        return {
            "query": query,
            "type": search_type,
            "summary": self._format_search_result(result),
            "raw": result
        }

    async def _execute_web_search_general(self, query: str, language: str, policy: str = "general") -> Dict:
        """
        General/research-style web search (issue #4 phase 1) - SearXNG via
        SearchBroker for discovery, then real fetch-and-extract enrichment
        of the top few results via the (SSRF-hardened) ProxySandbox, so the
        model gets actual source text with URL/title/retrieval time instead
        of just a short snippet. Degrades gracefully (empty sources list,
        not an exception) if SearXNG is unreachable - the caller/model
        should be able to say "couldn't find anything" rather than the
        whole tool call failing.

        policy="fresh" (issue #4 phase 2) re-sorts by publish date instead
        of SearXNG's relevance order - dated results first, most recent
        first, undated ones pushed to the end rather than dropped (a
        result having no known date doesn't mean it's wrong, just that
        recency can't be claimed for it).
        """
        broker_results = await self.search_broker.search(query, language=language)

        if policy == "fresh":
            broker_results = self._sort_by_freshness(broker_results)

        to_enrich = broker_results[:WEB_SEARCH_ENRICH_TOP_N]

        # fetch_safe() is a synchronous, blocking call (real HTTP request,
        # up to its own 10s timeout) - run each in a thread, concurrently,
        # so this doesn't block the event loop for every other request this
        # worker is serving, and so N sources cost ~one fetch's worth of
        # wall-clock time instead of N times that.
        fetched_pages = await asyncio.gather(
            *[asyncio.to_thread(self.proxy_sandbox.fetch_safe, item["url"]) for item in to_enrich],
            return_exceptions=True
        )

        sources = []
        for item, fetched in zip(to_enrich, fetched_pages):
            if isinstance(fetched, Exception) or fetched.get("error"):
                # Fetch failed for this one source (blocked, timed out,
                # non-HTML, etc.) - fall back to just the search snippet
                # rather than dropping the source entirely.
                text = item.get("snippet", "")
                title = item.get("title", "")
            else:
                text = fetched.get("text_content", "")[:WEB_SEARCH_SOURCE_TEXT_CAP]
                title = item.get("title") or fetched.get("title", "")

            sources.append({
                "url": item["url"],
                "title": title,
                "domain": item.get("domain", ""),
                "published_at": item.get("published_at"),
                "dated": bool(item.get("published_at")),
                "retrieved_at": datetime.utcnow().isoformat(),
                "source_type": "search_result",
                "text": text,
                "search_rank": item.get("rank")
            })

        summary = (
            f"{len(sources)} Quelle(n) gefunden für '{query}'." if sources
            else f"Keine Ergebnisse für '{query}' gefunden (Suche nicht verfügbar oder keine Treffer)."
        )
        undated_count = sum(1 for s in sources if not s["dated"])
        if policy == "fresh" and undated_count:
            summary += (
                f" Hinweis: {undated_count} von {len(sources)} Quelle(n) haben kein bekanntes "
                "Veröffentlichungsdatum - nicht als Beleg für aktuelle Ereignisse werten."
            )

        return {
            "query": query,
            "type": "web",
            "sources": sources,
            "summary": summary
        }

    def _sort_by_freshness(self, results: List[Dict]) -> List[Dict]:
        """
        Dated entries first (most recent first), undated entries after in
        their original relative order - never drops undated results, just
        deprioritizes them, since "no known date" isn't the same as "not
        relevant".
        """
        def parse_date(item):
            raw = item.get("published_at")
            if not raw:
                return None
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        dated = [(parse_date(item), item) for item in results]
        with_date = [d for d in dated if d[0] is not None]
        without_date = [d[1] for d in dated if d[0] is None]
        with_date.sort(key=lambda d: d[0], reverse=True)
        return [d[1] for d in with_date] + without_date

    async def _execute_weather(self, params: Dict[str, Any]) -> Dict:
        """Führt Wetter-Abfrage aus."""
        from services.web_search_service import execute_weather_tool
        return await execute_weather_tool(params)
    
    def _get_user_location(self, user_id: int) -> Optional[Dict]:
        """Short-lived-session wrapper around location_service.get_user_location (issue #13 item 6)."""
        db = SessionLocal()
        try:
            return self.location_service.get_user_location(db, user_id)
        finally:
            db.close()

    async def _execute_location(self, user_id: int) -> Dict:
        """
        Returns the user's already-consented stored location (see
        PrivacySettings.jsx / location_router.py) - never a live IP lookup
        here, since a backend tool call has no access to the original
        end-user request's IP anyway (calling get_location_from_ip(None)
        would just resolve this server's own IP, not the user's).
        """
        location = self._get_user_location(user_id)
        if not location:
            return {
                "error": "Kein Standort hinterlegt",
                "message": "Der Nutzer hat der Standort-Erkennung noch nicht zugestimmt (Einstellungen -> Datenschutz)."
            }

        return {
            "city": location.get("city", "Unknown"),
            "region": location.get("region", "Unknown"),
            "country": location.get("country", "Unknown"),
            "timezone": location.get("timezone", "UTC")
        }
    
    async def _execute_wikipedia(self, params: Dict[str, Any]) -> Dict:
        """Führt Wikipedia-Suche aus"""
        query = params.get("query")
        language = params.get("language", "de")
        
        result = await self.web_search.search_wikipedia(query, language)

        return {
            "query": query,
            "summary": result.get("extract", "Kein Ergebnis gefunden"),
            "url": result.get("url", ""),
            "title": result.get("title", query)
        }

    async def _execute_delegate_research(self, params: Dict[str, Any]) -> Dict:
        """
        Spins up a ResearchAgent sub-instance and runs it to completion for
        the given task, returning just its final answer - same idea as
        base_agent.py's delegate_research tool for the Agent Hub, wired into
        the normal chat's tool-calling loop too (multi-agent orchestration).
        Shared with base_agent.py via run_delegated_research() so the
        model/step-budget/prompt tuning lives in one place.
        """
        from services.agents.research_agent import run_delegated_research
        return await run_delegated_research(params.get("task", ""))

    async def _execute_current_time(self, params: Dict[str, Any]) -> Dict:
        """Gibt aktuelle Zeit zurück"""
        from datetime import datetime
        import pytz
        
        timezone = params.get("timezone", "Europe/Berlin")
        format_type = params.get("format", "full")
        
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            
            result = {
                "timestamp": now.isoformat(),
                "timezone": timezone
            }
            
            if format_type == "date":
                result["formatted"] = now.strftime("%d.%m.%Y")
            elif format_type == "time":
                result["formatted"] = now.strftime("%H:%M:%S")
            else:
                result["formatted"] = now.strftime("%A, %d. %B %Y, %H:%M:%S Uhr")
                result["date"] = now.strftime("%d.%m.%Y")
                result["time"] = now.strftime("%H:%M:%S")
                result["weekday"] = now.strftime("%A")
            
            return result
            
        except pytz.UnknownTimeZoneError:
            return {
                "error": f"Unknown timezone: {timezone}",
                "available_timezones": pytz.common_timezones[:10]
            }
    
    def _format_search_result(self, result: Dict) -> str:
        """Formatiert Suchergebnis für LLM"""
        parts = []
        
        if result.get("abstract"):
            parts.append(f"**Zusammenfassung**: {result['abstract']}")
        
        if result.get("answer"):
            parts.append(f"**Antwort**: {result['answer']}")
        
        if result.get("definition"):
            parts.append(f"**Definition**: {result['definition']}")
        
        if not parts:
            parts.append("Keine detaillierten Informationen gefunden.")
        
        return "\n\n".join(parts)
    
    def _validate_parameters(
        self,
        tool_call: ToolCall,
        tool_def: ToolDefinition
    ) -> Optional[str]:
        """
        Validiert Tool-Parameter
        
        Returns:
            Error message oder None
        """
        # Prüfe erforderliche Parameter
        for param in tool_def.parameters:
            if param.required and param.name not in tool_call.parameters:
                return f"Missing required parameter: {param.name}"
        
        # Prüfe Parameter-Typen
        for param_name, param_value in tool_call.parameters.items():
            # Finde Parameter-Definition
            param_def = next(
                (p for p in tool_def.parameters if p.name == param_name),
                None
            )
            
            if not param_def:
                # Unknown parameter - reject by default (issue #9): no tool
                # currently needs extensible parameters, and accepting
                # undeclared fields weakens the tool boundary as new tools
                # get added. A tool that genuinely needs this should get an
                # explicit opt-in on its ToolDefinition, not a silent global
                # allowance.
                return f"Unknown parameter: {param_name}"
            
            # Type check (basic)
            expected_type = param_def.type
            if expected_type == "string" and not isinstance(param_value, str):
                return f"Parameter {param_name} must be a string"
            elif expected_type == "number" and not isinstance(param_value, (int, float)):
                return f"Parameter {param_name} must be a number"
            elif expected_type == "boolean" and not isinstance(param_value, bool):
                return f"Parameter {param_name} must be a boolean"
            
            # Enum check
            if param_def.enum and param_value not in param_def.enum:
                return f"Parameter {param_name} must be one of: {param_def.enum}"
        
        return None
    
    async def _check_user_consent(self, user_id: int, tool_def: ToolDefinition) -> bool:
        """
        Prüft ob User Consent für Tool gegeben hat
        """
        # web_search/wikipedia_search have a real, already-shipped consent
        # flag (user_privacy_settings.allow_web_search / PrivacySettings.jsx's
        # "Web-Suche erlauben" toggle) - checked before the blanket
        # privacy_level shortcut below since both tools are "low" but should
        # still respect an explicit opt-out.
        if tool_def.name in ("web_search", "wikipedia_search", "delegate_research"):
            return self._check_web_search_consent(user_id)

        # workspace_* tools need their own dedicated opt-in
        # (user_preferences.workspace_agent_enabled) - unlike web_search this
        # defaults to False (opt-in, not opt-out): letting a model read/
        # propose changes to a user's own files is a bigger step than a
        # public web lookup, so silence should mean "off" here.
        if tool_def.name in WORKSPACE_AGENT_TOOLS:
            return self._check_workspace_agent_consent(user_id)

        # detect_location has a real, already-shipped consent mechanism
        # (user_location_preferences / PrivacySettings.jsx / location_router.py)
        # - just check whether this user has actually granted it, instead of
        # a blanket deny. No generic "user_tool_consents" table exists for
        # any other tool, so everything else still falls through to the
        # honest "not implemented" denial below.
        if tool_def.name == "detect_location":
            return self._get_user_location(user_id) is not None

        # Für jetzt: Erlaube alle übrigen Tools mit niedrigem Privacy-Level
        if tool_def.privacy_level == "low":
            return True

        # Mittlere und hohe Privacy-Levels ohne eigenen Consent-Mechanismus
        logger.warning(f"Consent check not fully implemented - denying {tool_def.name}")
        return False

    def _check_web_search_consent(self, user_id: int) -> bool:
        """
        Checks user_privacy_settings.allow_web_search via its own short-lived
        session (issue #13 item 6) rather than a caller-supplied one whose
        lifetime might span an entire multi-minute SSE stream. Defaults to
        allowed (matches the column's own DEFAULT TRUE) when there's no
        settings row yet, so a user who's never opened Privacy Settings
        isn't silently blocked - only an explicit opt-out denies.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT allow_web_search FROM user_privacy_settings WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).first()
            return True if row is None else bool(row[0])
        finally:
            db.close()

    def _check_workspace_agent_consent(self, user_id: int) -> bool:
        """
        Checks user_preferences.workspace_agent_enabled via its own
        short-lived session (issue #13 item 6). Opt-in: defaults to False
        when there's no row yet - opposite default direction from
        _check_web_search_consent, deliberately, since this gates the model
        reading/proposing changes to the user's own files.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT workspace_agent_enabled FROM user_preferences WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).first()
            return False if row is None else bool(row[0])
        finally:
            db.close()

    def _error_result(
        self,
        tool_name: str,
        error_msg: str,
        consent_required: bool = False,
        result: Optional[Dict] = None,
        execution_time_ms: int = 0,
    ) -> Dict[str, Any]:
        """
        Erstellt Fehler-Result. Same top-level key set as the success shape
        in execute() (issue #14: "Model tool-history receives a consistent
        status shape") - result/execution_time_ms default to None/0 for
        failures that never actually ran a tool (unknown tool, consent
        denied, bad parameters), and are populated for failures normalized
        from a genuinely-executed tool's own error dict.
        """
        return {
            "success": False,
            "tool": tool_name,
            "error": error_msg,
            "consent_required": consent_required,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": execution_time_ms,
        }


# Singleton instance
_executor = None

def get_tool_executor() -> ToolExecutor:
    """Get or create ToolExecutor singleton"""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
