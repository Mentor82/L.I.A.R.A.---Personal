# 🎨 Frontend - React + Vite UI

**Version:** 1.0  
**Erstellt:** 2025-12-03  
**Status:** ✅ Produktiv

---

## 📋 Übersicht

Liara's Frontend ist eine moderne **React + Vite** Single-Page Application mit Dark Theme und Real-time Backend-Integration.

---

## 🛠️ Tech Stack

| Technologie | Version | Zweck |
|------------|---------|-------|
| **React** | 19.2.0 | UI Framework |
| **Vite** | 7.2.4 | Build Tool & Dev Server |
| **ESLint** | - | Code Quality |
| **Node.js** | 20.x | Runtime |

---

## 📁 Projektstruktur

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat.jsx           # Chat-Interface
│   │   ├── Chat.css
│   │   ├── MoodStatus.jsx     # Mood-Display
│   │   └── MoodStatus.css
│   ├── services/
│   │   └── api.js             # API-Client
│   ├── App.jsx                # Main Component
│   ├── App.css
│   ├── main.jsx               # Entry Point
│   └── index.css              # Global Styles
├── public/                    # Static Assets
├── index.html                 # HTML Entry
├── vite.config.js             # Vite Configuration
├── package.json
└── eslint.config.js
```

---

## 🚀 Setup & Installation

### Dependencies installieren

```bash
cd /opt/liara/frontend
npm install
```

### Development Server starten

```bash
npm run dev
# → http://localhost:5173
```

### Production Build

```bash
npm run build
# → dist/ Ordner
```

### Linting

```bash
npm run lint
```

---

## ⚙️ Vite Configuration

**Datei:** `vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

**Proxy-Funktion:**
- Frontend-Request: `/api/chat/message`
- Backend-Request: `http://localhost:8100/chat/message`

---

## 🎨 Components

### 1. Chat Component

**Datei:** `src/components/Chat.jsx`

**Features:**
- Message-Input mit Enter-to-Send
- Message-History (User + Liara)
- Loading-Indicator (animierte Punkte)
- Model-Display
- Error-Handling

**State Management:**
```javascript
const [message, setMessage] = useState('');
const [messages, setMessages] = useState([]);
const [loading, setLoading] = useState(false);
```

**Message Format:**
```javascript
{
    role: 'user' | 'assistant' | 'error',
    content: 'Message text',
    model: 'llama3.2:3b'  // Optional
}
```

**Styling:**
- User-Messages: Rechts, Purple Gradient
- Liara-Messages: Links, Blue Border
- Error-Messages: Center, Red Border
- Loading: Animierte Punkte

---

### 2. MoodStatus Component

**Datei:** `src/components/MoodStatus.jsx`

**Features:**
- Emoji-Anzeige des aktuellen Moods
- Intensitäts-Anzeige (%)
- Trait-Modifiers als Balken
- Last Interaction
- Auto-Refresh (5s)
- Manual Refresh Button

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

### 3. App Component

**Datei:** `src/App.jsx`

**Layout:**
```javascript
<div className="app">
  <header>
    <h1>🌙 Liara - AI Companion</h1>
  </header>
  
  <div className="app-content">
    <div className="main-section">
      <Chat />
    </div>
    
    <aside className="sidebar">
      <MoodStatus />
    </aside>
  </div>
</div>
```

**Grid-Layout:**
- Desktop: 2-Column (Chat + Sidebar)
- Mobile: 1-Column (Stacked)

---

## 🌐 API Client

**Datei:** `src/services/api.js`

### Chat API

```javascript
import { chatAPI } from './services/api';

// Send Message
const response = await chatAPI.sendMessage(
    "Hallo Liara",
    "Optional context"
);

// Get Models
const models = await chatAPI.getModels();

// Get Status
const status = await chatAPI.getStatus();
```

---

### Mood API

```javascript
import { moodAPI } from './services/api';

// Get Status
const moodStatus = await moodAPI.getStatus();

// Get Modifiers
const modifiers = await moodAPI.getModifiers();

// Get Available States
const states = await moodAPI.getStates();

// Reset Mood
await moodAPI.reset();
```

---

### Persona API

```javascript
import { personaAPI } from './services/api';

// Get Persona
const persona = await personaAPI.getPersona();

// Get Status
const status = await personaAPI.getStatus();

// Get Health
const health = await personaAPI.getHealth();
```

---

### System API

```javascript
import { systemAPI } from './services/api';

// Get System Info
const info = await systemAPI.getInfo();

// Get Dashboard
const dashboard = await systemAPI.getDashboard();

// Get Full Health
const health = await systemAPI.getFullHealth();
```

---

## 🎨 Styling

### Color Scheme (Dark Theme)

```css
:root {
    --bg-primary: #1e1e2e;
    --bg-secondary: #2a2a3e;
    --text-primary: #e0e0e0;
    --text-secondary: #999;
    --accent-primary: #667eea;
    --accent-secondary: #764ba2;
}
```

### Gradients

```css
/* Purple Gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Dark Background */
background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
```

---

## 📱 Responsive Design

### Breakpoints

```css
@media (max-width: 1024px) {
    .app-content {
        grid-template-columns: 1fr;
    }
}
```

**Desktop (>1024px):**
- 2-Column Grid
- Chat links, Mood rechts

**Tablet/Mobile (≤1024px):**
- 1-Column Stack
- Chat oben, Mood unten

---

## 🔄 Auto-Refresh

### MoodStatus Component

```javascript
useEffect(() => {
    fetchMoodStatus();
    
    // Auto-refresh alle 5 Sekunden
    const interval = setInterval(fetchMoodStatus, 5000);
    
    return () => clearInterval(interval);
}, []);
```

---

## 🚦 Systemd Service

**Datei:** `/etc/systemd/system/liara-frontend.service`

```ini
[Unit]
Description=Liara Frontend (Vite Dev Server)
After=network.target

[Service]
Type=simple
User=mirko
WorkingDirectory=/opt/liara/frontend
ExecStart=/usr/bin/npm run dev -- --host --port 5173
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
# Service starten
sudo systemctl start liara-frontend

# Service stoppen
sudo systemctl stop liara-frontend

# Service neu starten
sudo systemctl restart liara-frontend

# Service Status
systemctl status liara-frontend
```

---

## 🌐 Zugriff

**Development:**
- **Lokal:** http://localhost:5173
- **Netzwerk:** http://192.168.178.50:5173
- **Hostname:** http://liara:5173

**Production:**
- Build mit `npm run build`
- Serve `dist/` mit nginx oder Apache

---

## 🧪 Testing

### Manual Testing

```bash
# Backend läuft?
curl http://localhost:8100/

# Frontend läuft?
curl http://localhost:5173/

# API-Proxy funktioniert?
# Im Browser: http://localhost:5173
# Console: Fetch /api/mood/status
```

---

## 📦 Dependencies

**Datei:** `package.json`

```json
{
    "dependencies": {
        "react": "^19.2.0",
        "react-dom": "^19.2.0"
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.3.4",
        "vite": "^7.2.4",
        "eslint": "^9.20.0"
    }
}
```

---

## 🚀 Geplante Features

### Tasks Component
```javascript
<Tasks />
// - Create Task
// - List Tasks
// - Mark Complete
// - Filter by Priority
```

### Calendar Component
```javascript
<Calendar />
// - Show Events
// - Create Event
// - Day/Week/Month View
```

### Notes Component
```javascript
<Notes />
// - Create Note
// - Search Notes
// - Tag Management
// - Pin/Archive
```

### Settings Component
```javascript
<Settings />
// - Model Selection
// - Theme Toggle
// - Language
// - Notifications
```

---

## ✅ Status

**Aktuell implementiert:**
- ✅ React + Vite Setup
- ✅ Chat Component
- ✅ MoodStatus Component
- ✅ API Client
- ✅ Dark Theme
- ✅ Responsive Design
- ✅ Auto-Refresh
- ✅ Systemd Service
- ✅ Vite Proxy

**Geplant:**
- [ ] Tasks Component
- [ ] Calendar Component
- [ ] Notes Component
- [ ] Settings Component
- [ ] Notification System
- [ ] PWA Support
- [ ] Offline Mode
