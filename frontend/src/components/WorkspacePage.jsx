import { useEffect, useMemo, useRef, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { StreamLanguage } from '@codemirror/language';
import { julia as juliaLegacyMode } from '@codemirror/legacy-modes/mode/julia';
import { chatAPI, workspaceAPI, codeExecAPI, preferencesAPI } from '../services/api';
import CodeRunResult from './CodeRunResult';
import DiffView from './DiffView';
import './WorkspacePage.css';

const PROPOSAL_ACTION_LABELS = {
  create: 'Neu anlegen',
  update: 'Überschreiben',
  delete: 'Löschen',
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

function WorkspacePage() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState(null);

  const [tabs, setTabs] = useState([]); // [{name, content, dirty}]
  const [activeTab, setActiveTab] = useState(null);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);

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

  const [agentEnabled, setAgentEnabled] = useState(false);
  const [proposals, setProposals] = useState([]);
  const [selectedProposalIds, setSelectedProposalIds] = useState(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

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

  useEffect(() => {
    (async () => {
      try {
        const list = await chatAPI.getSessions();
        setSessions(list);
        const savedId = parseInt(localStorage.getItem('liara_active_session'), 10);
        const initial = list.find((s) => s.id === savedId) || list[0];
        if (initial) setSessionId(initial.id);
      } catch (err) {
        setError(err.message || 'Sessions konnten nicht geladen werden.');
      }
    })();
    preferencesAPI.get()
      .then((prefs) => setAgentEnabled(!!prefs?.workspace_agent_enabled))
      .catch(() => {});
  }, []);

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

  useEffect(() => {
    if (sessionId) {
      loadFiles(sessionId);
      if (agentEnabled) loadProposals(sessionId);
    }
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
      setBulkBusy(false);
    }
  };

  const activeTabData = useMemo(() => tabs.find((t) => t.name === activeTab), [tabs, activeTab]);
  const activeExt = activeTab ? extensionOf(activeTab) : '';
  const activeLang = LANGUAGE_BY_EXTENSION[activeExt];

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

  const openFile = async (filename) => {
    const existing = tabs.find((t) => t.name === filename);
    if (existing) {
      setActiveTab(filename);
      return;
    }
    try {
      const content = await workspaceAPI.getFileContent(sessionId, filename);
      setTabs((prev) => [...prev, { name: filename, content, dirty: false }]);
      setActiveTab(filename);
    } catch (err) {
      setError(err.message || 'Datei konnte nicht geöffnet werden.');
    }
  };

  // Opens a search result - a bare path-match just opens the file, a
  // content-match also jumps to (and selects) the matching line once the
  // editor has the right content loaded (see the pendingScrollLine effect
  // below, which fires once activeTabData actually reflects this file).
  const openSearchResult = async (path, line = null) => {
    await openFile(path);
    if (line != null) setPendingScrollLine({ path, line });
  };

  const closeTab = (filename) => {
    setTabs((prev) => prev.filter((t) => t.name !== filename));
    if (activeTab === filename) {
      const remaining = tabs.filter((t) => t.name !== filename);
      setActiveTab(remaining.length ? remaining[remaining.length - 1].name : null);
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
    if (activeTab && isUnderPath(activeTab)) {
      const remaining = tabs.filter((t) => !isUnderPath(t.name));
      setActiveTab(remaining.length ? remaining[remaining.length - 1].name : null);
    }
  };

  const updateActiveContent = (value) => {
    setTabs((prev) => prev.map((t) => (t.name === activeTab ? { ...t, content: value, dirty: true } : t)));
  };

  const saveActiveTab = async () => {
    if (!activeTabData) return;
    try {
      await workspaceAPI.saveFile(sessionId, activeTabData.name, activeTabData.content);
      setTabs((prev) => prev.map((t) => (t.name === activeTab ? { ...t, dirty: false } : t)));
      loadFiles(sessionId);
    } catch (err) {
      setError(err.message || 'Speichern fehlgeschlagen.');
    }
  };

  const runActiveTab = async () => {
    if (!activeTabData || !activeLang) return;
    setRunning(true);
    setRunResult(null);
    try {
      const result = await codeExecAPI.run(sessionId, activeLang.runLanguage, activeTabData.content);
      setRunResult(result);
      loadFiles(sessionId);
    } catch (err) {
      setRunResult({ error: err.message || 'Ausführung fehlgeschlagen.' });
    } finally {
      setRunning(false);
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
          <h1>🗂️ Workspace</h1>
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
                  <span className="workspace-proposal-action">{PROPOSAL_ACTION_LABELS[p.action] || p.action}</span>
                  <span className="workspace-file-name">{p.filename}</span>
                </div>
                {p.description && <p className="workspace-proposal-description">{p.description}</p>}
                <DiffView diff={p.diff} />
                <div className="workspace-modal-actions">
                  <button className="workspace-btn-secondary" onClick={() => handleRejectProposal(p.id)}>Ablehnen</button>
                  <button className="primary" onClick={() => handleApproveProposal(p.id)}>Annehmen</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="workspace-body">
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

        <section className="workspace-main">
          <div className="workspace-tabs">
            {tabs.map((t) => (
              <button
                key={t.name}
                className={`workspace-tab ${activeTab === t.name ? 'active' : ''}`}
                onClick={() => setActiveTab(t.name)}
              >
                {t.name}{t.dirty ? ' •' : ''}
                <span className="workspace-tab-close" onClick={(e) => { e.stopPropagation(); closeTab(t.name); }}>✕</span>
              </button>
            ))}
          </div>

          {activeTabData ? (
            <>
              <div className="workspace-toolbar">
                <button className="workspace-btn-secondary" onClick={saveActiveTab} disabled={!activeTabData.dirty}>💾 Speichern</button>
                <button className="workspace-btn-primary" onClick={runActiveTab} disabled={!activeLang || running}>
                  {running ? 'Läuft…' : '▶ Ausführen'}
                </button>
              </div>
              <div className="workspace-editor-wrapper">
                <CodeMirror
                  value={activeTabData.content}
                  height="420px"
                  theme="dark"
                  extensions={activeLang ? [activeLang.cm] : []}
                  onChange={updateActiveContent}
                  onCreateEditor={(view) => { editorViewRef.current = view; }}
                />
              </div>
              {runResult && (
                <div className="workspace-output">
                  <CodeRunResult result={runResult} sessionId={sessionId} />
                </div>
              )}
            </>
          ) : (
            <div className="workspace-empty">
              <div className="workspace-empty-icon">📄</div>
              <p className="workspace-empty-title">Keine Datei geöffnet</p>
              <p className="workspace-empty-subtitle">Datei aus der Liste öffnen oder eine neue anlegen.</p>
            </div>
          )}
        </section>
      </div>

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
