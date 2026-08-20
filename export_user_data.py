#!/usr/bin/env python3
"""
Export all user interaction data from Liara database
"""
import psycopg2
import json
import sys
from datetime import datetime

def export_user_data(username):
    conn = psycopg2.connect(
        dbname="liara_db",
        user="postgres",
        host="localhost"
    )
    cur = conn.cursor()
    
    # Get user ID
    cur.execute("SELECT id, username, email, role, created_at FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    
    if not user:
        print(f"User '{username}' not found")
        sys.exit(1)
    
    user_id = user[0]
    
    export_data = {
        "user": {
            "id": user_id,
            "username": user[1],
            "email": user[2],
            "role": user[3],
            "created_at": str(user[4])
        },
        "chat_sessions": [],
        "chat_messages": [],
        "search_history": [],
        "privacy_settings": {},
        "location_preferences": {},
        "tasks": [],
        "notes": [],
        "calendar_events": []
    }
    
    # Chat Sessions
    cur.execute("SELECT * FROM chat_sessions WHERE user_id = %s ORDER BY created_at", (user_id,))
    for row in cur.fetchall():
        export_data["chat_sessions"].append({
            "id": row[0],
            "title": row[2],
            "created_at": str(row[3]),
            "updated_at": str(row[4])
        })
    
    # Chat Messages
    cur.execute("SELECT * FROM chat_messages WHERE user_id = %s ORDER BY timestamp", (user_id,))
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        msg = dict(zip(cols, row))
        # Convert datetime to string
        if msg.get('timestamp'):
            msg['timestamp'] = str(msg['timestamp'])
        export_data["chat_messages"].append(msg)
    
    # Search History
    cur.execute("SELECT * FROM user_search_history WHERE user_id = %s ORDER BY searched_at", (user_id,))
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        hist = dict(zip(cols, row))
        if hist.get('searched_at'):
            hist['searched_at'] = str(hist['searched_at'])
        export_data["search_history"].append(hist)
    
    # Privacy Settings
    cur.execute("SELECT * FROM user_privacy_settings WHERE user_id = %s", (user_id,))
    cols = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row:
        export_data["privacy_settings"] = dict(zip(cols, row))
    
    # Location
    cur.execute("SELECT * FROM user_location_preferences WHERE user_id = %s", (user_id,))
    cols = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row:
        loc = dict(zip(cols, row))
        if loc.get('last_updated'):
            loc['last_updated'] = str(loc['last_updated'])
        export_data["location_preferences"] = loc
    
    # Tasks
    cur.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at", (user_id,))
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        task = dict(zip(cols, row))
        if task.get('created_at'):
            task['created_at'] = str(task['created_at'])
        if task.get('due_date'):
            task['due_date'] = str(task['due_date'])
        export_data["tasks"].append(task)
    
    # Notes
    cur.execute("SELECT * FROM notes WHERE user_id = %s ORDER BY created_at", (user_id,))
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        note = dict(zip(cols, row))
        if note.get('created_at'):
            note['created_at'] = str(note['created_at'])
        if note.get('updated_at'):
            note['updated_at'] = str(note['updated_at'])
        export_data["notes"].append(note)
    
    # Calendar Events
    cur.execute("SELECT * FROM calendar_events WHERE user_id = %s ORDER BY start_time", (user_id,))
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        event = dict(zip(cols, row))
        if event.get('start_time'):
            event['start_time'] = str(event['start_time'])
        if event.get('end_time'):
            event['end_time'] = str(event['end_time'])
        if event.get('created_at'):
            event['created_at'] = str(event['created_at'])
        export_data["calendar_events"].append(event)
    
    cur.close()
    conn.close()
    
    # Export to JSON file
    filename = f"user_export_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Exported data for user '{username}' to {filename}")
    print(f"\nSummary:")
    print(f"  - Chat Sessions: {len(export_data['chat_sessions'])}")
    print(f"  - Chat Messages: {len(export_data['chat_messages'])}")
    print(f"  - Search History: {len(export_data['search_history'])}")
    print(f"  - Tasks: {len(export_data['tasks'])}")
    print(f"  - Notes: {len(export_data['notes'])}")
    print(f"  - Calendar Events: {len(export_data['calendar_events'])}")
    
    return filename

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 export_user_data.py <username>")
        sys.exit(1)
    
    export_user_data(sys.argv[1])
