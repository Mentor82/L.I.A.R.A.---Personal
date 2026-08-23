// Data model for the interactive Architecture Map (/architecture).
// Node/edge content is Personal-specific; the *pattern* (typed nodes with
// manual x/y layout, edges filtered per view, click-to-select) is adapted
// from the sibling LIARA-core repo's own architecture map
// (Mentor82/L.I.A.R.A., frontend/web-ui/src/app/architecture/), per
// GitHub issue #3's explicit instruction to reuse that UI/interaction
// approach without copying its LIARA-core-specific content (governance,
// dreaming, WSL sessions, live heartbeat) 1:1.
//
// Edges are modeled as a system FLOW, not just a static topology: every
// edge carries a semantic `kind` (what actually moves - a request, a
// stream, context, a memory read/write, a tool call, its result, an
// optional cloud hop, a consent gate...) which maps to one of four
// visual "flow roles" via KIND_FLOW below:
//   - main     - the normal forward happy-path (solid)
//   - optional - conditional / not-always-taken (dashed)
//   - feedback - a result/response flowing BACK against the main
//                direction (distinct color, bowed curve so it doesn't
//                sit on top of the forward edge between the same pair)
//   - cloud    - crosses the local/Ollama-Cloud trust boundary (dashed)

export const architectureViews = [
  { id: 'system', label: 'System', description: 'Der Chat-Happy-Path auf einen Blick' },
  { id: 'chat', label: 'Chat & Agent', description: 'Alle Stationen, Nebenpfade und Rückkopplungen' },
  { id: 'persistence', label: 'Persistenz', description: 'Wo Daten und Sitzungsartefakte landen' },
];

export const statusLabels = {
  implemented: 'Implementiert',
  'in-progress': 'In Arbeit',
  planned: 'Geplant',
};

export const boundaryLabels = {
  client: 'Nutzer-Gerät',
  local: 'Self-hosted (lokal)',
  cloud: 'Ollama Cloud',
};

// Fine-grained semantic type of what an edge actually carries.
export const kindLabels = {
  request: 'Anfrage',
  stream: 'Stream / Antwort',
  context: 'Kontext',
  'memory-read': 'Memory-Read',
  'memory-write': 'Memory-Write',
  'tool-call': 'Tool-Call',
  'tool-result': 'Tool-Ergebnis',
  evidence: 'Evidence',
  'model-inference': 'Modell-Inferenz',
  'optional-cloud': 'Optional: Cloud',
  'auth-consent': 'Auth/Consent',
};

// Which visual flow-role each semantic kind renders as.
export const kindFlow = {
  request: 'main',
  stream: 'feedback',
  context: 'main',
  'memory-read': 'main',
  'memory-write': 'feedback',
  'tool-call': 'optional',
  'tool-result': 'feedback',
  evidence: 'feedback',
  'model-inference': 'main',
  'optional-cloud': 'cloud',
  'auth-consent': 'optional',
};

// The 4 visual line styles - what the legend actually shows.
export const flowStyles = {
  main: { color: '#62dff5', dash: null, bow: false, label: 'Hauptfluss' },
  optional: { color: '#f2bd58', dash: '6 5', bow: false, label: 'Optional / bedingt' },
  feedback: { color: '#34d399', dash: '2 5', bow: true, label: 'Rückfluss / Feedback' },
  cloud: { color: '#c084fc', dash: '6 5', bow: false, label: 'Cloud-Grenze' },
};

// {id, title, subtitle, layer, status, boundary, description,
//  responsibilities[], paths[], views[], x, y}
// No port numbers / worker counts / runtime IDs in any text field here -
// this is the public view; those details belong in deployment docs.
export const architectureNodes = [
  {
    id: 'user-browser', title: 'Nutzer / Browser', subtitle: 'Web-Client', layer: 'Interface',
    status: 'implemented', boundary: 'client',
    description: 'Die Person, die Liara über den Browser nutzt - eingeloggt oder als Gast. Startpunkt und Endpunkt jeder Anfrage.',
    responsibilities: ['Anfrage stellen', 'Antwort, Diagramme und Dateien empfangen'],
    paths: [], views: ['system', 'chat'], x: 20, y: 290,
  },
  {
    id: 'native-apps', title: 'Native Apps', subtitle: 'iOS · Android · Windows', layer: 'Interface',
    status: 'planned', boundary: 'client',
    description: 'Geplante native Clients für iOS, Android und Windows - würden dieselben Backend-Contracts wie das Web-Frontend nutzen, aber ohne über die React-SPA zu laufen.',
    responsibilities: ['Gleiche API/Auth-Contracts wie das Web-Frontend nutzen', 'Push-Benachrichtigungen (geplant)'],
    paths: [], views: ['system', 'chat'], x: 20, y: 420,
  },
  {
    id: 'frontend', title: 'Frontend', subtitle: 'React SPA', layer: 'Interface',
    status: 'implemented', boundary: 'local',
    description: 'Single-Page-App, ausgeliefert vom selbstgehosteten Server. Reicht die Anfrage weiter und rendert die zurückgestreamte Antwort.',
    responsibilities: ['Anfrage weiterreichen', 'SSE-Stream konsumieren und rendern'],
    paths: ['frontend/src/components/Chat.jsx', 'frontend/src/App.jsx'],
    views: ['system', 'chat'], x: 250, y: 290,
  },
  {
    id: 'backend', title: 'Liara Backend', subtitle: 'FastAPI · Chat-Streaming', layer: 'Boundary',
    status: 'implemented', boundary: 'local',
    description: 'Zentraler API-Server. Prüft Auth/Consent, lädt Kontext und übergibt an die Modell-Inferenz.',
    responsibilities: ['Request validieren', 'Auth/Consent durchsetzen', 'Kontext-Ladung anstoßen', 'An Modell-Inferenz übergeben'],
    paths: ['app/main.py', 'app/api/routers'],
    views: ['system', 'chat', 'persistence'], x: 430, y: 430,
  },
  {
    id: 'auth-privacy-consent', title: 'Auth, Privacy & Consent', subtitle: 'Login · Consent-Gates', layer: 'Governance',
    status: 'implemented', boundary: 'local',
    description: 'JWT-Login und die Consent-Prüfungen, die jedem sensiblen Tool-Aufruf vorgeschaltet sind (z.B. Websuche, Standort) - ein bedingtes Gate, kein fester Bestandteil jeder Anfrage.',
    responsibilities: ['Login/Session verwalten', 'Privacy-Einstellungen speichern', 'Consent je Tool prüfen, bevor es aufgerufen wird'],
    paths: ['app/api/routers/privacy_router.py', 'app/services/tool_executor.py'],
    views: ['chat', 'persistence'], x: 340, y: 110,
  },
  {
    id: 'admin-functions', title: 'Admin-Funktionen', subtitle: 'Nutzer · System · Logs · Terminal', layer: 'Governance',
    status: 'implemented', boundary: 'local',
    description: 'Verwaltungsoberfläche für Admin-Nutzer: Benutzerverwaltung, Systemkonfiguration, Log-Einsicht, Service-Terminal, Update-Check.',
    responsibilities: ['Nutzer verwalten', 'Dienste neu starten/beobachten', 'Logs einsehen', 'Updates prüfen'],
    paths: ['app/api/routers/admin_router.py', 'frontend/src/components/AdminLayout.jsx'],
    views: ['persistence'], x: 430, y: 580,
  },
  {
    id: 'context-memory', title: 'Context & Memory', subtitle: 'Konzept-Graph · Verlauf', layer: 'Knowledge',
    status: 'implemented', boundary: 'local',
    description: 'Lädt Verlauf und Konzept-Graph zu einem Kontext für die nächste Antwort - und nimmt nach der Antwort neue Konzepte wieder auf (Rückkopplung: die heutige Antwort wird zum Kontext von morgen).',
    responsibilities: ['Verlauf + Graph zu Kontext zusammenstellen', 'Neue Konzepte nach der Antwort aufnehmen'],
    paths: ['app/services/memory_service.py'],
    views: ['system', 'chat', 'persistence'], x: 610, y: 290,
  },
  {
    id: 'model-inference', title: 'Model / Inferenz', subtitle: 'Reasoning · Tool-Entscheidung', layer: 'Reasoning',
    status: 'implemented', boundary: 'local',
    description: 'Der eigentliche Denk-/Antwortschritt: entscheidet pro Runde, ob direkt geantwortet oder zuerst ein Tool aufgerufen wird (bis zu drei Zusatzrunden), bevor eine finale Antwort erzwungen wird.',
    responsibilities: ['Antwort generieren', 'Direkt antworten oder Tool aufrufen entscheiden', 'Tool-Ergebnisse in die nächste Runde einbeziehen'],
    paths: ['app/api/routers/chat_streaming.py', 'app/services/tool_executor.py'],
    views: ['system', 'chat'], x: 790, y: 290,
  },
  {
    id: 'chat-streaming', title: 'Chat-Streaming', subtitle: 'SSE-Transport', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: 'Verpackt die Modell-Ausgabe als separate SSE-Ereignistypen (thinking/tasks/content) statt nur als Text und schickt sie zurück ans Frontend.',
    responsibilities: ['Ereignistypen trennen', 'Antwort ans Frontend zurückstreamen'],
    paths: ['app/api/routers/chat_streaming.py'],
    views: ['chat'], x: 790, y: 150,
  },
  {
    id: 'thinking', title: 'Thinking', subtitle: 'Natives Denkfeld', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: "Ollamas nativer Denkprozess, separat vom Antworttext gestreamt.",
    responsibilities: ['Denkprozess vom Antworttext trennen', 'Live streamen'],
    paths: ['app/api/routers/chat_streaming.py'],
    views: ['chat'], x: 610, y: 50,
  },
  {
    id: 'tasks', title: 'Tasks / Aufgaben', subtitle: 'Modellbehauptetes Update', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: 'Vom Modell selbst formulierte Aufgabenliste (aus einem <tasks>-Block) - bewusst als "vom Modell behauptet" gekennzeichnet, nicht als system-bestätigt.',
    responsibilities: ['<tasks>-Block erkennen', 'Als Vorschlag darstellen'],
    paths: ['app/services/task_block_extractor.py'],
    views: ['chat'], x: 970, y: 50,
  },
  {
    id: 'tool-executor', title: 'Tool Calling / Agent', subtitle: 'Native Ollama Tools', layer: 'Reasoning',
    status: 'implemented', boundary: 'local',
    description: 'Führt ein vom Modell gewähltes Tool aus, nachdem ein echter Consent-Check bestanden wurde, und liefert das Ergebnis zurück an die Modell-Inferenz.',
    responsibilities: ['Consent prüfen', 'Tool ausführen', 'Ergebnis an Model/Inferenz zurückgeben'],
    paths: ['app/services/tool_registry.py', 'app/services/tool_executor.py'],
    views: ['system', 'chat'], x: 970, y: 290,
  },
  {
    id: 'web-search', title: 'Web-Suche', subtitle: 'SearXNG · Freshness-Policy', layer: 'Reasoning',
    status: 'implemented', boundary: 'local',
    description: 'Recherchiert über ein selbstgehostetes, keyless SearXNG - niemals über kommerzielle Such-APIs.',
    responsibilities: ['SearXNG abfragen', 'Ergebnisse nach Aktualität sortieren'],
    paths: ['app/services/search_broker.py'],
    views: ['chat'], x: 1150, y: 220,
  },
  {
    id: 'web-safety', title: 'Web-Safety', subtitle: 'SSRF-gehärteter Abruf', layer: 'Safety',
    status: 'implemented', boundary: 'local',
    description: 'Ruft einzelne Quellen sicher ab (blockiert private/loopback/Metadaten-Adressen) und liefert die geprüften Evidence-Records zurück an den Tool-Executor.',
    responsibilities: ['Zieladresse gegen private/interne Netze prüfen', 'Evidence-Record erzeugen'],
    paths: ['app/services/web_safety/proxy_sandbox.py'],
    views: ['chat'], x: 1330, y: 220,
  },
  {
    id: 'code-runner', title: 'Code-Ausführung', subtitle: 'Sandbox, netzwerk-isoliert', layer: 'Sandbox',
    status: 'implemented', boundary: 'local',
    description: 'Führt vom Nutzer angestoßenen Code in einer eigenen Sandbox aus - eigener OS-Nutzer, eigener Netzwerk-Namespace.',
    responsibilities: ['Code isoliert ausführen', 'Ergebnis/Artefakte zurückgeben'],
    paths: ['app/scripts/run_sandboxed.sh', 'app/api/routers/code_exec_router.py'],
    views: ['chat', 'persistence'], x: 1150, y: 380,
  },
  {
    id: 'workspace-artifacts', title: 'Workspace-Artefakte', subtitle: 'Dateien pro Sitzung', layer: 'Sandbox',
    status: 'in-progress', boundary: 'local',
    description: 'Von Code-Ausführungen erzeugte Dateien werden pro Sitzung gespeichert. Es gibt noch keine eigenständige Workspace-Übersicht, nur Download-Links direkt im Chat.',
    responsibilities: ['Sitzungsdateien speichern', 'Auflisten/Download erlauben'],
    paths: ['app/services/session_workspace.py', 'frontend/src/components/MarkdownMessage.jsx'],
    views: ['chat', 'persistence'], x: 1330, y: 380,
  },
  {
    id: 'persistence', title: 'Persistenz', subtitle: 'PostgreSQL · Neo4j · Redis', layer: 'Persistence',
    status: 'implemented', boundary: 'local',
    description: 'PostgreSQL (mit pgvector) für Konversationen und Nutzerdaten, Neo4j für den Konzept-Graph, Redis ausschließlich für kurzlebige Daten wie Rate-Limiting und Suchcache.',
    responsibilities: ['Konversationen dauerhaft speichern', 'Konzept-Graph führen', 'Rate-Limits/Kurzzeit-Cache halten'],
    paths: ['app/models', 'app/services/redis_service.py'],
    views: ['persistence'], x: 970, y: 480,
  },
  {
    id: 'ollama-local', title: 'Ollama (lokal)', subtitle: 'Lokale Modelle', layer: 'Runtime',
    status: 'implemented', boundary: 'local',
    description: 'Standard-Pfad für Inferenz - Modelle laufen vollständig auf eigener Hardware, nichts verlässt das System.',
    responsibilities: ['Lokale Modelle ausführen', 'Streaming-Tokens liefern'],
    paths: ['app/services/ollama_capabilities.py'],
    views: ['system', 'chat'], x: 790, y: 430,
  },
  {
    id: 'hailo-npu', title: 'Hailo-8L NPU', subtitle: 'RPi5 · Edge-Vision', layer: 'Edge',
    status: 'implemented', boundary: 'local',
    description: 'Eigenständiges Edge-Gerät (Raspberry Pi 5 + Hailo-8L) für Objekterkennung/Pose/Gesichter - ein optionaler Seitenpfad, unabhängig vom Text-Modell-Pfad, bleibt aber immer lokal.',
    responsibilities: ['Bilderkennung auf der NPU ausführen', 'Ergebnisse an das Backend zurückgeben'],
    paths: ['app/services/hailo_rpi5_client.py', 'app/api/routers/hailo_router.py'],
    views: ['chat'], x: 1150, y: 110,
  },
  {
    id: 'ollama-cloud', title: 'Ollama Cloud', subtitle: 'Nur bei :cloud-Modell', layer: 'Runtime',
    status: 'implemented', boundary: 'cloud',
    description: 'Wird ausschließlich erreicht, wenn ein Nutzer bewusst ein Modell mit ":cloud"-Kennzeichnung auswählt. Die lokale Infrastruktur, Persistenz und alle Nutzerdaten bleiben davon unberührt - nur der Inferenz-Aufruf für dieses eine Modell verlässt das System.',
    responsibilities: ['Inferenz für explizit gewählte :cloud-Modelle ausführen'],
    paths: [], views: ['system', 'chat'], x: 1600, y: 430,
  },
];

// {from, to, label, kind, views[]} - `kind` drives both the semantic
// label/legend grouping AND (via kindFlow above) the visual style.
export const architectureEdges = [
  { from: 'user-browser', to: 'frontend', label: 'Anfrage', kind: 'request', views: ['system', 'chat'] },
  { from: 'frontend', to: 'user-browser', label: 'Antwort', kind: 'stream', views: ['system', 'chat'] },
  { from: 'native-apps', to: 'backend', label: 'geplant: REST', kind: 'request', views: ['system', 'chat'] },

  { from: 'frontend', to: 'backend', label: 'REST + SSE', kind: 'request', views: ['system', 'chat'] },
  { from: 'backend', to: 'auth-privacy-consent', label: 'Consent-Gate', kind: 'auth-consent', views: ['chat'] },
  { from: 'backend', to: 'admin-functions', label: 'Admin-API', kind: 'request', views: ['persistence'] },
  { from: 'backend', to: 'hailo-npu', label: 'Vision-Anfrage', kind: 'tool-call', views: ['chat'] },

  { from: 'backend', to: 'context-memory', label: 'Kontext anfordern', kind: 'request', views: ['system', 'chat'] },
  { from: 'context-memory', to: 'model-inference', label: 'Kontext', kind: 'context', views: ['system', 'chat'] },
  { from: 'model-inference', to: 'context-memory', label: 'Verlauf speichern', kind: 'memory-write', views: ['system', 'chat'] },

  { from: 'backend', to: 'model-inference', label: 'Prompt', kind: 'request', views: ['system', 'chat'] },
  { from: 'model-inference', to: 'chat-streaming', label: 'Modell-Ausgabe', kind: 'stream', views: ['chat'] },
  { from: 'chat-streaming', to: 'thinking', label: 'thinking', kind: 'stream', views: ['chat'] },
  { from: 'chat-streaming', to: 'tasks', label: 'tasks', kind: 'stream', views: ['chat'] },
  { from: 'chat-streaming', to: 'frontend', label: 'Antwort', kind: 'stream', views: ['chat'] },

  { from: 'model-inference', to: 'tool-executor', label: 'ggf. Tool-Call', kind: 'tool-call', views: ['system', 'chat'] },
  { from: 'tool-executor', to: 'model-inference', label: 'Evidence / Ergebnis', kind: 'tool-result', views: ['system', 'chat'] },
  { from: 'tool-executor', to: 'web-search', label: 'search_type=web', kind: 'request', views: ['chat'] },
  { from: 'web-search', to: 'web-safety', label: 'Quellen abrufen', kind: 'request', views: ['chat'] },
  { from: 'web-safety', to: 'tool-executor', label: 'Evidence Records', kind: 'evidence', views: ['chat'] },
  { from: 'tool-executor', to: 'code-runner', label: 'Code ausführen', kind: 'request', views: ['chat'] },
  { from: 'code-runner', to: 'workspace-artifacts', label: 'Dateien ablegen', kind: 'memory-write', views: ['chat', 'persistence'] },

  { from: 'model-inference', to: 'ollama-local', label: 'lokale Inferenz', kind: 'model-inference', views: ['system', 'chat'] },
  { from: 'model-inference', to: 'ollama-cloud', label: 'nur bei :cloud-Modell', kind: 'optional-cloud', views: ['system', 'chat'] },

  { from: 'backend', to: 'persistence', label: 'Sessions/Nutzer', kind: 'memory-write', views: ['persistence'] },
  { from: 'persistence', to: 'context-memory', label: 'Verlauf laden', kind: 'memory-read', views: ['persistence'] },
  { from: 'context-memory', to: 'persistence', label: 'Konzept-Graph', kind: 'memory-write', views: ['persistence'] },
  { from: 'auth-privacy-consent', to: 'persistence', label: 'Consent-Status', kind: 'memory-write', views: ['persistence'] },
  { from: 'admin-functions', to: 'persistence', label: 'Nutzerverwaltung', kind: 'memory-write', views: ['persistence'] },
];
