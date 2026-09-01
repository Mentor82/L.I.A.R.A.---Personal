import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { StreamLanguage } from '@codemirror/language';
import { julia as juliaLegacyMode } from '@codemirror/legacy-modes/mode/julia';
import { useViewMode } from '../../contexts/ViewModeContext';
import { workspaceAPI, codeExecAPI } from '../../services/api';
import WorkspaceTerminal from '../WorkspaceTerminal';
import CodeRunResult from '../CodeRunResult';
import ImageViewer from '../EditorPane';
import './MobileWorkspace.css';

const juliaLanguage = StreamLanguage.define(juliaLegacyMode);

export default function MobileWorkspace() {
  const { t } = useTranslation();
  const { setViewMode } = useViewMode();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('files'); // 'files' | 'editor' | 'terminal'
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem('liara_active_session');
    return saved ? parseInt(saved) : 1;
  });

  const [files, setFiles] = useState([]);
  const [openFileName, setOpenFileName] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [processes, setProcesses] = useState([]);
  const fileInputRef = useRef(null);

  // Load files
  const loadFiles = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await workspaceAPI.listFiles(sessionId);
      setFiles(data.files || []);
    } catch {
      setFiles([]);
    }
  }, [sessionId]);

  // Load running processes
  const loadProcesses = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await workspaceAPI.listProcesses(sessionId);
      setProcesses(data.processes || []);
    } catch {
      setProcesses([]);
    }
  }, [sessionId]);

  useEffect(() => {
    loadFiles();
    loadProcesses();
    const interval = setInterval(loadProcesses, 3000);
    return () => clearInterval(interval);
  }, [loadFiles, loadProcesses]);

  const handleOpenFile = async (filename) => {
    try {
      const content = await workspaceAPI.getFileContent(sessionId, filename);
      setOpenFileName(filename);
      setFileContent(content);
      setDirty(false);
      setActiveTab('editor');
    } catch (err) {
      alert(err.message || 'Fehler beim Laden');
    }
  };

  const handleSaveFile = async () => {
    if (!openFileName) return;
    try {
      await workspaceAPI.saveFile(sessionId, openFileName, fileContent);
      setDirty(false);
    } catch (err) {
      alert('Speichern fehlgeschlagen: ' + err.message);
    }
  };

  const handleRunCode = async () => {
    if (!openFileName || running) return;
    const lang = openFileName.endsWith('.jl') ? 'julia' : 'python';
    setRunning(true);
    setRunResult(null);
    try {
      const res = await codeExecAPI.run(lang, fileContent, sessionId);
      setRunResult(res);
      await loadFiles();
      await loadProcesses();
    } catch (err) {
      setRunResult({ error: err.message || 'Ausführung fehlgeschlagen' });
    } finally {
      setRunning(false);
    }
  };

  const handleUpload = async (e) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    try {
      await workspaceAPI.uploadFiles(sessionId, fileList);
      await loadFiles();
    } catch (err) {
      alert('Upload fehlgeschlagen: ' + err.message);
    }
  };

  const isPy = openFileName?.endsWith('.py');
  const isJl = openFileName?.endsWith('.jl');
  const langExtension = isPy ? python() : isJl ? juliaLanguage : [];

  return (
    <div className="mobile-workspace-app">
      {/* Header */}
      <header className="mobile-ws-header">
        <button className="mobile-icon-btn" onClick={() => navigate('/')} title="Zurück zum Chat">
          ← Chat
        </button>
        <span className="mobile-ws-title">🗂️ {t('mobile.workspace')}</span>
        <button
          className="mobile-icon-btn"
          onClick={() => setViewMode('desktop')}
          title={t('mobile.switchDesktop')}
        >
          🖥️
        </button>
      </header>

      {/* Tabs */}
      <nav className="mobile-ws-nav">
        <button
          className={`mobile-ws-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          📁 {t('mobile.files')} ({files.length})
        </button>
        <button
          className={`mobile-ws-tab ${activeTab === 'editor' ? 'active' : ''}`}
          onClick={() => setActiveTab('editor')}
        >
          📝 {t('mobile.editor')} {openFileName ? `(${openFileName.split('/').pop()})` : ''}
        </button>
        <button
          className={`mobile-ws-tab ${activeTab === 'terminal' ? 'active' : ''}`}
          onClick={() => setActiveTab('terminal')}
        >
          💻 {t('mobile.terminal')}
          {processes.length > 0 && <span className="mobile-ws-proc-badge">{processes.length}</span>}
        </button>
      </nav>

      {/* Tab 1: Files */}
      {activeTab === 'files' && (
        <div className="mobile-ws-view mobile-ws-files">
          <div className="mobile-files-actions">
            <button className="mobile-btn-primary" onClick={() => fileInputRef.current?.click()}>
              ⬆️ {t('mobile.uploadFile')}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              style={{ display: 'none' }}
              onChange={handleUpload}
            />
          </div>

          <ul className="mobile-file-list">
            {files.length === 0 ? (
              <li className="mobile-file-empty">Keine Dateien im Workspace</li>
            ) : (
              files.map((f) => {
                const icon = f.name.endsWith('.py') ? '🐍' : f.name.endsWith('.jl') ? '🟣' : f.name.match(/\.(png|jpe?g|svg)$/i) ? '🖼️' : '📄';
                return (
                  <li key={f.name} className="mobile-file-item" onClick={() => handleOpenFile(f.name)}>
                    <div className="mobile-file-info">
                      <span className="mobile-file-icon">{icon}</span>
                      <span className="mobile-file-name">{f.name}</span>
                    </div>
                    <span className="mobile-file-arrow">▸</span>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}

      {/* Tab 2: Editor */}
      {activeTab === 'editor' && (
        <div className="mobile-ws-view mobile-ws-editor">
          <div className="mobile-editor-toolbar">
            <span className="mobile-editor-filename">{openFileName || 'Keine Datei ausgewählt'}</span>
            <div className="mobile-editor-btns">
              <button
                className="mobile-btn-sm"
                onClick={handleSaveFile}
                disabled={!openFileName || !dirty}
                title={t('mobile.save')}
              >
                💾 {t('mobile.save')}
              </button>
              {(isPy || isJl) && (
                <button
                  className="mobile-btn-sm mobile-run-btn"
                  onClick={handleRunCode}
                  disabled={running || !openFileName}
                  title={t('mobile.run')}
                >
                  {running ? '⏳' : '▶'} {t('mobile.run')}
                </button>
              )}
            </div>
          </div>

          <div className="mobile-codemirror-wrapper">
            <CodeMirror
              value={fileContent}
              height="100%"
              theme="dark"
              extensions={langExtension ? [langExtension] : []}
              onChange={(val) => {
                setFileContent(val);
                setDirty(true);
              }}
            />
          </div>

          {runResult && (
            <div className="mobile-run-result-box">
              <CodeRunResult
                result={runResult}
                onClose={() => setRunResult(null)}
              />
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Terminal */}
      {activeTab === 'terminal' && (
        <div className="mobile-ws-view mobile-ws-terminal">
          <WorkspaceTerminal sessionId={sessionId} onClose={() => setActiveTab('editor')} />
        </div>
      )}
    </div>
  );
}
