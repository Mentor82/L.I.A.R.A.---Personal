import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import './WorkspaceTerminal.css';

// Sandboxed interactive shell for one Workspace session - the same xterm.js +
// WebSocket-PTY pattern as the admin panel's TerminalTabs.jsx, but a single
// always-on session (no multi-tab management, no SSH mode) scoped to
// api/routers/workspace_terminal.py's per-session endpoint, which runs the
// shell as the unprivileged liara-runner OS user (see run_sandboxed_shell.sh)
// instead of the admin terminal's own unrestricted local shell.
export default function WorkspaceTerminal({ sessionId, onClose }) {
  const containerRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);
  const wsRef = useRef(null);
  const [status, setStatus] = useState('connecting'); // 'connecting' | 'connected' | 'disconnected'

  useEffect(() => {
    if (!sessionId || !containerRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: 'block',
      // Matches this project's other monospace UI (workspace file search
      // etc.) - JetBrains Mono reads noticeably crisper than Fira Code at
      // small sizes for lookalike characters (l/1/I, 0/O).
      fontFamily: '"JetBrains Mono", "Fira Code", "Courier New", monospace',
      fontSize: 10,
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
        setStatus('disconnected');
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/workspace/sessions/${sessionId}/terminal/ws`;
      ws = new WebSocket(wsUrl, [token]);
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed) return;
        setStatus('connected');
        setTimeout(() => {
          try {
            fitAddon.fit();
            ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
          } catch {
            // pane not visible yet - next resize/fit pass will catch up
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

      ws.onerror = () => setStatus('disconnected');

      ws.onclose = () => {
        if (disposed) return;
        setStatus('disconnected');
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
        // container might still be mid-layout - next observed resize retries
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

  return (
    <div className="workspace-shell-panel">
      <div className="workspace-shell-header">
        <span>
          💻 Terminal <span className={`workspace-shell-status ${status}`}>●</span>
        </span>
        <button className="workspace-icon-btn" onClick={onClose} title="Schließen">✕</button>
      </div>
      <div className="workspace-shell-body" ref={containerRef} />
    </div>
  );
}
