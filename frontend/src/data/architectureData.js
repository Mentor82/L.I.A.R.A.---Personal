// Data model for the interactive Architecture Map (/architecture).
// Node/edge content is Personal-specific; the *pattern* (typed nodes with
// manual x/y layout, edges filtered per view, click-to-select) is adapted
// from the sibling LIARA-core repo's own architecture map
// (Mentor82/L.I.A.R.A., frontend/web-ui/src/app/architecture/), per
// GitHub issue #3's explicit instruction to reuse that UI/interaction
// approach without copying its LIARA-core-specific content (governance,
// dreaming, WSL sessions, live heartbeat) 1:1.

export const architectureViews = [
  { id: 'system', label: 'System', description: 'Alle Komponenten und die lokal/Cloud-Grenze' },
  { id: 'chat', label: 'Chat & Agent', description: 'Vom Nutzer-Request bis zur geprüften Antwort' },
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

export const kindLabels = {
  data: 'Daten',
  decision: 'Entscheidung',
  mutation: 'Mutation',
  validation: 'Prüfung',
};

// {id, title, subtitle, layer, status, boundary, description,
//  responsibilities[], paths[], views[], x, y}
// No port numbers / worker counts / runtime IDs in any text field here -
// this is the public view; those details belong in deployment docs.
export const architectureNodes = [
  {
    id: 'user-browser', title: 'Nutzer / Browser', subtitle: 'Web-Client', layer: 'Interface',
    status: 'implemented', boundary: 'client',
    description: 'Die Person, die Liara über den Browser nutzt - eingeloggt oder als Gast.',
    responsibilities: ['Anfragen stellen', 'Antworten, Diagramme und Dateien empfangen'],
    paths: [], views: ['system', 'chat'], x: 20, y: 290,
  },
  {
    id: 'frontend', title: 'Frontend', subtitle: 'React SPA', layer: 'Interface',
    status: 'implemented', boundary: 'local',
    description: 'Single-Page-App, ausgeliefert vom selbstgehosteten Server - keine Drittanbieter-CDN-Abhängigkeit.',
    responsibilities: ['UI rendern', 'SSE-Stream konsumieren', 'Konsens-Dialoge anzeigen'],
    paths: ['frontend/src/components/Chat.jsx', 'frontend/src/App.jsx'],
    views: ['system', 'chat'], x: 250, y: 290,
  },
  {
    id: 'backend', title: 'Liara Backend', subtitle: 'FastAPI', layer: 'Boundary',
    status: 'implemented', boundary: 'local',
    description: 'Zentraler API-Server. Nimmt Requests entgegen, prüft Auth/Consent und delegiert an die Fachdienste.',
    responsibilities: ['Requests validieren', 'Auth/Consent durchsetzen', 'An Chat-, Admin- und Vision-Pfade delegieren'],
    paths: ['app/main.py', 'app/api/routers'],
    views: ['system', 'chat', 'persistence'], x: 430, y: 290,
  },
  {
    id: 'auth-privacy-consent', title: 'Auth, Privacy & Consent', subtitle: 'Login · Consent-Gates', layer: 'Governance',
    status: 'implemented', boundary: 'local',
    description: 'JWT-Login und die Consent-Prüfungen, die jedem sensiblen Tool-Aufruf vorgeschaltet sind (z.B. Websuche, Standort).',
    responsibilities: ['Login/Session verwalten', 'Privacy-Einstellungen speichern', 'Consent je Tool prüfen, bevor es aufgerufen wird'],
    paths: ['app/api/routers/privacy_router.py', 'app/services/tool_executor.py'],
    views: ['chat', 'persistence'], x: 340, y: 100, },
  {
    id: 'admin-functions', title: 'Admin-Funktionen', subtitle: 'Nutzer · System · Logs · Terminal', layer: 'Governance',
    status: 'implemented', boundary: 'local',
    description: 'Verwaltungsoberfläche für Admin-Nutzer: Benutzerverwaltung, Systemkonfiguration, Log-Einsicht, Service-Terminal, Update-Check.',
    responsibilities: ['Nutzer verwalten', 'Dienste neu starten/beobachten', 'Logs einsehen', 'Updates prüfen'],
    paths: ['app/api/routers/admin_router.py', 'frontend/src/components/AdminLayout.jsx'],
    views: ['persistence'], x: 430, y: 480,
  },
  {
    id: 'chat-streaming', title: 'Chat-Streaming', subtitle: 'SSE-Ereignisse', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: 'Streamt eine Antwort als mehrere separate Ereignistypen statt nur als Text - Denkprozess, Aufgaben-Update und Agent-Schritte bleiben unterscheidbar.',
    responsibilities: ['Modellantwort streamen', 'Ereignistypen (thinking/tasks/agent_steps/content) trennen', 'Nachricht am Ende persistieren'],
    paths: ['app/api/routers/chat_streaming.py'],
    views: ['system', 'chat'], x: 610, y: 290,
  },
  {
    id: 'thinking', title: 'Thinking', subtitle: 'Natives Denkfeld', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: "Zeigt Ollamas nativen Denkprozess separat von der eigentlichen Antwort an.",
    responsibilities: ['Denkprozess vom Antworttext trennen', 'Live streamen'],
    paths: ['app/api/routers/chat_streaming.py'],
    views: ['chat'], x: 790, y: 100,
  },
  {
    id: 'tasks', title: 'Tasks / Aufgaben', subtitle: 'Modellbehauptetes Update', layer: 'Chat',
    status: 'implemented', boundary: 'local',
    description: 'Vom Modell selbst formulierte Aufgabenliste (aus einem <tasks>-Block) - bewusst als "vom Modell behauptet" gekennzeichnet, nicht als system-bestätigt.',
    responsibilities: ['<tasks>-Block erkennen', 'Als Vorschlag darstellen'],
    paths: ['app/services/task_block_extractor.py'],
    views: ['chat'], x: 790, y: 200,
  },
  {
    id: 'tool-executor', title: 'Tool Calling / Agent', subtitle: 'Native Ollama Tools', layer: 'Reasoning',
    status: 'implemented', boundary: 'local',
    description: 'Modelle mit Tool-Fähigkeit können bis zu drei zusätzliche Runden selbst Tools aufrufen, bevor eine finale Antwort erzwungen wird. Jeder Aufruf durchläuft zuerst einen echten Consent-Check.',
    responsibilities: ['Tool-Aufrufe des Modells entgegennehmen', 'Consent prüfen', 'Tool ausführen und Ergebnis zurückgeben'],
    paths: ['app/services/tool_registry.py', 'app/services/tool_executor.py'],
    views: ['system', 'chat'], x: 790, y: 290,
  },
  {
    id: 'context-memory', title: 'Context & Memory', subtitle: 'Konzept-Graph · Verlauf', layer: 'Knowledge',
    status: 'implemented', boundary: 'local',
    description: 'Baut aus dem Gesprächsverlauf und extrahierten Konzepten (Nomen/Eigennamen) den Gedächtnis-Kontext für die nächste Antwort.',
    responsibilities: ['Konzepte extrahieren', 'Kontext aus Verlauf + Graph zusammenstellen'],
    paths: ['app/services/memory_service.py'],
    views: ['system', 'chat', 'persistence'], x: 610, y: 480,
  },
  {
    id: 'web-search', title: 'Web-Suche', subtitle: 'SearXNG · Freshness-Policy', layer: 'Reasoning',
    status: 'implemented', boundary: 'local',
    description: 'Recherchiert über ein selbstgehostetes, keyless SearXNG - niemals über kommerzielle Such-APIs. Ergebnisse können nach Aktualität sortiert werden, undatierte Quellen werden markiert.',
    responsibilities: ['SearXNG abfragen', 'Ergebnisse nach Aktualität sortieren', 'Quellen mit Datum/Domain aufbereiten'],
    paths: ['app/services/search_broker.py'],
    views: ['chat'], x: 970, y: 200,
  },
  {
    id: 'web-safety', title: 'Web-Safety', subtitle: 'SSRF-gehärteter Abruf', layer: 'Safety',
    status: 'implemented', boundary: 'local',
    description: 'Ruft einzelne Quellen sicher ab: blockiert private/loopback/Metadaten-Adressen und nicht-http(s)-Schemata, auch nach Redirects.',
    responsibilities: ['Zieladresse gegen private/interne Netze prüfen', 'Nur http(s) erlauben', 'Redirect-Ziel erneut prüfen'],
    paths: ['app/services/web_safety/proxy_sandbox.py'],
    views: ['chat'], x: 1150, y: 200,
  },
  {
    id: 'code-runner', title: 'Code-Ausführung', subtitle: 'Sandbox, netzwerk-isoliert', layer: 'Sandbox',
    status: 'implemented', boundary: 'local',
    description: 'Führt vom Nutzer angestoßenen Code in einer eigenen Sandbox aus - eigener OS-Nutzer, eigener Netzwerk-Namespace.',
    responsibilities: ['Code in isolierter Sandbox ausführen', 'Ressourcenlimits durchsetzen', 'Ergebnis/Artefakte zurückgeben'],
    paths: ['app/scripts/run_sandboxed.sh', 'app/api/routers/code_exec_router.py'],
    views: ['chat', 'persistence'], x: 970, y: 380,
  },
  {
    id: 'workspace-artifacts', title: 'Workspace-Artefakte', subtitle: 'Dateien pro Sitzung', layer: 'Sandbox',
    status: 'in-progress', boundary: 'local',
    description: 'Von Code-Ausführungen erzeugte Dateien werden pro Sitzung gespeichert und können heruntergeladen werden. Es gibt noch keine eigenständige Workspace-Übersicht, nur Download-Links direkt im Chat.',
    responsibilities: ['Sitzungsdateien speichern', 'Auflisten/Download erlauben'],
    paths: ['app/services/session_workspace.py', 'frontend/src/components/MarkdownMessage.jsx'],
    views: ['chat', 'persistence'], x: 1150, y: 380,
  },
  {
    id: 'persistence', title: 'Persistenz', subtitle: 'PostgreSQL · Neo4j · Redis', layer: 'Persistence',
    status: 'implemented', boundary: 'local',
    description: 'PostgreSQL (mit pgvector) für Konversationen und Nutzerdaten, Neo4j für den Konzept-Graph, Redis ausschließlich für kurzlebige Daten wie Rate-Limiting und Suchcache.',
    responsibilities: ['Konversationen dauerhaft speichern', 'Konzept-Graph führen', 'Rate-Limits und Kurzzeit-Cache halten'],
    paths: ['app/models', 'app/services/redis_service.py'],
    views: ['persistence'], x: 970, y: 480,
  },
  {
    id: 'ollama-local', title: 'Ollama (lokal)', subtitle: 'Lokale Modelle', layer: 'Runtime',
    status: 'implemented', boundary: 'local',
    description: 'Standard-Pfad für Inferenz - Modelle laufen vollständig auf eigener Hardware, nichts verlässt das System.',
    responsibilities: ['Lokale Modelle ausführen', 'Streaming-Tokens liefern'],
    paths: ['app/services/ollama_capabilities.py'],
    views: ['system', 'chat'], x: 520, y: 100,
  },
  {
    id: 'hailo-npu', title: 'Hailo-8L NPU', subtitle: 'RPi5 · Edge-Vision', layer: 'Edge',
    status: 'implemented', boundary: 'local',
    description: 'Eigenständiges Edge-Gerät (Raspberry Pi 5 + Hailo-8L) für Objekterkennung/Pose/Gesichter - bleibt eine lokale Edge/NPU-Komponente, unabhängig davon, ob gerade ein Cloud-Modell für den Text-Chat gewählt ist.',
    responsibilities: ['Bilderkennung auf der NPU ausführen', 'Ergebnisse an das Backend zurückgeben'],
    paths: ['app/services/hailo_rpi5_client.py', 'app/api/routers/hailo_router.py'],
    views: ['system'], x: 700, y: 100,
  },
  {
    id: 'ollama-cloud', title: 'Ollama Cloud', subtitle: 'Nur bei :cloud-Modell', layer: 'Runtime',
    status: 'implemented', boundary: 'cloud',
    description: 'Wird ausschließlich erreicht, wenn ein Nutzer bewusst ein Modell mit ":cloud"-Kennzeichnung auswählt. Die lokale Infrastruktur, Persistenz und alle Nutzerdaten bleiben davon unberührt - nur der Inferenz-Aufruf für dieses eine Modell verlässt das System.',
    responsibilities: ['Inferenz für explizit gewählte :cloud-Modelle ausführen'],
    paths: [], views: ['system'], x: 1420, y: 100,
  },
];

// {from, to, label, kind: 'data'|'decision'|'mutation'|'validation', views[], crossesBoundary?}
export const architectureEdges = [
  { from: 'user-browser', to: 'frontend', label: 'HTTPS', kind: 'data', views: ['system', 'chat'] },
  { from: 'frontend', to: 'backend', label: 'REST + SSE', kind: 'data', views: ['system', 'chat'] },
  { from: 'backend', to: 'auth-privacy-consent', label: 'Consent-Gate', kind: 'validation', views: ['chat'] },
  { from: 'backend', to: 'admin-functions', label: 'Admin-API', kind: 'data', views: ['persistence'] },
  { from: 'backend', to: 'chat-streaming', label: 'Chat-Request', kind: 'data', views: ['system', 'chat'] },
  { from: 'chat-streaming', to: 'thinking', label: 'thinking', kind: 'data', views: ['chat'] },
  { from: 'chat-streaming', to: 'tasks', label: 'tasks', kind: 'data', views: ['chat'] },
  { from: 'chat-streaming', to: 'tool-executor', label: 'tool_calls', kind: 'decision', views: ['system', 'chat'] },
  { from: 'chat-streaming', to: 'context-memory', label: 'Kontext laden', kind: 'data', views: ['system', 'chat'] },
  { from: 'tool-executor', to: 'web-search', label: 'search_type=web', kind: 'data', views: ['chat'] },
  { from: 'web-search', to: 'web-safety', label: 'Quellen abrufen', kind: 'data', views: ['chat'] },
  { from: 'tool-executor', to: 'code-runner', label: 'Code ausführen', kind: 'mutation', views: ['chat'] },
  { from: 'code-runner', to: 'workspace-artifacts', label: 'Dateien ablegen', kind: 'mutation', views: ['chat', 'persistence'] },
  { from: 'backend', to: 'ollama-local', label: 'Prompt', kind: 'data', views: ['system', 'chat'] },
  { from: 'backend', to: 'ollama-cloud', label: 'nur bei :cloud-Modell', kind: 'data', views: ['system'], crossesBoundary: true },
  { from: 'backend', to: 'hailo-npu', label: 'Vision-Anfrage', kind: 'data', views: ['system'] },
  { from: 'backend', to: 'persistence', label: 'Sessions/Nutzer', kind: 'mutation', views: ['persistence'] },
  { from: 'context-memory', to: 'persistence', label: 'Konzept-Graph', kind: 'mutation', views: ['persistence'] },
  { from: 'auth-privacy-consent', to: 'persistence', label: 'Consent-Status', kind: 'mutation', views: ['persistence'] },
  { from: 'admin-functions', to: 'persistence', label: 'Nutzerverwaltung', kind: 'mutation', views: ['persistence'] },
];
