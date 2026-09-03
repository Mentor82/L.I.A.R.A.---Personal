"""
Productivity Tools for L.I.A.R.A.
=================================
Modular definitions and execution handlers for Notes, Tasks, Calendar Events,
and 4D Memory search.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.database import SessionLocal
from api.models.base_models import Note, CalendarEvent, Task

try:
    from services.memory_integration import store_in_4d_memory, get_relevant_context, invalidate_message
except ImportError:
    def store_in_4d_memory(*args, **kwargs):
        pass

    def get_relevant_context(*args, **kwargs):
        return []

    def invalidate_message(*args, **kwargs):
        return False

logger = logging.getLogger(__name__)

PRODUCTIVITY_TOOL_NAMES = (
    "create_note", "list_notes",
    "create_task", "list_tasks", "update_task_status",
    "create_calendar_event", "list_calendar_events",
    "search_memory", "store_memory", "correct_memory"
)


def register_productivity_tools(registry) -> None:
    """Registers Notes, Tasks, Calendar, and Memory tools into ToolRegistry."""
    from services.tool_registry import ToolDefinition, ToolParameter, ToolCategory

    registry.register_tool(ToolDefinition(
        name="create_note",
        description="Erstellt eine neue persönliche Notiz und speichert sie im 4D-Gedächtnis.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="title", type="string", description="Titel der Notiz", required=True),
            ToolParameter(name="content", type="string", description="Inhalt der Notiz", required=True),
            ToolParameter(name="category", type="string", description="Kategorie (optional)", required=False),
            ToolParameter(name="tags", type="array", description="Tags (optional)", required=False),
            ToolParameter(name="parent_id", type="number", description="Parent Note ID (optional)", required=False)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="list_notes",
        description="Durchsucht und listet gespeicherte Notizen des Benutzers auf.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="category", type="string", description="Kategorie-Filter", required=False),
            ToolParameter(name="tag", type="string", description="Tag-Filter", required=False),
            ToolParameter(name="search", type="string", description="Suchbegriff", required=False),
            ToolParameter(name="limit", type="number", description="Max Anzahl (Standard: 20)", required=False, default=20)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="create_task",
        description="Erstellt eine neue Aufgabe (To-Do) mit Priorität und optionalem Fälligkeitsdatum.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="title", type="string", description="Titel der Aufgabe", required=True),
            ToolParameter(name="description", type="string", description="Beschreibung (optional)", required=False),
            ToolParameter(name="priority", type="string", description="Priorität (low, medium, high)", required=False, default="medium", enum=["low", "medium", "high"]),
            ToolParameter(name="due_date", type="string", description="Fälligkeitsdatum", required=False),
            ToolParameter(name="tags", type="array", description="Tags (optional)", required=False)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="list_tasks",
        description="Listet Aufgaben des Benutzers auf, optional gefiltert.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="completed", type="boolean", description="Erledigt-Filter", required=False),
            ToolParameter(name="priority", type="string", description="Prioritäts-Filter", required=False, enum=["low", "medium", "high"]),
            ToolParameter(name="tag", type="string", description="Tag-Filter", required=False),
            ToolParameter(name="search", type="string", description="Suchbegriff", required=False),
            ToolParameter(name="limit", type="number", description="Max Anzahl (Standard: 20)", required=False, default=20)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="update_task_status",
        description="Aktualisiert den Status einer Aufgabe (erledigt / offen).",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="task_id", type="number", description="ID der Aufgabe", required=True),
            ToolParameter(name="completed", type="boolean", description="true für erledigt, false für offen", required=True)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="create_calendar_event",
        description="Erstellt einen neuen Kalendereintrag / Termin.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="title", type="string", description="Titel des Termins", required=True),
            ToolParameter(name="start_time", type="string", description="Startzeit (YYYY-MM-DD HH:MM)", required=True),
            ToolParameter(name="end_time", type="string", description="Endzeit (YYYY-MM-DD HH:MM)", required=True),
            ToolParameter(name="description", type="string", description="Beschreibung (optional)", required=False),
            ToolParameter(name="location", type="string", description="Ort (optional)", required=False),
            ToolParameter(name="event_type", type="string", description="Art des Termins", required=False, default="meeting", enum=["meeting", "private", "other"]),
            ToolParameter(name="all_day", type="boolean", description="Ganztägig", required=False, default=False)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="list_calendar_events",
        description="Ruft Kalendereinträge des Benutzers ab.",
        category=ToolCategory.PRODUCTIVITY,
        parameters=[
            ToolParameter(name="start_date", type="string", description="Termine ab Datum", required=False),
            ToolParameter(name="end_date", type="string", description="Termine bis Datum", required=False),
            ToolParameter(name="search", type="string", description="Suchbegriff", required=False),
            ToolParameter(name="limit", type="number", description="Max Anzahl (Standard: 20)", required=False, default=20)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="search_memory",
        description="Durchsucht das 4D Memory Langzeitgedächtnis semantisch nach früheren Gesprächen, Notizen und Fakten.",
        category=ToolCategory.MEMORY,
        parameters=[
            ToolParameter(name="query", type="string", description="Suchanfrage", required=True),
            ToolParameter(name="limit", type="number", description="Max Anzahl (Standard: 5)", required=False, default=5)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    registry.register_tool(ToolDefinition(
        name="store_memory",
        description="Speichert ein wichtiges Faktum, eine Vorliebe oder eine persönliche Information des Nutzers dauerhaft im 4D-Gedächtnis.",
        category=ToolCategory.MEMORY,
        parameters=[
            ToolParameter(name="content", type="string", description="Der zu merkende Inhalt / Fakt", required=True),
            ToolParameter(name="category", type="string", description="Kategorie (z.B. 'preference', 'fact', 'contact', 'general')", required=False, default="fact"),
            ToolParameter(name="tags", type="array", description="Tags (optional)", required=False)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))

    # Trigger c (memory_verification.py): explizite, bewusst angeforderte
    # Korrektur - höchste Priorität der drei Verifikations-Trigger, im
    # Unterschied zu Trigger b (chat_streaming.py's heuristisch erkannter
    # Nutzer-Widerspruch) hart statt weich, weil hier ein bewusster,
    # eindeutiger Korrektur-Befehl vorliegt statt nur eines Heuristik-Treffers.
    registry.register_tool(ToolDefinition(
        name="correct_memory",
        description=(
            "Korrigiert eine falsche/veraltete Erinnerung im 4D-Gedächtnis, wenn der Nutzer "
            "explizit sagt, dass etwas Gespeichertes falsch war. Sucht die passendste frühere "
            "Erinnerung zur query, markiert sie als widerlegt (CONTRADICTED) und speichert die "
            "korrekte Fassung neu."
        ),
        category=ToolCategory.MEMORY,
        parameters=[
            ToolParameter(name="query", type="string", description="Wonach in der falschen alten Erinnerung gesucht werden soll", required=True),
            ToolParameter(name="correction", type="string", description="Der korrekte, richtige Inhalt", required=True)
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))


async def _stub_fn(**kwargs):
    return {"error": "Not implemented"}


def execute_productivity_tool(
    tool_name: str,
    user_id: int,
    params: Dict[str, Any],
    session_factory=None,
    session_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Executes a productivity tool and returns a result dict, or None if not handled.

    session_id is the originating chat_sessions.id (if any) - not a tool
    parameter the LLM supplies, but injected by the caller from the actual
    request context, the same way user_id already is. Only create_note uses
    it today (see Note.session_id); every other tool ignores it.
    """
    sf = session_factory or SessionLocal
    if tool_name == "create_note":
        return _execute_create_note(user_id, params, sf, session_id)
    elif tool_name == "list_notes":
        return _execute_list_notes(user_id, params, sf)
    elif tool_name == "create_task":
        return _execute_create_task(user_id, params, sf)
    elif tool_name == "list_tasks":
        return _execute_list_tasks(user_id, params, sf)
    elif tool_name == "update_task_status":
        return _execute_update_task_status(user_id, params, sf)
    elif tool_name == "create_calendar_event":
        return _execute_create_calendar_event(user_id, params, sf)
    elif tool_name == "list_calendar_events":
        return _execute_list_calendar_events(user_id, params, sf)
    elif tool_name == "search_memory":
        return _execute_search_memory(user_id, params)
    elif tool_name == "store_memory":
        return _execute_store_memory(user_id, params, sf)
    elif tool_name == "correct_memory":
        return _execute_correct_memory(user_id, params, sf)
    return None


def _execute_create_note(
    user_id: int, params: Dict[str, Any], session_factory, session_id: Optional[int] = None
) -> Dict[str, Any]:
    title = (params.get("title") or "").strip()
    content = (params.get("content") or "").strip()
    if not title:
        return {"error": "Titel der Notiz darf nicht leer sein"}
    category = params.get("category")
    tags = params.get("tags") or []
    parent_id = params.get("parent_id")

    with session_factory() as db:
        if parent_id is not None:
            parent = db.query(Note).filter(Note.id == parent_id, Note.user_id == user_id).first()
            if not parent:
                return {"error": f"Übergeordnete Notiz #{parent_id} wurde nicht gefunden"}

        note = Note(
            user_id=user_id,
            title=title,
            content=content,
            category=category,
            tags=tags,
            parent_id=parent_id,
            session_id=session_id,
            is_pinned=False,
            is_archived=False
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.id

        try:
            store_in_4d_memory(
                db=db,
                user_id=user_id,
                content_type="note",
                content_id=note_id,
                content_text=f"{title}. {content}",
                additional_context={"category": category, "tags": tags}
            )
        except Exception as e:
            logger.warning(f"4D Memory indexing failed for note #{note_id}: {e}")

    return {
        "success": True,
        "note_id": note_id,
        "title": title,
        "category": category,
        "tags": tags,
        "message": f"✅ Notiz \"{title}\" (ID: {note_id}) erfolgreich erstellt."
    }


def _execute_list_notes(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    category = params.get("category")
    tag = params.get("tag")
    search = params.get("search")
    limit = min(max(int(params.get("limit", 20)), 1), 100)

    with session_factory() as db:
        query = db.query(Note).filter(Note.user_id == user_id, Note.is_archived == False)
        if category:
            query = query.filter(Note.category == category)
        if tag:
            query = query.filter(Note.tags.contains([tag]))
        if search:
            search_term = f"%{search}%"
            query = query.filter((Note.title.ilike(search_term)) | (Note.content.ilike(search_term)))

        notes = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).limit(limit).all()
        notes_data = [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
                "category": n.category,
                "tags": n.tags,
                "is_pinned": n.is_pinned,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notes
        ]

    return {
        "count": len(notes_data),
        "notes": notes_data,
        "message": f"{len(notes_data)} Notiz(en) gefunden." if notes_data else "Keine Notizen gefunden."
    }


def _execute_create_task(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    title = (params.get("title") or "").strip()
    if not title:
        return {"error": "Titel der Aufgabe darf nicht leer sein"}
    description = params.get("description")
    priority = params.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    due_date_str = params.get("due_date")
    due_date = None
    if due_date_str:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                due_date = datetime.strptime(due_date_str.split(".")[0].replace("Z", ""), fmt)
                break
            except ValueError:
                pass
        if due_date is None:
            try:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            except Exception:
                pass
    tags = params.get("tags") or []

    with session_factory() as db:
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags,
            completed=False
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        try:
            store_in_4d_memory(
                db=db,
                user_id=user_id,
                content_type="task",
                content_id=task_id,
                content_text=f"{title}. {description or ''}",
                additional_context={"priority": priority, "tags": tags}
            )
        except Exception as e:
            logger.warning(f"4D Memory indexing failed for task #{task_id}: {e}")

    return {
        "success": True,
        "task_id": task_id,
        "title": title,
        "priority": priority,
        "due_date": due_date.isoformat() if due_date else None,
        "message": f"✅ Aufgabe \"{title}\" (Priorität: {priority}) erfolgreich erstellt."
    }


def _execute_list_tasks(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    completed = params.get("completed")
    priority = params.get("priority")
    tag = params.get("tag")
    search = params.get("search")
    limit = min(max(int(params.get("limit", 20)), 1), 100)

    with session_factory() as db:
        query = db.query(Task).filter(Task.user_id == user_id)
        if completed is not None:
            query = query.filter(Task.completed == bool(completed))
        if priority in ("low", "medium", "high"):
            query = query.filter(Task.priority == priority)
        if tag:
            query = query.filter(Task.tags.contains([tag]))
        if search:
            search_term = f"%{search}%"
            query = query.filter((Task.title.ilike(search_term)) | (Task.description.ilike(search_term)))

        tasks = query.order_by(Task.completed.asc(), Task.created_at.desc()).limit(limit).all()
        tasks_data = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "completed": t.completed,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "tags": t.tags
            }
            for t in tasks
        ]

    return {
        "count": len(tasks_data),
        "tasks": tasks_data,
        "message": f"{len(tasks_data)} Aufgabe(n) gefunden." if tasks_data else "Keine Aufgaben gefunden."
    }


def _execute_update_task_status(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    task_id = params.get("task_id")
    completed = params.get("completed")
    if task_id is None:
        return {"error": "task_id erforderlich"}
    if completed is None:
        return {"error": "completed (boolean) erforderlich"}

    with session_factory() as db:
        task = db.query(Task).filter(Task.id == int(task_id), Task.user_id == user_id).first()
        if not task:
            return {"error": f"Aufgabe #{task_id} wurde nicht gefunden"}
        task.completed = bool(completed)
        db.commit()
        title = task.title

    status_text = "erledigt" if completed else "wieder geöffnet"
    return {
        "success": True,
        "task_id": int(task_id),
        "title": title,
        "completed": bool(completed),
        "message": f"✅ Aufgabe \"{title}\" wurde als {status_text} markiert."
    }


def _execute_create_calendar_event(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    title = (params.get("title") or "").strip()
    if not title:
        return {"error": "Titel des Termins darf nicht leer sein"}
    start_str = params.get("start_time")
    end_str = params.get("end_time")
    if not start_str or not end_str:
        return {"error": "start_time und end_time sind erforderlich"}

    def parse_dt(val: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(val.split(".")[0].replace("Z", ""), fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)
    if not start_dt or not end_dt:
        return {"error": "Ungültiges Datumsformat für start_time oder end_time"}
    if end_dt <= start_dt:
        return {"error": "end_time muss nach start_time liegen"}

    description = params.get("description")
    location = params.get("location")
    event_type = params.get("event_type", "meeting")
    all_day = bool(params.get("all_day", False))

    with session_factory() as db:
        event = CalendarEvent(
            user_id=user_id,
            title=title,
            description=description,
            start_time=start_dt,
            end_time=end_dt,
            location=location,
            event_type=event_type,
            all_day=all_day
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id

        try:
            store_in_4d_memory(
                db=db,
                user_id=user_id,
                content_type="event",
                content_id=event_id,
                content_text=f"{title}. {description or ''} Ort: {location or ''}",
                additional_context={
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "location": location,
                    "event_type": event_type
                }
            )
        except Exception as e:
            logger.warning(f"4D Memory indexing failed for event #{event_id}: {e}")

    return {
        "success": True,
        "event_id": event_id,
        "title": title,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "location": location,
        "message": f"✅ Termin \"{title}\" am {start_dt.strftime('%d.%m.%Y um %H:%M Uhr')} erfolgreich eingetragen."
    }


def _execute_list_calendar_events(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    search = params.get("search")
    limit = min(max(int(params.get("limit", 20)), 1), 100)

    with session_factory() as db:
        query = db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id)
        if start_date_str:
            try:
                s_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                query = query.filter(CalendarEvent.end_time >= s_dt)
            except Exception:
                pass
        if end_date_str:
            try:
                e_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                query = query.filter(CalendarEvent.start_time <= e_dt)
            except Exception:
                pass
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (CalendarEvent.title.ilike(search_term)) |
                (CalendarEvent.description.ilike(search_term)) |
                (CalendarEvent.location.ilike(search_term))
            )

        events = query.order_by(CalendarEvent.start_time.asc()).limit(limit).all()
        events_data = [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "start_time": e.start_time.isoformat() if e.start_time else None,
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "location": e.location,
                "event_type": e.event_type,
                "all_day": e.all_day
            }
            for e in events
        ]

    return {
        "count": len(events_data),
        "events": events_data,
        "message": f"{len(events_data)} Termin(e) gefunden." if events_data else "Keine Termine gefunden."
    }


def _execute_search_memory(user_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    query = (params.get("query") or "").strip()
    if not query:
        return {"error": "Suchbegriff für Gedächtnisabfrage darf nicht leer sein"}
    limit = min(max(int(params.get("limit", 5)), 1), 20)

    try:
        results = get_relevant_context(user_id=user_id, query_text=query, limit=limit)
        return {
            "query": query,
            "count": len(results),
            "memories": results,
            "message": f"{len(results)} relevante Erinnerung(en) im 4D-Gedächtnis gefunden." if results else "Keine passenden Erinnerungen gefunden."
        }
    except Exception as e:
        logger.warning(f"Semantic search failed: {e}")
        return {
            "query": query,
            "count": 0,
            "memories": [],
            "message": f"Suche im 4D Memory nicht verfügbar: {str(e)}"
        }


def _execute_store_memory(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    content = (params.get("content") or "").strip()
    if not content:
        return {"error": "Inhalt der Erinnerung darf nicht leer sein"}
    category = params.get("category", "fact")
    tags = params.get("tags") or []
    
    with session_factory() as db:
        short_title = content[:40] + ("..." if len(content) > 40 else "")
        note = Note(
            user_id=user_id,
            title=f"Erinnerung ({category}): {short_title}",
            content=content,
            category=category,
            tags=list(set(tags + ["memory", "fact"])),
            is_pinned=False,
            is_archived=False
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.id
        
        try:
            store_in_4d_memory(
                db=db,
                user_id=user_id,
                content_type="memory",
                content_id=note_id,
                content_text=content,
                additional_context={"category": category, "tags": tags}
            )
        except Exception as e:
            logger.warning(f"4D Memory indexing failed for store_memory: {e}")

    return {
        "success": True,
        "note_id": note_id,
        "content": content,
        "category": category,
        "message": f"✅ Erinnerung / Fakt erfolgreich im 4D-Gedächtnis gespeichert: \"{content}\""
    }


def _execute_correct_memory(user_id: int, params: Dict[str, Any], session_factory) -> Dict[str, Any]:
    """Trigger c (memory_verification.py): explizite, bewusste Korrektur.

    Sucht per bestehender Semantik-Suche (dieselbe wie search_memory) nach der
    zur query passendsten früheren Erinnerung, invalidiert sie hart
    (epistemic_state=CONTRADICTED, confidence -> nahe 0) und speichert die
    korrekte Fassung als neue Notiz - derselbe Speicherpfad wie store_memory,
    damit die Korrektur dauerhaft und durchsuchbar bleibt.

    Absichtlich KEIN neuer :Message-Knoten für die Korrektur (anders als
    supersede_message's new-Message-Fall): eine synthetische Message-ID aus
    einem Tool-Aufruf würde in denselben ID-Raum wie echte chat_messages.id
    schreiben und könnte kollidieren - die Korrektur landet stattdessen im
    Notizen-Pfad, der einen eigenen, unabhängigen ID-Raum hat.
    """
    query = (params.get("query") or "").strip()
    correction = (params.get("correction") or "").strip()
    if not query or not correction:
        return {"error": "Sowohl query (was war falsch) als auch correction (was stimmt) müssen angegeben werden"}

    invalidated_count = 0
    try:
        matches = get_relevant_context(user_id=user_id, query_text=query, limit=3)
        seen_message_ids = set()
        for item in matches:
            for msg in item.get('related_messages', []):
                mid = msg.get('message_id')
                if mid is None or mid in seen_message_ids:
                    continue
                seen_message_ids.add(mid)
                try:
                    if invalidate_message(user_id=user_id, message_id=mid, reason=f"correct_memory: {correction[:100]}", hard=True):
                        invalidated_count += 1
                except Exception as inv_err:
                    logger.warning(f"correct_memory: invalidate_message failed for {mid}: {inv_err}")
    except Exception as e:
        logger.warning(f"correct_memory: lookup of old memory failed: {e}")

    store_result = _execute_store_memory(
        user_id, {"content": correction, "category": "correction"}, session_factory
    )

    return {
        "success": True,
        "invalidated_count": invalidated_count,
        "correction": correction,
        "note_id": store_result.get("note_id"),
        "message": (
            f"✅ {invalidated_count} alte, widersprüchliche Erinnerung(en) als widerlegt markiert. "
            f"Korrektur gespeichert: \"{correction}\""
        )
    }

