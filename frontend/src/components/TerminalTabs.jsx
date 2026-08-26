import { useState, useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import AiExecTab from './AiExecTab';
import './TerminalTabs.css';

// Silent-refreshes the access token before opening a PTY WebSocket. Unlike a
// plain fetch() there's no way to retry a failed WS handshake with a new
// token after the fact (see services/api.js's 401-retry pattern), so this
// gets the freshest token available *before* connecting instead. Falls back
// to whatever's already in localStorage if refresh isn't possible/fails.
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('liara_refresh_token');
  if (!refreshToken) return false;

  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    if (!res.ok) return false;

    const data = await res.json();
    localStorage.setItem('liara_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('liara_refresh_token', data.refresh_token);
    }
    return true;
  } catch {
    return false;
  }
}

function TerminalTabs() {
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [showNewTabConfig, setShowNewTabConfig] = useState(false);
  const [newTabConfig, setNewTabConfig] = useState({
    type: 'local',
    host: '',
    port: '22',
    username: 'root'
  });
  
  const tabInstancesRef = useRef({});

  // Get status color (Ampel)
  const getStatusColor = (status) => {
    switch(status) {
      case 'connected': return '🟢';
      case 'connecting': return '🟡';
      case 'disconnected': return '🔴';
      default: return '⚪';
    }
  };

  // Create new tab
  const createNewTab = () => {
    // Validate SSH config if SSH mode
    if (newTabConfig.type === 'ssh') {
      if (!newTabConfig.host.trim() || !newTabConfig.username.trim()) {
        alert('SSH Host und Username sind erforderlich');
        return;
      }
    }

    const tabId = `tab-${Date.now()}`;
    const tabName = newTabConfig.type === 'ai'
      ? (newTabConfig.host.trim() ? `🤖 ${newTabConfig.username}@${newTabConfig.host}` : '🤖 AI Exec')
      : newTabConfig.type === 'local' ? 'Local Shell' : `${newTabConfig.username}@${newTabConfig.host}`;
    const newTab = {
      id: tabId,
      name: tabName,
      type: newTabConfig.type,
      config: { ...newTabConfig },
      // AI tabs use plain request/response, not a persistent connection - nothing to "connect"
      status: newTabConfig.type === 'ai' ? 'connected' : 'disconnected'
    };
    
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
    setShowNewTabConfig(false);
    
    // Reset config for next tab
    setNewTabConfig({
      type: 'local',
      host: '',
      port: '22',
      username: 'root'
    });
  };

  // Close tab
  const closeTab = (tabId, e) => {
    e?.stopPropagation();
    
    const instance = tabInstancesRef.current[tabId];
    if (instance) {
      if (instance.ws) {
        instance.ws.close();
      }
      if (instance.term) {
        instance.term.dispose();
      }
      delete tabInstancesRef.current[tabId];
    }
    
    setTabs(prev => {
      const newTabs = prev.filter(t => t.id !== tabId);
      if (activeTabId === tabId && newTabs.length > 0) {
        setActiveTabId(newTabs[newTabs.length - 1].id);
      } else if (newTabs.length === 0) {
        setActiveTabId(null);
      }
      return newTabs;
    });
  };

  // Update tab status
  const updateTabStatus = (tabId, status) => {
    setTabs(prev => prev.map(tab => 
      tab.id === tabId ? { ...tab, status } : tab
    ));
  };

  // Connect tab
  const connectTab = async (tabId) => {
    const tab = tabs.find(t => t.id === tabId);
    if (!tab || tab.status === 'connected' || tab.status === 'connecting') return;

    updateTabStatus(tabId, 'connecting');

    const instance = tabInstancesRef.current[tabId];
    if (!instance || !instance.term) {
      console.error('Terminal instance not found for tab:', tabId);
      updateTabStatus(tabId, 'disconnected');
      return;
    }

    try {
      await refreshAccessToken();
      const token = localStorage.getItem('liara_token');
      if (!token) {
        throw new Error('Keine Authentifizierung gefunden');
      }

      // Build WebSocket URL - the JWT itself travels via the WS subprotocol
      // list, not the query string (issue #10): query-string bearer tokens
      // are far more likely to leak into reverse-proxy/access logs or
      // browser diagnostics than a protocol value, and a browser WebSocket
      // can't set a custom Authorization header, so this is the only way to
      // keep it off the URL. type/ssh_* aren't secrets and stay in the query
      // string.
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      let wsUrl = `${protocol}//${host}/api/admin/terminal/ws?type=${tab.type}`;

      if (tab.type === 'ssh') {
        wsUrl += `&ssh_host=${encodeURIComponent(tab.config.host)}`;
        wsUrl += `&ssh_port=${encodeURIComponent(tab.config.port)}`;
        wsUrl += `&ssh_user=${encodeURIComponent(tab.config.username)}`;
      }

      const ws = new WebSocket(wsUrl, [token]);

      ws.onopen = () => {
        console.log('WebSocket connected for tab:', tabId);
        updateTabStatus(tabId, 'connected');
        
        // Fit and resize
        setTimeout(() => {
          if (instance.fitAddon && instance.term) {
            try {
              instance.fitAddon.fit();
              const cols = instance.term.cols;
              const rows = instance.term.rows;
              
              ws.send(JSON.stringify({
                type: 'resize',
                cols: cols,
                rows: rows
              }));
              console.log(`📤 Tab ${tabId} resize: ${cols}x${rows}`);
            } catch (err) {
              console.warn('Fit error:', err);
            }
          }
        }, 200);
      };

      ws.onmessage = (event) => {
        if (!instance.term) return;
        
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'data') {
            instance.term.write(message.data);
          } else if (message.type === 'error') {
            instance.term.writeln(`\x1b[1;31m❌ Error: ${message.data}\x1b[0m`);
          }
        } catch (e) {
          instance.term.write(event.data);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error for tab:', tabId, err);
        updateTabStatus(tabId, 'disconnected');
      };

      ws.onclose = () => {
        console.log('WebSocket closed for tab:', tabId);
        updateTabStatus(tabId, 'disconnected');
        if (instance.term) {
          instance.term.writeln('');
          instance.term.writeln('\x1b[1;31m🔌 Verbindung getrennt\x1b[0m');
        }
      };

      // Handle user input
      if (instance.term) {
        instance.term.onData((data) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'data',
              data: data
            }));
          }
        });
      }

      instance.ws = ws;

    } catch (err) {
      console.error('Connection error:', err);
      updateTabStatus(tabId, 'disconnected');
    }
  };

  // Disconnect tab
  const disconnectTab = (tabId) => {
    const instance = tabInstancesRef.current[tabId];
    if (instance?.ws) {
      instance.ws.close();
    }
    updateTabStatus(tabId, 'disconnected');
  };

  // Initialize terminal for active tab
  useEffect(() => {
    if (!activeTabId) return;

    const tab = tabs.find(t => t.id === activeTabId);
    if (!tab) return;

    // AI tabs use plain HTTP request/response (AiExecTab) - no xterm/WS needed
    if (tab.type === 'ai') return;

    // Skip if already initialized
    if (tabInstancesRef.current[activeTabId]?.term) {
      return;
    }

    // Get terminal ref
    const terminalElement = document.getElementById(`terminal-${activeTabId}`);
    if (!terminalElement) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"Fira Code", "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      scrollback: 1000,
      convertEol: true,
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
        blue: '#4a7ba7',              // Dunkler Blauton
        magenta: '#b88a5f',
        cyan: '#5a9b8a',
        white: '#c7c7c7',
        brightBlack: '#686868',
        brightRed: '#a66165',         // Noch dunkler
        brightGreen: '#708356',       // Noch dunkler  
        brightYellow: '#9a7850',      // Noch dunkler
        brightBlue: '#4a6b85',        // SEHR dunkel statt grell hellblau
        brightMagenta: '#9a8850',     // Noch dunkler
        brightCyan: '#5a7d70',        // Noch dunkler
        brightWhite: '#8a8a8a'        // Grau statt weiß
      }
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(terminalElement);
    
    setTimeout(() => {
      if (fitAddon) {
        try {
          fitAddon.fit();
        } catch (err) {
          console.warn('Initial fit error:', err);
        }
      }
    }, 100);

    tabInstancesRef.current[activeTabId] = {
      term,
      fitAddon,
      ws: null
    };

    // Auto-connect
    setTimeout(() => connectTab(activeTabId), 300);

    // Cleanup when component unmounts
    return () => {
      // Don't dispose here - only on tab close
    };
  }, [activeTabId, tabs]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (activeTabId) {
        const instance = tabInstancesRef.current[activeTabId];
        if (instance?.fitAddon && instance?.term) {
          try {
            instance.fitAddon.fit();
            if (instance.ws?.readyState === WebSocket.OPEN) {
              instance.ws.send(JSON.stringify({
                type: 'resize',
                cols: instance.term.cols,
                rows: instance.term.rows
              }));
            }
          } catch (err) {
            console.warn('Resize error:', err);
          }
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [activeTabId]);

  const activeTab = tabs.find(t => t.id === activeTabId);

  return (
    <div className="terminal-container">
      <div className="page-header" style={{ marginBottom: 'var(--space-md)' }}>
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            💻 Interactive Terminal (Multi-Tab)
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            MC, vim, su und SSH-Verbindungen unterstützt
          </p>
        </div>
        <button 
          onClick={() => setShowNewTabConfig(!showNewTabConfig)}
          className="halo-button"
          style={{ fontSize: '0.95rem', padding: '0.6rem 1.2rem' }}
        >
          ➕ Neuer Tab
        </button>
      </div>

      {/* New Tab Configuration Panel */}
      {showNewTabConfig && (
        <div className="halo-panel" style={{ marginBottom: 'var(--space-md)', padding: 'var(--space-md)' }}>
          <h3 className="halo-header" style={{ fontSize: '1.1rem', marginBottom: 'var(--space-md)' }}>
            🔧 Neuer Terminal-Tab
          </h3>
          
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <label className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)', fontSize: '0.85rem' }}>
              Typ:
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
              <button
                onClick={() => setNewTabConfig({...newTabConfig, type: 'local'})}
                className="halo-button"
                style={{
                  flex: 1,
                  backgroundColor: newTabConfig.type === 'local' ? '#53bdfa' : 'transparent',
                  border: `2px solid ${newTabConfig.type === 'local' ? '#53bdfa' : 'var(--border-color)'}`,
                  color: newTabConfig.type === 'local' ? '#0a0e14' : 'inherit'
                }}
              >
                🖥️ Local
              </button>
              <button
                onClick={() => setNewTabConfig({...newTabConfig, type: 'ssh'})}
                className="halo-button"
                style={{
                  flex: 1,
                  backgroundColor: newTabConfig.type === 'ssh' ? '#53bdfa' : 'transparent',
                  border: `2px solid ${newTabConfig.type === 'ssh' ? '#53bdfa' : 'var(--border-color)'}`,
                  color: newTabConfig.type === 'ssh' ? '#0a0e14' : 'inherit'
                }}
              >
                🔐 SSH
              </button>
              <button
                onClick={() => setNewTabConfig({...newTabConfig, type: 'ai'})}
                className="halo-button"
                style={{
                  flex: 1,
                  backgroundColor: newTabConfig.type === 'ai' ? '#53bdfa' : 'transparent',
                  border: `2px solid ${newTabConfig.type === 'ai' ? '#53bdfa' : 'var(--border-color)'}`,
                  color: newTabConfig.type === 'ai' ? '#0a0e14' : 'inherit'
                }}
              >
                🤖 AI
              </button>
            </div>
          </div>

          {newTabConfig.type === 'ai' && (
            <>
              <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: 'var(--space-md)', backgroundColor: 'rgba(83, 189, 250, 0.1)', borderRadius: '4px', marginBottom: 'var(--space-md)' }}>
                🤖 <strong>AI Exec:</strong><br/>
                Befehle laufen asynchron im Hintergrund, Ergebnis kommt als JSON (stdout/stderr/exit_code) statt interaktivem Terminal.
                Host optional angeben, um stattdessen per SSH auf einem Zielhost auszuführen (AI SSH Exec) - zuverlässiger als der
                interaktive SSH-Tab für Skripte/mehrzeilige Befehle.
              </div>
              <div style={{ display: 'grid', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
                <input
                  type="text"
                  value={newTabConfig.host}
                  onChange={(e) => setNewTabConfig({...newTabConfig, host: e.target.value})}
                  placeholder="Host (leer = lokal, sonst z.B. 192.168.1.100 für SSH)"
                  className="halo-input"
                  style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                />
                {newTabConfig.host.trim() && (
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-sm)' }}>
                    <input
                      type="text"
                      value={newTabConfig.username}
                      onChange={(e) => setNewTabConfig({...newTabConfig, username: e.target.value})}
                      placeholder="Username (z.B. root)"
                      className="halo-input"
                      style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                    />
                    <input
                      type="text"
                      value={newTabConfig.port}
                      onChange={(e) => setNewTabConfig({...newTabConfig, port: e.target.value})}
                      placeholder="Port"
                      className="halo-input"
                      style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                    />
                  </div>
                )}
              </div>
            </>
          )}

          {newTabConfig.type === 'ssh' && (
            <div style={{ display: 'grid', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
              <input
                type="text"
                value={newTabConfig.host}
                onChange={(e) => setNewTabConfig({...newTabConfig, host: e.target.value})}
                placeholder="Host (z.B. 192.168.1.100)"
                className="halo-input"
                style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-sm)' }}>
                <input
                  type="text"
                  value={newTabConfig.username}
                  onChange={(e) => setNewTabConfig({...newTabConfig, username: e.target.value})}
                  placeholder="Username (z.B. root)"
                  className="halo-input"
                  style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                />
                <input
                  type="text"
                  value={newTabConfig.port}
                  onChange={(e) => setNewTabConfig({...newTabConfig, port: e.target.value})}
                  placeholder="Port"
                  className="halo-input"
                  style={{ padding: 'var(--space-sm)', fontSize: '0.9rem' }}
                />
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
            <button onClick={createNewTab} className="halo-button" style={{ flex: 1 }}>
              ✅ Tab erstellen
            </button>
            <button 
              onClick={() => setShowNewTabConfig(false)} 
              className="halo-button-secondary"
              style={{ flex: 1 }}
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}

      {/* Tab Bar */}
      {tabs.length > 0 && (
        <div className="halo-panel" style={{ 
          padding: '0',
          marginBottom: 'var(--space-md)',
          overflow: 'hidden'
        }}>
          <div style={{ 
            display: 'flex',
            overflowX: 'auto',
            gap: '2px',
            backgroundColor: 'rgba(0,0,0,0.2)',
            padding: 'var(--space-xs)'
          }}>
            {tabs.map(tab => (
              <div
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  backgroundColor: activeTabId === tab.id ? 'var(--panel-background)' : 'rgba(0,0,0,0.3)',
                  border: activeTabId === tab.id ? '2px solid #53bdfa' : '1px solid var(--border-color)',
                  borderRadius: '6px 6px 0 0',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-sm)',
                  minWidth: '150px',
                  transition: 'all 0.2s ease'
                }}
              >
                <span style={{ fontSize: '1rem' }}>{getStatusColor(tab.status)}</span>
                <span className="halo-mono" style={{ 
                  fontSize: '0.85rem',
                  flex: 1,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {tab.name}
                </span>
                <button
                  onClick={(e) => closeTab(tab.id, e)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    lineHeight: '1',
                    padding: '0 var(--space-xs)'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Tab Status */}
      {activeTab && activeTab.type !== 'ai' && activeTab.status === 'connected' && (
        <div className="halo-panel" style={{ 
          marginBottom: 'var(--space-sm)',
          padding: 'var(--space-sm) var(--space-md)',
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-md)'
        }}>
          <span style={{ fontSize: '1rem' }}>🟢</span>
          <div style={{ flex: 1 }}>
            <span className="halo-mono" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {activeTab.type === 'local' ? (
                <>📍 Lokaler Server</>
              ) : (
                <>🌐 SSH → {activeTab.config.username}@{activeTab.config.host}:{activeTab.config.port}</>
              )}
            </span>
          </div>
          <button
            onClick={() => disconnectTab(activeTab.id)}
            className="halo-button-secondary"
            style={{ 
              fontSize: '0.75rem',
              padding: 'var(--space-xs) var(--space-sm)',
              background: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--color-red)',
              border: '1px solid rgba(239, 68, 68, 0.3)'
            }}
          >
            Trennen
          </button>
        </div>
      )}

      {/* Terminal Display */}
      <div className="halo-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {tabs.length === 0 ? (
          <div style={{ 
            padding: 'var(--space-xl)',
            textAlign: 'center',
            color: 'var(--text-secondary)'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: 'var(--space-md)' }}>💻</div>
            <h3 className="halo-header" style={{ fontSize: '1.3rem', marginBottom: 'var(--space-sm)' }}>
              Keine Terminals geöffnet
            </h3>
            <p className="halo-mono" style={{ fontSize: '0.85rem', marginBottom: 'var(--space-lg)' }}>
              Erstelle einen neuen Tab, um zu starten
            </p>
            <button 
              onClick={() => setShowNewTabConfig(true)}
              className="halo-button"
              style={{ fontSize: '1rem', padding: 'var(--space-md) var(--space-xl)' }}
            >
              ➕ Ersten Tab erstellen
            </button>
          </div>
        ) : (
          <div style={{ position: 'relative' }}>
            {tabs.map(tab => (
              <div
                key={tab.id}
                id={`terminal-${tab.id}`}
                style={{
                  width: '100%',
                  height: '650px',
                  padding: tab.type === 'ai' ? 0 : 'var(--space-md)',
                  paddingBottom: tab.type === 'ai' ? 0 : '40px',
                  backgroundColor: '#0a0e14',
                  display: activeTabId === tab.id ? 'block' : 'none',
                  boxSizing: 'border-box',
                  overflow: tab.type === 'ai' ? 'hidden' : 'auto'
                }}
              >
                {tab.type === 'ai' && (
                  <AiExecTab sshTarget={tab.config.host?.trim() ? tab.config : null} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default TerminalTabs;
