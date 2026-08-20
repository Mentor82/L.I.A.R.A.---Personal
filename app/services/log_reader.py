"""
Log Reader Service
Reads and parses system logs from various services
"""
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum


class ServiceType(str, Enum):
    BACKEND = "backend"
    SSE = "sse"
    FRONTEND = "frontend"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogReaderService:
    """Service to read and parse system logs"""
    
    SERVICE_UNITS = {
        ServiceType.BACKEND: "liara-backend",
        ServiceType.SSE: "liara-sse",
        ServiceType.FRONTEND: "liara-frontend"
    }
    
    def __init__(self):
        pass
    
    def get_logs(
        self,
        service: ServiceType,
        level: Optional[LogLevel] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Read logs from log files
        
        Args:
            service: Service to read logs from
            level: Filter by log level
            since: Start time for logs
            until: End time for logs
            search: Search term to filter logs
            limit: Maximum number of log entries
            
        Returns:
            List of log entries with timestamp, level, message
        """
        try:
            logs = []
            
            if service == ServiceType.BACKEND:
                error_log_path = "/var/log/liara/error.log"
                access_log_path = "/var/log/liara/access.log"
                
                # Read error logs
                try:
                    with open(error_log_path, 'r') as f:
                        error_lines = f.readlines()[-200:]
                    for line in error_lines:
                        if line.strip():
                            logs.append({
                                'timestamp': datetime.now().isoformat(),
                                'level': LogLevel.ERROR.value,
                                'message': line.strip(),
                                'service': service.value
                            })
                except Exception as e:
                    print(f"Error reading error log: {e}")
                
                # Read access logs
                try:
                    with open(access_log_path, 'r') as f:
                        access_lines = f.readlines()[-200:]
                    for line in access_lines:
                        if line.strip():
                            logs.append({
                                'timestamp': datetime.now().isoformat(),
                                'level': LogLevel.INFO.value,
                                'message': line.strip(),
                                'service': service.value
                            })
                except Exception as e:
                    print(f"Error reading access log: {e}")
            
            # Apply filters
            if level:
                logs = [log for log in logs if log['level'] == level.value]
            if search:
                logs = [log for log in logs if search.lower() in log['message'].lower()]
            
            return logs[:limit]
            
        except Exception as e:
            print(f"Error reading logs: {e}")
            return []
    
    def _detect_log_level(self, message: str) -> str:
        """Detect log level from message content"""
        message_upper = message.upper()
        
        if 'CRITICAL' in message_upper or 'FATAL' in message_upper:
            return LogLevel.CRITICAL
        elif 'ERROR' in message_upper:
            return LogLevel.ERROR
        elif 'WARNING' in message_upper or 'WARN' in message_upper:
            return LogLevel.WARNING
        elif 'DEBUG' in message_upper:
            return LogLevel.DEBUG
        else:
            return LogLevel.INFO
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """
        Get recent system activity across all services
        
        Args:
            limit: Number of recent activities to return
            
        Returns:
            List of recent activities with type, user, timestamp, details
        """
        activities = []
        
        # Read from Gunicorn access log (more relevant for user activity)
        try:
            access_log_path = "/var/log/liara/access.log"
            with open(access_log_path, 'r') as f:
                lines = f.readlines()[-100:]  # Last 100 lines
                
            for line in lines:
                activity = self._parse_access_log(line)
                if activity:
                    activities.append(activity)
        except Exception as e:
            print(f"Error reading access log: {e}")
        
        # Also read from systemd journal for system events
        since = datetime.now() - timedelta(hours=24)
        for service in ServiceType:
            try:
                logs = self.get_logs(
                    service=service,
                    since=since,
                    limit=10
                )
                
                for log in logs:
                    activity = self._parse_activity(log)
                    if activity:
                        activities.append(activity)
            except:
                pass
        
        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return activities[:limit]
    
    def _parse_access_log(self, line: str) -> Optional[Dict]:
        """Parse Gunicorn access log line"""
        import re
        
        # Example: 2a02:810a:9306:2300:4582:5298:7ba8:53ed:0 - "POST /auth/login HTTP/1.1" 200
        match = re.search(r'"(GET|POST|PUT|DELETE|PATCH) ([^"]+) HTTP', line)
        if not match:
            return None
        
        method = match.group(1)
        endpoint = match.group(2)
        
        # Determine activity type and action
        activity_type = 'api_call'
        action = f"{method} {endpoint}"
        icon = '🔌'
        
        if '/auth/login' in endpoint:
            activity_type = 'login'
            action = 'User login'
            icon = '🔐'
        elif '/chat/message' in endpoint or '/chat/stream' in endpoint:
            activity_type = 'chat'
            action = 'Chat message'
            icon = '💬'
        elif '/admin/' in endpoint:
            activity_type = 'admin'
            action = f"Admin: {endpoint.split('/')[-1]}"
            icon = '⚡'
        
        return {
            'timestamp': datetime.now().isoformat(),  # Access log doesn't have timestamp in this format
            'service': 'backend',
            'level': 'INFO',
            'type': activity_type,
            'user': None,
            'action': action,
            'details': endpoint,
            'icon': icon
        }
    
    def _parse_activity(self, log: Dict) -> Optional[Dict]:
        """Parse log entry into activity"""
        message = log['message']
        
        # Extract user activities
        activity = {
            'timestamp': log['timestamp'],
            'service': log['service'],
            'level': log['level'],
            'type': 'system',
            'user': None,
            'action': None,
            'details': message
        }
        
        # Detect login
        if 'login' in message.lower() or 'logged in' in message.lower():
            activity['type'] = 'login'
            activity['action'] = 'User logged in'
        
        # Detect chat message
        elif 'POST /chat' in message or 'chat/stream' in message:
            activity['type'] = 'chat'
            activity['action'] = 'Chat message sent'
        
        # Detect API calls
        elif '"GET ' in message or '"POST ' in message:
            activity['type'] = 'api_call'
            # Extract endpoint
            import re
            match = re.search(r'"(GET|POST|PUT|DELETE) ([^"]+)"', message)
            if match:
                activity['action'] = f"{match.group(1)} {match.group(2)}"
        
        # Detect errors
        elif log['level'] in [LogLevel.ERROR, LogLevel.CRITICAL]:
            activity['type'] = 'error'
            activity['action'] = 'System error'
        
        return activity


# Singleton instance
_log_reader_service = None

def get_log_reader_service() -> LogReaderService:
    """Get or create LogReaderService singleton"""
    global _log_reader_service
    if _log_reader_service is None:
        _log_reader_service = LogReaderService()
    return _log_reader_service
