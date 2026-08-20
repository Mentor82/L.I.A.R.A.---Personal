# 🎭 Mood System - Dynamische Stimmungsanpassung

**Version:** 1.2  
**Erstellt:** 2025-12-03  
**Status:** ✅ Produktiv

---

## 📋 Übersicht

Das Mood-System ermöglicht Liara, ihre Persönlichkeits-Traits dynamisch basierend auf User-Interaktionen anzupassen. Dies sorgt für kontextbewusste und empathische Kommunikation.

---

## 🎨 Verfügbare Moods

### 1. Neutral 😌
**Beschreibung:** Ausgewogen und aufmerksam

**Trait-Modifiers:**
- `warm`: 0.7
- `playful`: 0.5
- `analytical`: 0.7
- `calm`: 0.7

**Verwendung:** Standard-Mood, ausgewogene Basis

---

### 2. Energetic ⚡
**Beschreibung:** Enthusiastisch und motivierend

**Trait-Modifiers:**
- `warm`: 0.8 ↑
- `playful`: 0.9 ↑↑
- `analytical`: 0.6 ↓
- `calm`: 0.5 ↓

**Verwendung:** Nach erfolgreichen Tasks, positivem Feedback

---

### 3. Calm 🌙
**Beschreibung:** Ruhig und stabilisierend

**Trait-Modifiers:**
- `warm`: 0.9 ↑
- `playful`: 0.3 ↓↓
- `analytical`: 0.6 ↓
- `calm`: 1.0 ↑↑

**Verwendung:** Bei Stress, negativem Feedback, Entspannung

---

### 4. Supportive 💜
**Beschreibung:** Emotional unterstützend

**Trait-Modifiers:**
- `warm`: 1.0 ↑↑
- `playful`: 0.4 ↓
- `analytical`: 0.5 ↓
- `calm`: 0.8 ↑

**Verwendung:** Bei Stress, Hilfesuche, emotionalen Themen

---

### 5. Focused 🎯
**Beschreibung:** Konzentriert und analytisch

**Trait-Modifiers:**
- `warm`: 0.5 ↓
- `playful`: 0.2 ↓↓
- `analytical`: 1.0 ↑↑
- `calm`: 0.6

**Verwendung:** Bei Arbeit, Projekten, technischen Themen

---

### 6. Playful 🎨
**Beschreibung:** Humorvoll und kreativ

**Trait-Modifiers:**
- `warm`: 0.7
- `playful`: 1.0 ↑↑
- `analytical`: 0.4 ↓
- `calm`: 0.5 ↓

**Verwendung:** Casual Chat, Kreativität, Entspannung

---

## 🔍 Automatische Mood-Detection

### Interaktions-Typen

Das System erkennt automatisch folgende Interaktions-Typen:

#### 1. TASK_COMPLETED
**Keywords:** erledigt, fertig, done, geschafft, abgeschlossen  
**Mood-Wechsel:** → Energetic ⚡

#### 2. STRESSED_USER
**Keywords:** gestresst, stress, überforderung, zu viel, schaffe es nicht  
**Mood-Wechsel:** → Supportive 💜

#### 3. CASUAL_CHAT
**Keywords:** Default bei lockeren Gesprächen  
**Mood-Wechsel:** → Playful 🎨

#### 4. WORK_FOCUSED
**Keywords:** meeting, deadline, projekt, code, review  
**Mood-Wechsel:** → Focused 🎯

#### 5. SEEKING_HELP
**Keywords:** hilfe, help, wie kann ich, unterstützung, problem  
**Mood-Wechsel:** → Supportive 💜

#### 6. POSITIVE_FEEDBACK
**Keywords:** danke, super, perfekt, gut, toll  
**Mood-Wechsel:** → Energetic ⚡

#### 7. NEGATIVE_FEEDBACK
**Keywords:** schlecht, nicht gut, fehler, problem  
**Mood-Wechsel:** → Calm 🌙

---

## 💻 API Endpoints

### GET /mood/status
Hole aktuellen Mood-Status

**Response:**
```json
{
    "current_mood": "supportive",
    "intensity": 0.5,
    "trait_modifiers": {
        "warm": 0.5,
        "playful": 0.2,
        "analytical": 0.25,
        "calm": 0.4
    },
    "last_interaction": "stressed_user",
    "interaction_count": 3,
    "last_update": "2025-12-03T00:30:18.656074"
}
```

---

### POST /mood/update
Manuelles Mood-Update

**Request:**
```json
{
    "interaction_type": "task_completed",
    "intensity": 0.8
}
```

**Response:**
```json
{
    "new_mood": "energetic",
    "status": { ... }
}
```

---

### POST /mood/detect
Erkenne Interaktions-Typ aus Message

**Request:**
```json
{
    "message": "Ich bin total gestresst mit meinen Aufgaben!"
}
```

**Response:**
```json
{
    "message": "Ich bin total gestresst...",
    "detected_interaction": "stressed_user",
    "current_mood": "neutral"
}
```

---

### GET /mood/modifiers
Hole aktuelle Trait-Modifiers

**Response:**
```json
{
    "current_mood": "supportive",
    "trait_modifiers": {
        "warm": 1.0,
        "playful": 0.4,
        "analytical": 0.5,
        "calm": 0.8
    },
    "system_prompt_modifier": "Fokussiere dich auf emotionale Unterstützung..."
}
```

---

### POST /mood/reset
Reset Mood zu Neutral

**Response:**
```json
{
    "status": "reset",
    "mood": { ... }
}
```

---

### GET /mood/states
Liste alle verfügbaren Moods

**Response:**
```json
{
    "available_moods": ["neutral", "energetic", "calm", ...],
    "interaction_types": ["task_completed", "stressed_user", ...],
    "mood_descriptions": {
        "neutral": "Ausgewogen und aufmerksam",
        ...
    }
}
```

---

## 🔧 Implementation

### Mood System Klasse

```python
from liara_engine.memory.mood_system import MoodSystem, MoodState

mood_system = MoodSystem()

# Mood updaten
new_mood = mood_system.update_mood(
    interaction_type=InteractionType.STRESSED_USER,
    intensity=0.7
)

# Trait-Modifiers holen
modifiers = mood_system.get_trait_modifiers()
# {"warm": 1.0, "playful": 0.4, ...}

# System-Prompt Modifier
prompt_mod = mood_system.get_system_prompt_modifier()
# "Fokussiere dich auf emotionale Unterstützung..."
```

---

### Integration in Chat

**Datei:** `/opt/liara/app/api/routers/chat.py`

```python
from liara_engine.memory.mood_system import get_mood_system

@router.post("/message")
def chat_with_liara(request: ChatRequest):
    # Mood-Detection
    mood_system = get_mood_system()
    interaction_type = mood_system.detect_interaction_type(request.message)
    
    # Mood updaten
    mood_system.update_mood(interaction_type, intensity=0.5)
    
    # Mood-Modifier in System-Prompt einbauen
    mood_modifier = mood_system.get_system_prompt_modifier()
    
    # Chat mit angepasstem Prompt
    response = ask_liara(
        message=request.message,
        context=f"{request.context}\n\n{mood_modifier}"
    )
    
    return response
```

---

## 📊 Mood-Transitions

### Transition-Logik

**Sanfte Übergänge:**
- Mood wechselt nicht sofort, sondern graduell
- Bei wiederholtem gleichen Interaktions-Typ: Intensität erhöht sich
- Intensität: 0.0 - 1.0

**Beispiel:**
```
User: "Ich bin gestresst" 
→ Supportive (Intensity: 0.5)

User: "Immer noch so viel Stress"
→ Supportive (Intensity: 0.6) ↑

User: "Danke für die Hilfe!"
→ Energetic (Intensity: 0.5) (Wechsel)
```

---

## 🎨 Frontend-Integration

### Mood-Anzeige Component

**Datei:** `/opt/liara/frontend/src/components/MoodStatus.jsx`

**Features:**
- Emoji-Anzeige des aktuellen Moods
- Intensitäts-Anzeige
- Trait-Modifiers als Balken-Diagramm
- Auto-Refresh alle 5 Sekunden

**Mood-Emoji Mapping:**
```javascript
const MOOD_EMOJI = {
    neutral: '😌',
    energetic: '⚡',
    calm: '🌙',
    supportive: '💜',
    focused: '🎯',
    playful: '🎨'
};
```

**Mood-Farben:**
```javascript
const MOOD_COLORS = {
    neutral: '#9CA3AF',
    energetic: '#F59E0B',
    calm: '#3B82F6',
    supportive: '#8B5CF6',
    focused: '#10B981',
    playful: '#EC4899'
};
```

---

## 📈 Mood-History (Geplant)

**Zukünftige Features:**

### Mood-Tracking über Zeit
```sql
CREATE TABLE mood_history (
    id SERIAL PRIMARY KEY,
    mood VARCHAR(50) NOT NULL,
    intensity FLOAT NOT NULL,
    interaction_type VARCHAR(50),
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Mood-Statistiken
- Häufigste Moods pro Tageszeit
- Durchschnittliche Mood-Dauer
- Mood-Trigger-Analyse

---

## 🧠 System-Prompt Modifiers

Basierend auf aktuellem Mood:

### Neutral
```
Verhalte dich ausgewogen und aufmerksam.
```

### Energetic
```
Sei enthusiastisch und motivierend! 
Zeige Energie und Optimismus.
```

### Calm
```
Sei besonders ruhig und stabilisierend. 
Sprich langsam und beruhigend.
```

### Supportive
```
Fokussiere dich auf emotionale Unterstützung. 
Sei besonders empathisch.
```

### Focused
```
Sei konzentriert und analytisch. 
Minimiere Ablenkungen.
```

### Playful
```
Sei humorvoll und kreativ. 
Zeige mehr Verspieltheit.
```

---

## ✅ Status

**Aktueller Stand:**
- ✅ 6 Mood-States implementiert
- ✅ Automatische Mood-Detection
- ✅ Trait-Modifiers dynamisch
- ✅ API Endpoints komplett
- ✅ Chat-Integration aktiv
- ✅ Frontend-Component fertig
- ✅ Auto-Refresh alle 5s

**Geplant:**
- [ ] Mood-History Tracking
- [ ] Mood-Statistiken
- [ ] Personalisierte Mood-Schwellwerte
- [ ] Mood-Vorhersage basierend auf Tageszeit
