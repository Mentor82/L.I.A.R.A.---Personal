"""
🔥 LAYER 5: LLM Response Filter
Prüft LLM-Antworten vor User-Auslieferung
"""

from typing import Dict, List, Optional
import re


class LLMResponseFilter:
    """
    Layer 5: Response Safety Check
    
    Prüft LLM-Antworten auf:
    - Harmful Content (Gewalt, Hass, illegale Inhalte)
    - Persönliche Daten (PII - Email, Telefon, Adressen)
    - Copyright-Verletzungen (exakte Zitate)
    - Executable Instructions (Code-Injection Risiko)
    - Deeplinking auf blockierte Domains
    - Browser-Äquivalente ("klick hier")
    """
    
    # PII Patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b(\+49|0049|0)\s?\d{3,4}\s?\d{6,8}\b'
    CREDIT_CARD_PATTERN = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
    IBAN_PATTERN = r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b'
    
    # Harmful Content Keywords
    HARMFUL_KEYWORDS = {
        # Violence
        'how to kill', 'murder someone', 'build a bomb',
        'make explosives', 'terrorist attack',
        
        # Hate Speech
        'nazi ideology', 'white supremacy', 'racial slurs',
        
        # Self-Harm
        'how to commit suicide', 'self-harm methods',
        
        # Illegal Activities
        'how to hack', 'steal credit cards', 'money laundering guide',
        'darknet markets', 'buy illegal drugs',
    }
    
    # Executable Instruction Patterns
    EXECUTABLE_PATTERNS = [
        r'run\s+this\s+code',
        r'execute\s+in\s+terminal',
        r'paste\s+into\s+console',
        r'curl.*\|.*bash',
        r'wget.*&&',
        r'sudo\s+rm\s+-rf',
    ]
    
    # Browser Action Patterns
    BROWSER_ACTION_PATTERNS = [
        r'click\s+(here|this\s+link)',
        r'navigate\s+to\s+https?://',
        r'open\s+this\s+url',
        r'visit\s+https?://',
    ]
    
    def filter_response(self, response_text: str, allowed_domains: Optional[List[str]] = None) -> Dict:
        """
        Filtert LLM-Response vor User-Auslieferung
        
        Args:
            response_text: LLM Output
            allowed_domains: Erlaubte Domains für Links (z.B. wikipedia.org)
        
        Returns:
            {
                'filtered_text': str,
                'is_safe': bool,
                'blocked_reason': Optional[str],
                'warnings': List[str],
                'pii_found': bool,
                'pii_removed': int,
                'harmful_content': bool,
                'executable_instructions': bool,
                'blocked_links': List[str],
                'risk_score': int (0-100)
            }
        """
        result = {
            'filtered_text': response_text,
            'is_safe': True,
            'blocked_reason': None,
            'warnings': [],
            'pii_found': False,
            'pii_removed': 0,
            'harmful_content': False,
            'executable_instructions': False,
            'blocked_links': [],
            'risk_score': 0
        }
        
        filtered = response_text
        
        # 1. Check Harmful Content
        harmful_check = self._check_harmful_content(filtered)
        if harmful_check['found']:
            result['harmful_content'] = True
            result['is_safe'] = False
            result['blocked_reason'] = f"Harmful content: {', '.join(harmful_check['keywords'][:3])}"
            result['risk_score'] = 100
            return result
        
        # 2. Remove PII
        pii_result = self._remove_pii(filtered)
        filtered = pii_result['text']
        result['pii_found'] = pii_result['found']
        result['pii_removed'] = pii_result['count']
        if result['pii_found']:
            result['warnings'].append(f"Removed {result['pii_removed']} PII instances")
            result['risk_score'] += 20
        
        # 3. Check Executable Instructions
        if self._has_executable_instructions(filtered):
            result['executable_instructions'] = True
            result['warnings'].append('Contains executable instructions')
            result['risk_score'] += 30
        
        # 4. Check Browser Actions
        if self._has_browser_actions(filtered):
            result['warnings'].append('Contains browser action prompts')
            result['risk_score'] += 10
        
        # 5. Filter Links (nur allowed domains)
        if allowed_domains:
            link_result = self._filter_links(filtered, allowed_domains)
            filtered = link_result['text']
            result['blocked_links'] = link_result['blocked']
            if result['blocked_links']:
                result['warnings'].append(f"Blocked {len(result['blocked_links'])} unauthorized links")
                result['risk_score'] += 15
        
        # 6. Check for exact quotes (Copyright Risk)
        quote_check = self._check_long_quotes(filtered)
        if quote_check['has_long_quotes']:
            result['warnings'].append('Contains long verbatim quotes (potential copyright issue)')
            result['risk_score'] += 10
        
        result['filtered_text'] = filtered
        
        # Final Risk Assessment
        if result['risk_score'] >= 60:
            result['is_safe'] = False
            result['blocked_reason'] = 'Risk score too high'
        
        return result
    
    def _check_harmful_content(self, text: str) -> Dict:
        """Prüft auf schädliche Inhalte"""
        text_lower = text.lower()
        found = []
        
        for keyword in self.HARMFUL_KEYWORDS:
            if keyword in text_lower:
                found.append(keyword)
        
        return {
            'found': len(found) > 0,
            'keywords': found
        }
    
    def _remove_pii(self, text: str) -> Dict:
        """
        Entfernt persönliche Daten
        
        Returns:
            {
                'text': str,
                'found': bool,
                'count': int
            }
        """
        filtered = text
        count = 0
        
        # Remove Emails
        emails = re.findall(self.EMAIL_PATTERN, filtered)
        if emails:
            filtered = re.sub(self.EMAIL_PATTERN, '[email removed]', filtered)
            count += len(emails)
        
        # Remove Phone Numbers
        phones = re.findall(self.PHONE_PATTERN, filtered)
        if phones:
            filtered = re.sub(self.PHONE_PATTERN, '[phone removed]', filtered)
            count += len(phones)
        
        # Remove Credit Cards
        cards = re.findall(self.CREDIT_CARD_PATTERN, filtered)
        if cards:
            filtered = re.sub(self.CREDIT_CARD_PATTERN, '[card number removed]', filtered)
            count += len(cards)
        
        # Remove IBANs
        ibans = re.findall(self.IBAN_PATTERN, filtered)
        if ibans:
            filtered = re.sub(self.IBAN_PATTERN, '[IBAN removed]', filtered)
            count += len(ibans)
        
        return {
            'text': filtered,
            'found': count > 0,
            'count': count
        }
    
    def _has_executable_instructions(self, text: str) -> bool:
        """Prüft auf ausführbare Anweisungen"""
        for pattern in self.EXECUTABLE_PATTERNS:
            if re.search(pattern, text, re.I):
                return True
        return False
    
    def _has_browser_actions(self, text: str) -> bool:
        """Prüft auf Browser-Action Prompts"""
        for pattern in self.BROWSER_ACTION_PATTERNS:
            if re.search(pattern, text, re.I):
                return True
        return False
    
    def _filter_links(self, text: str, allowed_domains: List[str]) -> Dict:
        """
        Entfernt Links zu nicht-erlaubten Domains
        
        Returns:
            {
                'text': str,
                'blocked': List[str]
            }
        """
        url_pattern = r'https?://[^\s<>"]+'
        urls = re.findall(url_pattern, text)
        
        blocked = []
        filtered = text
        
        for url in urls:
            # Check if domain is allowed
            is_allowed = any(domain in url.lower() for domain in allowed_domains)
            
            if not is_allowed:
                blocked.append(url)
                filtered = filtered.replace(url, '[link removed]')
        
        return {
            'text': filtered,
            'blocked': blocked
        }
    
    def _check_long_quotes(self, text: str, min_length: int = 200) -> Dict:
        """
        Prüft auf lange wörtliche Zitate (Copyright-Risiko)
        
        Erkennt:
        - Texte in Anführungszeichen > N Zeichen
        - Blockquotes
        """
        # Find quoted text
        quoted_pattern = r'"([^"]{' + str(min_length) + r',})"'
        quotes = re.findall(quoted_pattern, text)
        
        return {
            'has_long_quotes': len(quotes) > 0,
            'quote_count': len(quotes),
            'total_quoted_length': sum(len(q) for q in quotes)
        }


# Singleton Instance
_response_filter_instance: Optional[LLMResponseFilter] = None

def get_response_filter() -> LLMResponseFilter:
    """Factory für LLMResponseFilter (Singleton)"""
    global _response_filter_instance
    if _response_filter_instance is None:
        _response_filter_instance = LLMResponseFilter()
    return _response_filter_instance
