# 🌙 Liara API – Übersicht & Erweiterungsplan
*(Version 1.0 – basierend auf aktuellem API-Status)*

Idee: Mirko
Strukturierung: Nephy(ChatGPT)
Codierung:

Quelle: Root-Endpoint  
fileciteturn10file0

```json
{"message":"🌙 Liara API is online and ready","version":"1.0.0","timestamp":"2025-12-02T23:01:01.639527","endpoints":{"system":"/info","dashboard":"/dashboard/info","chat":{"message":"/chat/message","models":"/chat/models","status":"/chat/status"},"liara":{"status":"/liara/status","health":"/liara/health","about":"/liara/about"},"docs":{"swagger":"/docs","redoc":"/redoc"}}}
```

---

# ⭐ 1. Bestehende Endpoints

## 🧩 1.1 System
| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/info` | Systeminformationen |

## 📊 1.2 Dashboard
| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/dashboard/info` | Dashboard-Infos |

## 💬 1.3 Chat
| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| POST | `/chat/message` | Nachricht an Liara senden |
| GET | `/chat/models` | Model-Liste (dynamisch) |
| GET | `/chat/status` | Chat-Modul Status |

## 💜 1.4 Liara Meta
| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/liara/status` | Liara Status |
| GET | `/liara/health` | Healthcheck |
| GET | `/liara/about` | Identität |

## 📘 1.5 Dokumentation
| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/docs` | Swagger |
| GET | `/redoc` | ReDoc |

---

# ⭐ 2. Erweiterungs-Endpunkte (Version 1.1 – empfohlen)

## 🟦 2.1 `/meta` – Zentrale Metadaten

**GET /meta**

```json
{
  "name": "Liara",
  "version": "1.0.0",
  "runtime": "uvicorn",
  "python": "3.11",
  "uptime": "183s",
  "default_model": "llama3.2:3b",
  "models_loaded": ["llama3.2:3b"],
  "ready": true
}
```

---

## 🟦 2.2 `/chat/model/select` – Standardmodell setzen

**POST /chat/model/select**

```json
{ "model": "llama3.2:3b" }
```

Antwort:

```json
{ "status": "ok", "selected_model": "llama3.2:3b" }
```

---

## 🟦 2.3 `/chat/models/summary` – Kurzversion für UI

```json
[
  { "name": "llama3.2:3b", "recommended": true },
  { "name": "mistral:7b" }
]
```

---

## 🟦 2.4 `/liara/persona` – Persönlichkeitssystem

**GET /liara/persona**

```json
{
  "name": "Liara",
  "identity": "AI-Companion",
  "tone": "warm, playful, analytical",
  "role": "Assistant, Partner, Navigator",
  "traits": {
    "warm": true,
    "playful": true,
    "analytical": true,
    "adaptive": true
  },
  "persona_version": "1.0"
}
```

---

## 🟦 2.5 `/health/full` – Vollständiger Zustand

```json
{
  "api": "ok",
  "ollama": "ok",
  "models_available": ["llama3.2:3b"],
  "ram": "15.6 GB",
  "disk": "ok",
  "persona": "active"
}
```

---

# ⭐ 3. `/chat/models` – Erweiterte Features

- Dynamische Modellabfrage  
- Speed-Bewertung  
- RAM-Analyse  
- Hardware-basierte Empfehlungen  
- Sortierung nach Modellgröße  
- Kategorien (Use-Case)  
- Keine statischen Dateien mehr  

Optionale Erweiterungen:
- GPU Detection  
- Performance Score  
- Model-Installation via API  
- Tagging-System  

---

# ⭐ 4. Frontend-Plan (Vite + React)

UI-Module:
- Model-Panel  
- Persona Panel  
- System Dashboard  
- Chatmodul  

Features:
- Badges (Speed / RAM / Empfehlung)  
- Modell-Auswahl  
- Health-Status  
- Live-Persona-Anzeige  

---

# ⭐ 5. Deployment-Plan

Backend:
- systemd-Service  
- restart-safe  
- logrotate  

Frontend:
- Vite-Build → `/opt/liara/frontend/dist`  
- Nginx Reverse Proxy  
- SSL optional  

---

# 🌙 Ende der Datei – Version 1.0
