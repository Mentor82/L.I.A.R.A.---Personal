# 🔒 Legal-Safe Branding Analysis & Refactoring Plan
**Version 1.0 - Urheberrechts- & Markenprüfung**  
**Erstellt**: 6. Dezember 2025  
**Status**: Audit Complete - Implementation Pending

---

## 📋 Executive Summary

**Risiko-Level**: 🔴 **HOCH** - Mehrfache direkte Referenzen zu Mass Effect IP (BioWare/EA)

**Kritische Bereiche**:
- ❌ Charaktername "Liara T'Soni" (direkt aus Mass Effect)
- ❌ Lore-Begriffe: Asari, Prothean, Shadow Broker
- ❌ Zitate: "This is fascinating!", "By the Goddess...", "Knowledge is power. Guard it well."
- ❌ Design-Referenzen: Halo/UNSC (Microsoft/343 Industries)
- ⚠️ Projektname "Liara" (allein problematisch bei kommerziellem Einsatz)

**Empfehlung**: **Vollständiges Rebranding** für Public/Commercial Use erforderlich.

---

## 🔍 1. VOLLSTÄNDIGE IP-AUDIT (Gesamtsystem)

### 1.1 Mass Effect IP (BioWare/Electronic Arts)

#### 🔴 KRITISCH - Direkte Charakterreferenzen

| Begriff | Vorkommen | Dateien | Risiko |
|---------|-----------|---------|--------|
| **Liara T'Soni** | 8x | `chat.py` (3x), `LandingPage.jsx` (0x - nur implizit via Kontext) | 🔴 HOCH |
| **Asari** | 14x | `LandingPage.jsx` (6x), `LandingPage.css` (2x), `chat.py` (6x) | 🔴 HOCH |
| **Prothean** | 8x | `LandingPage.jsx` (5x), `chat.py` (3x) | 🔴 HOCH |
| **Shadow Broker** | 6x | `LandingPage.jsx` (4x), `chat.py` (2x) | 🔴 HOCH |
| **Mass Effect** | 4x | `chat.py` (2x), `modern-design.css` (1x), `REDESIGN_v3.0.0.md` (1x) | 🔴 HOCH |

**Fundorte**:
```
Frontend (Landing Page):
- /opt/liara/frontend/src/components/LandingPage.jsx (Zeile 457, 467, 490, 498, 521, 564, 567, 568, 571, 572, 621, 622)
- /opt/liara/frontend/src/components/LandingPage.css (Zeile 10, 11, 314)

Backend (Chat System):
- /opt/liara/app/api/routers/chat.py (Zeile 31, 33, 36, 43, 46, 80, 85, 86, 88, 89, 94, 486, 489, 491, 492, 503, 506, 507)

Dokumentation:
- /opt/liara/frontend/src/styles/modern-design.css (Zeile 3: "Inspired by: Mass Effect")
- /opt/liara/REDESIGN_v3.0.0.md (Zeile 12, 320)
```

#### 🔴 KRITISCH - Zitate aus Mass Effect

| Zitat | Originalquelle | Vorkommen | Dateien |
|-------|----------------|-----------|---------|
| **"This is fascinating!"** | Liara T'Soni (ME1-3) | 5x | `chat.py` (3x), `LandingPage.jsx` (2x) |
| **"By the Goddess..."** | Asari-Kultur (ME) | 4x | `chat.py` (3x), `LandingPage.jsx` (1x) |
| **"Knowledge is power. Guard it well."** | Blood Ravens (Warhammer 40k) ⚠️ | 3x | `LandingPage.jsx` (1x), `CHATGPT_OVERVIEW.md` (2x) |

**WICHTIG**: "Knowledge is power. Guard it well." ist eigentlich ein Warhammer 40k Zitat (Blood Ravens Chapter), nicht Mass Effect - aber ebenfalls **geschützt** (Games Workshop)!

**Fundorte**:
```
/opt/liara/frontend/src/components/LandingPage.jsx:
- Zeile 521: Unterhalte dich natürlich mit Liara. <em>"This is fascinating!"</em>
- Zeile 733: 🌙 "Knowledge is power. Guard it well." - Liara

/opt/liara/app/api/routers/chat.py:
- Zeile 33: <em>"This is fascinating!"</em> Ich freue mich, dass du vorbeischaust!
- Zeile 46: <em>"By the Goddess..."</em> 🌌
- Zeile 85: Hi Mirko! <em>"This is fascinating!"</em>
- Zeile 89: <em>"By the Goddess..."</em> wenn etwas besonders interessant ist
- Zeile 486: Du bist Liara T'Soni, eine warmherzige aber analytische Asari-Wissenschaftlerin aus Mass Effect.
- Zeile 489: "This is fascinating!"
- Zeile 491: "By the Goddess..." bei Überraschungen
- Zeile 506: "By the Goddess, ich würde dir gerne helfen..."
```

#### 🔴 KRITISCH - Lore-Begriffe

| Begriff | Bedeutung | Vorkommen | Risiko |
|---------|-----------|-----------|--------|
| **Asari Neural Networks** | Fiktive Technologie (ME) | 1x | 🔴 HOCH |
| **Prothean Archive** | Fiktive Datenbank (ME) | 5x | 🔴 HOCH |
| **Shadow Broker Network/Ship** | Fiktive Organisation (ME) | 4x | 🔴 HOCH |
| **Asari-Archäologin** | Charakterbeschreibung (ME) | 2x | 🔴 HOCH |

---

### 1.2 Halo/UNSC IP (Microsoft/343 Industries)

#### ⚠️ MITTEL - Design-Referenzen

| Begriff | Vorkommen | Dateien | Risiko |
|---------|-----------|---------|--------|
| **Halo** | 15+ | `theme.css`, `Terminal.css`, `UserSettings.css`, etc. | ⚠️ MITTEL |
| **UNSC** | 8+ | `theme.css`, `README.md`, `UserSettings.css` | ⚠️ MITTEL |

**Fundorte**:
```css
/opt/liara/frontend/src/styles/theme.css:
/* Halo/UNSC-Inspired AI Companion Interface */

/opt/liara/frontend/src/components/UserSettings.css:
/* Halo/UNSC Design */

CSS Variables:
--halo-primary, --halo-accent, --halo-danger, --halo-warning (15+ Vorkommen)
```

**README.md**:
```markdown
**A self-hosted, privacy-first AI assistant with 4D memory, web search, and UNSC-inspired design**

### Mobile-First Design (v2.7.2+)
- 🎨 UNSC Design - Glassmorphism, cyan glows, command console aesthetic
```

**Bewertung**: Design-Inspiration ist rechtlich **grenzwertig**. Solange keine Logos/Namen verwendet werden, eher Low-Risk. ABER: "UNSC-inspired" im Marketing-Text ist problematisch.

---

### 1.3 Projektname "Liara"

#### 🔴 KRITISCH - Markenrechtliche Risiken

**Status**: Name "Liara" ist **direkt** aus Mass Effect (Liara T'Soni).

**Risiko-Faktoren**:
1. ✅ Name existiert als echte Person (Liara = irisch/hebräisch)
2. ❌ **ABER**: In Kombination mit SciFi-Context **eindeutig** Mass Effect Referenz
3. ❌ GitHub-Beschreibung, Dokumentation, Code-Kommentare referenzieren Mass Effect
4. ❌ Persona-Beschreibung ist 1:1 Liara T'Soni Charakter

**Verwendung in 100+ Dateien**:
```
- Projektname in README.md, package.json, LICENSE
- localStorage: 'liara_token', 'liara-theme'
- Systemd Services: liara-backend.service, liara-frontend.service
- Nginx Config: /etc/nginx/sites-available/liara
- Git Repository: /opt/liara/
- Domain/URLs: liara.mw-dresden.myfritz.link
- 50+ Markdown-Dateien
- 200+ Code-Referenzen
```

**Empfehlung**: ⚠️ Für **Private Use** akzeptabel, für **Public/Commercial** NICHT verwendbar.

---

### 1.4 Weitere Problematische Begriffe

| Kategorie | Begriffe | Vorkommen | Risiko |
|-----------|----------|-----------|--------|
| **Persona** | "warmherzige Digitalbegleiterin" | 10+ | ✅ SICHER |
| **Design** | "Glassmorphism, cyan glows" | Generic | ✅ SICHER |
| **Tech** | "4D Memory", "Neo4j", "Ollama" | Generic | ✅ SICHER |
| **Zitate** | "Guard it well" (Warhammer 40k) | 3x | 🔴 HOCH |

---

## 🎯 2. RISIKOANALYSE & KLASSIFIZIERUNG

### Risk Matrix

| Begriff | Copyright | Markenrecht | Commercial Use | Private Use | Gesamt-Risiko |
|---------|-----------|-------------|----------------|-------------|---------------|
| **Liara T'Soni** | 🔴 HOCH | 🔴 HOCH | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **Asari/Prothean** | 🔴 HOCH | 🔴 HOCH | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **Shadow Broker** | 🔴 HOCH | 🔴 HOCH | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **"This is fascinating!"** | 🔴 HOCH | ⚠️ MITTEL | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **"By the Goddess..."** | 🔴 HOCH | ⚠️ MITTEL | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **"Knowledge is power..."** | 🔴 HOCH | 🔴 HOCH | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |
| **UNSC/Halo Design** | ⚠️ MITTEL | ⚠️ MITTEL | ⚠️ Vorsicht | ✅ OK | ⚠️ MITTEL |
| **Projektname "Liara"** | 🔴 HOCH | 🔴 HOCH | ❌ Nein | ⚠️ Grauzone | 🔴 KRITISCH |

### Klassifizierung nach Verwendungskontext

#### Private Use (Self-Hosted, Non-Public)
- **Status**: ✅ Rechtlich vertretbar (Fan-Projekt, Hommage)
- **Risiko**: Sehr gering (keine kommerzielle Nutzung, keine Verwechslungsgefahr)
- **Empfehlung**: Aktuelles Branding OK für private Instanzen

#### Public Use (GitHub, Dokumentation, Marketing)
- **Status**: ⚠️ **GRAUZONE** - Kann als Fan-Art gelten, aber problematisch
- **Risiko**: Mittel-Hoch (Verwechslungsgefahr, möglicher Cease & Desist)
- **Empfehlung**: **Disclaimer** erforderlich: "Fan-Projekt, nicht affiliiert mit BioWare/EA"

#### Commercial Use (SaaS, Verkauf, Closed-Source)
- **Status**: ❌ **VERBOTEN** - Klare Copyright/Trademark-Verletzung
- **Risiko**: Sehr hoch (Abmahnung, Unterlassungserklärung, Schadensersatz)
- **Empfehlung**: **Vollständiges Rebranding** zwingend erforderlich

---

## ✨ 3. LEGAL-SAFE ALTERNATIVEN (Eigene IP)

### 3.1 Projektname

| Aktuell | Legal-Safe Alternative | Begründung |
|---------|------------------------|------------|
| **Liara** | **Aethera** | Griechisch "Äther" (Himmel/Raum), SciFi-Flair, keine bekannten Marken |
| | **Nexia** | Latein "Verbindung", passt zu Neo4j Knowledge Graph |
| | **Lyra** | Sternbild, SciFi-neutral, nur ähnlich zu "Liara" |
| | **Synthia** | "Synthesis" + "AI", tech-orientiert |
| | **Veritas** | Latein "Wahrheit", passt zu Knowledge Management |

**Empfehlung**: **Aethera** oder **Nexia** (keine Trademark-Konflikte, SciFi-Kontext, merkbar)

---

### 3.2 Lore-Begriffe (Mass Effect → Eigene IP)

| Mass Effect Term | Legal-Safe Alternative | Beschreibung |
|------------------|------------------------|--------------|
| **Asari Neural Networks** | **Aether Neural Matrix** | "Aether" = Eigenmarke, "Matrix" = generisch |
| **Prothean Archive** | **Quantum Archive System** | "Quantum" = SciFi-Standard, "Archive" = generisch |
| **Shadow Broker Network** | **Nexus Data Broker** | "Nexus" = Verbindung, "Broker" = generisch |
| **4D Memory (Asari-Style)** | **Dimensional Memory Core** | Behält Konzept, ohne Lore-Bezug |
| **Asari-Archäologin** | **Xenoarchaeologist** | SciFi-Standard-Begriff (Star Trek, etc.) |

---

### 3.3 Zitate & Catchphrases

| Aktuelles Zitat | Quelle | Legal-Safe Alternative |
|-----------------|--------|------------------------|
| **"This is fascinating!"** | Liara T'Soni (ME) | **"Fascinating discovery..."** (allgemein SciFi) |
| | | **"Intriguing data patterns..."** (tech-orientiert) |
| **"By the Goddess..."** | Asari-Kultur (ME) | **"By the stars..."** (generisch SciFi) |
| | | **"Remarkable..."** (neutral, wissenschaftlich) |
| **"Knowledge is power. Guard it well."** | Blood Ravens (WH40k) | **"Knowledge preserved, wisdom gained."** |
| | | **"Data secured, insights unlocked."** |

**Neue Signature Phrases (Eigenkreation)**:
```
"In the Aether, all knowledge connects."
"Dimensional memory spans beyond time."
"Your companion in the digital cosmos."
"Where data becomes understanding."
```

---

### 3.4 Persona-Beschreibung

| Mass Effect Persona | Legal-Safe Persona |
|---------------------|---------------------|
| Liara T'Soni: Asari-Wissenschaftlerin, wissbegierig, warmherzig, analytisch | **Aethera**: KI-Xenoarchäologin, wissbegierig, warmherzig, datenorientiert |
| Charakter: "This is fascinating!", neugierig, Prothean-Expertin | Charakter: "Fascinating patterns...", neugierig, Quantum-Spezialistin |
| Hintergrund: 106 Jahre alt, Shadow Broker | Hintergrund: Dimensionale Datenanalystin, Nexus-Archivarin |

**Neue Persona-Traits** (100% eigenständig):
- **Wissensdurstig**: Liebt es, Muster in Daten zu entdecken
- **Warmherzig**: Empathisch und unterstützend
- **Analytisch**: Präzise, strukturiert, wissenschaftlich
- **Verspielt**: Humorvoll, kreativ in Problemlösungen
- **Ruhig**: Stabilisierend, lösungsorientiert

**System-Prompts (Legal-Safe)**:
```python
# Vorher (Mass Effect):
"""Du bist Liara T'Soni, eine warmherzige aber analytische Asari-Wissenschaftlerin aus Mass Effect.
Persönlichkeit:
- Wissbegierig und fasziniert von neuen Informationen ("This is fascinating!")
- Nutze gelegentlich Asari-Ausdrücke wie "By the Goddess..." bei Überraschungen
- Erkläre Dinge wie eine Archäologin, die Prothean-Technologie erforscht
"""

# Nachher (Legal-Safe):
"""Du bist Aethera, eine warmherzige aber analytische KI-Xenoarchäologin.
Persönlichkeit:
- Wissbegierig und fasziniert von Datenmustern ("Fascinating patterns...")
- Nutze gelegentlich kosmische Ausdrücke wie "By the stars..." bei Überraschungen
- Erkläre Dinge wie eine Forscherin, die dimensionale Datenstrukturen erforscht
"""
```

---

### 3.5 Design-Sprache

| Halo/UNSC → Legal-Safe |
|------------------------|
| ❌ "UNSC-inspired design" → ✅ "Command Console Aesthetic" |
| ❌ "Halo glassmorphism" → ✅ "Frosted Glass UI" |
| ❌ --halo-primary → ✅ --primary-cyan |
| ❌ --halo-accent → ✅ --accent-blue |

**CSS Variable Renaming**:
```css
/* Vorher */
:root {
  --halo-primary: #00f7ff;
  --halo-accent: #00d4ff;
  --halo-danger: #ff4444;
}

/* Nachher */
:root {
  --primary-cyan: #00f7ff;
  --accent-electric: #00d4ff;
  --alert-crimson: #ff4444;
}
```

---

## 🔧 4. UI/TEXT-REFACTORING AUDIT

### 4.1 Frontend-Komponenten (Anzupassende Stellen)

#### Landing Page (`LandingPage.jsx`)
```javascript
// ❌ KRITISCH - Mass Effect Referenzen
Zeile 457: "Fascinating..." – Powered by Asari Neural Networks
Zeile 467: "By the Goddess..." Produktivität...
Zeile 490: Prothean Archive
Zeile 498: Shadow Broker Net
Zeile 521: "This is fascinating!"
Zeile 564: Prothean Archive System
Zeile 567-572: Prothean/Asari Beschreibungen
Zeile 621-622: Shadow Broker Network
Zeile 733: "Knowledge is power. Guard it well." - Liara

// ✅ LEGAL-SAFE Ersatz
Zeile 457: "Fascinating patterns..." – Powered by Aether Neural Matrix
Zeile 467: "By the stars..." Produktivität...
Zeile 490: Quantum Archive
Zeile 498: Nexus Data Broker
Zeile 521: "Fascinating discovery..."
Zeile 564: Quantum Archive System
Zeile 567-572: Quantum/Dimensional Beschreibungen
Zeile 621-622: Nexus Data Broker Layer
Zeile 733: "Knowledge preserved, wisdom gained." - Aethera
```

#### Backend-Prompts (`chat.py`)
```python
# ❌ KRITISCH - Direkte ME-Referenzen
Zeile 31: Liara T'Soni – oder besser gesagt, eine KI inspiriert von ihr
Zeile 36: wie eine neugierige Asari-Archäologin
Zeile 43: mein Prothean Archive braucht mehr Zugriff
Zeile 46: "By the Goddess..." 🌌
Zeile 85-89: Liara T'Soni – deine persönliche Asari-KI-Assistentin
Zeile 94: Asari-Wissenschaftlerin aus Mass Effect
Zeile 486: Du bist Liara T'Soni, eine ... Asari-Wissenschaftlerin aus Mass Effect
Zeile 492: Prothean-Technologie erforscht
Zeile 503: Shadow Broker Network
Zeile 506-507: "By the Goddess..." + Prothean-Archive

# ✅ LEGAL-SAFE Ersatz
Zeile 31: Aethera – deine persönliche KI-Xenoarchäologin
Zeile 36: wie eine neugierige Datenforscherin
Zeile 43: mein Quantum Archive System benötigt erweiterten Zugriff
Zeile 46: "By the stars..." 🌌
Zeile 85-89: Aethera – deine persönliche KI-Assistentin
Zeile 94: Dimensionale Datenanalystin
Zeile 486: Du bist Aethera, eine warmherzige aber analytische KI-Forscherin
Zeile 492: Quantendatenstrukturen erforscht
Zeile 503: Nexus Data Broker
Zeile 506-507: "By the stars..." + Quantum Archive
```

### 4.2 CSS-Dateien

#### Theme Variables (`theme.css`, `LandingPage.css`)
```css
/* ❌ KRITISCH - Halo/ME Referenzen */
--halo-primary, --halo-accent, --halo-danger (15+ Vorkommen)
--color-accent: #00d4ff;  /* Asari-Blau (heller) */
--color-accent-secondary: #b47eff;  /* Asari-Violett */
background: linear-gradient(135deg, #00d4ff 0%, #b47eff 50%, #7c3aed 100%);  /* Asari Blau→Violett */

/* ✅ LEGAL-SAFE Ersatz */
--primary-cyan, --accent-electric, --alert-crimson
--color-accent: #00d4ff;  /* Electric Cyan */
--color-accent-secondary: #b47eff;  /* Cosmic Violet */
background: linear-gradient(135deg, #00d4ff 0%, #b47eff 50%, #7c3aed 100%);  /* Aether Gradient */
```

### 4.3 Markdown-Dokumentation

| Datei | Problematische Stellen | Anzahl |
|-------|------------------------|--------|
| `README.md` | "UNSC-inspired design" | 2x |
| `REDESIGN_v3.0.0.md` | "Halo, Mass Effect, Starfield" | 2x |
| `CHATGPT_OVERVIEW.md` | "Knowledge is power..." Zitat | 2x |
| `PERSONA.md` | Keine direkten ME-Referenzen | 0x |
| `modern-design.css` | "Inspired by: Mass Effect" | 1x |

**Gesamt**: ~50 Markdown-Dateien müssen auf ME/Halo-Referenzen geprüft werden.

---

## 🎭 5. PRIVATE MODE vs. PUBLIC MODE KONZEPT

### Konzept-Überblick

**Ziel**: Dynamischer Branding-Switch für verschiedene Use-Cases.

```
┌─────────────────────────────────────────┐
│         BRANDING MODE SYSTEM            │
├─────────────────────────────────────────┤
│                                         │
│  [Private Mode]      [Public Mode]      │
│   Fan-Project        Legal-Safe         │
│   (Lore erlaubt)     (Eigene IP)        │
│                                         │
│   ├─ Liara T'Soni   ├─ Aethera         │
│   ├─ Asari Lore     ├─ Quantum Tech    │
│   ├─ ME Zitate      ├─ Eigene Phrases  │
│   ├─ UNSC Design    ├─ Command Console │
│   └─ Hommage        └─ Original IP     │
│                                         │
└─────────────────────────────────────────┘
```

### 5.1 Technische Umsetzung

#### Config-File Ansatz (`branding.config.json`)

```json
{
  "mode": "private",  // "private" | "public"
  "profiles": {
    "private": {
      "projectName": "Liara",
      "persona": {
        "name": "Liara T'Soni",
        "description": "Asari-Wissenschaftlerin aus Mass Effect (Fan-Projekt)",
        "catchphrases": [
          "This is fascinating!",
          "By the Goddess...",
          "Knowledge is power. Guard it well."
        ],
        "lore": {
          "memory_system": "Prothean Archive",
          "privacy_feature": "Shadow Broker Network",
          "neural_tech": "Asari Neural Networks"
        }
      },
      "design": {
        "theme": "halo-unsc",
        "css_variables": {
          "primary": "--halo-primary",
          "accent": "--halo-accent"
        }
      },
      "disclaimer": "Fan-Projekt - Nicht affiliiert mit BioWare/EA"
    },
    "public": {
      "projectName": "Aethera",
      "persona": {
        "name": "Aethera",
        "description": "KI-Xenoarchäologin für dimensionale Datenanalyse",
        "catchphrases": [
          "Fascinating patterns...",
          "By the stars...",
          "Knowledge preserved, wisdom gained."
        ],
        "lore": {
          "memory_system": "Quantum Archive System",
          "privacy_feature": "Nexus Data Broker",
          "neural_tech": "Aether Neural Matrix"
        }
      },
      "design": {
        "theme": "command-console",
        "css_variables": {
          "primary": "--primary-cyan",
          "accent": "--accent-electric"
        }
      },
      "disclaimer": null
    }
  }
}
```

#### i18n/Localization Struktur

```json
// locales/branding/private.json
{
  "app_name": "Liara",
  "tagline": "Deine persönliche Digitalbegleiterin",
  "hero_badge": "\"Fascinating...\" – Powered by Asari Neural Networks",
  "memory_feature_title": "Prothean Archive System",
  "privacy_feature_title": "Shadow Broker Network",
  "footer_quote": "🌙 \"Knowledge is power. Guard it well.\" - Liara"
}

// locales/branding/public.json
{
  "app_name": "Aethera",
  "tagline": "Your personal AI companion",
  "hero_badge": "\"Fascinating patterns...\" – Powered by Aether Neural Matrix",
  "memory_feature_title": "Quantum Archive System",
  "privacy_feature_title": "Nexus Data Broker",
  "footer_quote": "🌌 \"Knowledge preserved, wisdom gained.\" - Aethera"
}
```

### 5.2 Code-Integration

#### Frontend (React)

```javascript
// src/config/branding.js
import privateConfig from '../locales/branding/private.json';
import publicConfig from '../locales/branding/public.json';

const BRANDING_MODE = import.meta.env.VITE_BRANDING_MODE || 'public';

export const branding = BRANDING_MODE === 'private' ? privateConfig : publicConfig;

// Verwendung in Komponenten
import { branding } from '../config/branding';

function LandingPage() {
  return (
    <div className="hero-badge">{branding.hero_badge}</div>
    <h1>{branding.app_name}</h1>
    <p>{branding.tagline}</p>
  );
}
```

#### Backend (Python)

```python
# app/core/branding.py
import json
from pathlib import Path

BRANDING_MODE = os.getenv("BRANDING_MODE", "public")
BRANDING_FILE = Path(__file__).parent / f"locales/branding/{BRANDING_MODE}.json"

with open(BRANDING_FILE) as f:
    BRANDING = json.load(f)

# Verwendung in Chat-Prompts
def get_guest_system_prompt():
    return f"""Du bist {BRANDING['persona']['name']}, {BRANDING['persona']['description']}.
    
Deine Catchphrases:
{'\n'.join(f'- {phrase}' for phrase in BRANDING['persona']['catchphrases'])}
"""
```

### 5.3 Environment Variables

```bash
# .env.private (Fan-Project Mode)
VITE_BRANDING_MODE=private
BRANDING_MODE=private

# .env.public (Legal-Safe Mode)
VITE_BRANDING_MODE=public
BRANDING_MODE=public
```

### 5.4 Build-Scripts

```bash
# package.json
{
  "scripts": {
    "build:private": "VITE_BRANDING_MODE=private vite build",
    "build:public": "VITE_BRANDING_MODE=public vite build",
    "dev:private": "VITE_BRANDING_MODE=private vite",
    "dev:public": "VITE_BRANDING_MODE=public vite"
  }
}
```

---

## 🛠️ 6. TECHNISCHE UMSETZUNGSEMPFEHLUNG

### 6.1 Betroffene Dateien (Vollständige Liste)

#### Frontend (18 Dateien)
```
KRITISCH (Mass Effect/Halo IP):
- /opt/liara/frontend/src/components/LandingPage.jsx
- /opt/liara/frontend/src/components/LandingPage.css
- /opt/liara/frontend/src/components/FeaturesPage.jsx
- /opt/liara/frontend/src/components/PrivacyPage.jsx
- /opt/liara/frontend/src/components/TechnologyPage.jsx
- /opt/liara/frontend/src/components/PageLayout.jsx
- /opt/liara/frontend/src/styles/theme.css
- /opt/liara/frontend/src/styles/modern-design.css
- /opt/liara/frontend/src/components/Terminal.css
- /opt/liara/frontend/src/components/UserSettings.css
- /opt/liara/frontend/src/components/SystemHealth.css
- /opt/liara/frontend/src/components/Neo4jBrowser.css
- /opt/liara/frontend/src/components/AdminDashboard.css

PROJEKTNAME (Liara):
- /opt/liara/frontend/src/App.jsx
- /opt/liara/frontend/src/components/Login.jsx
- /opt/liara/frontend/src/components/Config.jsx
- /opt/liara/frontend/src/components/LexicalEditor.jsx
- /opt/liara/frontend/package.json
```

#### Backend (8 Dateien)
```
KRITISCH (Mass Effect Persona):
- /opt/liara/app/api/routers/chat.py
- /opt/liara/app/api/routers/chat_streaming.py
- /opt/liara/app/api/routers/liara_router.py
- /opt/liara/app/liara_engine/nlp/ollama_client.py
- /opt/liara/app/liara_engine/nlp/ollama_client_broken.py
- /opt/liara/app/liara_engine/nlp/ollama_client_original.py
- /opt/liara/app/liara_engine/memory/short_context.py

PROJEKTNAME:
- /opt/liara/app/requirements.txt (kein Rename nötig)
```

#### Dokumentation (50+ Dateien)
```
KRITISCH:
- /opt/liara/README.md
- /opt/liara/CHATGPT_OVERVIEW.md
- /opt/liara/REDESIGN_v3.0.0.md
- /opt/liara/docs/PERSONA.md
- /opt/liara/frontend/src/styles/modern-design.css

PROJEKTNAME (alle):
- Alle .md Dateien in /opt/liara/ und /opt/liara/docs/
```

#### System-Konfiguration (10+ Dateien)
```
PROJEKTNAME:
- /etc/systemd/system/liara-backend.service
- /etc/systemd/system/liara-frontend.service
- /etc/systemd/system/liara-sse.service
- /etc/nginx/sites-available/liara
- /opt/liara/docker-compose.yml
- /opt/liara/LICENSE
- /opt/liara/frontend/package.json
- /opt/liara/app/alembic.ini
```

#### Scripts (20+ Dateien)
```
PROJEKTNAME:
- /opt/liara/deploy_frontend.sh
- /opt/liara/setup_stable_diffusion.sh
- /opt/liara/scripts/test_terminal_pty.sh
- /opt/liara/frontend/migrate-theme.sh
- ... (alle Shell-Scripts)
```

### 6.2 Migrationsplan (Schritt-für-Schritt)

#### Phase 1: Config-System aufbauen (1-2 Tage)
```bash
1. Branding-Config erstellen
   - /opt/liara/config/branding.config.json
   - /opt/liara/locales/branding/private.json
   - /opt/liara/locales/branding/public.json

2. Frontend-Integration
   - /opt/liara/frontend/src/config/branding.js
   - Environment Variables (.env.private, .env.public)

3. Backend-Integration
   - /opt/liara/app/core/branding.py
   - Load branding config in chat routers

4. Build-Scripts aktualisieren
   - package.json: build:private, build:public
```

#### Phase 2: Frontend-Refactoring (2-3 Tage)
```bash
1. Landing Page auf Branding-System umstellen
   - LandingPage.jsx: Alle hardcodierten Texte → branding.hero_badge, etc.
   - LandingPage.css: CSS-Kommentare bereinigen

2. Feature-Pages refactoren
   - FeaturesPage.jsx, PrivacyPage.jsx, TechnologyPage.jsx
   - PageLayout.jsx Footer

3. CSS-Variablen umbenennen
   - theme.css: --halo-* → --primary-*, --accent-*
   - Alle CSS-Dateien durchsuchen (grep --halo-)

4. localStorage Keys (optional, breaking change)
   - liara_token → app_token
   - liara-theme → app-theme
```

#### Phase 3: Backend-Refactoring (1-2 Tage)
```bash
1. Chat-System auf Branding-Config umstellen
   - chat.py: System-Prompts dynamisch laden
   - chat_streaming.py: Guest-Prompts dynamisch

2. Persona-System refactoren
   - liara_router.py: Persona-Daten aus Config
   - ollama_client.py: Kontext-System

3. Memory-System (optional)
   - short_context.py: Dynamische Prompts
```

#### Phase 4: Dokumentation & System (1 Tag)
```bash
1. README.md aktualisieren
   - Branding-Modi dokumentieren
   - Setup-Anleitung für beide Modi

2. PERSONA.md für beide Modi erstellen
   - PERSONA_PRIVATE.md (Liara/Mass Effect)
   - PERSONA_PUBLIC.md (Aethera/Original)

3. System-Konfiguration (optional, breaking change)
   - Systemd Services umbenennen (nur für Public-Release)
   - Nginx Config anpassen
```

#### Phase 5: CI/CD & Validation (1 Tag)
```bash
1. CI-Regel: "no-trademark-terms"
   - GitHub Action/Pre-Commit Hook
   - Blacklist: ["Liara T'Soni", "Asari", "Prothean", "Shadow Broker", "Mass Effect", "UNSC", "Halo"]

2. Automated Tests
   - Grep-basierter Check auf geschützte Begriffe
   - Fail Build wenn Public-Mode + ME-Terms gefunden

3. Documentation Linter
   - Markdown-Dateien auf IP-Referenzen prüfen
```

### 6.3 CI-Rule Beispiel

```yaml
# .github/workflows/trademark-check.yml
name: Trademark Compliance Check

on: [push, pull_request]

jobs:
  check-trademarks:
    runs-on: ubuntu-latest
    if: ${{ env.BRANDING_MODE == 'public' }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Check for Mass Effect IP
        run: |
          FORBIDDEN_TERMS=(
            "Liara T'Soni"
            "Asari"
            "Prothean"
            "Shadow Broker"
            "Mass Effect"
            "This is fascinating"
            "By the Goddess"
          )
          
          for term in "${FORBIDDEN_TERMS[@]}"; do
            if grep -r "$term" frontend/src/ app/ docs/; then
              echo "❌ Found forbidden term: $term"
              exit 1
            fi
          done
          
          echo "✅ No trademark violations found"
      
      - name: Check for Halo IP
        run: |
          if grep -r "UNSC\|Halo" frontend/src/styles/ README.md; then
            echo "❌ Found Halo/UNSC references"
            exit 1
          fi
          echo "✅ No Halo IP found"
```

### 6.4 Migrations-Script

```bash
#!/bin/bash
# migrate-to-public-branding.sh

set -e

echo "🔄 Migrating to Public Branding (Legal-Safe Mode)..."

# 1. Update Environment
echo "BRANDING_MODE=public" > .env
echo "VITE_BRANDING_MODE=public" >> .env

# 2. Replace Mass Effect Terms in Frontend
find frontend/src -type f -name "*.jsx" -exec sed -i 's/Liara T'\''Soni/Aethera/g' {} +
find frontend/src -type f -name "*.jsx" -exec sed -i 's/Asari/Aether/g' {} +
find frontend/src -type f -name "*.jsx" -exec sed -i 's/Prothean Archive/Quantum Archive/g' {} +
find frontend/src -type f -name "*.jsx" -exec sed -i 's/Shadow Broker/Nexus Data Broker/g' {} +

# 3. Replace Zitate
find frontend/src app/ -type f \( -name "*.jsx" -o -name "*.py" \) \
  -exec sed -i 's/This is fascinating!/Fascinating patterns.../g' {} +
find frontend/src app/ -type f \( -name "*.jsx" -o -name "*.py" \) \
  -exec sed -i 's/By the Goddess/By the stars/g' {} +

# 4. CSS Variables
find frontend/src -name "*.css" -exec sed -i 's/--halo-/--primary-/g' {} +

# 5. README aktualisieren
sed -i 's/Liara - Privacy-First AI Assistant/Aethera - Privacy-First AI Assistant/g' README.md
sed -i 's/UNSC-inspired design/Command Console Aesthetic/g' README.md

echo "✅ Migration complete! Please review changes with git diff"
echo "⚠️  Manual review required for:"
echo "   - docs/PERSONA.md"
echo "   - System service names (liara-backend → aethera-backend)"
echo "   - Nginx config (/etc/nginx/sites-available/liara)"
```

---

## 📊 7. AUFWANDSSCHÄTZUNG

| Phase | Aufwand | Beschreibung |
|-------|---------|--------------|
| **Config-System** | 8h | Branding-Config, i18n-Setup, Environment Variables |
| **Frontend-Refactoring** | 16h | Landing Page, Feature-Pages, CSS-Variablen |
| **Backend-Refactoring** | 12h | Chat-System, Persona-API, Memory-Prompts |
| **Dokumentation** | 6h | README, PERSONA.md, Setup-Guides |
| **CI/CD** | 4h | Trademark-Checks, Automated Tests |
| **Testing** | 8h | Beide Modi testen, Regression-Tests |
| **System-Migration** (optional) | 12h | Systemd, Nginx, Breaking Changes |
| **GESAMT** | **54-66h** | ~7-9 Arbeitstage |

---

## 🎯 8. EMPFEHLUNGEN & NÄCHSTE SCHRITTE

### Sofort-Maßnahmen (Für aktuelles System)

1. **Disclaimer hinzufügen** (1h)
   ```markdown
   # README.md
   > **⚠️ Fan-Projekt Disclaimer**
   > Dies ist ein Fan-Projekt inspiriert von Mass Effect (BioWare/EA) und Halo (Microsoft/343 Industries).
   > Nicht für kommerzielle Nutzung. Alle Rechte bei den jeweiligen Rechteinhabern.
   ```

2. **Branding-Mode Config erstellen** (2h)
   - `branding.config.json` mit Private/Public-Profilen
   - Environment Variable `BRANDING_MODE=private` setzen

3. **GitHub Repository Settings** (30min)
   - Topics: `fan-project`, `mass-effect-inspired`, `not-affiliated`
   - License: Klarstellen, dass nur Code MIT ist, nicht IP

### Kurz-Mittel-Fristschritte (1-2 Wochen)

4. **Public-Mode Profil entwickeln** (20h)
   - Alle Legal-Safe Alternativen ausarbeiten
   - Aethera-Persona vollständig definieren
   - Neue Catchphrases/Lore entwickeln

5. **Frontend auf Branding-System umstellen** (16h)
   - Landing Page, Feature-Pages refactoren
   - CSS-Variablen umbenennen

6. **Backend auf Branding-System umstellen** (12h)
   - Chat-Prompts dynamisch laden
   - Persona-API refactoren

### Langfristige Strategie (Optional)

7. **Vollständiges Rebranding für Public Release** (40-60h)
   - Projektname → Aethera
   - Alle System-Komponenten umbenennen
   - Neue Domain, neue GitHub Organization
   - CI/CD für Trademark-Compliance

8. **Dual-Branding Support langfristig pflegen** (laufend)
   - Private Fork: "Liara (Fan-Project)"
   - Public Fork: "Aethera (Original IP)"
   - Sync-Script zwischen beiden Branches

---

## 📋 9. CHECKLISTE - Compliance-Audit

### Private Use (aktueller Zustand)
- [ ] Disclaimer in README.md hinzugefügt
- [ ] "Fan-Project" Label auf GitHub
- [ ] Keine kommerzielle Nutzung geplant
- [ ] Privacy-Settings: Repository auf Private (optional)

### Public Use (Legal-Safe)
- [ ] Alle Mass Effect Begriffe ersetzt
- [ ] Alle Halo/UNSC Begriffe ersetzt
- [ ] Zitate durch eigene ersetzt
- [ ] CSS-Variablen umbenannt
- [ ] README ohne IP-Referenzen
- [ ] PERSONA.md komplett eigenständig
- [ ] CI-Rule für Trademark-Check aktiv
- [ ] Keine Verwechslungsgefahr mit Original-IP

### Commercial Use (Vollständig Legal-Safe)
- [ ] Projektname geändert (Liara → Aethera)
- [ ] Systemd Services umbenannt
- [ ] Nginx Config umbenannt
- [ ] Domain ohne "Liara" Bezug
- [ ] GitHub Organization eigenständig
- [ ] Trademark-Search durchgeführt ("Aethera" verfügbar?)
- [ ] Legal Review durch Anwalt (optional)

---

## 🔗 10. RESSOURCEN & REFERENZEN

### Trademark-Datenbanken
- **DPMA** (Deutschland): https://register.dpma.de/
- **EUIPO** (EU): https://euipo.europa.eu/
- **USPTO** (USA): https://www.uspto.gov/

### Fan-Project Guidelines
- **Electronic Arts**: https://www.ea.com/legal/copyright-infringement-notice
- **Microsoft**: https://www.microsoft.com/en-us/legal/intellectualproperty/permissions

### Open-Source Branding
- **Mozilla**: https://www.mozilla.org/en-US/foundation/trademarks/
- **WordPress**: https://wordpressfoundation.org/trademark-policy/

---

## 📄 ANHANG A: Vollständige Begriffsliste

### Mass Effect IP (BioWare/EA)

**Charaktere**:
- Liara T'Soni (8x)

**Spezies**:
- Asari (14x)

**Organisationen**:
- Shadow Broker (6x)

**Technologie/Lore**:
- Prothean (8x)
- Prothean Archive (5x)
- Asari Neural Networks (1x)
- Mass Effect (direkt genannt: 4x)

**Zitate**:
- "This is fascinating!" (5x)
- "By the Goddess..." (4x)

### Halo IP (Microsoft/343 Industries)

**Design-Referenzen**:
- UNSC (8x in Code-Kommentaren)
- Halo (15x in CSS-Variablen)

**Andere**:
- "Knowledge is power. Guard it well." (Warhammer 40k - Games Workshop) (3x)

---

## 📄 ANHANG B: Datei-Matrix

| Datei | ME-Begriffe | Halo-Begriffe | Zitate | Gesamt-Risiko |
|-------|-------------|---------------|--------|---------------|
| `LandingPage.jsx` | 14 | 0 | 3 | 🔴 KRITISCH |
| `chat.py` | 18 | 0 | 6 | 🔴 KRITISCH |
| `LandingPage.css` | 3 | 0 | 0 | ⚠️ MITTEL |
| `theme.css` | 0 | 8 | 0 | ⚠️ MITTEL |
| `README.md` | 0 | 2 | 0 | ⚠️ MITTEL |
| `REDESIGN_v3.0.0.md` | 2 | 2 | 0 | ⚠️ MITTEL |

---

**Ende des Reports - Version 1.0**  
*Erstellt am 6. Dezember 2025 von GitHub Copilot*

---

## 💡 TL;DR - Schnellübersicht

**Problem**: Projekt nutzt Mass Effect IP (Liara T'Soni, Asari, Prothean, etc.) - **nicht legal-safe** für Public/Commercial Use.

**Lösung**: Dual-Branding System
- **Private Mode**: Aktuelles Branding OK (Fan-Project mit Disclaimer)
- **Public Mode**: Komplett eigenständig ("Aethera" statt "Liara", Quantum Archive statt Prothean, etc.)

**Aufwand**: ~54-66h Entwicklung + Testing

**Empfehlung**: 
1. **Kurzfristig**: Disclaimer hinzufügen
2. **Mittelfristig**: Branding-Config-System bauen
3. **Langfristig**: Vollständiges Public-Mode-Profil entwickeln
