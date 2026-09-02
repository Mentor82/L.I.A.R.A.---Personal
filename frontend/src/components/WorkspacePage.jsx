import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { EditorView } from '@codemirror/view';
import { python } from '@codemirror/lang-python';
import { StreamLanguage } from '@codemirror/language';
import { julia as juliaLegacyMode } from '@codemirror/legacy-modes/mode/julia';
import { chatAPI, workspaceAPI, codeExecAPI, preferencesAPI } from '../services/api';
import { streamChatSSE } from '../services/sseClient';
import { getSessionMessages } from '../services/chatService';
import CodeRunResult from './CodeRunResult';
import DiffView from './DiffView';
import MarkdownMessage from './MarkdownMessage';
import AgentDrawer from './AgentDrawer';
import WorkspaceTerminal from './WorkspaceTerminal';
import EditorPane from './EditorPane';
import './WorkspacePage.css';

const PROPOSAL_ACTION_LABELS = {
  create: 'Neu anlegen',
  update: 'Überschreiben',
  delete: 'Löschen',
  install: '📦 Paket installieren',
  remove: '📦 Paket entfernen',
};

const juliaLanguage = StreamLanguage.define(juliaLegacyMode);

// Maps a file extension to a CodeMirror language extension and the sandbox's
// language identifier (app/services/code_sandbox.py's LANGUAGE_ALIASES) -
// files with no known extension are still fully editable, just without
// syntax highlighting and without a Run button.
const LANGUAGE_BY_EXTENSION = {
  py: { cm: python(), runLanguage: 'python' },
  jl: { cm: juliaLanguage, runLanguage: 'julia' },
};

// Three fixed presets (not a slider/numeric input) - "Klein/Mittel/Groß" is
// enough range for reading comfort without turning this into a settings
// screen, matching issue #5's "ruhig, kein Feature-Regler" steer. Kept in
// sync with app/api/routers/user_preferences_router.py's WORKSPACE_FONT_SIZES.
const FONT_SIZE_PRESETS = [
  { size: 13, label: 'Klein' },
  { size: 15, label: 'Mittel' },
  { size: 17, label: 'Groß' },
];
const DEFAULT_FONT_SIZE = 14; // matches the backend column's DEFAULT before a user ever picks a preset

// Same family as code-server/VS Code's own editor.fontFamily convention
// (a deliberate coding font first, native monospace fallbacks after) -
// JetBrains Mono/Fira Code are already used for the Terminal and search
// matches elsewhere on this page, Consolas/Menlo cover Windows/Mac when
// neither webfont is installed locally.
const EDITOR_FONT_STACK = "'JetBrains Mono', 'Fira Code', Consolas, Menlo, 'Courier New', monospace";

// Reads the app-wide dark/light choice straight off the DOM attribute
// PageLayout/UserPreferences already resolve it to (see utils/theme.js's
// applyTheme) rather than re-deriving system-preference logic here, and
// stays in sync via a MutationObserver so a theme change made elsewhere
// (e.g. the Preferences page, still mounted in another tab) is picked up
// without needing Workspace-specific plumbing for it.
function useAppTheme() {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute('data-theme') || 'dark'
  );
  useEffect(() => {
    const target = document.documentElement;
    const observer = new MutationObserver(() => {
      setTheme(target.getAttribute('data-theme') || 'dark');
    });
    observer.observe(target, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);
  return theme;
}

function extensionOf(filename) {
  const dot = filename.lastIndexOf('.');
  return dot >= 0 ? filename.slice(dot + 1).toLowerCase() : '';
}

function basenameOf(path) {
  return path.includes('/') ? path.slice(path.lastIndexOf('/') + 1) : path;
}

function parentOf(path) {
  return path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
}

/**
 * Builds a tree (folders-first, then files, alphabetically within each
 * group) from the flat, path-addressed entry list list_session_files()
 * returns. Kept as a pure client-side projection of that one flat list -
 * the backend never nests JSON - so a future search/filter view can reuse
 * the exact same entries without a second data shape.
 */
function buildTree(entries) {
  const byParent = new Map();
  for (const entry of entries) {
    const key = entry.parent || '';
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key).push(entry);
  }
  const sortGroup = (arr) => [...arr].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  const build = (parentPath) => sortGroup(byParent.get(parentPath) || []).map((entry) => ({
    ...entry,
    children: entry.type === 'folder' ? build(entry.path) : null,
  }));
  return build('');
}

function formatBytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

// Wraps the first occurrence of `query` in `text` with <mark> - search
// results only ever highlight one hit per line (the line itself already
// tells the user there's a match; this is just a visual pointer to where).
function highlightMatch(text, query, caseSensitive) {
  if (!query) return text;
  const haystack = caseSensitive ? text : text.toLowerCase();
  const needle = caseSensitive ? query : query.toLowerCase();
  const idx = haystack.indexOf(needle);
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="workspace-search-highlight">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

const SOURCE_LABELS = {
  user: 'Selbst erstellt',
  upload: 'Hochgeladen',
  code_runner: 'Von Code-Ausführung erzeugt',
  liara: 'Von LIARA erstellt',
  agent: 'Vom Agent erstellt',
  web_research: 'Aus Web-Recherche',
  generated: 'Automatisch erzeugt',
  unknown: 'Unbekannte Herkunft',
};

// Color-codes the same source values (badge look matches Tasks.jsx's
// category/priority pill convention) instead of plain gray meta text.
const SOURCE_BADGE_CLASS = {
  user: 'workspace-badge-user',
  upload: 'workspace-badge-user',
  code_runner: 'workspace-badge-code-runner',
  liara: 'workspace-badge-liara',
  agent: 'workspace-badge-liara',
  web_research: 'workspace-badge-liara',
  generated: 'workspace-badge-code-runner',
  unknown: 'workspace-badge-unknown',
};

export function isImageFile(filename) {
  if (!filename) return false;
  return /\.(png|jpe?g|gif|webp|svg|bmp|ico)$/i.test(filename);
}

function getFileIcon(filename) {
  if (isImageFile(filename)) return '🖼️';
  if (filename.endsWith('.py')) return '🐍';
  if (filename.endsWith('.jl')) return '🟣';
  if (filename.endsWith('.json')) return '📋';
  if (filename.endsWith('.md')) return '📝';
  return '📄';
}

/**
 * One row of the Explorer tree - a folder (expandable, with "new file/folder
 * here"/rename/delete) or a file (existing open/context/download/rename/
 * delete actions). Recurses into `node.children` for folders. All actions
 * are passed down as a single `handlers` object rather than drilled
 * individually, since every recursive call needs the exact same set.
 */
function WorkspaceTreeNode({ node, depth, activeTab, collapsedFolders, dragOverTarget, handlers }) {
  const indent = { paddingLeft: `${depth * 1.1}rem` };

  if (node.type === 'folder') {
    const collapsed = collapsedFolders.has(node.path);
    return (
      <li className="workspace-tree-folder">
        <div
          className={`workspace-tree-row ${dragOverTarget === node.path ? 'workspace-drag-over' : ''}`}
          style={indent}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); handlers.onFolderDragEnter(node.path); }}
          onDragLeave={(e) => { e.stopPropagation(); handlers.onFolderDragLeave(); }}
          onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handlers.onFolderDrop(node.path, e.dataTransfer.files); }}
        >
          <button
            className="workspace-file-open workspace-folder-open"
            onClick={() => handlers.onToggleCollapse(node.path)}
          >
            <span className="workspace-tree-chevron">{collapsed ? '▸' : '▾'}</span>
            <span className="workspace-folder-icon">📁</span>
            <span className="workspace-file-name">{node.name}</span>
          </button>
          <div className="workspace-file-actions">
            <button className="workspace-icon-btn" title="Neue Datei hier" onClick={() => handlers.onNewFileHere(node.path)}>➕</button>
            <button className="workspace-icon-btn" title="Neuer Ordner hier" onClick={() => handlers.onNewFolderHere(node.path)}>📁</button>
            <button className="workspace-icon-btn" title="Hierher hochladen" onClick={() => handlers.onUploadHere(node.path)}>⬆️</button>
            <button className="workspace-icon-btn" title="Umbenennen" onClick={() => handlers.onRename(node.path, node.name)}>✏️</button>
            <button className="workspace-icon-btn danger" title="Löschen" onClick={() => handlers.onDelete(node.path, 'folder')}>🗑️</button>
          </div>
        </div>
        {!collapsed && node.children.length > 0 && (
          <ul className="workspace-file-list workspace-tree-children">
            {node.children.map((child) => (
              <WorkspaceTreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                activeTab={activeTab}
                collapsedFolders={collapsedFolders}
                dragOverTarget={dragOverTarget}
                handlers={handlers}
              />
            ))}
          </ul>
        )}
      </li>
    );
  }

  return (
    <li className={activeTab === node.path ? 'active' : ''}>
      <div className="workspace-tree-row" style={indent}>
        <button className="workspace-file-open" onClick={() => handlers.onOpenFile(node.path)}>
          <span className="workspace-file-icon">{getFileIcon(node.name)}</span>
          <span className="workspace-file-name">{node.name}</span>
          <span className="workspace-file-badges">
            <span className="workspace-file-size">{formatBytes(node.size)}</span>
            <span className={`workspace-source-badge ${SOURCE_BADGE_CLASS[node.source] || 'workspace-badge-unknown'}`}>
              {SOURCE_LABELS[node.source] || node.source}
            </span>
          </span>
        </button>
        <div className="workspace-file-actions">
          <button
            className={`workspace-icon-btn ${node.selected_for_context ? 'active' : ''}`}
            title="Zu Chat-Kontext hinzufügen"
            onClick={() => handlers.onToggleContext(node.path)}
          >💬</button>
          <button className="workspace-icon-btn" title="Umbenennen" onClick={() => handlers.onRename(node.path, node.name)}>✏️</button>
          <button className="workspace-icon-btn" title="Herunterladen" onClick={() => handlers.onDownload(node.path)}>⬇️</button>
          <button className="workspace-icon-btn danger" title="Löschen" onClick={() => handlers.onDelete(node.path, 'file')}>🗑️</button>
        </div>
      </div>
    </li>
  );
}

/**
 * Right-hand chat panel scoped to the Workspace's current session - reuses
 * the exact same /api/chat/stream agent Chat.jsx talks to (same session_id,
 * same tool registry, same workspace_propose_change tool), not a separate
 * workspace-only agent (deliberate call, see the architecture discussion:
 * the session's workspace manifest + "add to context" files already flow
 * into that one shared agent server-side, keyed by session_id). This is
 * intentionally a minimal SSE consumer - only 'content', 'workspace_proposal'
 * and 'error' are handled, unlike Chat.jsx's full event set (thinking/tasks/
 * web search/agent steps), since this panel is for quick workspace-scoped
 * asks, not a replacement for the main chat.
 */
function AgentChatPanel({ sessionId, onClose, onWorkspaceProposal }) {
  const [messages, setMessages] = useState([]); // [{role: 'user'|'assistant', content}]
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  // Model selector - shares the same localStorage key Chat.jsx reads/writes
  // (liara_selected_model), so picking one here also becomes the main chat's
  // pre-selected model next time it opens, and vice versa - one "last used
  // model" for the user, not two independently-drifting selections.
  const [models, setModels] = useState([]);
  const [model, setModel] = useState(() => localStorage.getItem('liara_selected_model') || 'llama3.2:3b');

  useEffect(() => {
    chatAPI.getModels()
      .then((data) => setModels(data?.models || []))
      .catch(() => setModels([]));
  }, []);

  const changeModel = (value) => {
    setModel(value);
    localStorage.setItem('liara_selected_model', value);
  };

  // Loads this session's existing conversation (the same one visible in
  // /chat) so the panel isn't confusingly blank on open - it's one shared
  // history, not a separate workspace-only thread.
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingHistory(true);
    getSessionMessages(sessionId)
      .then((list) => {
        if (!cancelled) setMessages((list || []).map((m) => ({ role: m.role, content: m.content })));
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => { cancelled = true; };
  }, [sessionId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || sending || !sessionId) return;
    setError(null);
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setSending(true);

    const assistantMsgId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : 'ws_msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);

    let assistantContent = '';

    const updateAssistantMsg = (newContent) => {
      assistantContent = newContent;
      setMessages((prev) => {
        const idx = prev.findIndex(m => m.id === assistantMsgId);
        if (idx === -1) {
          return [...prev, { id: assistantMsgId, role: 'assistant', content: assistantContent }];
        }
        const copy = [...prev];
        copy[idx] = { ...copy[idx], content: assistantContent };
        return copy;
      });
    };

    try {
      await streamChatSSE('/api/chat/stream', {
        message: text,
        model,
        session_id: sessionId
      }, {
        onEvent: (parsed) => {
          if (parsed.type === 'content') {
            updateAssistantMsg(assistantContent + (parsed.text || ''));
          } else if (parsed.type === 'workspace_proposal') {
            onWorkspaceProposal?.();
          }
        }
      });
    } catch (err) {
      setError(err.message || 'Fehler bei der Kommunikation mit LIARA.');
      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, role: 'assistant', content: `⚠️ ${err.message || 'Fehler bei der Kommunikation mit LIARA.'}` }
      ]);
    } finally {
      setSending(false);
    }
  };

  // Once the assistant's reply has actually started streaming in (the last
  // message is that growing entry), a separate "LIARA schreibt…" bubble
  // would just duplicate it - only show it before the first content chunk
  // arrives (last message is still the user's own).
  const assistantIsReplying = messages.length > 0 && messages[messages.length - 1].role === 'assistant';

  return (
    <aside className="workspace-agent-panel">
      <div className="workspace-agent-header">
        <span>🤖 Agent-Chat</span>
        <div className="workspace-agent-header-actions">
          <select
            className="workspace-agent-model-select"
            value={model}
            onChange={(e) => changeModel(e.target.value)}
            title="Modell auswählen"
          >
            {models.length === 0 && <option value={model}>{model}</option>}
            {models.map((m) => (
              <option key={m.name} value={m.name}>{m.name} {m.speed}</option>
            ))}
          </select>
          <button className="workspace-icon-btn" title="Schließen" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="workspace-agent-body" ref={scrollRef}>
        {loadingHistory && <p className="workspace-hint">Lade Verlauf…</p>}
        {!loadingHistory && messages.length === 0 && (
          <div className="workspace-empty">
            <div className="workspace-empty-icon">🤖</div>
            <p className="workspace-empty-title">Noch keine Nachrichten</p>
            <p className="workspace-empty-subtitle">
              Frag LIARA direkt zu dieser Session - Dateien im Kontext werden
              automatisch berücksichtigt.
            </p>
          </div>
        )}
        {!loadingHistory && messages.length > 0 && (
          <div className="workspace-agent-messages">
            {messages.map((m, i) => (
              <div key={i} className={`workspace-agent-message ${m.role === 'user' ? 'user' : 'assistant'}`}>
                {m.role === 'user' ? m.content : <MarkdownMessage content={m.content} sessionId={sessionId} />}
              </div>
            ))}
            {sending && !assistantIsReplying && (
              <div className="workspace-agent-message assistant workspace-agent-typing">LIARA schreibt…</div>
            )}
          </div>
        )}
      </div>

      {error && <div className="workspace-error workspace-agent-error">{error} <button onClick={() => setError(null)}>✕</button></div>}

      <div className="workspace-agent-input-row">
        <input
          type="text"
          placeholder="Nachricht an LIARA…"
          value={input}
          disabled={sending || !sessionId}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
        />
        <button className="workspace-btn-primary" disabled={sending || !input.trim() || !sessionId} onClick={sendMessage}>
          {sending ? '…' : 'Senden'}
        </button>
      </div>
    </aside>
  );
}


function WorkspacePage() {
  // Set by Chat.jsx's WorkspaceArtifactsBlock ("<filename> im Workspace
  // öffnen" link, via <Link state={{openWorkspaceFile}}>) - captured once in
  // a ref (not read from `location` again later) so it fires exactly once
  // per navigation into this page, not on every re-render.
  const location = useLocation();
  const pendingOpenFileRef = useRef(location.state?.openWorkspaceFile || null);

  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState(null);

  const [tabs, setTabs] = useState([]); // [{name, content, dirty}]
  const [activeTab, setActiveTab] = useState(null);
  const [running, setRunning] = useState(false);
  const [pythonVersion, setPythonVersion] = useState(
    () => localStorage.getItem('liara_sandbox_python_version') || 'python3.14'
  );

  const handlePythonVersionChange = (ver) => {
    setPythonVersion(ver);
    localStorage.setItem('liara_sandbox_python_version', ver);
  };
  // Terminal scrollback for this pane - every run, not just the last one
  // (see runTab below). Capped client-side; nothing persisted server-side.
  const [runHistory, setRunHistory] = useState([]);

  const [newFileOpen, setNewFileOpen] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderPath, setNewFolderPath] = useState('');
  const [renameTarget, setRenameTarget] = useState(null); // full path being renamed
  const [renameTargetType, setRenameTargetType] = useState('file');
  const [renameValue, setRenameValue] = useState(''); // new leaf name only, no "/"
  const [deleteTarget, setDeleteTarget] = useState(null); // full path being deleted
  const [deleteTargetType, setDeleteTargetType] = useState('file');
  const [modalError, setModalError] = useState(null);

  // Collapsed-folder paths (Explorer tree) - tracked as "collapsed" rather
  // than "expanded" so a freshly loaded/created folder needs no extra state
  // update to default to open.
  const [collapsedFolders, setCollapsedFolders] = useState(new Set());

  const cmTheme = useAppTheme() === 'light' ? 'light' : 'dark';
  const [fontSize, setFontSize] = useState(DEFAULT_FONT_SIZE);
  // Single EditorView.theme() extension shared by both panes - font size is
  // Workspace-wide, not per-pane, so one preference change updates both at
  // once. Previously had no fontFamily at all, so the editor silently fell
  // back to the browser's own default monospace font (varies by OS/browser -
  // Consolas, DejaVu Sans Mono, whatever) instead of a deliberate choice.
  // EDITOR_FONT_STACK matches the mono font already used elsewhere in this
  // page (Terminal, search matches) plus native fallbacks for platforms
  // without those two installed, same idea as code-server/VS Code's own
  // editor.fontFamily default. Line-height tightened from a prose-like 1.6
  // to 1.45 - closer to VS Code's own ~1.35-1.5 "auto" editor line-height,
  // denser and more IDE-like than the old, more spacious value.
  const fontSizeExtension = useMemo(() => EditorView.theme({
    '&': { fontSize: `${fontSize}px`, fontFamily: EDITOR_FONT_STACK },
    '.cm-content': { lineHeight: '1.45', fontFamily: EDITOR_FONT_STACK },
    '.cm-gutters': { fontSize: `${fontSize}px`, fontFamily: EDITOR_FONT_STACK },
  }), [fontSize]);

  const [agentEnabled, setAgentEnabled] = useState(false);
  const [proposals, setProposals] = useState([]);
  const [selectedProposalIds, setSelectedProposalIds] = useState(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

  // Issue #5: minimal on-demand environment status + package popover - never
  // polled, only (re)loaded on session change and after an install/remove/
  // proposal-approve actually changes something.
  const [envStatus, setEnvStatus] = useState(null); // {exists, python_version, package_count} | null
  const [packagesOpen, setPackagesOpen] = useState(false);
  const [sessionPackages, setSessionPackages] = useState([]);
  const [packagesLoading, setPackagesLoading] = useState(false);
  const [packageInput, setPackageInput] = useState('');
  const [packageBusy, setPackageBusy] = useState(false);
  const [packageError, setPackageError] = useState(null);

  // Upload from the local computer - either the hidden <input type="file">
  // (triggered per-folder or at root) or drag & drop onto the Explorer.
  // dragOverTarget is a folder path, "root", or null - purely cosmetic
  // (hover highlight), the actual drop target is whatever fired onDrop.
  const uploadInputRef = useRef(null);
  const uploadTargetRef = useRef('');
  const [dragOverTarget, setDragOverTarget] = useState(null);

  // Project-wide text search - searchResults === null means "not searching,
  // show the normal Explorer tree"; an object (even with an empty results
  // array) means a search ran and should replace the tree view.
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCaseSensitive, setSearchCaseSensitive] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  // CodeMirror's underlying view instance, captured once on first mount
  // (switching tabs only changes the `value` prop, it doesn't remount the
  // editor) - lets a search-result click imperatively scroll to a line
  // without needing the editor to expose that as a declarative prop.
  const editorViewRef = useRef(null);
  const [pendingScrollLine, setPendingScrollLine] = useState(null); // { path, line }

  // Split editor - capped at exactly two panes (left/primary + right/split),
  // not a general N-way pane system: `splitTab` is the right pane's active
  // file, or null when not split at all. Both panes share the same `tabs`
  // pool (opening/closing a file affects both strips), each just tracks its
  // own active tab and has its own run state/editor view, mirroring the
  // primary pane's activeTab/running/runHistory/editorViewRef.
  const [splitTab, setSplitTab] = useState(null);
  const [splitRunning, setSplitRunning] = useState(false);
  const [splitRunHistory, setSplitRunHistory] = useState([]);
  const splitEditorViewRef = useRef(null);

  // Which pane last had editor focus - only rendered as a visual indicator
  // once split (see EditorPane's isActivePane), so it adds no noise in the
  // common single-pane case (issue #5: "aktiver Bereich klar erkennbar").
  const [activePane, setActivePane] = useState('primary');

  // Explorer collapse and the right-hand agent chat panel - plain client
  // state (like collapsedFolders above), not persisted server-side. Both
  // just resize the 3-way grid in .workspace-body; unmounting the collapsed
  // sidebar/closed panel loses no data since all the state that matters
  // (tabs, files, search) lives here in WorkspacePage regardless.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const [agentDrawerOpen, setAgentDrawerOpen] = useState(false);
  // Sandboxed interactive shell (WorkspaceTerminal) - docks below the editor
  // (like a normal IDE terminal), not in the right-hand panel column, so it
  // doesn't need to fight Agent-Chat/Agent Hub for a slot.
  const [shellOpen, setShellOpen] = useState(false);

  const toggleAgentPanel = () => setAgentPanelOpen((v) => !v);
  const toggleAgentDrawer = () => setAgentDrawerOpen((v) => !v);
  const toggleShell = () => setShellOpen((v) => !v);

  useEffect(() => {
    (async () => {
      try {
        let list = await chatAPI.getSessions();
        if (!list || list.length === 0) {
          try {
            const fresh = await chatAPI.createSession('Workspace');
            list = [fresh];
          } catch {
            list = [];
          }
        }
        setSessions(list);
        const savedId = parseInt(localStorage.getItem('liara_active_session'), 10);
        const initial = list.find((s) => s.id === savedId) || list[0];
        if (initial) {
          setSessionId(initial.id);
          localStorage.setItem('liara_active_session', initial.id.toString());
        }
      } catch (err) {
        setError(err.message || 'Sessions konnten nicht geladen werden.');
      }
    })();
    preferencesAPI.get()
      .then((prefs) => {
        setAgentEnabled(!!prefs?.workspace_agent_enabled);
        if (prefs?.workspace_font_size) setFontSize(prefs.workspace_font_size);
      })
      .catch(() => {});
  }, []);

  // Persisted immediately on click (not debounced - this is a deliberate,
  // infrequent choice from 3 fixed presets, not a slider being dragged).
  const changeFontSize = (size) => {
    setFontSize(size);
    preferencesAPI.update({ workspace_font_size: size }).catch(() => {});
  };

  const loadFiles = async (id) => {
    setLoadingFiles(true);
    setError(null);
    try {
      const { files: list } = await workspaceAPI.listFiles(id);
      setFiles(list);
    } catch (err) {
      setError(err.message || 'Dateien konnten nicht geladen werden.');
    } finally {
      setLoadingFiles(false);
    }
  };

  const loadProposals = async (id) => {
    try {
      const { proposals: list } = await workspaceAPI.listProposals(id, 'pending');
      setProposals(list);
      // Drop selections for proposals that no longer exist/are no longer
      // pending (already resolved elsewhere, or a session switch) instead of
      // silently keeping stale ids around for the next bulk action.
      const stillPending = new Set(list.map((p) => p.id));
      setSelectedProposalIds((prev) => new Set([...prev].filter((id) => stillPending.has(id))));
    } catch (err) {
      // Non-fatal - the proposals panel simply stays empty/stale.
    }
  };

  const loadEnvironment = async (id) => {
    try {
      const status = await workspaceAPI.getEnvironment(id);
      setEnvStatus(status);
    } catch {
      setEnvStatus(null);
    }
  };

  const loadPackages = async (id) => {
    setPackagesLoading(true);
    try {
      const { packages } = await workspaceAPI.getPackages(id);
      setSessionPackages(packages || []);
    } catch {
      setSessionPackages([]);
    } finally {
      setPackagesLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId) {
      loadFiles(sessionId);
      loadEnvironment(sessionId);
      if (agentEnabled) loadProposals(sessionId);
    }
    setPackagesOpen(false);
  }, [sessionId, agentEnabled]);

  // Debounced project-wide search - fires 300ms after the user stops typing
  // rather than on every keystroke. Clearing the query reverts to the
  // normal Explorer tree (searchResults back to null).
  useEffect(() => {
    const query = searchQuery.trim();
    if (!sessionId || !query) {
      setSearchResults(null);
      setSearching(false);
      return;
    }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const data = await workspaceAPI.search(sessionId, query, searchCaseSensitive);
        setSearchResults(data);
      } catch (err) {
        setSearchResults({ results: [], truncated: false });
        setError(err.message || 'Suche fehlgeschlagen.');
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, searchCaseSensitive, sessionId]);

  const handleApproveProposal = async (proposalId) => {
    try {
      await workspaceAPI.approveProposal(sessionId, proposalId);
      loadProposals(sessionId);
      loadFiles(sessionId);
      // Cheap either way (a package proposal changes the count, a file
      // proposal doesn't) - simpler than branching on p.kind here.
      loadEnvironment(sessionId);
      if (packagesOpen) loadPackages(sessionId);
    } catch (err) {
      setError(err.message || 'Annehmen fehlgeschlagen.');
    }
  };

  const handleRejectProposal = async (proposalId) => {
    try {
      await workspaceAPI.rejectProposal(sessionId, proposalId);
      loadProposals(sessionId);
    } catch (err) {
      setError(err.message || 'Ablehnen fehlgeschlagen.');
    }
  };

  const toggleProposalSelection = (proposalId) => {
    setSelectedProposalIds((prev) => {
      const next = new Set(prev);
      if (next.has(proposalId)) next.delete(proposalId);
      else next.add(proposalId);
      return next;
    });
  };

  const toggleSelectAllProposals = () => {
    setSelectedProposalIds((prev) =>
      prev.size === proposals.length ? new Set() : new Set(proposals.map((p) => p.id))
    );
  };

  // Bulk annehmen/ablehnen - reuses the same single-proposal endpoints (no
  // new backend bulk endpoint), fired concurrently via allSettled so one
  // failure (e.g. a proposal already resolved elsewhere) doesn't hide the
  // others that did succeed.
  const handleBulkResolve = async (approve) => {
    const ids = Array.from(selectedProposalIds);
    if (ids.length === 0 || bulkBusy) return;
    setBulkBusy(true);
    setError(null);
    try {
      const results = await Promise.allSettled(
        ids.map((id) => (approve ? workspaceAPI.approveProposal(sessionId, id) : workspaceAPI.rejectProposal(sessionId, id)))
      );
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0) {
        setError(`${failed} von ${ids.length} Vorschlägen konnten nicht ${approve ? 'angenommen' : 'abgelehnt'} werden.`);
      }
    } finally {
      setSelectedProposalIds(new Set());
      loadProposals(sessionId);
      loadFiles(sessionId);
      loadEnvironment(sessionId);
      if (packagesOpen) loadPackages(sessionId);
      setBulkBusy(false);
    }
  };

  const activeTabData = useMemo(() => tabs.find((t) => t.name === activeTab), [tabs, activeTab]);
  const activeExt = activeTab ? extensionOf(activeTab) : '';
  const activeLang = LANGUAGE_BY_EXTENSION[activeExt];

  const splitTabData = useMemo(() => tabs.find((t) => t.name === splitTab), [tabs, splitTab]);
  const splitExt = splitTab ? extensionOf(splitTab) : '';
  const splitLang = LANGUAGE_BY_EXTENSION[splitExt];

  // Performs the actual scroll-to-line once the editor is showing the file
  // the pending search-result click asked for (openSearchResult may have
  // had to wait on an async file fetch first, so this can't happen inline).
  useEffect(() => {
    if (!pendingScrollLine || !activeTabData || activeTabData.name !== pendingScrollLine.path) return;
    const view = editorViewRef.current;
    if (!view) {
      setPendingScrollLine(null);
      return;
    }
    try {
      const targetLine = Math.min(Math.max(pendingScrollLine.line, 1), view.state.doc.lines);
      const lineInfo = view.state.doc.line(targetLine);
      view.dispatch({
        selection: { anchor: lineInfo.from, head: lineInfo.to },
        scrollIntoView: true,
      });
      view.focus();
    } catch (err) {
      // Line out of range or a transient editor-state mismatch - not worth
      // surfacing as an error, the file itself still opened correctly.
    }
    setPendingScrollLine(null);
  }, [pendingScrollLine, activeTabData]);

  // Fetches a file's content into the shared `tabs` pool if it isn't already
  // open - both openFile (left pane) and openInSplit (right pane) build on
  // this, so a file already open in one pane opens instantly in the other.
  const ensureTabLoaded = async (filename) => {
    if (tabs.some((t) => t.name === filename)) return true;
    try {
      if (isImageFile(filename)) {
        const blob = await workspaceAPI.getFileBlob(sessionId, filename);
        const imageUrl = URL.createObjectURL(blob);
        setTabs((prev) => [...prev, { name: filename, content: '', imageUrl, isImage: true, dirty: false, size: blob.size }]);
        return true;
      }
      const content = await workspaceAPI.getFileContent(sessionId, filename);
      setTabs((prev) => [...prev, { name: filename, content, isImage: false, dirty: false }]);
      return true;
    } catch (err) {
      setError(err.message || 'Datei konnte nicht geöffnet werden.');
      return false;
    }
  };

  const openFile = async (filename) => {
    if (await ensureTabLoaded(filename)) setActiveTab(filename);
  };

  // Runs once sessionId first resolves (either the saved/most-recent one, or
  // whichever session the artifact-producing chat turn itself was in - both
  // already the same value by the time this fires, since Chat.jsx keeps
  // liara_active_session in sync before ever rendering the link that got us
  // here). ensureTabLoaded fetches by filename directly from the API, so
  // this doesn't need to wait for the Explorer's own file list to load.
  useEffect(() => {
    if (sessionId && pendingOpenFileRef.current) {
      const filename = pendingOpenFileRef.current;
      pendingOpenFileRef.current = null;
      openFile(filename);
    }
  }, [sessionId]);

  // Opens (or switches to) a file in the second, split pane - via the tab
  // strip there, or the primary pane's "🗗 Teilen" button duplicating its
  // current file. Explorer/search clicks always target the primary pane;
  // this is the only way a file lands in the split one.
  const openInSplit = async (filename) => {
    if (await ensureTabLoaded(filename)) setSplitTab(filename);
  };

  const closeSplit = () => setSplitTab(null);

  // Opens a search result - a bare path-match just opens the file, a
  // content-match also jumps to (and selects) the matching line once the
  // editor has the right content loaded (see the pendingScrollLine effect
  // below, which fires once activeTabData actually reflects this file).
  const openSearchResult = async (path, line = null) => {
    await openFile(path);
    if (line != null) setPendingScrollLine({ path, line });
  };

  const closeTab = (filename) => {
    const tabToClose = tabs.find((t) => t.name === filename);
    if (tabToClose?.imageUrl) {
      URL.revokeObjectURL(tabToClose.imageUrl);
    }
    setTabs((prev) => prev.filter((t) => t.name !== filename));
    const remaining = tabs.filter((t) => t.name !== filename);
    if (activeTab === filename) {
      setActiveTab(remaining.length ? remaining[remaining.length - 1].name : null);
    }
    if (splitTab === filename) {
      setSplitTab(remaining.length ? remaining[remaining.length - 1].name : null);
    }
  };

  // Deleting a folder removes every file nested under it - any open tabs
  // pointing at one of those now-gone paths would otherwise silently point
  // at nothing, so close the exact path plus anything with a `path/` prefix
  // in one state update (rather than looping closeTab(), which would only
  // ever account for one removal at a time against a stale tabs snapshot).
  const closeTabsUnder = (path) => {
    const prefix = `${path}/`;
    const isUnderPath = (name) => name === path || name.startsWith(prefix);
    setTabs((prev) => prev.filter((t) => !isUnderPath(t.name)));
    const remaining = tabs.filter((t) => !isUnderPath(t.name));
    if (activeTab && isUnderPath(activeTab)) {
      setActiveTab(remaining.length ? remaining[remaining.length - 1].name : null);
    }
    if (splitTab && isUnderPath(splitTab)) {
      setSplitTab(remaining.length ? remaining[remaining.length - 1].name : null);
    }
  };

  const updateTabContent = (filename, value) => {
    setTabs((prev) => prev.map((t) => (t.name === filename ? { ...t, content: value, dirty: true } : t)));
  };

  const saveTab = async (filename) => {
    const tabData = tabs.find((t) => t.name === filename);
    if (!tabData) return;
    try {
      await workspaceAPI.saveFile(sessionId, filename, tabData.content);
      setTabs((prev) => prev.map((t) => (t.name === filename ? { ...t, dirty: false } : t)));
      loadFiles(sessionId);
    } catch (err) {
      setError(err.message || 'Speichern fehlgeschlagen.');
    }
  };

  // Same codeExecAPI.run() call as before - the only change is appending the
  // result to that pane's terminal scrollback instead of replacing a single
  // "last result" slot. Capped at the most recent 20 entries per pane so a
  // long session doesn't grow this state unboundedly.
  const runTab = async (filename, lang, setRunningState, setHistoryState) => {
    const tabData = tabs.find((t) => t.name === filename);
    if (!tabData || !lang) return;
    setRunningState(true);
    try {
      const targetLang = lang.runLanguage === 'python' ? pythonVersion : lang.runLanguage;
      const result = await codeExecAPI.run(sessionId, targetLang, tabData.content);
      setHistoryState((prev) => [
        ...prev,
        { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, filename, timestamp: new Date(), result },
      ].slice(-20));
      loadFiles(sessionId);
      // A run is the one thing that can turn envStatus from "not yet
      // created" into a real venv (run_sandboxed.sh creates it lazily on
      // first use) - only worth re-checking while we don't already know it
      // exists, so a chatty session running code repeatedly doesn't turn
      // this into a poll.
      if (!envStatus?.exists) loadEnvironment(sessionId);
    } catch (err) {
      setHistoryState((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          filename,
          timestamp: new Date(),
          result: { error: err.message || 'Ausführung fehlgeschlagen.' },
        },
      ].slice(-20));
    } finally {
      setRunningState(false);
    }
  };

  const toggleContextSelection = async (filename) => {
    const selectedNow = files.filter((f) => f.type === 'file' && f.selected_for_context).map((f) => f.path);
    const next = selectedNow.includes(filename)
      ? selectedNow.filter((n) => n !== filename)
      : [...selectedNow, filename];
    try {
      await workspaceAPI.setContextSelection(sessionId, next);
      loadFiles(sessionId);
    } catch (err) {
      setError(err.message || 'Kontext-Auswahl konnte nicht gespeichert werden.');
    }
  };

  // Opens the "new file" modal, optionally prefilled with a folder prefix
  // (Explorer's per-folder "Neue Datei hier" action) - typing after the
  // prefix just extends the same `/`-joined path createFile already expects.
  const openNewFileModal = (folderPath = '') => {
    setModalError(null);
    setNewFileName(folderPath ? `${folderPath}/` : '');
    setNewFileOpen(true);
  };

  const openNewFolderModal = (folderPath = '') => {
    setModalError(null);
    setNewFolderPath(folderPath ? `${folderPath}/` : '');
    setNewFolderOpen(true);
  };

  const openRenameModal = (path, type, currentName) => {
    setModalError(null);
    setRenameTarget(path);
    setRenameTargetType(type);
    setRenameValue(currentName);
  };

  const openDeleteModal = (path, type) => {
    setDeleteTarget(path);
    setDeleteTargetType(type);
  };

  const handleCreateFile = async () => {
    setModalError(null);
    if (!newFileName.trim()) return;
    try {
      await workspaceAPI.createFile(sessionId, newFileName.trim(), '');
      setNewFileOpen(false);
      setNewFileName('');
      await loadFiles(sessionId);
      openFile(newFileName.trim());
    } catch (err) {
      setModalError(err.message || 'Datei konnte nicht erstellt werden.');
    }
  };

  const handleCreateFolder = async () => {
    setModalError(null);
    if (!newFolderPath.trim()) return;
    try {
      await workspaceAPI.createFolder(sessionId, newFolderPath.trim());
      setNewFolderOpen(false);
      setNewFolderPath('');
      loadFiles(sessionId);
    } catch (err) {
      setModalError(err.message || 'Ordner konnte nicht erstellt werden.');
    }
  };

  const handleRename = async () => {
    setModalError(null);
    if (!renameValue.trim() || !renameTarget) return;
    const newName = renameValue.trim();
    const newFullPath = parentOf(renameTarget) ? `${parentOf(renameTarget)}/${newName}` : newName;
    try {
      await workspaceAPI.renameFile(sessionId, renameTarget, newName);
      // Renaming a folder moves its whole subtree on disk - any open tab
      // under the old prefix needs its own name rewritten to match, not
      // just an exact match on renameTarget itself.
      const oldPrefix = `${renameTarget}/`;
      setTabs((prev) => prev.map((t) => {
        if (t.name === renameTarget) return { ...t, name: newFullPath };
        if (renameTargetType === 'folder' && t.name.startsWith(oldPrefix)) {
          return { ...t, name: newFullPath + t.name.slice(renameTarget.length) };
        }
        return t;
      }));
      if (activeTab === renameTarget) {
        setActiveTab(newFullPath);
      } else if (renameTargetType === 'folder' && activeTab && activeTab.startsWith(oldPrefix)) {
        setActiveTab(newFullPath + activeTab.slice(renameTarget.length));
      }
      if (splitTab === renameTarget) {
        setSplitTab(newFullPath);
      } else if (renameTargetType === 'folder' && splitTab && splitTab.startsWith(oldPrefix)) {
        setSplitTab(newFullPath + splitTab.slice(renameTarget.length));
      }
      setRenameTarget(null);
      setRenameValue('');
      loadFiles(sessionId);
    } catch (err) {
      setModalError(err.message || 'Umbenennen fehlgeschlagen.');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await workspaceAPI.deleteFile(sessionId, deleteTarget);
      if (deleteTargetType === 'folder') {
        closeTabsUnder(deleteTarget);
      } else {
        closeTab(deleteTarget);
      }
      setDeleteTarget(null);
      loadFiles(sessionId);
    } catch (err) {
      setError(err.message || 'Löschen fehlgeschlagen.');
    }
  };

  // Shared by the file-picker input and drag & drop - both just hand over a
  // FileList/File[] and a target folder ("" for workspace root). The error
  // (if any) is applied AFTER loadFiles(), not before/in a finally - loadFiles
  // itself does setError(null) at its start, which would otherwise clobber
  // the very message this function just set, in the same tick.
  const handleUpload = async (fileList, folder = '') => {
    if (!fileList || fileList.length === 0) return;
    let uploadError = null;
    try {
      const { results } = await workspaceAPI.uploadFiles(sessionId, fileList, folder);
      const failed = results.filter((r) => !r.ok);
      if (failed.length > 0) {
        uploadError = `${failed.length} von ${results.length} Datei(en) konnten nicht hochgeladen werden: ${failed.map((f) => `${f.filename} (${f.error})`).join(', ')}`;
      }
    } catch (err) {
      uploadError = err.message || 'Upload fehlgeschlagen.';
    }
    await loadFiles(sessionId);
    if (uploadError) setError(uploadError);
  };

  const triggerUpload = (folder = '') => {
    uploadTargetRef.current = folder;
    uploadInputRef.current?.click();
  };

  const handleUploadInputChange = (e) => {
    handleUpload(e.target.files, uploadTargetRef.current);
    e.target.value = ''; // allow picking the exact same file(s) again later
  };

  const toggleFolderCollapse = (path) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  // Nutzer-direkt path (issue #5) - immediate, no approval needed, since
  // it's the user's own action on their own session. LIARA's side always
  // goes through a proposal instead (see the proposals panel above).
  const togglePackagesPopover = () => {
    setPackageError(null);
    setPackagesOpen((open) => {
      const next = !open;
      if (next) loadPackages(sessionId);
      return next;
    });
  };

  const handleInstallPackage = async () => {
    const spec = packageInput.trim();
    if (!spec || packageBusy) return;
    setPackageBusy(true);
    setPackageError(null);
    try {
      await workspaceAPI.installPackage(sessionId, spec);
      setPackageInput('');
      await loadPackages(sessionId);
      loadEnvironment(sessionId);
    } catch (err) {
      setPackageError(err.message || 'Installation fehlgeschlagen.');
    } finally {
      setPackageBusy(false);
    }
  };

  const handleRemovePackage = async (name) => {
    if (packageBusy) return;
    setPackageBusy(true);
    setPackageError(null);
    try {
      await workspaceAPI.removePackage(sessionId, name);
      await loadPackages(sessionId);
      loadEnvironment(sessionId);
    } catch (err) {
      setPackageError(err.message || 'Entfernen fehlgeschlagen.');
    } finally {
      setPackageBusy(false);
    }
  };

  const tree = useMemo(() => buildTree(files), [files]);
  const treeHandlers = {
    onToggleCollapse: toggleFolderCollapse,
    onOpenFile: openFile,
    onToggleContext: toggleContextSelection,
    onDownload: (path) => codeExecAPI.downloadFile(sessionId, path),
    onRename: (path, name) => openRenameModal(path, files.find((f) => f.path === path)?.type || 'file', name),
    onDelete: (path, type) => openDeleteModal(path, type),
    onNewFileHere: openNewFileModal,
    onNewFolderHere: openNewFolderModal,
    onUploadHere: triggerUpload,
    onFolderDragEnter: (path) => setDragOverTarget(path),
    onFolderDragLeave: () => setDragOverTarget(null),
    onFolderDrop: (path, fileList) => { setDragOverTarget(null); handleUpload(fileList, path); },
  };

  return (
    <div className="workspace-page">
      <div className="workspace-header">
        <div className="workspace-header-left">
          <button
            className="workspace-icon-btn"
            title={sidebarCollapsed ? 'Explorer einblenden' : 'Explorer ausblenden'}
            onClick={() => setSidebarCollapsed((v) => !v)}
          >
            {sidebarCollapsed ? '▶' : '◀'}
          </button>
          <h1>🗂️ Workspace</h1>
        </div>
        <div className="workspace-header-right">
          <button
            className={`workspace-icon-btn ${agentPanelOpen ? 'active' : ''}`}
            title={agentPanelOpen ? 'Agent-Chat ausblenden' : 'Agent-Chat einblenden'}
            onClick={toggleAgentPanel}
          >
            🤖
          </button>
          <button
            className={`workspace-icon-btn ${shellOpen ? 'active' : ''}`}
            title={shellOpen ? 'Terminal ausblenden' : 'Terminal einblenden'}
            onClick={toggleShell}
          >
            💻
          </button>
          <div className="workspace-env-status">
            <button
              className="workspace-env-chip"
              onClick={togglePackagesPopover}
              title="Laufzeitumgebung / Pakete"
            >
              {envStatus?.exists
                ? `🐍 ${envStatus.python_version} · ${envStatus.package_count} Paket${envStatus.package_count === 1 ? '' : 'e'}`
                : '🐍 venv wird beim ersten Ausführen angelegt'}
            </button>
            {packagesOpen && (
              <div className="workspace-packages-popover">
                <div className="workspace-packages-header">
                  <span>📦 Pakete dieser Session</span>
                  <button className="workspace-icon-btn" onClick={() => setPackagesOpen(false)}>✕</button>
                </div>
                {packagesLoading ? (
                  <p className="workspace-hint">Lade…</p>
                ) : sessionPackages.length === 0 ? (
                  <p className="workspace-hint">Noch keine eigenen Pakete installiert.</p>
                ) : (
                  <ul className="workspace-packages-list">
                    {sessionPackages.map((pkg) => {
                      const name = pkg.split('==')[0];
                      return (
                        <li key={pkg}>
                          <span>{pkg}</span>
                          <button
                            className="workspace-icon-btn danger"
                            title="Entfernen"
                            disabled={packageBusy}
                            onClick={() => handleRemovePackage(name)}
                          >🗑️</button>
                        </li>
                      );
                    })}
                  </ul>
                )}
                <div className="workspace-packages-add">
                  <input
                    type="text"
                    placeholder="z. B. requests==2.31.0"
                    value={packageInput}
                    onChange={(e) => setPackageInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleInstallPackage(); }}
                  />
                  <button className="workspace-btn-secondary" disabled={packageBusy || !packageInput.trim()} onClick={handleInstallPackage}>
                    {packageBusy ? '…' : 'Installieren'}
                  </button>
                </div>
                {packageError && <p className="workspace-modal-error">{packageError}</p>}
              </div>
            )}
          </div>
          <div className="workspace-font-size-group" role="group" aria-label="Schriftgröße">
            {FONT_SIZE_PRESETS.map((preset) => (
              <button
                key={preset.size}
                className={`workspace-font-size-btn ${fontSize === preset.size ? 'active' : ''}`}
                style={{ fontSize: `${preset.size}px` }}
                title={preset.label}
                onClick={() => changeFontSize(preset.size)}
              >
                A
              </button>
            ))}
          </div>
          <select
            className="workspace-session-select"
            value={sessionId || ''}
            onChange={(e) => setSessionId(parseInt(e.target.value, 10))}
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>{s.title}</option>
            ))}
          </select>
          <button
            className={`workspace-agent-hub-btn ${agentDrawerOpen ? 'active' : ''}`}
            title="Autonomous Agents & ACI Engine öffnen"
            onClick={toggleAgentDrawer}
          >
            🤖 Agent Hub
          </button>
        </div>
      </div>

      {error && <div className="workspace-error">{error} <button onClick={() => setError(null)}>✕</button></div>}

      {agentEnabled && proposals.length > 0 && (
        <div className="workspace-proposals">
          <div className="workspace-proposals-header">
            <div className="workspace-proposals-title-row">
              <span>📝 Vorschläge von LIARA</span>
              <span className="workspace-proposals-count">{proposals.length}</span>
            </div>
            <div className="workspace-proposals-bulk-row">
              <label className="workspace-checkbox-label">
                <input
                  type="checkbox"
                  checked={proposals.length > 0 && selectedProposalIds.size === proposals.length}
                  onChange={toggleSelectAllProposals}
                />
                <span>Alle auswählen</span>
              </label>
              {selectedProposalIds.size > 0 && (
                <div className="workspace-bulk-actions">
                  <span className="workspace-bulk-count">{selectedProposalIds.size} ausgewählt</span>
                  <button className="workspace-btn-secondary" disabled={bulkBusy} onClick={() => handleBulkResolve(false)}>Ablehnen</button>
                  <button className="primary" disabled={bulkBusy} onClick={() => handleBulkResolve(true)}>Annehmen</button>
                </div>
              )}
            </div>
          </div>
          <ul className="workspace-proposal-list">
            {proposals.map((p) => (
              <li key={p.id} className="workspace-proposal">
                <div className="workspace-proposal-header">
                  <input
                    type="checkbox"
                    className="workspace-proposal-checkbox"
                    checked={selectedProposalIds.has(p.id)}
                    onChange={() => toggleProposalSelection(p.id)}
                  />
                  <span className={`workspace-proposal-action ${p.kind === 'package' ? 'workspace-proposal-action-package' : ''}`}>
                    {PROPOSAL_ACTION_LABELS[p.action] || p.action}
                  </span>
                  <span className="workspace-file-name">{p.filename}</span>
                </div>
                {p.description && <p className="workspace-proposal-description">{p.description}</p>}
                {p.kind !== 'package' && <DiffView diff={p.diff} />}
                <div className="workspace-modal-actions">
                  <button className="workspace-btn-secondary" onClick={() => handleRejectProposal(p.id)}>Ablehnen</button>
                  <button className="primary" onClick={() => handleApproveProposal(p.id)}>Annehmen</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className={`workspace-body ${sidebarCollapsed ? 'sidebar-collapsed' : ''} ${agentPanelOpen ? 'agent-open' : ''} ${agentDrawerOpen ? 'agent-drawer-open' : ''}`}>
        {!sidebarCollapsed && (
        <aside
          className={`workspace-sidebar ${dragOverTarget === 'root' ? 'workspace-drag-over' : ''}`}
          onDragOver={(e) => e.preventDefault()}
          onDragEnter={(e) => { e.preventDefault(); setDragOverTarget('root'); }}
          onDragLeave={() => setDragOverTarget(null)}
          onDrop={(e) => { e.preventDefault(); setDragOverTarget(null); handleUpload(e.dataTransfer.files, ''); }}
        >
          <div className="workspace-sidebar-header">
            <span>Explorer</span>
            <div className="workspace-sidebar-header-actions">
              <button className="workspace-icon-btn" onClick={() => openNewFileModal()} title="Neue Datei">➕</button>
              <button className="workspace-icon-btn" onClick={() => openNewFolderModal()} title="Neuer Ordner">📁</button>
              <button className="workspace-icon-btn" onClick={() => triggerUpload('')} title="Hochladen">⬆️</button>
            </div>
          </div>
          <input
            type="file"
            multiple
            ref={uploadInputRef}
            style={{ display: 'none' }}
            onChange={handleUploadInputChange}
          />

          <div className="workspace-search">
            <input
              type="text"
              className="workspace-search-input"
              placeholder="🔍 Im Projekt suchen…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="workspace-icon-btn" title="Suche zurücksetzen" onClick={() => setSearchQuery('')}>✕</button>
            )}
            <button
              className={`workspace-icon-btn ${searchCaseSensitive ? 'active' : ''}`}
              title="Groß-/Kleinschreibung beachten"
              onClick={() => setSearchCaseSensitive((v) => !v)}
            >Aa</button>
          </div>

          {searchResults !== null ? (
            <>
              {searching && <p className="workspace-hint">Suche…</p>}
              {!searching && searchResults.results.length === 0 && (
                <div className="workspace-empty">
                  <div className="workspace-empty-icon">🔍</div>
                  <p className="workspace-empty-title">Keine Treffer</p>
                  <p className="workspace-empty-subtitle">Keine Datei enthält „{searchQuery.trim()}“.</p>
                </div>
              )}
              {!searching && searchResults.results.length > 0 && (
                <ul className="workspace-search-results">
                  {searchResults.results.map((r) => (
                    <li key={r.path} className="workspace-search-file">
                      <button className="workspace-search-file-path" onClick={() => openSearchResult(r.path)}>
                        📄 {r.path}
                      </button>
                      {r.content_matches.length > 0 && (
                        <ul className="workspace-search-matches">
                          {r.content_matches.map((m) => (
                            <li key={m.line}>
                              <button className="workspace-search-match" onClick={() => openSearchResult(r.path, m.line)}>
                                <span className="workspace-search-line-number">{m.line}</span>
                                <span className="workspace-search-line-text">{highlightMatch(m.text, searchQuery.trim(), searchCaseSensitive)}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                  {searchResults.truncated && (
                    <li className="workspace-hint">Weitere Treffer nicht angezeigt (Limit erreicht).</li>
                  )}
                </ul>
              )}
            </>
          ) : (
            <>
              {loadingFiles && <p className="workspace-hint">Lade…</p>}
              {!loadingFiles && files.length === 0 && (
                <div className="workspace-empty">
                  <div className="workspace-empty-icon">🗂️</div>
                  <p className="workspace-empty-title">Noch keine Dateien</p>
                  <p className="workspace-empty-subtitle">Lege eine neue Datei/Ordner an, lade eine hoch (auch per Drag &amp; Drop) oder lass LIARA eine vorschlagen.</p>
                </div>
              )}
              <ul className="workspace-file-list">
                {tree.map((node) => (
                  <WorkspaceTreeNode
                    key={node.path}
                    node={node}
                    depth={0}
                    activeTab={activeTab}
                    collapsedFolders={collapsedFolders}
                    dragOverTarget={dragOverTarget}
                    handlers={treeHandlers}
                  />
                ))}
              </ul>
            </>
          )}
        </aside>
        )}

        <div className="workspace-editor-column">
        <div className="workspace-editor-row">
          <EditorPane
            tabs={tabs}
            activeTabName={activeTab}
            tabData={activeTabData}
            activeLang={activeLang}
            onSelectTab={setActiveTab}
            onCloseTab={closeTab}
            onChangeContent={(value) => updateTabContent(activeTab, value)}
            onCreateEditor={(view) => {
              editorViewRef.current = view;
              view.dom.addEventListener('focusin', () => setActivePane('primary'));
            }}
            running={running}
            runHistory={runHistory}
            onClearHistory={() => setRunHistory([])}
            onSave={() => saveTab(activeTab)}
            onRun={() => runTab(activeTab, activeLang, setRunning, setRunHistory)}
            sessionId={sessionId}
            isSecondary={false}
            onSplit={() => activeTab && openInSplit(activeTab)}
            cmTheme={cmTheme}
            fontSizeExtension={fontSizeExtension}
            isActivePane={!!splitTab && activePane === 'primary'}
            pythonVersion={pythonVersion}
            onPythonVersionChange={handlePythonVersionChange}
          />
          {splitTab && (
            <EditorPane
              tabs={tabs}
              activeTabName={splitTab}
              tabData={splitTabData}
              activeLang={splitLang}
              onSelectTab={setSplitTab}
              onCloseTab={closeTab}
              onChangeContent={(value) => updateTabContent(splitTab, value)}
              onCreateEditor={(view) => {
                splitEditorViewRef.current = view;
                view.dom.addEventListener('focusin', () => setActivePane('split'));
              }}
              running={splitRunning}
              runHistory={splitRunHistory}
              onClearHistory={() => setSplitRunHistory([])}
              onSave={() => saveTab(splitTab)}
              onRun={() => runTab(splitTab, splitLang, setSplitRunning, setSplitRunHistory)}
              sessionId={sessionId}
              isSecondary={true}
              onCloseSplitPane={closeSplit}
              cmTheme={cmTheme}
              fontSizeExtension={fontSizeExtension}
              isActivePane={activePane === 'split'}
              pythonVersion={pythonVersion}
              onPythonVersionChange={handlePythonVersionChange}
            />
          )}
        </div>

        {shellOpen && sessionId && (
          <WorkspaceTerminal sessionId={sessionId} onClose={() => setShellOpen(false)} />
        )}
        </div>

        {agentPanelOpen && (
          <AgentChatPanel
            sessionId={sessionId}
            onClose={() => setAgentPanelOpen(false)}
            onWorkspaceProposal={() => loadProposals(sessionId)}
          />
        )}

        {agentDrawerOpen && (
          <AgentDrawer
            sessionId={sessionId}
            onClose={() => setAgentDrawerOpen(false)}
            onFilesChanged={() => {
              loadFiles(sessionId);
              loadProposals(sessionId);
            }}
            onOpenFile={openFile}
          />
        )}
      </div>

      {/* IDE Status Bar */}
      <footer className="workspace-status-bar">
        <div className="status-bar-left">
          <span className="status-item session-tag">🌿 Session #{sessionId || '–'}</span>
          <span className="status-item file-tag">
            {activeTab ? `📄 ${activeTab} (${activeLang?.runLanguage?.toUpperCase() || 'PLAIN'})` : 'Keine Datei geöffnet'}
          </span>
          {proposals.length > 0 && (
            <span className="status-item proposals-tag">
              📝 {proposals.length} Vorschlag{proposals.length > 1 ? 'e' : ''}
            </span>
          )}
        </div>
        <div className="status-bar-right">
          <span className="status-item">UTF-8</span>
          <span className="status-item">Tab-Größe: 4</span>
          <span className="status-item env-tag">
            🐍 {envStatus?.venv_present ? `Python venv (${envStatus.package_count || 0} Pakete)` : 'System Python'}
          </span>
          <button
            className={`status-item terminal-tag ${shellOpen ? 'active' : ''}`}
            onClick={toggleShell}
            title="Sandboxed Terminal & Prozesse ein-/ausblenden"
          >
            💻 Terminal {shellOpen ? '▾' : '▴'}
          </button>
          <button
            className={`status-item agent-tag ${agentDrawerOpen ? 'active' : ''}`}
            onClick={() => setAgentDrawerOpen((v) => !v)}
            title="Agent Hub öffnen/schließen"
          >
            🤖 Multi-Agent: {agentDrawerOpen ? 'Aktiv' : 'Bereit'}
          </button>
        </div>
      </footer>

      {newFileOpen && (
        <div className="workspace-modal-overlay" onClick={() => setNewFileOpen(false)}>
          <div className="workspace-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Neue Datei</h3>
            <input
              type="text"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder="z. B. analyse.py oder utils/helper.py"
              autoFocus
            />
            {modalError && <p className="workspace-modal-error">{modalError}</p>}
            <div className="workspace-modal-actions">
              <button className="workspace-btn-secondary" onClick={() => { setNewFileOpen(false); setModalError(null); }}>Abbrechen</button>
              <button className="primary" onClick={handleCreateFile}>Anlegen</button>
            </div>
          </div>
        </div>
      )}

      {newFolderOpen && (
        <div className="workspace-modal-overlay" onClick={() => setNewFolderOpen(false)}>
          <div className="workspace-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Neuer Ordner</h3>
            <input
              type="text"
              value={newFolderPath}
              onChange={(e) => setNewFolderPath(e.target.value)}
              placeholder="z. B. utils oder utils/tests"
              autoFocus
            />
            {modalError && <p className="workspace-modal-error">{modalError}</p>}
            <div className="workspace-modal-actions">
              <button className="workspace-btn-secondary" onClick={() => { setNewFolderOpen(false); setModalError(null); }}>Abbrechen</button>
              <button className="primary" onClick={handleCreateFolder}>Anlegen</button>
            </div>
          </div>
        </div>
      )}

      {renameTarget && (
        <div className="workspace-modal-overlay" onClick={() => setRenameTarget(null)}>
          <div className="workspace-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{renameTargetType === 'folder' ? 'Ordner umbenennen' : 'Datei umbenennen'}</h3>
            <input type="text" value={renameValue} onChange={(e) => setRenameValue(e.target.value)} autoFocus />
            {modalError && <p className="workspace-modal-error">{modalError}</p>}
            <div className="workspace-modal-actions">
              <button className="workspace-btn-secondary" onClick={() => { setRenameTarget(null); setModalError(null); }}>Abbrechen</button>
              <button className="primary" onClick={handleRename}>Umbenennen</button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="workspace-modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="workspace-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{deleteTargetType === 'folder' ? 'Ordner löschen?' : 'Datei löschen?'}</h3>
            <p>
              „{deleteTarget}" wird unwiderruflich gelöscht
              {deleteTargetType === 'folder' ? ' - und alle enthaltenen Dateien' : ''}.
            </p>
            <div className="workspace-modal-actions">
              <button className="workspace-btn-secondary" onClick={() => setDeleteTarget(null)}>Abbrechen</button>
              <button className="danger" onClick={handleDelete}>Löschen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkspacePage;
