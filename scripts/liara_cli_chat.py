#!/usr/bin/env python3
"""
Liara CLI Chat: Sende Nachrichten an die Liara-API direkt aus dem Terminal/SSH.
"""
import requests
import sys
import os
import getpass


API_URL = os.getenv('LIARA_API_URL', 'http://localhost:8100')
USERNAME = os.getenv('LIARA_USER', 'admin')
MAX_ATTEMPTS = 3

def get_token():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        password = os.getenv('LIARA_PASS')
        if not password:
            password = getpass.getpass(f"Passwort für {USERNAME}: ")
        auth_resp = requests.post(f"{API_URL}/auth/login", json={"username": USERNAME, "password": password})
        if auth_resp.ok:
            return auth_resp.json().get('access_token')
        else:
            print(f"Login fehlgeschlagen ({attempt}/{MAX_ATTEMPTS}):", auth_resp.json().get('detail', auth_resp.text))
            if attempt < MAX_ATTEMPTS:
                os.environ['LIARA_PASS'] = ''  # erzwinge erneute Passworteingabe
    print("Maximale Login-Versuche überschritten. Beende.")
    sys.exit(1)

token = get_token()
headers = {"Authorization": f"Bearer {token}"}

# Hole aktive Chat-Session oder erstelle eine neue

sessions_resp = requests.get(f"{API_URL}/chat/sessions/", headers=headers)
try:
    sessions = sessions_resp.json()
except Exception as e:
    print("Fehler beim Parsen der Antwort von /chat/sessions/:", e)
    print("Status Code:", sessions_resp.status_code)
    print("Antwort:", sessions_resp.text)
    sys.exit(1)
if sessions:
    session_id = sessions[0]['id']
else:
    session_resp = requests.post(f"{API_URL}/chat/sessions/", json={"title": "CLI-Chat"}, headers=headers)
    try:
        session = session_resp.json()
    except Exception as e:
        print("Fehler beim Parsen der Antwort von /chat/sessions/ (POST):", e)
        print("Status Code:", session_resp.status_code)
        print("Antwort:", session_resp.text)
        sys.exit(1)
    session_id = session['id']

print("Willkommen im Liara CLI-Chat! (Beenden mit Ctrl+C)")
while True:
    try:
        msg = input("Du: ").strip()
        if not msg:
            continue
        # Sende Nachricht
        resp = requests.post(f"{API_URL}/chat/messages/", json={"session_id": session_id, "content": msg, "role": "user"}, headers=headers)
        if not resp.ok:
            print("Fehler beim Senden:", resp.text)
            continue
        # Lade alle Nachrichten der Session
        messages = requests.get(f"{API_URL}/chat/messages/session/{session_id}", headers=headers).json()
        # Zeige nur die letzten 2 Nachrichten (User+Bot)
        for m in messages[-2:]:
            who = "Du" if m['role'] == 'user' else 'Liara'
            print(f"{who}: {m['content']}")
    except KeyboardInterrupt:
        print("\nChat beendet.")
        break
