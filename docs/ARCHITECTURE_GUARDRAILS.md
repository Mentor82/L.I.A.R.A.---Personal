# 🏛️ Architecture Guardrails & Monolith Prevention (Issue #21)

## 1. Motivation & Zielsetzung
Große, monolithische Dateien („God Files“) erschweren die Wartbarkeit, erhöhen das Risiko von Race Conditions, erschweren Code-Reviews und führen zu unübersichtlichen Import- und Abhängigkeitsstrukturen.

Mit **Issue #21** wurden verbindliche architektonische Guardrails und automatisierte Qualitätsprüfungen eingeführt, um:
1. Unbemerktes Anschwellen von Dateien zu verhindern.
2. Klare Grenzen für neue Module zu setzen (**Hard-Limit: 800 Zeilen**).
3. Eine Anti-Ratchet-Garantie für bestehende Legacy-Dateien zu etablieren (**Bestehende Dateien dürfen kleiner werden, aber nicht unbemerkt wachsen**).
4. Eine strukturierte Roadmap für die Modularisierung der identifizierten Monolithen bereitzustellen.

---

## 2. Guardrail-Grenzwerte & Regeln

| Regel | Grenzwert | Verhalten | Maßnahme |
|---|---|---|---|
| **Soft-Limit** | **> 500 Zeilen** | Warnung im Report | Prüfung auf Modularisierungspotenzial / SRP |
| **Hard-Limit (neue Dateien)** | **> 800 Zeilen** | Build/CI-Fehler (`exit 1`) | Aufteilung in Submodule vor dem Merge erforderlich |
| **Anti-Ratchet (Legacy-Dateien)** | **Baseline + 25 Zeilen** | Build/CI-Fehler (`exit 1`) | Kein weiteres Code-Wachstum in Legacy-Monolithen |
| **Refactoring-Fortschritt** | **> 50 Zeilen Reduktion** | Grüner Info-Report | Baseline kann mit `--update-baseline` aktualisiert werden |

---

## 3. Verwendung des Guardrail-Tools

Das Tool befindet sich in [`scripts/check_architecture.py`](../scripts/check_architecture.py):

```bash
# 1. Lokale Prüfung durchführen
python scripts/check_architecture.py

# 2. Strikter CI-Modus (bricht bei Fehlern ab)
python scripts/check_architecture.py --ci

# 3. Baseline nach erfolgreicher Modularisierung aktualisieren
python scripts/check_architecture.py --update-baseline
```

### Pytest-Integration
Die Architektur-Guardrails sind direkt in die Testsuite eingebunden:
```bash
pytest app/tests/test_architecture_guardrails.py
```

---

## 4. Top-Hotspots & Modularisierungs-Roadmap

### A. Backend Monolithen (`app/`)

1. **`app/api/routers/chat_streaming.py` (~2150 Zeilen) → [Ziel von Issue #23]**
   * *Problem:* Vereint Prompt-Building, Mood-System, SSE-Generierung, Lock-Koordination, Tool-Execution, Memory-Hooks und DB-Persistenz in einer einzigen Funktion.
   * *Zielarchitektur:* Deklarative Pipeline mit separaten Stage-Handlern:
     * `app/services/chat_stream/lock_guard.py` (Watchdog & Lock Racing)
     * `app/services/chat_stream/prompt_stage.py` (Prompt Assembly & Capabilities)
     * `app/services/chat_stream/generator_stage.py` (Ollama & LiNeP Streaming Loops)
     * `app/services/chat_stream/tool_stage.py` (Tool Execution & Agent Steps)
     * `app/services/chat_stream/persistence_stage.py` (Canonical Turn Persistence)

2. **`app/api/routers/chat.py` (~1120 Zeilen)**
   * *Problem:* Nicht-streamende Chat-Endpunkte, Session-Management und historische Hilfsfunktionen gemischt.
   * *Zielarchitektur:* Aufteilung in Session-CRUD (`chat_sessions.py`) und Message-CRUD (`chat_messages.py`).

3. **`app/services/session_workspace.py` (~967 Zeilen)**
   * *Problem:* Workspace-Dateizugriff, Session-Sync, Git/Diff-Handling und Terminal-Prozesse in einem Service.
   * *Zielarchitektur:* Aufteilung in `workspace_file_service.py`, `workspace_git_service.py` und `workspace_process_service.py`.

4. **`app/services/memory_integration.py` (~801 Zeilen)**
   * *Problem:* Vektoreinbettung, Wissensgraphen-Sync und Heuristik-Extraktion gekoppelt.
   * *Zielarchitektur:* Aufteilung in `concept_extractor.py`, `graph_memory_sync.py` und `vector_store_adapter.py`.

---

### B. Frontend Monolithen (`frontend/src/`)

1. **`frontend/src/components/Chat.jsx` (~1720 Zeilen) & `Chat.css` (~1530 Zeilen)**
   * *Problem:* UI-Layout, SSE-State, Audio/TTS, File-Upload, Modals und Message-Rendering in einer Komponente.
   * *Zielarchitektur:* Zerlegung in:
     * `ChatInputBar.jsx` (Eingabe, Audio-Record, File-Picker)
     * `ChatMessageList.jsx` & `ChatMessageItem.jsx` (Rendering einzelner Turns)
     * `ChatHeaderActions.jsx` (Export, Einstellungen, Modellwahl)
     * Modularisierte CSS-Dateien (`ChatInput.css`, `ChatMessage.css`).

2. **`frontend/src/components/WorkspacePage.jsx` (~1680 Zeilen) & `WorkspacePage.css` (~1440 Zeilen)**
   * *Problem:* Terminal-Tabs, File-Tree, Diff-Viewer, Code-Editor und Agent-Drawer in einer Hauptkomponente.
   * *Zielarchitektur:* Klare Zerlegung in `WorkspaceFileTree.jsx`, `WorkspaceDiffViewer.jsx`, `WorkspaceEditor.jsx` und `WorkspaceTerminal.jsx`.

3. **`frontend/src/components/CalendarView.jsx` (~990 Zeilen) & `Tasks.jsx` (~765 Zeilen)**
   * *Problem:* Kalender-Grid, Event-Dialoge und Filterlogik zusammengefasst.
   * *Zielarchitektur:* Auslagerung der Sub-Dialoge und View-Filter in separate Subkomponenten.
