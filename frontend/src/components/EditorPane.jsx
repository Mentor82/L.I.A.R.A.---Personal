import React, { useState, useEffect, useRef } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import CodeRunResult from './CodeRunResult';

function formatClockTime(date) {
  if (!date) return '';
  return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
 * One editor group (tab strip + toolbar + CodeMirror + terminal panel).
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
            {t.name}{t.dirty ? ' •' : ''}
            <span className="workspace-tab-close" onClick={(e) => { e.stopPropagation(); onCloseTab(t.name); }}>✕</span>
          </button>
        ))}
      </div>

      {tabData ? (
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
