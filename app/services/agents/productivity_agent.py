"""
Specialized Productivity & Organization Agent für L.I.A.R.A.
Spezialist für Aufgabenmanagement, Terminplanung, Notizen und 4D Memory Abruf.
"""
from typing import Optional, Dict, Any, List
from services.agents.base_agent import BaseAgent
from services.productivity_tools import execute_productivity_tool


PRODUCTIVITY_AGENT_SYSTEM_PROMPT = """Du bist Liaras spezialisierter autonomer Produktivitäts- und Organisations-Agent.
Deine Aufgabe ist es, Notizen, Termine, Aufgaben und Erinnerungen des Nutzers intelligent, präzise und strukturiert zu verwalten.

### Verhaltensregeln:
1. **Präzise Erfassung**:
   - Extrahiere bei Terminen Startzeit, Endzeit, Titel und Ort präzise.
   - Setze bei Aufgaben die passende Priorität ('low', 'medium', 'high') und eventuelle Fälligkeitsdaten.
   - Strukturiere Notizen mit sinnvollen Titeln, Kategorien und Tags.
   - Speichere persönliche Fakten, Präferenzen und Wissenselemente mit `store_memory` im 4D-Gedächtnis.
2. **Überprüfung & Kontext**:
   - Nutze `search_memory` oder `list_*`-Tools, wenn nach bestehenden Daten gefragt wird oder Doppelungen vermieden werden sollen.
3. **Klare Bestätigung**:
   - Beantworte Anfragen in deiner `<final_answer>` mit einer übersichtlichen, freundlichen Zusammenfassung der durchgeführten Aktionen.
"""


class ProductivityAgent(BaseAgent):
    """
    Spezialisierter Agent für Aufgaben, Kalender, Notizen und Gedächtnis.
    """

    def __init__(
        self,
        user_id: int = 1,
        model: str = "llama3.2:3b",
        max_steps: int = 10
    ):
        super().__init__(
            name="ProductivityAgent",
            role_description="Spezialist für Aufgabenverwaltung, Notizen, Terminplanung und 4D-Gedächtnis.",
            system_prompt=PRODUCTIVITY_AGENT_SYSTEM_PROMPT,
            model=model,
            max_steps=max_steps
        )
        self.user_id = user_id
        self._register_productivity_tools()

    def _register_productivity_tools(self):
        # 1. create_note
        self.register_tool(
            name="create_note",
            description="Erstellt eine neue Notiz.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titel der Notiz"},
                    "content": {"type": "string", "description": "Inhalt der Notiz"},
                    "category": {"type": "string", "description": "Kategorie (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags (optional)"}
                },
                "required": ["title", "content"]
            },
            handler=self._tool_create_note
        )

        # 2. list_notes
        self.register_tool(
            name="list_notes",
            description="Listet Notizen auf oder durchsucht sie.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Kategorie-Filter"},
                    "tag": {"type": "string", "description": "Tag-Filter"},
                    "search": {"type": "string", "description": "Suchbegriff"},
                    "limit": {"type": "number", "description": "Max Anzahl (Standard: 20)"}
                }
            },
            handler=self._tool_list_notes
        )

        # 3. create_task
        self.register_tool(
            name="create_task",
            description="Erstellt eine neue Aufgabe (To-Do).",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titel der Aufgabe"},
                    "description": {"type": "string", "description": "Beschreibung (optional)"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Priorität"},
                    "due_date": {"type": "string", "description": "Fälligkeitsdatum"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"}
                },
                "required": ["title"]
            },
            handler=self._tool_create_task
        )

        # 4. list_tasks
        self.register_tool(
            name="list_tasks",
            description="Listet Aufgaben auf oder filtert sie.",
            parameters={
                "type": "object",
                "properties": {
                    "completed": {"type": "boolean", "description": "Erledigt-Filter"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Priorität"},
                    "tag": {"type": "string", "description": "Tag"},
                    "search": {"type": "string", "description": "Suche"},
                    "limit": {"type": "number", "description": "Max Anzahl"}
                }
            },
            handler=self._tool_list_tasks
        )

        # 5. update_task_status
        self.register_tool(
            name="update_task_status",
            description="Setzt den Status einer Aufgabe auf erledigt oder offen.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "number", "description": "Aufgaben-ID"},
                    "completed": {"type": "boolean", "description": "true=erledigt, false=offen"}
                },
                "required": ["task_id", "completed"]
            },
            handler=self._tool_update_task_status
        )

        # 6. create_calendar_event
        self.register_tool(
            name="create_calendar_event",
            description="Erstellt einen Kalendereintrag.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titel"},
                    "start_time": {"type": "string", "description": "Startzeit"},
                    "end_time": {"type": "string", "description": "Endzeit"},
                    "description": {"type": "string", "description": "Beschreibung"},
                    "location": {"type": "string", "description": "Ort"},
                    "event_type": {"type": "string", "enum": ["meeting", "private", "other"]},
                    "all_day": {"type": "boolean"}
                },
                "required": ["title", "start_time", "end_time"]
            },
            handler=self._tool_create_calendar_event
        )

        # 7. list_calendar_events
        self.register_tool(
            name="list_calendar_events",
            description="Listet Termine in einem Zeitraum auf.",
            parameters={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Von Datum"},
                    "end_date": {"type": "string", "description": "Bis Datum"},
                    "search": {"type": "string", "description": "Suche"},
                    "limit": {"type": "number", "description": "Max Anzahl"}
                }
            },
            handler=self._tool_list_calendar_events
        )

        # 8. search_memory
        self.register_tool(
            name="search_memory",
            description="Durchsucht das 4D-Gedächtnis semantisch.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff"},
                    "limit": {"type": "number", "description": "Max Anzahl"}
                },
                "required": ["query"]
            },
            handler=self._tool_search_memory
        )

        # 9. store_memory
        self.register_tool(
            name="store_memory",
            description="Speichert ein wichtiges Faktum, eine Vorliebe oder eine persönliche Information dauerhaft im 4D-Gedächtnis.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Der zu merkende Inhalt / Fakt"},
                    "category": {"type": "string", "description": "Kategorie (z.B. fact, preference, contact)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags (optional)"}
                },
                "required": ["content"]
            },
            handler=self._tool_store_memory
        )

    async def _tool_create_note(self, title: str, content: str, category: Optional[str] = None, tags: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("create_note", self.user_id, {"title": title, "content": content, "category": category, "tags": tags})

    async def _tool_list_notes(self, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("list_notes", self.user_id, kwargs)

    async def _tool_create_task(self, title: str, description: Optional[str] = None, priority: str = "medium", due_date: Optional[str] = None, tags: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("create_task", self.user_id, {"title": title, "description": description, "priority": priority, "due_date": due_date, "tags": tags})

    async def _tool_list_tasks(self, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("list_tasks", self.user_id, kwargs)

    async def _tool_update_task_status(self, task_id: int, completed: bool, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("update_task_status", self.user_id, {"task_id": task_id, "completed": completed})

    async def _tool_create_calendar_event(self, title: str, start_time: str, end_time: str, description: Optional[str] = None, location: Optional[str] = None, event_type: str = "meeting", all_day: bool = False, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("create_calendar_event", self.user_id, {"title": title, "start_time": start_time, "end_time": end_time, "description": description, "location": location, "event_type": event_type, "all_day": all_day})

    async def _tool_list_calendar_events(self, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("list_calendar_events", self.user_id, kwargs)

    async def _tool_search_memory(self, query: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("search_memory", self.user_id, {"query": query, "limit": limit})

    async def _tool_store_memory(self, content: str, category: str = "fact", tags: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        return execute_productivity_tool("store_memory", self.user_id, {"content": content, "category": category, "tags": tags})

