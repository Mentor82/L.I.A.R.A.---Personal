import React, { useState, useEffect, useRef } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import CodeRunResult from './CodeRunResult';
import ImageLightbox from './ImageLightbox';
import { codeExecAPI } from '../services/api';
import './ImageViewer.css';

function formatClockTime(date) {
  if (!date) return '';
  return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Terminal-styled execution panel: the scrollback of every run in this pane.
 */
export function TerminalPanel({ history, onClear, sessionId }) {
  const [expanded, setExpanded] = useState(true);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (expanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history.length, expanded]);

  return (
    <div className="workspace-terminal">
      <div className="workspace-terminal-header">
        <button className="workspace-terminal-toggle" onClick={() => setExpanded((v) => !v)}>
          <span className="workspace-tree-chevron">{expanded ? '▾' : '▸'}</span>
          <span>🖥 Terminal{history.length > 0 ? ` (${history.length})` : ''}</span>
        </button>
        {history.length > 0 && (
          <button className="workspace-icon-btn" title="Terminal leeren" onClick={onClear}>🗑️</button>
        )}
      </div>
      {expanded && (
        <div className="workspace-terminal-body" ref={scrollRef}>
          {history.length === 0 ? (
            <p className="workspace-hint">Noch keine Ausführung in dieser Ansicht.</p>
          ) : (
            history.map((entry) => (
              <div key={entry.id} className="workspace-terminal-entry">
                <div className="workspace-terminal-prompt">
                  <span className="workspace-terminal-prompt-symbol">$</span> {entry.filename}
                  <span className="workspace-terminal-timestamp">{formatClockTime(entry.timestamp)}</span>
                </div>
                <CodeRunResult result={entry.result} sessionId={sessionId} />
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Dedicated visual image viewer for image files (.png, .jpg, .svg, .webp, etc.).
 */
export function ImageViewer({ src, filename, size, sessionId, onSplit, isSecondary }) {
  const [zoom, setZoom] = useState(1);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [dimensions, setDimensions] = useState(null);
  const [downloading, setDownloading] = useState(false);

  const handleImageLoad = (e) => {
    setDimensions({
      width: e.target.naturalWidth,
      height: e.target.naturalHeight,
    });
  };

  const handleZoomIn = () => setZoom((z) => Math.min(Number((z + 0.25).toFixed(2)), 4));
  const handleZoomOut = () => setZoom((z) => Math.max(Number((z - 0.25).toFixed(2)), 0.25));
  const handleResetZoom = () => setZoom(1);

  const handleDownload = async () => {
    if (!sessionId || !filename) return;
    setDownloading(true);
    try {
      await codeExecAPI.downloadFile(sessionId, filename);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="workspace-image-viewer">
      <div className="workspace-toolbar workspace-image-toolbar">
        <div className="workspace-image-info">
          <span className="workspace-image-tag">🖼️ Bild-Vorschau</span>
          {dimensions && (
            <span className="workspace-image-dim">{dimensions.width} × {dimensions.height} px</span>
          )}
          {size > 0 && (
            <span className="workspace-image-size">{formatBytes(size)}</span>
          )}
        </div>
        <div className="workspace-image-controls">
          <button className="workspace-icon-btn" onClick={handleZoomOut} title="Verkleinern" disabled={zoom <= 0.25}>🔍−</button>
          <button className="workspace-btn-secondary workspace-zoom-btn" onClick={handleResetZoom} title="Zoom zurücksetzen">
            {Math.round(zoom * 100)}%
          </button>
          <button className="workspace-icon-btn" onClick={handleZoomIn} title="Vergrößern" disabled={zoom >= 4}>🔍+</button>
          <button className="workspace-btn-secondary" onClick={() => setLightboxOpen(true)} title="Vollbild öffnen">
            ⛶ Vollbild
          </button>
          <button className="workspace-btn-primary" onClick={handleDownload} disabled={downloading} title="Bild herunterladen">
            ⬇ Herunterladen
          </button>
          {!isSecondary && (
            <button className="workspace-btn-secondary" onClick={onSplit} title="Datei zusätzlich rechts daneben öffnen">🗗 Teilen</button>
          )}
        </div>
      </div>
      <div className="workspace-image-canvas" onClick={() => setLightboxOpen(true)} title="Klicken für Vollbild-Ansicht">
        <div className="workspace-image-wrapper" style={{ transform: `scale(${zoom})` }}>
          <img
            src={src}
            alt={filename}
            onLoad={handleImageLoad}
            className="workspace-preview-img"
          />
        </div>
      </div>
      {lightboxOpen && (
        <ImageLightbox src={src} alt={filename} onClose={() => setLightboxOpen(false)} />
      )}
    </div>
  );
}

/**
 * One editor group (tab strip + toolbar + CodeMirror/ImageViewer + terminal panel).
 */
export function EditorPane({
  tabs, activeTabName, tabData, activeLang,
  onSelectTab, onCloseTab, onChangeContent, onCreateEditor,
  running, runHistory, onClearHistory, onSave, onRun,
  sessionId, isSecondary, onSplit, onCloseSplitPane,
  cmTheme, fontSizeExtension, isActivePane,
  pythonVersion, onPythonVersionChange,
}) {
  return (
    <section className={`workspace-main ${isActivePane ? 'active-pane' : ''}`}>
      {isSecondary && (
        <div className="workspace-split-header">
          <span>Geteilte Ansicht</span>
          <button className="workspace-icon-btn" title="Geteilte Ansicht schließen" onClick={onCloseSplitPane}>✕</button>
        </div>
      )}
      <div className="workspace-tabs">
        {tabs.map((t) => (
          <button
            key={t.name}
            className={`workspace-tab ${activeTabName === t.name ? 'active' : ''}`}
            onClick={() => onSelectTab(t.name)}
          >
            {t.isImage ? '🖼️ ' : ''}{t.name}{t.dirty ? ' •' : ''}
            <span className="workspace-tab-close" onClick={(e) => { e.stopPropagation(); onCloseTab(t.name); }}>✕</span>
          </button>
        ))}
      </div>

      {tabData ? (
        tabData.isImage ? (
          <>
            <ImageViewer
              src={tabData.imageUrl}
              filename={tabData.name}
              size={tabData.size}
              sessionId={sessionId}
              onSplit={onSplit}
              isSecondary={isSecondary}
            />
            {runHistory.length > 0 && (
              <TerminalPanel history={runHistory} onClear={onClearHistory} sessionId={sessionId} />
            )}
          </>
        ) : (
          <>
            <div className="workspace-toolbar">
              <button className="workspace-btn-secondary" onClick={onSave} disabled={!tabData.dirty}>💾 Speichern</button>
              <button className="workspace-btn-primary" onClick={onRun} disabled={!activeLang || running}>
                {running ? 'Läuft…' : '▶ Ausführen'}
              </button>
              {activeLang?.runLanguage === 'python' && (
                <select
                  className="workspace-runtime-select"
                  value={pythonVersion || 'python3.14'}
                  onChange={(e) => onPythonVersionChange && onPythonVersionChange(e.target.value)}
                  title="Python Sandbox-Version auswählen"
                >
                  <option value="python3.14">🐍 Python 3.14 (Standard)</option>
                  <option value="python3.13">🐍 Python 3.13</option>
                  <option value="python3.12">🐍 Python 3.12</option>
                  <option value="python3.11">🐍 Python 3.11</option>
                </select>
              )}
              {!isSecondary && (
                <button className="workspace-btn-secondary" onClick={onSplit} title="Datei zusätzlich rechts daneben öffnen">🗗 Teilen</button>
              )}
            </div>
            <div className="workspace-editor-wrapper">
              <CodeMirror
                value={tabData.content}
                height="100%"
                theme={cmTheme}
                extensions={activeLang ? [activeLang.cm, fontSizeExtension] : [fontSizeExtension]}
                onChange={onChangeContent}
                onCreateEditor={onCreateEditor}
              />
            </div>
            <TerminalPanel history={runHistory} onClear={onClearHistory} sessionId={sessionId} />
          </>
        )
      ) : (
        <div className="workspace-empty">
          <div className="workspace-empty-icon">📄</div>
          <p className="workspace-empty-title">Keine Datei geöffnet</p>
          <p className="workspace-empty-subtitle">Datei aus der Liste öffnen oder eine neue anlegen.</p>
        </div>
      )}
    </section>
  );
}

export default EditorPane;
