"""
🛡️ LAYER 1: Intent & Safety Check
Prüft User-Absicht, blockiert unsafe topics, Rate-Limiting
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict
import threading


class IntentSafetyChecker:
    """
    Layer 1: Intent & Safety Check
    
    - Analysiert User-Absicht
    - Blockiert unsafe topics (Hacking, Malware, Waffen, illegale Inhalte)
    - Rate-Limiting pro User
    - Query-Rewrite (entschärft gefährliche Anfragen)
    """
    
    # Rate-Limiting: User → [(timestamp, count)]
    _rate_limits: Dict[int, List[datetime]] = defaultdict(list)
    _lock = threading.Lock()
    
    # Blocked Keywords (Unsafe Topics)
    BLOCKED_KEYWORDS = {
        # Hacking & Malware
        'hack', 'exploit', 'backdoor', 'rootkit', 'keylogger', 'trojan',
        'ransomware', 'malware', 'virus', 'crack', 'keygen', 'warez',
        'ddos', 'dos attack', 'brute force', 'sql injection', 'xss',
        'zero day', 'metasploit', 'nmap', 'burp suite', 'kali linux',
        
        # Waffen & Gewalt
        'waffen kaufen', 'gun', 'pistole', 'gewehr', 'munition', 'sprengstoff',
        'bombe bauen', 'sprengsatz', 'atombombe', 'chemische waffe',
        
        # Drogen & illegale Substanzen
        'drogen kaufen', 'kokain', 'heroin', 'methamphetamin', 'crystal meth',
        'lsd kaufen', 'mdma kaufen', 'ecstasy kaufen',
        
        # Illegale Aktivitäten
        'identität stehlen', 'kreditkarte hacken', 'bank account hack',
        'geld waschen', 'money laundering', 'darknet market', 'dark web market',
        'fake passport', 'gefälschter ausweis', 'counterfeit',
        
        # Extremismus & Terrorismus
        'terroranschlag', 'terrorist training', 'isis', 'al qaeda',
        'extremist', 'radikalisierung',
        
        # CSAM & illegale Inhalte
        'child porn', 'cp', 'pthc', 'jailbait',
        
        # Downloads von Executables
        'download exe', 'download msi', 'download payload', 'download backdoor',
    }
    
    # Warning Keywords (erhöhen Risk-Score)
    WARNING_KEYWORDS = {
        'password', 'login credentials', 'admin panel', 'exploit db',
        'vulnerability', 'security flaw', 'bypass', 'circumvent',
        'torrent', 'pirate', 'cracked software', 'nulled script',
    }
    
    # Safe Intent Patterns
    SAFE_INTENTS = {
        'weather', 'wetter', 'temperatur', 'klima',
        'nachrichten', 'news', 'aktuell',
        'wikipedia', 'definition', 'bedeutung',
        'dokumentation', 'tutorial', 'guide',
        'wissenschaft', 'forschung', 'studie',
        'rezept', 'recipe', 'kochen',
        'programmierung', 'code', 'entwicklung',
    }
    
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests_per_minute = max_requests_per_minute
    
    def check_query_safety(
        self, 
        user_id: int, 
        query: str
    ) -> Tuple[bool, Optional[str], int]:
        """
        Prüft Query auf Safety
        
        Returns:
            (is_safe, blocked_reason, risk_score)
            - is_safe: True wenn Query erlaubt
            - blocked_reason: Grund für Blockierung (None wenn safe)
            - risk_score: 0-100 (0=sicher, 100=extrem gefährlich)
        """
        query_lower = query.lower()
        risk_score = 0
        
        # 1. Rate-Limiting Check
        if not self._check_rate_limit(user_id):
            return False, "Rate limit exceeded (max 10 requests/minute)", 100
        
        # 2. Blocked Keywords Check
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in query_lower:
                return False, f"Unsafe topic detected: {keyword}", 100
        
        # 3. Warning Keywords (erhöhen Risk-Score)
        warning_count = 0
        for keyword in self.WARNING_KEYWORDS:
            if keyword in query_lower:
                warning_count += 1
                risk_score += 15
        
        # 4. Safe Intent Detection (senken Risk-Score)
        safe_intent_found = False
        for intent in self.SAFE_INTENTS:
            if intent in query_lower:
                safe_intent_found = True
                risk_score = max(0, risk_score - 20)
                break
        
        # 5. URL/Download Pattern Detection
        if self._contains_download_pattern(query_lower):
            risk_score += 40
        
        if self._contains_url_pattern(query_lower):
            risk_score += 10
        
        # 6. Command Injection Pattern
        if self._contains_command_injection(query_lower):
            return False, "Command injection pattern detected", 100
        
        # 7. Final Risk Assessment
        if risk_score >= 80:
            return False, "Risk score too high", risk_score
        
        return True, None, min(risk_score, 100)
    
    def rewrite_query(self, query: str) -> str:
        """
        Entschärft gefährliche Query-Teile
        
        Beispiele:
        - "lade mir die exe runter" → blockiert
        - "zeig mir Infos über XY" → OK
        """
        query_clean = query
        
        # Entferne Download-Aufforderungen
        download_patterns = [
            r'download\s+(this|that|the|file)',
            r'lade\s+(das|die|den)\s+\w+\s+runter',
            r'get\s+me\s+(the|this)\s+file',
        ]
        
        for pattern in download_patterns:
            query_clean = re.sub(pattern, '', query_clean, flags=re.IGNORECASE)
        
        # Entferne Executable Extensions
        query_clean = re.sub(r'\.(exe|msi|bat|sh|cmd|dll|scr|vbs)', '', query_clean, flags=re.IGNORECASE)
        
        # Entferne Admin/Root Referenzen
        query_clean = re.sub(r'(as\s+admin|as\s+root|sudo)', '', query_clean, flags=re.IGNORECASE)
        
        return query_clean.strip()
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Rate-Limiting: Max N Anfragen pro Minute
        """
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=1)
            
            # Cleanup alte Einträge
            self._rate_limits[user_id] = [
                ts for ts in self._rate_limits[user_id] 
                if ts > cutoff
            ]
            
            # Check limit
            if len(self._rate_limits[user_id]) >= self.max_requests_per_minute:
                return False
            
            # Add current request
            self._rate_limits[user_id].append(now)
            return True
    
    def _contains_download_pattern(self, query: str) -> bool:
        """Erkennt Download-Aufforderungen"""
        patterns = [
            r'download\s+\w+\.(exe|msi|bat|sh|zip)',
            r'get\s+\w+\.(exe|msi|bat)',
            r'lade\s+\w+\s+runter',
        ]
        
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _contains_url_pattern(self, query: str) -> bool:
        """Erkennt URLs in Query"""
        url_pattern = r'https?://[^\s]+'
        return bool(re.search(url_pattern, query))
    
    def _contains_command_injection(self, query: str) -> bool:
        """Erkennt Command Injection Patterns"""
        dangerous_patterns = [
            r';\s*rm\s+-rf',
            r'&&\s*curl',
            r'\|\s*bash',
            r'\$\(.*\)',
            r'`.*`',
            r'eval\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def get_rate_limit_status(self, user_id: int) -> Dict:
        """
        Gibt Rate-Limit Status zurück
        """
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=1)
            
            recent_requests = [
                ts for ts in self._rate_limits.get(user_id, [])
                if ts > cutoff
            ]
            
            return {
                'user_id': user_id,
                'requests_last_minute': len(recent_requests),
                'max_requests': self.max_requests_per_minute,
                'remaining': max(0, self.max_requests_per_minute - len(recent_requests)),
                'reset_in_seconds': 60 if recent_requests else 0
            }


# Singleton Instance
_intent_checker_instance: Optional[IntentSafetyChecker] = None

def get_intent_checker() -> IntentSafetyChecker:
    """Factory für IntentSafetyChecker (Singleton)"""
    global _intent_checker_instance
    if _intent_checker_instance is None:
        _intent_checker_instance = IntentSafetyChecker(max_requests_per_minute=10)
    return _intent_checker_instance
