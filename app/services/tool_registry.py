"""
🔧 Tool Registry für automatisches Tool-Calling
Zentrale Verwaltung verfügbarer Tools für Liara
"""
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class ToolCategory(str, Enum):
    """Tool-Kategorien"""
    INFORMATION = "information"  # Web-Suche, Wikipedia
    LOCATION = "location"        # Standort, Wetter
    SYSTEM = "system"            # Systemabfragen
    UTILITY = "utility"          # Hilfsfunktionen
    WORKSPACE = "workspace"      # Workspace-Dateien lesen/vorschlagen
    PRODUCTIVITY = "productivity"  # Notizen, Tasks, Kalender
    MEMORY = "memory"            # 4D Memory & Wissenssuche


# Single-shot tools hidden from the normal chat's own tool exposure (both the
# native tool-calling path and the text-tag prompt fallback for models
# without native support) in favor of steering toward delegate_research/
# delegate_code_task, which run the full multi-step agent loop those tasks
# usually need. Not unregistered - other callers (Agent Hub profiles, tests)
# still see the full set; this only trims what get_tools_for_ollama()/
# get_tool_descriptions_for_llm() hand to chat specifically.
CHAT_DELEGATION_EXCLUDED_TOOLS = ["web_search", "workspace_propose_change"]


@dataclass
class ToolParameter:
    """Tool-Parameter Definition"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Tool-Definition für Ollama"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    function: Callable
    requires_consent: bool = False
    privacy_level: str = "low"  # low, medium, high


class ToolRegistry:
    """Zentrale Registry für verfügbare Tools"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Registriere Standard-Tools"""
        
        # 🌍 Web Search & Page Fetch Tools (modularized in web_search_service.py)
        from services.web_search_service import register_web_tools
        register_web_tools(self)

        # 🐙 GitHub Research Tools (modularized in github_service.py)
        from services.github_service import register_github_tools
        register_github_tools(self)

        # 🩺 System Health & Metrics Tools (modularized in system_health_service.py)
        from services.system_health_service import register_system_health_tools
        register_system_health_tools(self)

        # 🌤️ Weather Tool
        self.register_tool(ToolDefinition(
            name="get_weather",
            description="Ruft aktuelle Wetterdaten UND eine mehrtägige Vorhersage für einen Ort ab (Quelle: Open-Meteo)",
            category=ToolCategory.LOCATION,
            parameters=[
                ToolParameter(
                    name="city",
                    type="string",
                    description="Stadt oder Ort",
                    required=True
                ),
                ToolParameter(
                    name="country",
                    type="string",
                    description="Land (optional)",
                    required=False
                ),
                ToolParameter(
                    name="days",
                    type="number",
                    description="Anzahl Vorhersage-Tage (1-7), Standard 3",
                    required=False,
                    default=3
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Sprache der Wettervorhersage",
                    required=False,
                    default="de",
                    enum=["de", "en"]
                )
            ],
            function=self._weather_stub,
            # Only ever operates on a city name the model already pulled from
            # the user's own message - never the user's real location/IP.
            # Same public-lookup privacy profile as web_search/wikipedia_search
            # (both "low", no consent gate) - "medium" was a miscategorization,
            # not a deliberate protection (see live-tested "Fix tools" plan).
            requires_consent=False,
            privacy_level="low"
        ))
        
        # 📍 Location Detection Tool
        self.register_tool(ToolDefinition(
            name="detect_location",
            description="Ermittelt den aktuellen Standort des Benutzers (Stadt/Region) basierend auf IP",
            category=ToolCategory.LOCATION,
            parameters=[],
            function=self._location_stub,
            requires_consent=True,
            privacy_level="high"
        ))
        
        # 📚 Wikipedia Search
        self.register_tool(ToolDefinition(
            name="wikipedia_search",
            description="Sucht nach Informationen in Wikipedia",
            category=ToolCategory.INFORMATION,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Suchbegriff",
                    required=True
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Wikipedia-Sprache",
                    required=False,
                    default="de",
                    enum=["de", "en", "fr", "es"]
                )
            ],
            function=self._wikipedia_stub,
            # Same allow_web_search gate as web_search - see that tool's comment.
            requires_consent=True,
            privacy_level="low"
        ))

        # 📋 Task Checklist (multi-step plan display, NOT the persistent
        # /tasks feature) - a real callable tool instead of hoping the model
        # spontaneously emits a <tasks> text tag on its own (see
        # build_task_list_instructions in prompt_builder.py): confirmed live
        # that several models either ignored that tag convention entirely or
        # confused it with the persistent create_task tool. Calling this
        # tool is far more reliable since native tool-calling is a stronger,
        # explicitly-trained affordance than "notice this instruction buried
        # in the system prompt and remember to emit these exact tags".
        self.register_tool(ToolDefinition(
            name="update_task_checklist",
            description=(
                "Zeigt eine abhakbare Schritt-Checkliste direkt in dieser Chat-Antwort an - NICHT "
                "die persistente Tasks-Verwaltung unter /tasks (dafür ist create_task da), sondern "
                "eine Plan-Übersicht für eine mehrschrittige Anleitung/Antwort in diesem Chat. Rufe "
                "das Tool mit der VOLLSTÄNDIGEN, aktuellen Liste auf (auch bereits erledigte Schritte "
                "als '[x]'), keine Teil-Updates - bei einer Statusänderung das Tool erneut mit der "
                "kompletten aktualisierten Liste aufrufen. Nur für wirklich mehrschrittige Anfragen, "
                "nicht für kurze/einfache Antworten."
            ),
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="markdown",
                    type="string",
                    description=(
                        "Eine Aufgabe pro Zeile im Format '- [ ] Label' (offen) oder "
                        "'- [x] Label' (erledigt), z.B.:\n- [ ] Erster Schritt\n"
                        "- [x] Zweiter Schritt\n- [ ] Dritter Schritt"
                    ),
                    required=True
                )
            ],
            function=self._task_checklist_stub,
            requires_consent=False,
            privacy_level="low"
        ))

        # 🔍 Delegate to the specialized Research Agent (multi-agent
        # orchestration) - a multi-step research sub-task (several
        # searches, cross-referencing sources, following links) that a
        # single web_search call can't do justice to. Runs a full
        # ResearchAgent instance (SearXNG + Wikipedia + GitHub tools, own
        # cloud model) and returns just its final answer - same idea as
        # base_agent.py's delegate_research tool for the Agent Hub, wired
        # into the normal chat's tool system too.
        self.register_tool(ToolDefinition(
            name="delegate_research",
            description=(
                "Delegiert eine mehrstufige Recherche-Aufgabe an den spezialisierten Research "
                "Agent (führt selbstständig mehrere Websuchen/Wikipedia/GitHub-Abfragen durch, "
                "gleicht Quellen ab und liefert eine fundierte Zusammenfassung mit "
                "Quellenangaben). Nutze dies für komplexere Recherchefragen statt eines "
                "einzelnen web_search-Aufrufs, wenn mehrere Suchschritte oder ein "
                "Quellenabgleich nötig sind."
            ),
            category=ToolCategory.INFORMATION,
            parameters=[
                ToolParameter(
                    name="task",
                    type="string",
                    description="Die konkrete Recherche-Aufgabe/Frage für den Research Agent",
                    required=True
                )
            ],
            function=self._delegate_research_stub,
            # Same allow_web_search gate as web_search/wikipedia_search -
            # this tool does real web searches under the hood too.
            requires_consent=True,
            privacy_level="low"
        ))

        # 💻 Delegate a multi-step code task to the specialized Code Agent -
        # same idea as delegate_research above, but for code creation/edits.
        # Runs a full CodeAgent instance (view_file/grep_search/replace_chunk/
        # create_file/delete_file, own model) in propose_only mode: every
        # write becomes a pending Workspace proposal, never a direct write -
        # same review-then-accept gate workspace_propose_change already uses.
        self.register_tool(ToolDefinition(
            name="delegate_code_task",
            description=(
                "Delegiert eine mehrstufige Code-Aufgabe (neue Datei, Refactoring, Bugfix über "
                "mehrere Schritte) an den spezialisierten Code Agent (analysiert den Workspace "
                "selbstständig mit view_file/grep_search, ändert dann gezielt Code). Ändert "
                "NICHTS direkt - jede Änderung landet als Vorschlag im Workspace-Tab, den der "
                "Nutzer noch bestätigen muss. Braucht eine aktive Workspace-Session."
            ),
            category=ToolCategory.WORKSPACE,
            parameters=[
                ToolParameter(
                    name="task",
                    type="string",
                    description="Die konkrete Code-Aufgabe für den Code Agent",
                    required=True
                )
            ],
            function=self._delegate_code_task_stub,
            # Same opt-in gate as workspace_propose_change - this operates on
            # the user's own workspace files, defaults to off.
            requires_consent=True,
            privacy_level="low"
        ))

        # 🕐 Current Time/Date
        self.register_tool(ToolDefinition(
            name="get_current_time",
            description="Gibt aktuelles Datum und Uhrzeit zurück",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="timezone",
                    type="string",
                    description="Zeitzone (optional)",
                    required=False,
                    default="Europe/Berlin"
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Ausgabeformat",
                    required=False,
                    default="full",
                    enum=["full", "date", "time"]
                )
            ],
            function=self._time_stub,
            requires_consent=False,
            privacy_level="low"
        ))

        # 🗂️ Workspace: inspect + propose (Agent-Vorbereitung v1). Reading
        # and proposing are both gated behind the same opt-in consent
        # (user_preferences.workspace_agent_enabled, default False) - see
        # ToolExecutor._check_workspace_agent_consent. privacy_level stays
        # "low" so get_tools_for_ollama() actually offers these to the model;
        # the real gate is requires_consent, exactly like web_search.
        self.register_tool(ToolDefinition(
            name="workspace_list_files",
            description=(
                "Listet Dateien und Ordner im Workspace der aktuellen Chat-Session auf "
                "(Pfad, Größe, Herkunft) - inklusive Unterordner. Nur möglich, wenn der "
                "Nutzer LIARA Workspace-Zugriff erlaubt hat."
            ),
            category=ToolCategory.WORKSPACE,
            parameters=[],
            function=self._workspace_list_stub,
            requires_consent=True,
            privacy_level="low"
        ))

        self.register_tool(ToolDefinition(
            name="workspace_read_file",
            description="Liest den Inhalt einer Datei im Workspace der aktuellen Chat-Session.",
            category=ToolCategory.WORKSPACE,
            parameters=[
                ToolParameter(
                    name="filename",
                    type="string",
                    description="Relativer Pfad der zu lesenden Datei im Workspace, z.B. 'analyse.py' oder 'utils/helper.py'",
                    required=True
                )
            ],
            function=self._workspace_read_stub,
            requires_consent=True,
            privacy_level="low"
        ))

        self.register_tool(ToolDefinition(
            name="workspace_propose_change",
            description=(
                "Schlägt eine Änderung an einer Workspace-Datei vor (anlegen, "
                "überschreiben oder löschen). Ändert NICHTS direkt - der Nutzer "
                "sieht den Vorschlag mit Diff im Workspace-Tab und muss ihn "
                "explizit annehmen, bevor er wirksam wird."
            ),
            category=ToolCategory.WORKSPACE,
            parameters=[
                ToolParameter(
                    name="filename",
                    type="string",
                    description="Relativer Pfad der betroffenen Datei im Workspace, z.B. 'analyse.py' oder 'utils/helper.py' (Zwischenordner werden bei Annahme automatisch angelegt)",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    description="Art der vorgeschlagenen Änderung",
                    required=True,
                    enum=["create", "update", "delete"]
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Neuer Dateiinhalt (erforderlich bei create/update, entfällt bei delete)",
                    required=False
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Kurze Begründung, warum diese Änderung vorgeschlagen wird",
                    required=True
                )
            ],
            function=self._workspace_propose_stub,
            requires_consent=True,
            privacy_level="low"
        ))

        self.register_tool(ToolDefinition(
            name="workspace_propose_dependency_change",
            description=(
                "Schlägt vor, ein Python-Paket im venv dieser Session zu "
                "installieren oder zu entfernen. Ändert NICHTS direkt - der "
                "Nutzer sieht den Vorschlag im Workspace-Tab und muss ihn "
                "explizit annehmen, bevor das Paket tatsächlich installiert/"
                "entfernt wird. Nur für Pakete aus PyPI per Name/Version, "
                "keine URLs oder lokalen Pfade."
            ),
            category=ToolCategory.WORKSPACE,
            parameters=[
                ToolParameter(
                    name="package",
                    type="string",
                    description="Paket-Angabe: nur 'name', 'name==version' oder 'name>=version' - keine URLs, keine Flags",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    description="Installieren oder Entfernen",
                    required=True,
                    enum=["install", "remove"]
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Kurze Begründung, warum dieses Paket gebraucht/entfernt wird",
                    required=True
                )
            ],
            function=self._workspace_propose_dependency_stub,
            requires_consent=True,
            privacy_level="low"
        ))

        # 📅 Notes, Tasks, Calendar, and Memory Tools (modularized in productivity_tools.py)
        from services.productivity_tools import register_productivity_tools
        register_productivity_tools(self)

    def register_tool(self, tool: ToolDefinition):
        """Registriere neues Tool"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Hole Tool-Definition"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """Liste alle Tools (optional gefiltert nach Kategorie)"""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())
    
    def get_tool_descriptions_for_llm(self, exclude: Optional[List[str]] = None) -> str:
        """Generiere Tool-Beschreibungen für Ollama System-Prompt"""
        lines = ["Du hast Zugriff auf folgende Tools:\n"]
        exclude_set = set(exclude or [])

        for tool in self._tools.values():
            if tool.name in exclude_set:
                continue
            params_str = ", ".join([
                f"{p.name}: {p.type}"
                + (f" [{'|'.join(p.enum)}]" if p.enum else "")
                + ("" if p.required else " (optional)")
                for p in tool.parameters
            ])

            lines.append(f"• {tool.name}({params_str})")
            lines.append(f"  → {tool.description}")
            if tool.requires_consent:
                lines.append(f"  ⚠️ Erfordert User-Zustimmung")
            lines.append("")
        
        lines.append("Um ein Tool zu verwenden, antworte mit:")
        lines.append("<tool_call>")
        lines.append("{")
        lines.append('  "tool": "tool_name",')
        lines.append('  "parameters": { "param": "value" }')
        lines.append("}")
        lines.append("</tool_call>")
        
        return "\n".join(lines)
    
    def get_tools_for_ollama(self, exclude: Optional[List[str]] = None) -> List[Dict]:
        """
        Serializes tools into Ollama's native function-calling format
        (`{"type": "function", "function": {...}}`, JSON-Schema parameters) -
        for the real tool_calls loop in chat_streaming.py, as opposed to
        get_tool_descriptions_for_llm()'s prompt text that teaches chat.py's
        model a <tool_call> tag to emit and tool_parser.py to regex out.

        Restricted to privacy_level == "low": get_weather/detect_location
        require consent, and ToolExecutor._check_user_consent is currently a
        stub that unconditionally denies anything above "low" - exposing
        them as callable tools here would just mean the model "calls" them
        and always gets a consent-denied error back. Filtering by the same
        field ToolExecutor itself checks means this list widens on its own,
        with no change needed here, once real per-user consent exists.

        `exclude` lets a caller hide specific tools without unregistering
        them globally - used by the normal chat to hide the single-shot
        web_search/workspace_propose_change in favor of steering the model
        toward delegate_research/delegate_code_task instead, while other
        callers (tests, any future non-chat caller) still see the full set.
        """
        exclude_set = set(exclude or [])
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            p.name: {
                                "type": p.type,
                                "description": p.description,
                                **({"enum": p.enum} if p.enum else {}),
                                **({"default": p.default} if p.default is not None else {})
                            }
                            for p in tool.parameters
                        },
                        "required": [p.name for p in tool.parameters if p.required]
                    }
                }
            }
            for tool in self._tools.values()
            if tool.privacy_level == "low" and tool.name not in exclude_set
        ]

    def get_tool_schema(self, name: str) -> Optional[Dict]:
        """Hole Tool-Schema als JSON (für API-Docs)"""
        tool = self.get_tool(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description,
                        **({"enum": p.enum} if p.enum else {}),
                        **({"default": p.default} if p.default is not None else {})
                    }
                    for p in tool.parameters
                },
                "required": [p.name for p in tool.parameters if p.required]
            },
            "requires_consent": tool.requires_consent,
            "privacy_level": tool.privacy_level
        }
    
    # Stub-Funktionen (werden später durch echte Services ersetzt)
    async def _weather_stub(self, **kwargs):
        """Placeholder für Weather"""
        return {"error": "Not implemented", "tool": "get_weather"}
    
    async def _location_stub(self, **kwargs):
        """Placeholder für Location"""
        return {"error": "Not implemented", "tool": "detect_location"}
    
    async def _wikipedia_stub(self, **kwargs):
        """Placeholder für Wikipedia"""
        return {"error": "Not implemented", "tool": "wikipedia_search"}
    
    async def _workspace_list_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "workspace_list_files"}

    async def _workspace_read_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "workspace_read_file"}

    async def _workspace_propose_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "workspace_propose_change"}

    async def _workspace_propose_dependency_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "workspace_propose_dependency_change"}

    async def _delegate_research_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "delegate_research"}

    async def _delegate_code_task_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "delegate_code_task"}

    async def _task_checklist_stub(self, **kwargs):
        """Placeholder - routed directly in ToolExecutor._execute_tool instead."""
        return {"error": "Not implemented", "tool": "update_task_checklist"}

    async def _time_stub(self, **kwargs):
        """Placeholder für Time"""
        from datetime import datetime
        import pytz
        
        tz = pytz.timezone(kwargs.get("timezone", "Europe/Berlin"))
        now = datetime.now(tz)
        
        format_type = kwargs.get("format", "full")
        
        if format_type == "date":
            return {"date": now.strftime("%d.%m.%Y")}
        elif format_type == "time":
            return {"time": now.strftime("%H:%M:%S")}
        else:
            return {
                "datetime": now.isoformat(),
                "formatted": now.strftime("%A, %d. %B %Y, %H:%M:%S Uhr"),
                "timezone": str(tz)
            }


# Singleton instance
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get or create ToolRegistry singleton"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
