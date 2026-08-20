#!/usr/bin/env python3
"""
🌌 LIARA 4D Memory - Sync Utility
Backfill existing data into 4D Memory system

Usage:
    python sync_memory.py --all                # Sync all content types
    python sync_memory.py --tasks              # Sync only tasks
    python sync_memory.py --notes              # Sync only notes
    python sync_memory.py --events             # Sync only calendar events
    python sync_memory.py --user-id 1          # Sync for specific user
    python sync_memory.py --dry-run            # Preview without writing
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
from core.database import get_db_context
from api.models.base_models import Task, Note, CalendarEvent
from services.memory_integration import store_in_4d_memory


def sync_tasks(db: Session, user_id: int = None, dry_run: bool = False):
    """Sync all tasks to 4D Memory"""
    query = db.query(Task)
    if user_id:
        query = query.filter(Task.user_id == user_id)
    
    tasks = query.all()
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing {len(tasks)} tasks...")
    
    success_count = 0
    error_count = 0
    
    for task in tasks:
        try:
            if not dry_run:
                content_text = f"{task.title}. {task.description or ''}"
                store_in_4d_memory(
                    db=db,
                    user_id=task.user_id,
                    content_type='task',
                    content_id=task.id,
                    content_text=content_text,
                    additional_context={
                        'priority': task.priority,
                        'due_date': str(task.due_date) if task.due_date else None,
                        'tags': task.tags,
                        'completed': task.completed
                    }
                )
            success_count += 1
            if success_count % 10 == 0:
                print(f"  Processed {success_count}/{len(tasks)} tasks...")
        except Exception as e:
            error_count += 1
            print(f"  Error syncing task {task.id}: {e}")
    
    print(f"✅ Tasks: {success_count} synced, {error_count} errors")
    return success_count, error_count


def sync_notes(db: Session, user_id: int = None, dry_run: bool = False):
    """Sync all notes to 4D Memory"""
    query = db.query(Note)
    if user_id:
        query = query.filter(Note.user_id == user_id)
    
    notes = query.all()
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing {len(notes)} notes...")
    
    success_count = 0
    error_count = 0
    
    for note in notes:
        try:
            if not dry_run:
                content_text = f"{note.title}. {note.content}"
                store_in_4d_memory(
                    db=db,
                    user_id=note.user_id,
                    content_type='note',
                    content_id=note.id,
                    content_text=content_text,
                    additional_context={
                        'category': note.category,
                        'tags': note.tags,
                        'is_pinned': note.is_pinned,
                        'is_archived': note.is_archived
                    }
                )
            success_count += 1
            if success_count % 10 == 0:
                print(f"  Processed {success_count}/{len(notes)} notes...")
        except Exception as e:
            error_count += 1
            print(f"  Error syncing note {note.id}: {e}")
    
    print(f"✅ Notes: {success_count} synced, {error_count} errors")
    return success_count, error_count


def sync_events(db: Session, user_id: int = None, dry_run: bool = False):
    """Sync all calendar events to 4D Memory"""
    query = db.query(CalendarEvent)
    if user_id:
        query = query.filter(CalendarEvent.user_id == user_id)
    
    events = query.all()
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing {len(events)} calendar events...")
    
    success_count = 0
    error_count = 0
    
    for event in events:
        try:
            if not dry_run:
                content_text = f"{event.title}. {event.description or ''}"
                if event.location:
                    content_text += f" Ort: {event.location}"
                
                store_in_4d_memory(
                    db=db,
                    user_id=event.user_id,
                    content_type='event',
                    content_id=event.id,
                    content_text=content_text,
                    additional_context={
                        'event_type': event.event_type,
                        'start_time': str(event.start_time),
                        'end_time': str(event.end_time),
                        'location': event.location,
                        'all_day': event.all_day
                    }
                )
            success_count += 1
            if success_count % 10 == 0:
                print(f"  Processed {success_count}/{len(events)} events...")
        except Exception as e:
            error_count += 1
            print(f"  Error syncing event {event.id}: {e}")
    
    print(f"✅ Events: {success_count} synced, {error_count} errors")
    return success_count, error_count


def get_memory_stats(db: Session):
    """Get current 4D Memory statistics"""
    stats = {}
    
    # Temporal entries
    result = db.execute(text("SELECT COUNT(*) FROM temporal_index"))
    stats['temporal_entries'] = result.scalar()
    
    # Semantic embeddings
    result = db.execute(text("SELECT COUNT(*) FROM semantic_metadata"))
    stats['semantic_embeddings'] = result.scalar()
    
    # Content relations
    result = db.execute(text("SELECT COUNT(*) FROM content_relations"))
    stats['content_relations'] = result.scalar()
    
    # By content type
    result = db.execute(text("""
        SELECT content_type, COUNT(*) 
        FROM semantic_metadata 
        GROUP BY content_type
    """))
    stats['by_type'] = {row[0]: row[1] for row in result}
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync existing content to 4D Memory system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--all', action='store_true', help='Sync all content types')
    parser.add_argument('--tasks', action='store_true', help='Sync tasks')
    parser.add_argument('--notes', action='store_true', help='Sync notes')
    parser.add_argument('--events', action='store_true', help='Sync calendar events')
    parser.add_argument('--user-id', type=int, help='Sync only for specific user ID')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing to database')
    parser.add_argument('--stats', action='store_true', help='Show current memory statistics')
    
    args = parser.parse_args()
    
    # Default to --all if no specific content type selected
    if not any([args.all, args.tasks, args.notes, args.events, args.stats]):
        args.all = True
    
    print("🌌 LIARA 4D Memory Sync Utility")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be written")
    
    if args.user_id:
        print(f"📌 Filtering for user_id: {args.user_id}")
    
    with get_db_context() as db:
        # Show current stats
        if args.stats or args.dry_run:
            print("\n📊 Current 4D Memory Statistics:")
            stats = get_memory_stats(db)
            print(f"  Temporal entries: {stats['temporal_entries']}")
            print(f"  Semantic embeddings: {stats['semantic_embeddings']}")
            print(f"  Content relations: {stats['content_relations']}")
            if stats['by_type']:
                print("  By type:")
                for content_type, count in stats['by_type'].items():
                    print(f"    {content_type}: {count}")
        
        if args.stats:
            return
        
        total_success = 0
        total_errors = 0
        
        # Sync tasks
        if args.all or args.tasks:
            success, errors = sync_tasks(db, args.user_id, args.dry_run)
            total_success += success
            total_errors += errors
        
        # Sync notes
        if args.all or args.notes:
            success, errors = sync_notes(db, args.user_id, args.dry_run)
            total_success += success
            total_errors += errors
        
        # Sync events
        if args.all or args.events:
            success, errors = sync_events(db, args.user_id, args.dry_run)
            total_success += success
            total_errors += errors
        
        print("\n" + "=" * 60)
        print(f"✅ Total synced: {total_success}")
        print(f"❌ Total errors: {total_errors}")
        
        if not args.dry_run:
            print("\n📊 Updated 4D Memory Statistics:")
            stats = get_memory_stats(db)
            print(f"  Temporal entries: {stats['temporal_entries']}")
            print(f"  Semantic embeddings: {stats['semantic_embeddings']}")
            print(f"  Content relations: {stats['content_relations']}")
            if stats['by_type']:
                print("  By type:")
                for content_type, count in stats['by_type'].items():
                    print(f"    {content_type}: {count}")
        
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
