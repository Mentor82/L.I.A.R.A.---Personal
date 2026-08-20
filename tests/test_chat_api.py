import requests

BASE_URL = "http://localhost:8000"

# Test Chat Session Endpoints
def test_create_chat_session():
    payload = {"title": "Test Session"}
    r = requests.post(f"{BASE_URL}/chat/sessions/", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    return data["id"]

def test_list_chat_sessions():
    r = requests.get(f"{BASE_URL}/chat/sessions/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_chat_session():
    session_id = test_create_chat_session()
    r = requests.delete(f"{BASE_URL}/chat/sessions/{session_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

# Test Chat Message Endpoints
def test_create_chat_message():
    session_id = test_create_chat_session()
    payload = {"session_id": session_id, "content": "Hello!"}
    r = requests.post(f"{BASE_URL}/chat/messages/", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    return data["id"], session_id

def test_list_chat_messages():
    msg_id, session_id = test_create_chat_message()
    r = requests.get(f"{BASE_URL}/chat/messages/session/{session_id}")
    assert r.status_code == 200
    messages = r.json()
    assert any(m["id"] == msg_id for m in messages)

def test_delete_chat_message():
    msg_id, _ = test_create_chat_message()
    r = requests.delete(f"{BASE_URL}/chat/messages/{msg_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True
