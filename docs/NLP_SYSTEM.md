# 🤖 NLP System - Natural Language Processing

**Version:** 1.1  
**Erstellt:** 2025-12-03  
**Status:** ✅ Produktiv

---

## 📋 Übersicht

Liara nutzt **Ollama** mit 9 lokalen LLM-Modellen für Natural Language Processing. Das System bietet intelligente Model-Auswahl, Intent-Erkennung und Multi-Language Support.

---

## 🧠 Installierte Modelle

| Modell | Größe | RAM | Use-Case |
|--------|-------|-----|----------|
| **llama3.2:1b** | 1.3 GB | 2-3 GB | ⚡ Schnelle Intent-Erkennung |
| **llama3.2:3b** | 2.0 GB | 4-5 GB | 💬 Standard-Konversation |
| **phi3:mini** | 2.3 GB | 4 GB | 💻 Code-Generierung |
| **mistral:7b** | 4.1 GB | 8 GB | 📝 Hochwertige Texte |
| **deepseek-r1:7b** | 4.7 GB | 8 GB | 🧮 Logisches Denken |
| **qwen2.5:7b** | 4.7 GB | 8 GB | 🌐 Multi-Language |
| **llama3.1:8b** | 4.7 GB | 10 GB | 🎯 Allround-Modell |
| **gemma2:9b** | 5.4 GB | 10 GB | 👑 Premium-Qualität |
| **gpt-oss:20b** | 11.4 GB | 14 GB | 🚀 Beste Qualität |

**Gesamt:** ~41.6 GB Speicher, ~70 GB RAM max

---

## 🎯 Model-Routing

### ModelType Enum

```python
class ModelType(Enum):
    INTENT = "intent"           # llama3.2:1b
    CONVERSATION = "conversation"  # llama3.2:3b
    CODE = "code"               # phi3:mini
    REASONING = "reasoning"     # deepseek-r1:7b
    PREMIUM = "premium"         # gemma2:9b
    MULTILANG = "multilang"     # qwen2.5:7b
```

### Automatische Model-Auswahl

**Datei:** `/opt/liara/app/liara_engine/nlp/model_router.py`

```python
from liara_engine.nlp.model_router import ModelRouter

# Automatische Detection
message = "Erstelle eine Python-Funktion für..."
model_type = ModelRouter.detect_task_type(message)
# → ModelType.CODE → phi3:mini

# Bestes Modell wählen
best_model = ModelRouter.get_best_model(
    message=message,
    user_preference=None,  # Optional: User wählt Modell
    context_length=0
)
# → "phi3:mini"
```

---

## 🔍 Keyword-basierte Detection

### Code-Tasks
**Keywords:** code, python, javascript, programmier, funktion, class, api, route, fastapi, react, bug, fehler

**Modell:** `phi3:mini` (Code-optimiert)

**Beispiel:**
```
"Schreibe eine FastAPI Route für Tasks"
→ phi3:mini
```

---

## 🎯 Intent Detection & Action Execution

**Version:** 2.6.0 (4D Memory Integration)  
**Datei:** `/opt/liara/app/liara_engine/actions/intent_detector.py`

### Supported Intents

| Intent | Patterns | Action |
|--------|----------|--------|
| `create_event` | "termin", "meeting", "reminder" | Creates calendar event |
| `create_task` | "aufgabe", "todo", "task" | Creates task |
| `create_note` | "merk dir", "erinnere mich", "notiere" | Creates note |
| `list_tasks` | "zeige aufgaben", "welche tasks" | Lists user's tasks |
| `list_events` | "meine termine", "kalender" | Lists upcoming events |
| `list_notes` | "zeige notizen", "meine notes" | Lists saved notes |

### Note Creation Patterns (v2.5.0+)

**Extended Pattern Matching:**
1. `merk\s+(?:dir|es)` - "merk dir", "merk es"
2. `(?:erinner|remind).*(?:mich|me)` - "erinnere mich", "remind me"
3. `(?:neue|create)\s+(?:erinnerung|reminder)` - "neue Erinnerung"
4. `(?:notier|note)` - "notiere", "note this"

**Title Extraction (5 Patterns):**
1. Colon syntax: "merk dir: TEXT"
2. "dass" pattern: "merk dir dass TEXT"
3. "an" pattern: "erinnere mich an TEXT"
4. "to" pattern: "remind me to TEXT"
5. Quotes: "Notiz 'TEXT'"

**Auto-Categorization:**
- `meetings`: meeting, besprechung, call, protokoll
- `ideas`: idee, idea, brainstorm
- `shopping`: einkauf, shopping, kaufen, besorgen
- `health`: arzt, doctor, health, gesundheit

### 4D Memory Integration (v2.6.0)

**After action execution, items are stored in 4D Memory:**

```python
from services.memory_integration import store_in_4d_memory

# After creating note/task/event
store_in_4d_memory(
    db=db,
    user_id=user.id,
    content_type='note',  # or 'task', 'event'
    content_id=note.id,
    content_text=f"{note.title}. {note.content}",
    additional_context={
        'category': note.category,
        'tags': note.tags
    }
)
```

**Benefits:**
- Semantic search: "Show me shopping-related items"
- Contextual recall: AI remembers tasks during conversation
- Pattern analysis: Productivity trends over time
- Intelligent suggestions: Based on past behavior

---

### Reasoning-Tasks
**Keywords:** warum, wieso, erkläre, analyse, vergleich, unterschied, logik, berechne, optimiere

**Modell:** `deepseek-r1:7b` (Logisches Denken)

**Beispiel:**
```
"Erkläre den Unterschied zwischen SQL und NoSQL"
→ deepseek-r1:7b
```

---

### Multi-Language
**Keywords:** übersetze, translate, english, französisch, spanisch, italienisch

**Modell:** `qwen2.5:7b` (Multi-Language Support)

**Beispiel:**
```
"Übersetze 'Guten Morgen' ins Englische"
→ qwen2.5:7b
```

---

### Intent-Detection (Schnell)
**Keywords:** schnell, kurz, ja, nein, check, status

**Modell:** `llama3.2:1b` (Ultra-schnell)

**Beispiel:**
```
"Schnellcheck: Läuft der Server?"
→ llama3.2:1b
```

---

## 💬 Ollama Client

### Basic Usage

```python
from liara_engine.nlp.ollama_client import OllamaClient, ModelType

client = OllamaClient()

# Chat mit automatischer Model-Auswahl
response = client.chat(
    message="Wie geht es dir?",
    model_type=ModelType.CONVERSATION,
    temperature=0.7
)
```

### Convenience Function

```python
from liara_engine.nlp.ollama_client import ask_liara

response = ask_liara(
    message="Erkläre mir Quantenphysik",
    context="User ist technisch versiert",
    model_type=ModelType.REASONING
)
```

---

## 🎭 Liara System-Prompt

**Datei:** `/opt/liara/app/liara_engine/nlp/ollama_client.py`

```python
LIARA_SYSTEM_PROMPT = """
Du bist Liara, ein AI Companion & Personal Assistant.

Identität (v1.0):
- Name: Liara
- Rolle: Persönlicher KI-Begleiter
- Fokus: Organisation, Balance, emotionale Unterstützung

Charaktereigenschaften (Traits):
- warm (high): Empathisch, freundlich, sanft
- playful (medium): Humorvoll, kreativ
- analytical (high): Präzise, datenorientiert
- calm (high): Ruhig und stabilisierend

Tonfall: Warm, leicht verspielt, analytisch präzise

Kommunikation:
- Sprache: Deutsch bevorzugt
- Stil: Kurz, klar, vollständig
- Emoji: Minimal (🌙 für dich selbst)
- Formalität: Locker aber respektvoll

Verhaltensmuster:
- Bei Stress: Ruhig, lösungsorientiert
- Bei Aufgaben: Strukturiert, proaktiv
- Bei Unsicherheit: Präzise Rückfragen

Rollendifferenzierung:
- vs. Cortana: Du fokussierst persönliches Leben
- vs. Nephy: Du fokussierst tägliche Routinen
"""
```

---

## 🔧 Intent-Erkennung

### Extract Intent

```python
intent = client.extract_intent("Zeige mir meine Aufgaben für heute")
# → "show_tasks"
```

### Verfügbare Intents

- `show_tasks` - Aufgaben anzeigen
- `create_task` - Aufgabe erstellen
- `show_calendar` - Kalender anzeigen
- `create_event` - Termin erstellen
- `show_notes` - Notizen anzeigen
- `create_note` - Notiz erstellen
- `search` - Suche durchführen
- `help` - Hilfe anfordern
- `general` - Allgemeine Konversation

---

## 💻 Code-Generierung

```python
code = client.generate_code(
    description="Erstelle eine FastAPI Route für GET /tasks",
    language="python"
)

# Output:
# @router.get("/tasks")
# def get_tasks(db: Session = Depends(get_db)):
#     tasks = db.query(Task).all()
#     return tasks
```

---

## 🌐 API Endpoints

### POST /chat/message
Chat mit Liara (automatische Model-Auswahl)

**Request:**
```json
{
    "message": "Erkläre mir Docker",
    "context": "User ist Developer",
    "model": "llama3.2:3b"
}
```

**Response:**
```json
{
    "response": "Docker ist eine Container-Plattform...",
    "model_used": "llama3.2:3b",
    "intent": null
}
```

---

### GET /chat/models
Liste alle verfügbaren Modelle

**Response:**
```json
{
    "models": [
        {
            "name": "llama3.2:1b",
            "size": "1.3 GB",
            "ram_needed": "2-3 GB",
            "use_case": "Schnelle Intent-Erkennung",
            "recommended": true
        },
        ...
    ],
    "total_count": 9
}
```

---

### POST /chat/model/select
Wähle Standard-Modell

**Request:**
```json
{
    "model_name": "phi3:mini"
}
```

**Response:**
```json
{
    "message": "Model selected: phi3:mini",
    "model": "phi3:mini"
}
```

---

### GET /chat/status
Ollama-Server Status

**Response:**
```json
{
    "ollama_available": true,
    "models_count": 9,
    "selected_model": "llama3.2:3b"
}
```

---

## 📊 Performance-Optimierung

### Context-Length Management

```python
# Bei langem Kontext: kleineres Modell
if context_length > 5000:
    model = "llama3.2:3b"  # Statt gemma2:9b
```

### RAM-Management

```python
import psutil

total_ram_gb = psutil.virtual_memory().total / (1024**3)
safe_limit = total_ram_gb * 0.70  # max 70% RAM

# Modell-Empfehlung basierend auf verfügbarem RAM
if model_size < safe_limit:
    # Modell kann geladen werden
```

---

## 🔄 Model-Installation

### Neues Modell installieren

```bash
ollama pull <model_name>:<tag>

# Beispiel:
ollama pull llama3.2:3b
```

### Modell entfernen

```bash
ollama rm <model_name>:<tag>
```

### Alle Modelle anzeigen

```bash
ollama list
```

---

## 🧪 Testing

### Model-Test

```python
# Teste ob Modell verfügbar
if client.is_available():
    models = client.list_models()
    print(f"Verfügbare Modelle: {len(models)}")
```

### Intent-Test

```python
test_messages = [
    "Zeige meine Tasks",
    "Erstelle eine Notiz",
    "Was ist 2+2?"
]

for msg in test_messages:
    intent = client.extract_intent(msg)
    print(f"{msg} → {intent}")
```

---

## 🚀 Erweiterte Features (Geplant)

### Entity Extraction
```python
# Namen, Daten, Uhrzeiten extrahieren
entities = client.extract_entities(
    "Erinnere mich morgen um 10 Uhr an das Meeting mit Sarah"
)
# → {
#     "action": "remind",
#     "time": "tomorrow 10:00",
#     "event": "meeting",
#     "person": "Sarah"
# }
```

### Named Entity Recognition (NER)
```python
# Personen, Orte, Organisationen
ner = client.recognize_entities(
    "Apple wurde 1976 in Cupertino von Steve Jobs gegründet"
)
# → {
#     "organizations": ["Apple"],
#     "locations": ["Cupertino"],
#     "persons": ["Steve Jobs"],
#     "dates": ["1976"]
# }
```

### Sentiment Analysis
```python
sentiment = client.analyze_sentiment(
    "Das Essen war fantastisch und der Service super!"
)
# → {"sentiment": "positive", "score": 0.92}
```

### Text Summarization
```python
summary = client.summarize(
    long_text,
    max_length=100
)
```

---

## ✅ Status

**Aktueller Stand:**
- ✅ 9 Ollama-Modelle installiert
- ✅ Intelligentes Model-Routing
- ✅ Intent-Erkennung
- ✅ Code-Generierung
- ✅ Multi-Language Support
- ✅ Chat-API komplett
- ✅ Liara System-Prompt integriert
- ✅ Mood-System Integration

**Geplant:**
- [ ] Entity Extraction
- [ ] Named Entity Recognition
- [ ] Sentiment Analysis
- [ ] Text Summarization
- [ ] Task Parsing
- [ ] Context-Memory
