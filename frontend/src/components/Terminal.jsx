import { useState, useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import './Terminal.css';

function Terminal() {
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [newTabConfig, setNewTabConfig] = useState({
    type: 'local',
    host: '',
    port: '22',
    username: 'root'
  });
  
  const tabsRef = useRef({});
  const nextTabId = useRef(1);

  useEffect(() => {
    // Initialize xterm.js terminal
    if (!terminalRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"Fira Code", "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      scrollback: 1000,
      convertEol: true,  // Convert \n to \r\n automatically
      disableStdin: false,
      cursorInactiveStyle: 'outline',
      theme: {
        background: '#0a0e14',
        foreground: '#b3b1ad',
        cursor: '#e6b450',
        cursorAccent: '#0a0e14',
        black: '#01060e',
        red: '#ea6c73',
        green: '#91b362',
        yellow: '#f9af4f',
        blue: '#53bdfa',
        magenta: '#fae994',
        cyan: '#90e1c6',
        white: '#c7c7c7',
        brightBlack: '#686868',
        brightRed: '#f07178',
        brightGreen: '#c2d94c',
        brightYellow: '#ffb454',
        brightBlue: '#59c2ff',
        brightMagenta: '#ffee99',
        brightCyan: '#95e6cb',
        brightWhite: '#ffffff'
      }
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(terminalRef.current);
    
    // Fit terminal after a short delay to ensure container is rendered
    setTimeout(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    }, 100);
    
    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current) {
        try {
          fitAddonRef.current.fit();
          
          // Send resize to backend
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'resize',
              cols: term.cols,
              rows: term.rows
            }));
          }
        } catch (err) {
          console.warn('Terminal resize error:', err);
        }
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (wsRef.current) {
        wsRef.current.close();
      }
      term.dispose();
    };
  }, []);

  const handleConnect = async () => {
    if (connecting || isConnected) return;
    
    // Validate SSH config if SSH mode
    if (connectionType === 'ssh') {
      if (!sshConfig.host.trim()) {
        setError('SSH Host erforderlich');
        return;
      }
      if (!sshConfig.username.trim()) {
        setError('SSH Username erforderlich');
        return;
      }
    }
    
    setConnecting(true);
    setError(null);

    try {
      const token = localStorage.getItem('liara_token');
      if (!token) {
        throw new Error('Keine Authentifizierung gefunden');
      }

      // Build WebSocket URL with connection params
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      
      let wsUrl = `${protocol}//${host}/api/admin/terminal/ws?token=${encodeURIComponent(token)}`;
      
      // Add connection type and SSH params if applicable
      wsUrl += `&type=${connectionType}`;
      if (connectionType === 'ssh') {
        wsUrl += `&ssh_host=${encodeURIComponent(sshConfig.host)}`;
        wsUrl += `&ssh_port=${encodeURIComponent(sshConfig.port)}`;
        wsUrl += `&ssh_user=${encodeURIComponent(sshConfig.username)}`;
      }

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket PTY connected');
        setIsConnected(true);
        setConnecting(false);
        
        // Fit terminal after connection
        setTimeout(() => {
          if (fitAddonRef.current) {
            try {
              fitAddonRef.current.fit();
              
              // Send resize IMMEDIATELY after fit (before any output)
              if (xtermRef.current) {
                const cols = xtermRef.current.cols;
                const rows = xtermRef.current.rows;
                console.log(`🖥️ Terminal fitted: ${cols} cols × ${rows} rows`);
                
                ws.send(JSON.stringify({
                  type: 'resize',
                  cols: cols,
                  rows: rows
                }));
                console.log(`📤 Resize sent to backend: ${cols}x${rows}`);
              }
            } catch (err) {
              console.warn('Terminal fit error:', err);
            }
          }
        }, 200);
      };

      ws.onmessage = (event) => {
        if (!xtermRef.current) return;
        
        // Try to parse as JSON first (backend sends control messages as JSON)
        try {
          const message = JSON.parse(event.data);
          
          // Handle different message types
          if (message.type === 'data') {
            // Terminal output data
            xtermRef.current.write(message.data);
          } else if (message.type === 'error') {
            // Error message
            xtermRef.current.writeln(`\x1b[1;31m❌ Error: ${message.data}\x1b[0m`);
          } else if (message.type === 'connected') {
            // Connection established (already handled in welcome message)
            console.log('PTY connected:', message.data);
          } else if (message.type === 'resize') {
            // Resize acknowledgment (ignore)
            console.log('Terminal resized:', message.data);
          }
        } catch (e) {
          // Not JSON - raw terminal data, write directly
          xtermRef.current.write(event.data);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('WebSocket-Verbindungsfehler');
        setConnecting(false);
      };

      ws.onclose = () => {
        console.log('WebSocket PTY closed');
        setIsConnected(false);
        setConnecting(false);
        
        if (xtermRef.current) {
          xtermRef.current.writeln('');
          xtermRef.current.writeln('\x1b[1;31m🔌 Verbindung getrennt\x1b[0m');
        }
      };

      // Send terminal input to WebSocket
      if (xtermRef.current) {
        xtermRef.current.onData((data) => {
          if (ws.readyState === WebSocket.OPEN) {
            // Send as JSON message with type
            ws.send(JSON.stringify({
              type: 'data',
              data: data
            }));
          }
        });
      }

      wsRef.current = ws;

    } catch (err) {
      console.error('Connection error:', err);
      setError(err.message);
      setConnecting(false);
    }
  };

  const handleDisconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  };

  return (
    <div className="terminal-container">
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            💻 Interactive Terminal
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {connectionType === 'local' 
              ? 'Lokaler Server-Zugriff (Liara Host)' 
              : `SSH → ${sshConfig.host || 'Kein Ziel'}:${sshConfig.port}`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center' }}>
          {!isConnected && (
            <button 
              onClick={() => setShowConfig(!showConfig)}
              className="halo-button"
              style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
            >
              ⚙️ {showConfig ? 'Schließen' : 'Konfiguration'}
            </button>
          )}
          {error && (
            <span style={{ color: '#ea6c73', fontSize: '0.85rem' }}>
              ⚠️ {error}
            </span>
          )}
          {isConnected && (
            <span className="status-indicator connected">
              🟢 Verbunden {connectionType === 'ssh' ? '(SSH)' : '(Lokal)'}
            </span>
          )}
          {!isConnected ? (
            <button 
              onClick={handleConnect} 
              disabled={connecting}
              className="halo-button"
              style={{ fontSize: '1rem', fontWeight: 'bold' }}
            >
              {connecting ? '⏳ Verbinde...' : '🚀 Verbinden'}
            </button>
          ) : (
            <button 
              onClick={handleDisconnect}
              className="halo-button"
              style={{ fontSize: '1rem', fontWeight: 'bold', backgroundColor: '#ea6c73' }}
            >
              ⛔ Trennen
            </button>
          )}
        </div>
      </div>

      {/* Connection Configuration Panel */}
      {showConfig && !isConnected && (
        <div className="halo-panel" style={{ marginBottom: 'var(--space-lg)' }}>
          <h3 className="halo-header" style={{ fontSize: '1.2rem', marginBottom: 'var(--space-md)' }}>
            🔧 Verbindungskonfiguration
          </h3>
          
          {/* Connection Type Selector */}
          <div style={{ marginBottom: 'var(--space-lg)' }}>
            <label className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)', fontSize: '0.9rem' }}>
              Verbindungstyp:
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
              <button
                onClick={() => setConnectionType('local')}
                className="halo-button"
                style={{
                  flex: 1,
                  backgroundColor: connectionType === 'local' ? '#53bdfa' : 'transparent',
                  border: `2px solid ${connectionType === 'local' ? '#53bdfa' : 'var(--border-color)'}`,
                  color: connectionType === 'local' ? '#0a0e14' : 'inherit'
                }}
              >
                🖥️ Lokaler Server
              </button>
              <button
                onClick={() => setConnectionType('ssh')}
                className="halo-button"
                style={{
                  flex: 1,
                  backgroundColor: connectionType === 'ssh' ? '#53bdfa' : 'transparent',
                  border: `2px solid ${connectionType === 'ssh' ? '#53bdfa' : 'var(--border-color)'}`,
                  color: connectionType === 'ssh' ? '#0a0e14' : 'inherit'
                }}
              >
                🔐 SSH Verbindung
              </button>
            </div>
          </div>

          {/* SSH Configuration Fields */}
          {connectionType === 'ssh' && (
            <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
              <div>
                <label className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)', fontSize: '0.85rem' }}>
                  Host / IP-Adresse *
                </label>
                <input
                  type="text"
                  value={sshConfig.host}
                  onChange={(e) => setSshConfig({...sshConfig, host: e.target.value})}
                  placeholder="z.B. 192.168.1.100 oder example.com"
                  className="halo-input"
                  style={{ width: '100%', padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-md)' }}>
                <div>
                  <label className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)', fontSize: '0.85rem' }}>
                    Username *
                  </label>
                  <input
                    type="text"
                    value={sshConfig.username}
                    onChange={(e) => setSshConfig({...sshConfig, username: e.target.value})}
                    placeholder="z.B. root oder admin"
                    className="halo-input"
                    style={{ width: '100%', padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                  />
                </div>
                
                <div>
                  <label className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)', fontSize: '0.85rem' }}>
                    Port
                  </label>
                  <input
                    type="text"
                    value={sshConfig.port}
                    onChange={(e) => setSshConfig({...sshConfig, port: e.target.value})}
                    placeholder="22"
                    className="halo-input"
                    style={{ width: '100%', padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                  />
                </div>
              </div>

              <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 'var(--space-sm)' }}>
                💡 <strong>Hinweis:</strong> Das Passwort wird beim Verbindungsaufbau im Terminal abgefragt.
              </div>
            </div>
          )}

          {/* Local Server Info */}
          {connectionType === 'local' && (
            <div className="halo-mono" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: 'var(--space-md)', backgroundColor: 'rgba(83, 189, 250, 0.1)', borderRadius: '4px' }}>
              📌 <strong>Lokale Verbindung:</strong><br/>
              Direkter Shell-Zugriff auf den Liara-Server (localhost).<br/>
              Keine zusätzliche Konfiguration erforderlich.
            </div>
          )}
        </div>
      )}

      {/* Connection Status Banner - shown when connected */}
      {isConnected && (
        <div className="halo-panel" style={{ 
          marginBottom: 'var(--space-md)',
          padding: 'var(--space-md)',
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-md)'
        }}>
          <span style={{ fontSize: '1.2rem' }}>🔌</span>
          <div style={{ flex: 1 }}>
            <div className="halo-mono" style={{ fontSize: '0.95rem', fontWeight: 'bold', color: 'var(--color-emerald)', marginBottom: '4px' }}>
              Terminal verbunden
            </div>
            <div className="halo-mono" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {connectionType === 'local' ? (
                <>📍 Lokaler Server (Liara Host)</>
              ) : (
                <>🌐 SSH → {sshConfig.username}@{sshConfig.host}:{sshConfig.port}</>
              )}
            </div>
          </div>
          <button
            onClick={handleDisconnect}
            className="halo-button-secondary"
            style={{ 
              fontSize: '0.85rem',
              padding: 'var(--space-sm) var(--space-md)',
              background: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--color-red)',
              border: '1px solid rgba(239, 68, 68, 0.3)'
            }}
          >
            Trennen
          </button>
        </div>
      )}

      <div className="terminal-wrapper halo-panel">
        {/* Always render terminal div for xterm.js initialization */}
        <div 
          className="terminal-xterm-container"
          style={{ 
            display: (isConnected || connecting) ? 'block' : 'none'
          }}
        >
          <div ref={terminalRef} style={{ width: '100%', height: '100%' }} />
        </div>
        
        {/* Welcome screen - shown when not connected */}
        {!isConnected && !connecting && (
          <div className="terminal-welcome">
            <div className="welcome-icon">💻</div>
            <h2 className="halo-header" style={{ fontSize: '1.5rem', marginBottom: 'var(--space-md)' }}>
              Interactive PTY Terminal
            </h2>
            <p className="halo-mono" style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-lg)' }}>
              Voller Terminal-Zugriff mit TTY-Unterstützung
            </p>
            <div className="terminal-features" style={{ marginBottom: 'var(--space-lg)', textAlign: 'left' }}>
              <p className="halo-mono" style={{ fontSize: '0.85rem', marginBottom: 'var(--space-sm)' }}>
                ✅ Unterstützt:
              </p>
              <ul className="halo-mono" style={{ fontSize: '0.85rem', marginLeft: 'var(--space-lg)', lineHeight: '1.8' }}>
                <li>su (Benutzerwechsel)</li>
                <li>vim, nano (interaktive Editoren)</li>
                <li>top, htop (Prozessmonitor)</li>
                <li>Interactive Prompts (Passwort-Eingaben)</li>
                <li>Farbige Ausgaben (ANSI Escape Codes)</li>
                <li>SSH zu externen Servern</li>
              </ul>
            </div>
            <button 
              onClick={handleConnect} 
              disabled={connecting}
              className="halo-button"
              style={{ fontSize: '1rem', padding: 'var(--space-md) var(--space-xl)' }}
            >
              {connecting ? '⏳ Verbinde...' : '🚀 Terminal starten'}
            </button>
            <div className="terminal-info halo-mono" style={{ marginTop: 'var(--space-xl)', fontSize: '0.75rem' }}>
              <p>⚠️ <strong>Sicherheitshinweis:</strong></p>
              <ul style={{ marginTop: 'var(--space-sm)', marginLeft: 'var(--space-lg)' }}>
                <li>Nur für Administratoren</li>
                <li>Alle Befehle werden protokolliert</li>
                <li>Voller Shell-Zugriff - seien Sie vorsichtig!</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Terminal;
