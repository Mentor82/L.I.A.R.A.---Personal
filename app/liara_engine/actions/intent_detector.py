"""
Intent Detection & Action Execution
Erkennt User-Intents und führt Aktionen aus (Calendar, Tasks, Notes)
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class IntentDetector:
    """Erkennt Intents aus Chat-Nachrichten"""
    
    # Muster für verschiedene Intents (Reihenfolge wichtig!)
    #
    # Every keyword alternative gets a LEADING \b only (not a trailing one) -
    # confirmed live that a plain trailing \b breaks legitimate inflected
    # forms ("Aufgaben" doesn't end where the stem "aufgabe" does, so
    # \baufgabe\b never matches it - only \baufgabe does, since nothing
    # requires the match to end at a word boundary). The leading \b alone
    # already fixes the actual bug: "Checkliste" no longer false-matches the
    # bare "liste" alternative (no boundary between "Check" and "liste",
    # both word chars) and "update_task_checklist" (a tool name) no longer
    # false-matches "task" (surrounded by "_", also a word char) - both
    # were hijacking messages that were never asking to list/create a task.
    PATTERNS = {
        # List/Show Intents (müssen ZUERST geprüft werden)
        'list_tasks': [
            r'\b(?:zeig|show|liste|anzeig).*\b(?:task|aufgabe|todo|to-do)',
            r'\b(?:welche|was für|meine).*\b(?:task|aufgabe|todo|to-do)',
            r'\b(?:task|aufgabe|todo|to-do).*\b(?:liste|übersicht|anzeig)',
            r'(?:was\s+muss\s+ich|was\s+ist\s+zu\s+tun)',
        ],
        'list_events': [
            r'\b(?:zeig|show|liste|anzeig).*\b(?:termin|meeting|event|kalender)',
            r'\b(?:welche|was für|meine).*\b(?:termin|meeting|event)',
            r'\b(?:termin|event|kalender).*\b(?:liste|übersicht|anzeig)',
            r'(?:was\s+steht\s+(?:heute|morgen|an))',
        ],
        'list_notes': [
            r'\b(?:zeig|show|liste|anzeig).*\b(?:notiz|note|erinnerung)',
            r'\b(?:welche|was für|meine).*\b(?:notiz|note|erinnerung)',
            r'\b(?:notiz|note|erinnerung).*\b(?:liste|übersicht|anzeig)',
        ],
        # Create Events (Termine & zeitgebundene Erinnerungen)
        'create_event': [
            r'\b(?:erstell|mach|hinzufüg|neu|trag|plan|setz).*\b(?:termin|meeting|event|besprechung|kalender)',
            r'\b(?:termin|meeting|besprechung|event).*(?:morgen|übermorgen|heute|nächste|um\s+\d+|\d+:\d+|\d+\s*uhr)',
            r'\b(?:erinner|remind).*\b(?:mich|me).*(?:morgen|übermorgen|heute|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|um\s+\d+|\d+:\d+|\d+\s*uhr|am\s+\d+)',
        ],
        # Create Tasks (To-Dos)
        'create_task': [
            r'\b(?:erstell|mach|hinzufüg|neu|add|trag).*\b(?:task|aufgabe|todo|to-do)',
            r'(?:muss|sollte|will)\s+(?:ich\s+)?(?:noch\s+)?(?:erledigen|machen|kaufen|besorgen)',
        ],
        # Create Notes (Notizen & allgemeine Erinnerungen/Gedächtnis)
        'create_note': [
            r'\b(?:erstell|mach|hinzufüg|neu|speicher|schreib|notier).*\b(?:notiz|note)',
            r'merk\s+(?:dir|es)',  # "merk dir", "merk es"
            r'\b(?:erinner|remind).*\b(?:mich|me)',  # Allgemeine Erinnerung
            r'(?:neue|create)\s+(?:erinnerung|reminder)',
        ]
    }
    
    def detect(self, message: str) -> Optional[str]:
        """
        Erkennt den Intent aus einer Nachricht
        
        Returns:
            Intent-Name oder None
        """
        message_lower = message.lower()
        
        # Prüfe jeden Intent
        for intent, patterns in self.PATTERNS.items():
            # Mindestens 1 Pattern muss matchen
            if any(re.search(pattern, message_lower) for pattern in patterns):
                return intent
        
        return None
    
    def extract_event_details(self, message: str) -> Dict:
        """Extrahiert Event-Details aus Nachricht"""
        details = {
            'title': None,
            'description': message,
            'start_time': None,
            'end_time': None,
            'location': None,
            'event_type': 'meeting'
        }
        
        # Event-Type ZUERST bestimmen (wird für Titel-Fallback gebraucht)
        if re.search(r'(?:privat|personal|familie)', message, re.IGNORECASE):
            details['event_type'] = 'private'
        elif re.search(r'(?:meeting|besprechung|firma|büro|raum)', message, re.IGNORECASE):
            details['event_type'] = 'meeting'
        else:
            details['event_type'] = 'other'
        
        # Extrahiere Location
        # Spezifische Patterns zuerst, dann generisch
        location = None
        
        # Pattern 1: Raumnummern (höchste Priorität)
        raum_match = re.search(r'(?:raum|zimmer|room)\s+(\d+[a-z]?)', message, re.IGNORECASE)
        if raum_match:
            location = f"Raum {raum_match.group(1)}"
        
        # Pattern 2: Firma/Büro
        if not location:
            firma_match = re.search(r'(?:in|bei)\s+(?:der\s+)?(firma|büro|arbeitsplatz|office)', message, re.IGNORECASE)
            if firma_match:
                loc_raw = firma_match.group(1).lower()
                if 'firm' in loc_raw:
                    location = 'Firma'
                elif 'büro' in loc_raw or 'office' in loc_raw:
                    location = 'Büro'
                else:
                    location = loc_raw.capitalize()
        
        # Pattern 3: Generische Orte (nur wenn kein Zeit-Keyword)
        if not location:
            gen_match = re.search(r'(?:in|bei|at|@)\s+([A-Za-zäöüß]+)', message, re.IGNORECASE)
            if gen_match:
                loc_candidate = gen_match.group(1)
                # Filtere Zeit- und Trigger-Keywords
                exclude_keywords = ['morgen', 'heute', 'übermorgen', 'der', 'die', 'das', 'termin', 'meeting', 'nächste', 'woche']
                if loc_candidate.lower() not in exclude_keywords:
                    location = loc_candidate
        
        details['location'] = location
        
        # Extrahiere Titel mit intelligenten Mustern
        title = None
        
        # Pattern 1: Expliziter Titel mit Anführungszeichen
        quoted_match = re.search(r'["\']([^"\']+)["\']', message)
        if quoted_match:
            title = quoted_match.group(1).strip()
        
        # Pattern 2: Kontext-basierte Erkennung
        if not title:
            # "Meeting" oder "Termin" oder "Erinnere mich an" + Kontext
            context_patterns = [
                r'(?:erinner|remind).*?(?:an|at)\s+([a-zA-ZäöüÄÖÜß\s]+?)(?:\s+um|\s+morgen|\s+heute|\s+in|$)',
                r'(?:meeting|termin|besprechung|treffen)\s+(?:mit\s+)?([a-zA-ZäöüÄÖÜß\s]+?)(?:\s+um|\s+morgen|\s+heute|\s+in|$)',
                r'(?:meeting|termin)\s+([^um]+?)(?:\s+um|\s+morgen|$)'
            ]
            
            for pattern in context_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip()
                    # Filtere Trigger-Wörter und Zeit-Keywords raus
                    time_keywords = ['morgen', 'heute', 'übermorgen', 'nächste', 'woche']
                    if candidate and len(candidate) > 2 and candidate.lower() not in ['der', 'die', 'das', 'in', 'bei', 'den', 'dem'] + time_keywords:
                        title = candidate
                        break
        
        # Pattern 3: Raum/Ort in Titel integrieren
        if not title and details['location']:
            title = f"Meeting {details['location']}"
        
        # Pattern 4: Generischer Fallback
        if not title:
            # Entferne Trigger-Wörter und Zeit-Angaben
            cleaned = re.sub(r'(?:erstell|mach|neu|add|hinzufüg|termin|meeting|event|besprechung|erinnere\s+mich\s+an|erinnere\s+mich|erinnerung)\s*', '', message, flags=re.IGNORECASE)
            cleaned = re.sub(r'(?:morgen|heute|übermorgen|nächste\s+woche|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'(?:um\s+)?\d{1,2}(?::\d{2})?\s*(?:uhr|h)?', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Mehrfach-Spaces entfernen
            
            # Auch Location aus Titel filtern wenn vorhanden
            if details['location']:
                cleaned = cleaned.replace(details['location'], '').strip()
            
            if cleaned and len(cleaned) > 2:
                title = cleaned[:50]
            else:
                # Wenn nichts übrig: Default basierend auf Event-Type
                if details['event_type'] == 'meeting':
                    title = "Meeting"
                else:
                    title = "Termin"
        
        details['title'] = title
        
        # Extrahiere Zeitangaben
        time_info = self._extract_time(message)
        if time_info:
            details['start_time'] = time_info['start']
            details['end_time'] = time_info['end']
        
        return details
    
    def extract_task_details(self, message: str) -> Dict:
        """Extrahiert Task-Details aus Nachricht"""
        details = {
            'title': None,
            'description': message,
            'priority': 'medium',
            'tags': []
        }
        
        # Extrahiere Titel
        title_patterns = [
            r'(?:task|aufgabe|todo)\s+["\']?([^"\']+)["\']?',
            r'["\']([^"\']+)["\']',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                details['title'] = match.group(1).strip()
                break
        
        if not details['title']:
            # Nutze ganzen Text als Titel (ohne Trigger-Wörter)
            title = re.sub(r'(?:erstelle|mach|add|hinzufügen|neue)\s+(?:task|aufgabe|todo)', '', message, flags=re.IGNORECASE)
            details['title'] = title.strip()[:200]
        
        # Erkenne Priorität
        if re.search(r'(?:urgent|wichtig|asap|dringend|high)', message, re.IGNORECASE):
            details['priority'] = 'high'
        elif re.search(r'(?:später|someday|low|unwichtig)', message, re.IGNORECASE):
            details['priority'] = 'low'
        
        # Extrahiere Tags
        tags = re.findall(r'#(\w+)', message)
        if tags:
            details['tags'] = tags
        
        return details
    
    def extract_note_details(self, message: str) -> Dict:
        """Extrahiert Notiz-Details aus Nachricht"""
        details = {
            'title': None,
            'content': message,
            'category': None,
            'tags': []
        }
        
        # Extrahiere Titel mit verschiedenen Patterns
        title_patterns = [
            # Pattern 1: Mit Doppelpunkt "merk dir: TEXT" oder "Notiz: TEXT"
            r'(?:notiz|note|merk\s+dir|merk\s+es|erinner|remind).*?:\s*(.+)',
            # Pattern 2: Nach "dass" - "merk dir dass TEXT"
            r'merk\s+(?:dir|es)\s+dass\s+(.+)',
            # Pattern 3: Nach "an" - "erinnere mich an TEXT"
            r'erinner.*?(?:an|at)\s+(.+)',
            # Pattern 4: "remind me to TEXT"
            r'remind\s+me\s+to\s+(.+)',
            # Pattern 5: Mit Anführungszeichen
            r'(?:notiz|note)\s+["\']([^"\']+)["\']',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                title_candidate = match.group(1).strip()
                # Entferne Trigger-Wörter am Ende wenn vorhanden
                title_candidate = re.sub(r'\s+(?:erstell|mach|speicher)$', '', title_candidate, flags=re.IGNORECASE)
                details['title'] = title_candidate[:100]  # Max 100 Zeichen für Titel
                break
        
        # Wenn kein Titel gefunden: Intelligenter Fallback
        if not details['title']:
            # Entferne Trigger-Wörter am Anfang
            cleaned = re.sub(r'^(?:erstell|mach|neu|speicher|schreib|merk\s+dir|erinner|neue)\s+(?:eine\s+)?(?:notiz|note|erinnerung)?\s*:?\s*', '', message, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            
            if cleaned and len(cleaned) > 2:
                # Erste 50 Zeichen als Titel
                details['title'] = cleaned[:50] + ('...' if len(cleaned) > 50 else '')
            else:
                # Absolute Fallback
                details['title'] = message[:50] + ('...' if len(message) > 50 else '')
        
        # Content ist immer die Original-Nachricht
        details['content'] = message
        
        # Extrahiere Kategorie
        category_match = re.search(r'(?:kategorie|category):\s*(\w+)', message, re.IGNORECASE)
        if category_match:
            details['category'] = category_match.group(1)
        else:
            # Auto-Kategorie basierend auf Keywords
            if re.search(r'(?:meeting|besprechung|call|protokoll)', message, re.IGNORECASE):
                details['category'] = 'meetings'
            elif re.search(r'(?:idee|idea|brainstorm)', message, re.IGNORECASE):
                details['category'] = 'ideas'
            elif re.search(r'(?:einkauf|shopping|kaufen|besorgen)', message, re.IGNORECASE):
                details['category'] = 'shopping'
            elif re.search(r'(?:arzt|doctor|health|gesundheit)', message, re.IGNORECASE):
                details['category'] = 'health'
        
        # Extrahiere Tags
        tags = re.findall(r'#(\w+)', message)
        if tags:
            details['tags'] = tags
        
        return details
    
    def _extract_time(self, message: str) -> Optional[Dict]:
        """Extrahiert Zeitangaben aus Nachricht mit erweitertem Parsing"""
        now = datetime.now()
        base_date = now
        
        # Relative Zeit-Patterns (Reihenfolge wichtig!)
        # "übermorgen" MUSS vor "morgen" geprüft werden
        if re.search(r'übermorgen', message, re.IGNORECASE):
            base_date = now + timedelta(days=2)
        # "morgen"
        elif re.search(r'morgen', message, re.IGNORECASE):
            base_date = now + timedelta(days=1)
        # "nächste Woche Montag" etc.
        elif re.search(r'nächste\s+woche', message, re.IGNORECASE):
            base_date = now + timedelta(days=7)
            # TODO: Wochentag-Erkennung für v2.2
        # "heute"
        elif re.search(r'heute', message, re.IGNORECASE):
            base_date = now
        # Wenn nur Uhrzeit ohne Tag → heute
        elif re.search(r'\d{1,2}(?::\d{2})?\s*(?:uhr|h)', message, re.IGNORECASE):
            base_date = now
        
        # Extrahiere Uhrzeit mit mehreren Pattern-Varianten
        time_patterns = [
            r'um\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr)?',  # "um 14 Uhr", "um 14:30"
            r'(\d{1,2}):(\d{2})\s*(?:uhr)?',            # "14:30 Uhr", "14:30"
            r'(\d{1,2})\s*(?:uhr|h)(?!\d)',             # "14 Uhr", "14h"
        ]
        
        hour = None
        minute = 0
        
        for pattern in time_patterns:
            time_match = re.search(pattern, message, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                if time_match.lastindex >= 2 and time_match.group(2):
                    minute = int(time_match.group(2))
                break
        
        # Wenn Uhrzeit gefunden
        if hour is not None:
            # Validiere Stunde (0-23)
            if 0 <= hour <= 23:
                start_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Standard-Dauer: 1 Stunde
                # TODO v2.2: Dauer aus Text extrahieren ("2 Stunden", "30 Minuten")
                end_time = start_time + timedelta(hours=1)
                
                return {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
        
        # Fallback: Keine Zeit gefunden → Default 9-10 Uhr
        start_time = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        return {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        }


# Singleton
_detector = None

def get_intent_detector() -> IntentDetector:
    """Get or create intent detector"""
    global _detector
    if _detector is None:
        _detector = IntentDetector()
    return _detector
