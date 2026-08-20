
from core.database import init_db
from api.models.chat_session import ChatSession
from api.models.chat_message import ChatMessage
from api.models.base_models import User

if __name__ == "__main__":
    init_db()
    print("Tabellen wurden erstellt (falls nicht vorhanden).")
