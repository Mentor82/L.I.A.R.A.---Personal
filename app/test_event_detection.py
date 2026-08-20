"""
Test Script für Event Detection Improvements
Version 2.1.0
"""

from liara_engine.actions.intent_detector import get_intent_detector
import json

# Test-Sätze
TEST_MESSAGES = [
    "Termin morgen um 10 Uhr",
    "Termin morgen um 10 in der Firma",
    "Meeting morgen 14 Uhr Raum 310",
    "Termin übermorgen um 9",
    "Besprechung heute um 15:30",
    "Meeting mit Thomas morgen um 11",
    "Termin 10 Uhr morgen",
    "morgen 10 Uhr Termin",
    "um 10 morgen meeting",
    "Termin nächste Woche Montag"
]

def test_event_detection():
    """Testet Event-Erkennung mit verschiedenen Eingaben"""
    detector = get_intent_detector()
    
    print("=" * 80)
    print("EVENT DETECTION TEST - Version 2.1.0")
    print("=" * 80)
    print()
    
    for i, message in enumerate(TEST_MESSAGES, 1):
        print(f"\n{'='*80}")
        print(f"Test #{i}: \"{message}\"")
        print(f"{'='*80}")
        
        # Intent Detection
        intent = detector.detect(message)
        print(f"✓ Intent: {intent}")
        
        if intent == 'create_event':
            # Event Details Extraction
            details = detector.extract_event_details(message)
            
            print(f"\n📅 Event Details:")
            print(f"  Title:      {details['title']}")
            print(f"  Location:   {details.get('location', 'N/A')}")
            print(f"  Start:      {details.get('start_time', 'N/A')}")
            print(f"  End:        {details.get('end_time', 'N/A')}")
            print(f"  Type:       {details.get('event_type', 'N/A')}")
            
            # Validierung
            errors = []
            
            # 1. Titel sollte nicht der ganze Satz sein
            if details['title'] == message or len(details['title']) > 80:
                errors.append(f"❌ Titel zu lang oder identisch mit Input: \"{details['title']}\"")
            else:
                print(f"  ✓ Titel OK")
            
            # 2. Location sollte nicht "termin" sein
            if details.get('location') and 'termin' in details['location'].lower():
                errors.append(f"❌ Location fehlerhaft: \"{details['location']}\"")
            elif details.get('location'):
                print(f"  ✓ Location OK")
            
            # 3. Zeit sollte existieren
            if not details.get('start_time'):
                errors.append(f"❌ Keine Start-Zeit gefunden")
            else:
                print(f"  ✓ Zeit OK")
            
            # 4. Event Type sollte korrekt sein
            if details.get('event_type') not in ['meeting', 'private', 'other']:
                errors.append(f"❌ Event Type ungültig: {details.get('event_type')}")
            else:
                print(f"  ✓ Event Type OK")
            
            if errors:
                print(f"\n⚠️  Probleme gefunden:")
                for error in errors:
                    print(f"  {error}")
            else:
                print(f"\n✅ Alle Validierungen bestanden!")
        else:
            print(f"❌ Falscher Intent erkannt: {intent} (erwartet: create_event)")


if __name__ == "__main__":
    test_event_detection()
