# Liara API Documentation

**Version**: 1.2.0  
**Base URL**: `http://localhost:8100`  
**Authentication**: JWT Bearer Token (required for protected endpoints)

## Table of Contents

- [Authentication](#authentication)
  - [Register](#register)
  - [Login](#login)
  - [Get Current User](#get-current-user)
  - [Logout](#logout)
- [Core APIs](#core-apis)
  - [Health & System Info](#health--system-info)
  - [Chat & AI](#chat--ai)
  - [Mood System](#mood-system)
- [CRUD APIs](#crud-apis)
  - [Tasks](#tasks)
  - [Calendar](#calendar)
  - [Notes](#notes)
- [Advanced Features](#advanced-features)
  - [GPU Detection](#gpu-detection)
  - [Ollama Management](#ollama-management)

---

## Authentication

Liara uses JWT (JSON Web Tokens) for authentication. Protected endpoints require a Bearer token in the Authorization header.

### Register

#### `POST /auth/register`
Create a new user account

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "johndoe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-12-03T03:40:00.000000",
    "last_login": null
  }
}
```

**Roles:**
- `admin`: Full system access, can manage users
- `user`: Standard access, can manage own data (default)
- `guest`: Read-only access

### Login

#### `POST /auth/login`
Authenticate and get JWT token

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securepass123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "johndoe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-12-03T03:40:00.000000",
    "last_login": "2025-12-03T03:45:00.000000"
  }
}
```

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123` (⚠️ Change after first login!)

### Get Current User

#### `GET /auth/me`
Get authenticated user information

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "id": 2,
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-12-03T03:40:00.000000",
  "last_login": "2025-12-03T03:45:00.000000"
}
```

### Logout

#### `POST /auth/logout`
Logout (client-side token removal)

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "message": "Logged out successfully",
  "username": "johndoe"
}
```

**Note:** JWT tokens are stateless. Logout is client-side - delete the token from storage.

---

## Core APIs

### Health & System Info

#### `GET /`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "mood_system": "active",
  "features": {
    "chat": true,
    "tasks": true,
    "calendar": true,
    "notes": true,
    "mood_tracking": true,
    "gpu_detection": true,
    "ollama_integration": true
  }
}
```

#### `GET /info`
System information

**Response:**
```json
{
  "hostname": "liara",
  "os": "Linux",
  "cpu_count": 12,
  "uptime_seconds": 86400
}
```

---

## Chat & AI

### `GET /chat/models`
List available Ollama models with metadata

**Response:**
```json
{
  "models": [
    {
      "name": "llama3.2:3b",
      "size": "2.0 GB",
      "modified": "2025-12-01T10:30:00",
      "ram_requirement": "4 GB",
      "gpu_recommended": false,
      "speed": "⚡⚡⚡",
      "quality": "⭐⭐⭐",
      "tags": ["fast", "lightweight", "cpu"]
    }
  ]
}
```

### `POST /chat/message`
Chat with Liara (includes Intent Detection & Action Execution)

**Request:**
```json
{
  "message": "Erstelle einen Termin morgen um 14 Uhr Meeting mit Team",
  "model": "llama3.2:3b",
  "context": "Optional context"
}
```

**Response:**
```json
{
  "response": "✅ Termin 'Meeting mit Team' wurde erstellt!",
  "model_used": "llama3.2:3b",
  "intent": "create_event",
  "action_result": {
    "success": true,
    "action": "create_event",
    "event_id": 2,
    "title": "Meeting mit Team",
    "start_time": "2025-12-04T14:00:00",
    "message": "✅ Termin 'Meeting mit Team' wurde erstellt!"
  }
}
```

**Supported Intents:**
- `create_event` - Calendar events (triggers: "termin", "meeting", "kalender")
- `create_task` - Tasks (triggers: "task", "aufgabe", "todo")
- `create_note` - Notes (triggers: "notiz", "note", "speicher")

### `GET /chat/stream`
SSE streaming endpoint for real-time chat

**Query Parameters:**
- `message` - User message
- `model` - Model name (default: llama3.2:3b)

**Response:** Server-Sent Events stream
```
data: {"chunk": "Hello", "done": false}
data: {"chunk": " world", "done": false}
data: {"chunk": "", "done": true}
```

---

## Mood System

### `GET /mood/current`
Get current mood state

**Response:**
```json
{
  "current_mood": {
    "tone": {
      "primary": {
        "focused": 0.75,
        "curious": 0.60,
        "playful": 0.45,
        "stressed": 0.20,
        "creative": 0.55,
        "supportive": 0.80,
        "social": 0.50
      },
      "confidence": 0.85
    },
    "timestamp": "2025-12-03T10:30:00"
  },
  "interaction_count": 42,
  "last_interaction": "2025-12-03T10:30:00"
}
```

### `GET /mood/history`
Get mood history (last 50 entries)

**Response:**
```json
{
  "history": [
    {
      "tone": { /* mood data */ },
      "timestamp": "2025-12-03T10:30:00",
      "confidence": 0.85
    }
  ],
  "total_entries": 50
}
```

### `POST /mood/reset`
Reset mood system to defaults

**Response:**
```json
{
  "status": "success",
  "message": "Mood system reset to default state"
}
```

---

## CRUD APIs

## Tasks

### `GET /tasks/`
List all tasks

**Query Parameters:**
- `completed` (bool) - Filter by completion status
- `priority` (string) - Filter by priority (low/medium/high)

**Response:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Fix Bug",
      "description": "Login issue",
      "priority": "high",
      "completed": false,
      "due_date": "2025-12-05T10:00:00",
      "tags": ["urgent", "backend"],
      "created_at": "2025-12-03T09:00:00",
      "updated_at": "2025-12-03T09:00:00"
    }
  ],
  "total": 5,
  "completed_count": 2
}
```

### `POST /tasks/`
Create new task

**Request:**
```json
{
  "title": "New Task",
  "description": "Task description",
  "priority": "medium",
  "tags": ["work", "dev"]
}
```

### `GET /tasks/{task_id}`
Get single task

### `PUT /tasks/{task_id}`
Update task

### `DELETE /tasks/{task_id}`
Delete task

### `POST /tasks/{task_id}/complete`
Mark task as complete

### `POST /tasks/{task_id}/uncomplete`
Mark task as incomplete

---

## Calendar

### `GET /calendar/`
List all events

**Response:**
```json
{
  "events": [
    {
      "id": 1,
      "title": "Team Meeting",
      "description": "Weekly sync",
      "start_time": "2025-12-03T10:00:00",
      "end_time": "2025-12-03T11:00:00",
      "location": "Zoom",
      "event_type": "meeting",
      "all_day": false,
      "recurrence": null,
      "created_at": "2025-12-01T09:00:00",
      "updated_at": "2025-12-01T09:00:00"
    }
  ],
  "total": 3
}
```

### `POST /calendar/`
Create new event

**Request:**
```json
{
  "title": "Meeting",
  "description": "Team sync",
  "start_time": "2025-12-04T14:00:00",
  "end_time": "2025-12-04T15:00:00",
  "location": "Office",
  "event_type": "meeting"
}
```

### `GET /calendar/today`
Get today's events

### `GET /calendar/week`
Get this week's events

### `GET /calendar/conflicts`
Check for scheduling conflicts

**Query Parameters:**
- `start` - Start datetime
- `end` - End datetime

### `GET /calendar/free`
Find free time slots

**Query Parameters:**
- `start` - Start datetime
- `end` - End datetime
- `duration` - Duration in minutes

### `GET /calendar/{event_id}`
Get single event

### `PUT /calendar/{event_id}`
Update event

### `DELETE /calendar/{event_id}`
Delete event

---

## Notes

### `GET /notes/`
List all notes

**Query Parameters:**
- `pinned_only` (bool) - Only pinned notes
- `archived` (bool) - Include archived notes
- `category` (string) - Filter by category

**Response:**
```json
{
  "notes": [
    {
      "id": 1,
      "title": "Meeting Notes",
      "content": "Key points from today's meeting...",
      "category": "meetings",
      "tags": ["important", "team"],
      "is_pinned": true,
      "is_archived": false,
      "created_at": "2025-12-03T09:00:00",
      "updated_at": "2025-12-03T09:30:00"
    }
  ],
  "total": 10
}
```

### `POST /notes/`
Create new note

**Request:**
```json
{
  "title": "Note Title",
  "content": "Note content",
  "category": "ideas",
  "tags": ["brainstorm"]
}
```

### `GET /notes/search`
Search notes

**Query Parameters:**
- `q` - Search query

### `GET /notes/{note_id}`
Get single note

### `PUT /notes/{note_id}`
Update note

### `DELETE /notes/{note_id}`
Delete note

### `POST /notes/{note_id}/pin`
Pin note

### `POST /notes/{note_id}/unpin`
Unpin note

### `POST /notes/{note_id}/archive`
Archive note

### `POST /notes/{note_id}/unarchive`
Unarchive note

---

## Advanced Features

## GPU Detection

### `GET /gpu/detect`
Detect GPU and get model recommendations

**Response:**
```json
{
  "gpu_available": true,
  "gpu_info": {
    "name": "NVIDIA GeForce RTX 3060",
    "vram_total": "12 GB",
    "driver_version": "550.54.15",
    "cuda_version": "12.4"
  },
  "recommended_models": [
    {
      "name": "llama3.1:8b",
      "size": "4.9 GB",
      "reason": "Fits in VRAM with headroom"
    }
  ]
}
```

---

## Ollama Management

### `GET /ollama/models`
List installed Ollama models with storage info

**Response:**
```json
{
  "models": [
    {
      "name": "llama3.2:3b",
      "size": "2.0 GB",
      "size_bytes": 2000000000,
      "modified": "2025-12-01T10:30:00"
    }
  ],
  "total_models": 9,
  "total_size": "42.6 GB",
  "total_size_bytes": 42600000000
}
```

### `POST /ollama/pull`
Pull/download a model

**Request:**
```json
{
  "model": "deepseek-r1:7b"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Model deepseek-r1:7b pulled successfully",
  "model": "deepseek-r1:7b"
}
```

### `DELETE /ollama/models/{model}`
Delete a model

**Response:**
```json
{
  "status": "success",
  "message": "Model llama3.2:1b deleted successfully"
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

---

## Rate Limiting

Currently no rate limiting is enforced. Production deployments should implement rate limiting via nginx.

---

## CORS

CORS is enabled for all origins in development. Production should restrict to specific origins.

---

## Authentication

HTTP Basic Auth is available but disabled by default. Enable via:

```bash
export LIARA_AUTH_ENABLED=true
```

Credentials are stored in `/opt/liara/app/.htpasswd` (Apache htpasswd format).
