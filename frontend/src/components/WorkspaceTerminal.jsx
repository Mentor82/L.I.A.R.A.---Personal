import { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { workspaceAPI } from '../services/api';
import './WorkspaceTerminal.css';

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  if (h === 0) return `${m}m ${s}s`;
  return `${h}h ${remM}m`;
}

function SingleTerminalInstance({ sessionId, active, onStatusChange }) {
  const containerRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!sessionId || !containerRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"JetBrains Mono", "Fira Code", "Courier New", monospace',
      fontSize: 11,
      lineHeight: 1.3,
      scrollback: 2000,
      convertEol: true,
      theme: {
        background: '#0a0e14',
        foreground: '#b3b1ad',
        cursor: '#e6b450',
        cursorAccent: '#0a0e14',
        black: '#01060e',
        red: '#ea6c73',
        green: '#91b362',
        yellow: '#f9af4f',
        blue: '#4a7ba7',
        magenta: '#b88a5f',
        cyan: '#5a9b8a',
        white: '#c7c7c7',
        brightBlack: '#686868',
        brightRed: '#a66165',
        brightGreen: '#708356',
        brightYellow: '#9a7850',
        brightBlue: '#4a6b85',
        brightMagenta: '#9a8850',
        brightCyan: '#5a7d70',
        brightWhite: '#8a8a8a',
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());
    term.open(containerRef.current);
    termRef.current = term;
    fitAddonRef.current = fitAddon;

    let ws;
    let disposed = false;

    const connect = async () => {
      const token = localStorage.getItem('liara_token');
      if (!token) {
        term.writeln('\x1b[1;31m❌ Keine Authentifizierung gefunden\x1b[0m');
        onStatusChange?.('disconnected');
        return;
      }

      onStatusChange?.('connecting');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/workspace/sessions/${sessionId}/terminal/ws`;
      ws = new WebSocket(wsUrl, [token]);
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed) return;
        onStatusChange?.('connected');
        setTimeout(() => {
          try {
            fitAddon.fit();
            ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
          } catch {
            // Cosmetic resize - not worth surfacing if the terminal isn't ready yet.
          }
        }, 150);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'data') {
            term.write(message.data);
          } else if (message.type === 'error') {
            term.writeln(`\x1b[1;31m❌ ${message.data}\x1b[0m`);
          }
        } catch {
          term.write(event.data);
        }
      };

      ws.onerror = () => onStatusChange?.('disconnected');

      ws.onclose = () => {
        if (disposed) return;
        onStatusChange?.('disconnected');
        term.writeln('');
        term.writeln('\x1b[1;31m🔌 Verbindung getrennt\x1b[0m');
      };

      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'data', data }));
        }
      });
    };

    connect();

    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
        }
      } catch {
        // Cosmetic resize - not worth surfacing if the terminal isn't ready yet.
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      disposed = true;
      resizeObserver.disconnect();
      ws?.close();
      term.dispose();
    };
  }, [sessionId]);

  useEffect(() => {
    if (active && fitAddonRef.current) {
      setTimeout(() => {
        try {
          fitAddonRef.current.fit();
          if (wsRef.current?.readyState === WebSocket.OPEN && termRef.current) {
            wsRef.current.send(JSON.stringify({
              type: 'resize',
              cols: termRef.current.cols,
              rows: termRef.current.rows,
            }));
          }
        } catch {
          // Cosmetic resize - not worth surfacing if the terminal isn't ready yet.
        }
      }, 50);
    }
  }, [active]);

  return (
    <div
      className="workspace-shell-body"
      ref={containerRef}
      style={{ display: active ? 'block' : 'none' }}
    />
  );
}

export default function WorkspaceTerminal({ sessionId, onClose }) {
  const [terminalTabs, setTerminalTabs] = useState([{ id: 1, name: 'Shell 1', status: 'connecting' }]);
  const [activeTabId, setActiveTabId] = useState(1);
  const [processes, setProcesses] = useState([]);
  const [processesOpen, setProcessesOpen] = useState(false);
  const [killingPid, setKillingPid] = useState(null);
  const nextTabIdRef = useRef(2);
  const popoverRef = useRef(null);

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
    loadProcesses();
    const interval = setInterval(loadProcesses, 3000);
    return () => clearInterval(interval);
  }, [loadProcesses]);

  // Click outside closes popover
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setProcessesOpen(false);
      }
    };
    if (processesOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [processesOpen]);

  const handleKill = async (pid) => {
    setKillingPid(pid);
    try {
      await workspaceAPI.killProcess(sessionId, pid);
      await loadProcesses();
    } catch (err) {
      console.error('Kill failed:', err);
    } finally {
      setKillingPid(null);
    }
  };

  const handleKillAll = async () => {
    try {
      await workspaceAPI.killAllProcesses(sessionId);
      await loadProcesses();
    } catch (err) {
      console.error('Kill all failed:', err);
    }
  };

  const addTab = () => {
    const newId = nextTabIdRef.current++;
    const newTab = { id: newId, name: `Shell ${newId}`, status: 'connecting' };
    setTerminalTabs((prev) => [...prev, newTab]);
    setActiveTabId(newId);
  };

  const closeTab = (tabId, e) => {
    e.stopPropagation();
    setTerminalTabs((prev) => {
      const filtered = prev.filter((t) => t.id !== tabId);
      if (filtered.length === 0) {
        onClose?.();
        return prev;
      }
      if (activeTabId === tabId) {
        setActiveTabId(filtered[filtered.length - 1].id);
      }
      return filtered;
    });
  };

  const handleStatusChange = (tabId, newStatus) => {
    setTerminalTabs((prev) =>
      prev.map((t) => (t.id === tabId ? { ...t, status: newStatus } : t))
    );
  };

  return (
    <div className="workspace-shell-panel">
      <div className="workspace-shell-header">
        <div className="workspace-shell-tabs">
          {terminalTabs.map((tab) => (
            <button
              key={tab.id}
              className={`workspace-shell-tab ${activeTabId === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTabId(tab.id)}
            >
              <span>💻 {tab.name}</span>
              <span className={`workspace-shell-status ${tab.status || 'connecting'}`}>●</span>
              {terminalTabs.length > 1 && (
                <span className="workspace-tab-close" onClick={(e) => closeTab(tab.id, e)} title="Terminal schließen">✕</span>
              )}
            </button>
          ))}
          <button className="workspace-icon-btn workspace-add-shell-btn" onClick={addTab} title="Neues Terminal öffnen">➕</button>
        </div>

        <div className="workspace-shell-actions" ref={popoverRef}>
          <button
            className={`workspace-processes-toggle ${processes.length > 0 ? 'has-processes' : ''} ${processesOpen ? 'active' : ''}`}
            onClick={() => {
              setProcessesOpen((v) => !v);
              if (!processesOpen) loadProcesses();
            }}
            title="Laufende Sandbox-Prozesse anzeigen & verwalten"
          >
            ⚡ {processes.length} {processes.length === 1 ? 'Prozess' : 'Prozesse'}
            {processes.length > 0 && <span className="workspace-proc-pulse" />}
          </button>

          {processesOpen && (
            <div className="workspace-processes-popover">
              <div className="workspace-processes-header">
                <span>Laufende Prozesse ({processes.length})</span>
                {processes.length > 0 && (
                  <button className="workspace-btn-danger-sm" onClick={handleKillAll} title="Alle Prozesse beenden">
                    🧹 Alle beenden
                  </button>
                )}
              </div>
              {processes.length === 0 ? (
                <p className="workspace-hint">Keine Hintergrund-Prozesse aktiv.</p>
              ) : (
                <ul className="workspace-proc-list">
                  {processes.map((proc) => {
                    const isPy = proc.name.includes('python');
                    const isJl = proc.name.includes('julia');
                    const icon = isPy ? '🐍' : isJl ? '🟣' : '⚙️';

                    return (
                      <li key={proc.pid} className="workspace-proc-item">
                        <div className="workspace-proc-main">
                          <span className="workspace-proc-icon">{icon}</span>
                          <div className="workspace-proc-details">
                            <span className="workspace-proc-cmd" title={proc.full_cmdline || proc.cmdline}>
                              {proc.cmdline || proc.name}
                            </span>
                            <span className="workspace-proc-meta">
                              PID: {proc.pid} • Laufzeit: {formatDuration(proc.running_seconds)} • {proc.memory_mb} MB RAM
                            </span>
                          </div>
                        </div>
                        <button
                          className="workspace-proc-kill-btn"
                          disabled={killingPid === proc.pid}
                          onClick={() => handleKill(proc.pid)}
                          title="Prozess beenden"
                        >
                          {killingPid === proc.pid ? '…' : '❌ Kill'}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}

          <button className="workspace-icon-btn" onClick={onClose} title="Terminal ausblenden">✕</button>
        </div>
      </div>

      <div className="workspace-shell-bodies">
        {terminalTabs.map((tab) => (
          <SingleTerminalInstance
            key={tab.id}
            sessionId={sessionId}
            active={activeTabId === tab.id}
            onStatusChange={(status) => handleStatusChange(tab.id, status)}
          />
        ))}
      </div>
    </div>
  );
}
