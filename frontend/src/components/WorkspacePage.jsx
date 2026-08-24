import { useEffect, useMemo, useState } from 'react';
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

function formatBytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

const SOURCE_LABELS = {
  user: 'Selbst erstellt',
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
  code_runner: 'workspace-badge-code-runner',
  liara: 'workspace-badge-liara',
  agent: 'workspace-badge-liara',
  web_research: 'workspace-badge-liara',
  generated: 'workspace-badge-code-runner',
  unknown: 'workspace-badge-unknown',
};

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
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [modalError, setModalError] = useState(null);

  const [agentEnabled, setAgentEnabled] = useState(false);
  const [proposals, setProposals] = useState([]);
  const [selectedProposalIds, setSelectedProposalIds] = useState(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

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

  const closeTab = (filename) => {
    setTabs((prev) => prev.filter((t) => t.name !== filename));
    if (activeTab === filename) {
      const remaining = tabs.filter((t) => t.name !== filename);
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
    const selectedNow = files.filter((f) => f.selected_for_context).map((f) => f.name);
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

  const handleRename = async () => {
    setModalError(null);
    if (!renameValue.trim() || !renameTarget) return;
    try {
      await workspaceAPI.renameFile(sessionId, renameTarget, renameValue.trim());
      if (activeTab === renameTarget) setActiveTab(renameValue.trim());
      setTabs((prev) => prev.map((t) => (t.name === renameTarget ? { ...t, name: renameValue.trim() } : t)));
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
      closeTab(deleteTarget);
      setDeleteTarget(null);
      loadFiles(sessionId);
    } catch (err) {
      setError(err.message || 'Löschen fehlgeschlagen.');
    }
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
        <aside className="workspace-sidebar">
          <div className="workspace-sidebar-header">
            <span>Dateien</span>
            <button className="workspace-icon-btn" onClick={() => setNewFileOpen(true)} title="Neue Datei">➕</button>
          </div>
          {loadingFiles && <p className="workspace-hint">Lade…</p>}
          {!loadingFiles && files.length === 0 && (
            <div className="workspace-empty">
              <div className="workspace-empty-icon">🗂️</div>
              <p className="workspace-empty-title">Noch keine Dateien</p>
              <p className="workspace-empty-subtitle">Lege eine neue Datei an oder lass LIARA eine vorschlagen.</p>
            </div>
          )}
          <ul className="workspace-file-list">
            {files.map((f) => (
              <li key={f.name} className={activeTab === f.name ? 'active' : ''}>
                <button className="workspace-file-open" onClick={() => openFile(f.name)}>
                  <span className="workspace-file-name">{f.name}</span>
                  <span className="workspace-file-badges">
                    <span className="workspace-file-size">{formatBytes(f.size)}</span>
                    <span className={`workspace-source-badge ${SOURCE_BADGE_CLASS[f.source] || 'workspace-badge-unknown'}`}>
                      {SOURCE_LABELS[f.source] || f.source}
                    </span>
                  </span>
                </button>
                <div className="workspace-file-actions">
                  <button
                    className={`workspace-icon-btn ${f.selected_for_context ? 'active' : ''}`}
                    title="Zu Chat-Kontext hinzufügen"
                    onClick={() => toggleContextSelection(f.name)}
                  >💬</button>
                  <button className="workspace-icon-btn" title="Umbenennen" onClick={() => { setRenameTarget(f.name); setRenameValue(f.name); }}>✏️</button>
                  <button className="workspace-icon-btn" title="Herunterladen" onClick={() => codeExecAPI.downloadFile(sessionId, f.name)}>⬇️</button>
                  <button className="workspace-icon-btn danger" title="Löschen" onClick={() => setDeleteTarget(f.name)}>🗑️</button>
                </div>
              </li>
            ))}
          </ul>
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
              placeholder="z. B. analyse.py"
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

      {renameTarget && (
        <div className="workspace-modal-overlay" onClick={() => setRenameTarget(null)}>
          <div className="workspace-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Datei umbenennen</h3>
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
            <h3>Datei löschen?</h3>
            <p>„{deleteTarget}" wird unwiderruflich gelöscht.</p>
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
