"""
Action Executor
Führt erkannte Aktionen aus (Calendar, Tasks, Notes)
"""

from typing import Dict, Optional
import logging
from datetime import datetime
from api.models.base_models import Task, CalendarEvent, Note
from services.memory_integration import store_in_4d_memory

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Führt Aktionen basierend auf Intents aus"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def execute_create_event(self, details: Dict, user_id: int = 1) -> Dict:
        """
        Erstellt einen Kalender-Event mit SQLAlchemy ORM
        
        Returns:
            Erfolgs-Info mit Event-ID
        """
        try:
            event = CalendarEvent(
                title=details.get('title', 'Neuer Termin'),
                description=details.get('description', ''),
                start_time=details.get('start_time'),
                end_time=details.get('end_time'),
                location=details.get('location'),
                event_type=details.get('event_type', 'meeting'),
                user_id=details.get('user_id', user_id)
            )
            
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            
            logger.info(f"Created calendar event #{event.id}: {event.title}")
            
            # 🌌 Store in 4D Memory System
            try:
                store_in_4d_memory(
                    db=self.db,
                    user_id=event.user_id,
                    content_type='event',
                    content_id=event.id,
                    content_text=f"{event.title}. {event.description or ''} Ort: {event.location or 'Nicht angegeben'}",
                    additional_context={
                        'event_type': event.event_type,
                        'location': event.location,
                        'start_time': str(event.start_time),
                        'end_time': str(event.end_time)
                    }
                )
                logger.info(f"Event #{event.id} stored in 4D Memory")
            except Exception as e:
                logger.warning(f"Failed to store event in 4D Memory: {e}")
            
            # Formatiere Start-Zeit für Bestätigung
            start_dt = datetime.fromisoformat(details.get('start_time'))
            time_str = start_dt.strftime('%d.%m.%Y um %H:%M Uhr')
            
            # Relative Zeit (morgen, heute, etc.)
            day_diff = (start_dt.date() - datetime.now().date()).days
            if day_diff == 0:
                day_name = "heute"
            elif day_diff == 1:
                day_name = "morgen"
            elif day_diff == 2:
                day_name = "übermorgen"
            else:
                day_name = f"am {start_dt.strftime('%d.%m.')}"
            
            # Baue schöne Bestätigungsnachricht
            location_part = f" in {event.location}" if event.location else ""
            message = f"✅ Ich habe dir {day_name} um {start_dt.strftime('%H:%M')} Uhr einen Termin \"{event.title}\"{location_part} erstellt."
            
            return {
                'success': True,
                'action': 'create_event',
                'event_id': event.id,
                'title': event.title,
                'start_time': str(event.start_time),
                'location': event.location,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            self.db.rollback()
            return {
                'success': False,
                'action': 'create_event',
                'error': str(e),
                'message': f"❌ Fehler beim Erstellen des Termins: {str(e)}"
            }
    
    async def execute_create_task(self, details: Dict, user_id: int = 1) -> Dict:
        """
        Erstellt eine Task mit SQLAlchemy ORM
        
        Returns:
            Erfolgs-Info mit Task-ID
        """
        try:
            task = Task(
                title=details.get('title', 'Neue Aufgabe'),
                description=details.get('description', ''),
                priority=details.get('priority', 'medium'),
                tags=details.get('tags', []),
                completed=False,
                user_id=details.get('user_id', user_id)
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"Created task #{task.id}: {task.title}")
            
            # 🌌 Store in 4D Memory System
            try:
                store_in_4d_memory(
                    db=self.db,
                    user_id=task.user_id,
                    content_type='task',
                    content_id=task.id,
                    content_text=f"{task.title}. {task.description or ''}",
                    additional_context={
                        'priority': task.priority,
                        'tags': task.tags,
                        'completed': task.completed
                    }
                )
                logger.info(f"Task #{task.id} stored in 4D Memory")
            except Exception as e:
                logger.warning(f"Failed to store task in 4D Memory: {e}")
            
            # Priority mit Emoji
            priority_map = {
                'high': ('🔴', 'Hohe'),
                'medium': ('🟡', 'Mittlere'),
                'low': ('🟢', 'Niedrige')
            }
            priority_emoji, priority_name = priority_map.get(task.priority, ('🟡', 'Mittlere'))
            
            return {
                'success': True,
                'action': 'create_task',
                'task_id': task.id,
                'title': task.title,
                'priority': task.priority,
                'message': f"✅ Task \"{task.title}\" wurde erstellt! {priority_emoji} {priority_name} Priorität"
            }
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            self.db.rollback()
            return {
                'success': False,
                'action': 'create_task',
                'error': str(e),
                'message': f"❌ Fehler beim Erstellen der Aufgabe: {str(e)}"
            }
    
    async def execute_create_note(self, details: Dict, user_id: int = 1) -> Dict:
        """
        Erstellt eine Notiz mit SQLAlchemy ORM
        
        Returns:
            Erfolgs-Info mit Note-ID
        """
        try:
            note = Note(
                title=details.get('title', 'Neue Notiz'),
                content=details.get('content', ''),
                category=details.get('category'),
                tags=details.get('tags', []),
                is_pinned=False,
                is_archived=False,
                user_id=details.get('user_id', user_id)
            )
            
            self.db.add(note)
            self.db.commit()
            self.db.refresh(note)
            
            logger.info(f"Created note #{note.id}: {note.title}")
            
            # 🌌 Store in 4D Memory System
            try:
                store_in_4d_memory(
                    db=self.db,
                    user_id=note.user_id,
                    content_type='note',
                    content_id=note.id,
                    content_text=f"{note.title}. {note.content}",
                    additional_context={
                        'category': note.category,
                        'tags': note.tags,
                        'is_pinned': note.is_pinned
                    }
                )
                logger.info(f"Note #{note.id} stored in 4D Memory")
            except Exception as e:
                logger.warning(f"Failed to store note in 4D Memory: {e}")
            
            category_part = f" in Kategorie \"{note.category}\"" if note.category else ""
            
            return {
                'success': True,
                'action': 'create_note',
                'note_id': note.id,
                'title': note.title,
                'message': f"✅ Notiz \"{note.title}\" wurde gespeichert{category_part}!"
            }
            
        except Exception as e:
            logger.error(f"Failed to create note: {e}")
            self.db.rollback()
            return {
                'success': False,
                'action': 'create_note',
                'error': str(e),
                'message': f"❌ Fehler beim Erstellen der Notiz: {str(e)}"
            }
    
    async def execute_list_tasks(self, user_id: int) -> Dict:
        """Liste alle Tasks des Users"""
        try:
            tasks = self.db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).limit(20).all()
            
            if not tasks:
                return {
                    'success': True,
                    'action': 'list_tasks',
                    'count': 0,
                    'message': "📋 Du hast noch keine Aufgaben erstellt."
                }
            
            # Gruppiere nach Status
            pending = [t for t in tasks if not t.completed]
            completed = [t for t in tasks if t.completed]
            
            # Formatiere Ausgabe
            lines = ["📋 **Deine Aufgaben:**\n"]
            
            if pending:
                lines.append(f"**Offen ({len(pending)}):**")
                for task in pending[:10]:
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task.priority, '🟡')
                    lines.append(f"{priority_emoji} {task.title}")
            
            if completed:
                lines.append(f"\n**Erledigt ({len(completed)}):**")
                for task in completed[:5]:
                    lines.append(f"✅ {task.title}")
            
            return {
                'success': True,
                'action': 'list_tasks',
                'count': len(tasks),
                'pending': len(pending),
                'completed': len(completed),
                'message': '\n'.join(lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return {
                'success': False,
                'action': 'list_tasks',
                'error': str(e),
                'message': f"❌ Fehler beim Laden der Aufgaben: {str(e)}"
            }
    
    async def execute_list_events(self, user_id: int) -> Dict:
        """Liste alle Events des Users"""
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            week_later = now + timedelta(days=7)
            
            events = self.db.query(CalendarEvent).filter(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= now
            ).order_by(CalendarEvent.start_time.asc()).limit(10).all()
            
            if not events:
                return {
                    'success': True,
                    'action': 'list_events',
                    'count': 0,
                    'message': "📅 Keine anstehenden Termine gefunden."
                }
            
            lines = ["📅 **Deine anstehenden Termine:**\n"]
            for event in events:
                start = event.start_time.strftime("%d.%m. %H:%M")
                type_emoji = {'meeting': '🤝', 'reminder': '⏰', 'appointment': '📌'}.get(event.event_type, '📅')
                lines.append(f"{type_emoji} {start} - {event.title}")
                if event.location:
                    lines.append(f"   📍 {event.location}")
            
            return {
                'success': True,
                'action': 'list_events',
                'count': len(events),
                'message': '\n'.join(lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return {
                'success': False,
                'action': 'list_events',
                'error': str(e),
                'message': f"❌ Fehler beim Laden der Termine: {str(e)}"
            }
    
    async def execute_list_notes(self, user_id: int) -> Dict:
        """Liste alle Notes des Users"""
        try:
            notes = self.db.query(Note).filter(
                Note.user_id == user_id,
                Note.is_archived == False
            ).order_by(Note.created_at.desc()).limit(10).all()
            
            if not notes:
                return {
                    'success': True,
                    'action': 'list_notes',
                    'count': 0,
                    'message': "📝 Keine Notizen gefunden."
                }
            
            lines = ["📝 **Deine Notizen:**\n"]
            for note in notes:
                pin_emoji = "📌 " if note.is_pinned else ""
                preview = note.content[:50] + "..." if len(note.content) > 50 else note.content
                lines.append(f"{pin_emoji}**{note.title}**")
                lines.append(f"   {preview}")
            
            return {
                'success': True,
                'action': 'list_notes',
                'count': len(notes),
                'message': '\n'.join(lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to list notes: {e}")
            return {
                'success': False,
                'action': 'list_notes',
                'error': str(e),
                'message': f"❌ Fehler beim Laden der Notizen: {str(e)}"
            }
