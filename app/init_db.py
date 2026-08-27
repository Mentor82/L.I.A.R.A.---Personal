"""
Dev/bootstrap-only table creation (issue #12 item 5) - NEVER run this
against production. Alembic (`alembic upgrade head`) is the single
authoritative schema path there; this script's create_all() only exists
for spinning up a throwaway local database quickly, and only creates
tables for whichever models happen to be imported below (not the full
schema - e.g. mood_state and auth_session are not imported here).
"""

from core.database import init_db
from api.models.chat_session import ChatSession
from api.models.chat_message import ChatMessage
from api.models.base_models import User

if __name__ == "__main__":
    init_db()
    print("Tabellen wurden erstellt (falls nicht vorhanden).")
