"""
Mirko Debug Logger - Spezielles Logging für User Mirko
Erstellt detaillierte Logs für Chat-Requests zur Echo-Debugging
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

MLOG_DIR = Path("/opt/liara/mlog")
MLOG_DIR.mkdir(exist_ok=True)


class MirkoLogger:
    """Logger für Mirko's Chat-Requests"""
    
    def __init__(self):
        self.log_file = MLOG_DIR / f"chat_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def log_chat_request(self, event: str, data: Dict[str, Any]):
        """
        Logge Chat-Event
        
        Args:
            event: Event-Typ (request_start, sse_chunk, response_sent, etc.)
            data: Event-Daten
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def log_request_start(self, user_id: int, username: str, message: str, session_id: int = None):
        """Logge Start einer Chat-Request"""
        self.log_chat_request("REQUEST_START", {
            "user_id": user_id,
            "username": username,
            "message": message[:100],  # Erste 100 Zeichen
            "session_id": session_id,
            "message_length": len(message)
        })
    
    def log_sse_chunk(self, chunk_type: str, content: str = None, metadata: Dict = None):
        """Logge SSE-Chunk"""
        self.log_chat_request("SSE_CHUNK", {
            "chunk_type": chunk_type,
            "content_preview": content[:50] if content else None,
            "content_length": len(content) if content else 0,
            "metadata": metadata
        })
    
    def log_response_sent(self, response_preview: str, model: str, intent: str = None):
        """Logge gesendete Response"""
        self.log_chat_request("RESPONSE_SENT", {
            "response_preview": response_preview[:100],
            "response_length": len(response_preview),
            "model": model,
            "intent": intent
        })
    
    def log_error(self, error: str, context: Dict = None):
        """Logge Fehler"""
        self.log_chat_request("ERROR", {
            "error": str(error),
            "context": context
        })


# Singleton-Instanz
_mirko_logger = MirkoLogger()


def get_mirko_logger() -> MirkoLogger:
    """Hole Mirko-Logger Instanz"""
    return _mirko_logger


def should_log_for_user(username: str) -> bool:
    """Prüfe ob für diesen User geloggt werden soll"""
    return username.lower() == "mirko"
