import { useState, useRef, useEffect } from 'react';

// AI-friendly terminal tab: plain JSON request/response instead of an
// interactive xterm PTY, so a command's result can be read/verified
// programmatically without simulating keystrokes into a canvas terminal.
//
// sshTarget (optional {host, username, port}): when set, the command runs
// on that remote host via SSH server-side (terminal_exec_router.py's
// ssh_host branch) instead of locally - same reliability benefit as plain
// "AI Exec", now also for the interactive SSH tab's targets, which used to
// be the only way to reach them and suffered from the PTY tab's
// simulated-keystroke multi-line/paste unreliability.
function AiExecTab({ sshTarget = null }) {
  const [history, setHistory] = useState([]);
  const [command, setCommand] = useState('');
  const [sending, setSending] = useState(false);
  const pollTimers = useRef({});
  const scrollRef = useRef(null);

  const authHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('liara_token')}`,
    'Content-Type': 'application/json'
  });

  // Mirrors services/api.js's refresh handling, which this tab's plain
  // fetch() calls don't go through - without this, the access token (60min
  // TTL, see core/security.py) just dies mid-session with a raw 401 and no
  // recovery, since it's never extended by use, only by an explicit refresh.
  const refreshAccessToken = async () => {
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
  };

  // fetch() wrapper: on 401, refresh once and retry with the new token
  // before giving up. authHeaders() is re-evaluated on retry so it picks up
  // the freshly stored token.
  const authFetch = async (url, options = {}) => {
    let res = await fetch(url, { ...options, headers: authHeaders() });
    if (res.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        res = await fetch(url, { ...options, headers: authHeaders() });
      }
    }
    return res;
  };

  useEffect(() => {
    return () => {
      Object.values(pollTimers.current).forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const pollJob = (jobId) => {
    pollTimers.current[jobId] = setTimeout(async () => {
      try {
        const res = await authFetch(`/api/admin/terminal/exec/${jobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const job = await res.json();
        setHistory(prev => prev.map(h => h.job_id === jobId ? job : h));
        if (job.status === 'running') {
          pollJob(jobId);
        }
      } catch (err) {
        setHistory(prev => prev.map(h => h.job_id === jobId
          ? { ...h, status: 'error', stderr: `Polling fehlgeschlagen: ${err.message}` }
          : h
        ));
      }
    }, 1000);
  };

  const sendCommand = async () => {
    const cmd = command.trim();
    if (!cmd || sending) return;
    setSending(true);
    setCommand('');

    try {
      const res = await authFetch('/api/admin/terminal/exec', {
        method: 'POST',
        body: JSON.stringify(sshTarget
          ? { command: cmd, ssh_host: sshTarget.host, ssh_port: sshTarget.port, ssh_user: sshTarget.username }
          : { command: cmd }
        )
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const job = await res.json();
      setHistory(prev => [...prev, job]);
      pollJob(job.job_id);
    } catch (err) {
      setHistory(prev => [...prev, {
        job_id: `error-${Date.now()}`,
        command: cmd,
        status: 'error',
        stderr: err.message,
        stdout: '',
        started_at: new Date().toISOString()
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendCommand();
    }
  };

  const statusBadge = (status) => {
    switch (status) {
      case 'running': return <span style={{ color: '#f9af4f' }}>🟡 läuft...</span>;
      case 'done': return <span style={{ color: '#91b362' }}>🟢 fertig</span>;
      case 'timeout': return <span style={{ color: '#ea6c73' }}>⏱️ Timeout</span>;
      case 'error': return <span style={{ color: '#ea6c73' }}>🔴 Fehler</span>;
      default: return <span>{status}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div
        ref={scrollRef}
        className="halo-mono"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: 'var(--space-md)',
          display: 'grid',
          gap: 'var(--space-md)',
          alignContent: 'start'
        }}
      >
        {history.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {sshTarget ? (
              <>🤖 AI-SSH-Exec-Tab → {sshTarget.username}@{sshTarget.host}:{sshTarget.port} — Befehl unten eingeben und senden.
              Läuft asynchron im Hintergrund (via SSH auf dem Zielhost), Ergebnis erscheint hier als JSON-Antwort statt
              interaktivem Terminal - mehrzeilige Befehle/Heredocs kommen unverändert an.</>
            ) : (
              <>🤖 AI-Exec-Tab — Befehl unten eingeben und senden. Läuft asynchron im Hintergrund,
              Ergebnis erscheint hier als JSON-Antwort statt interaktivem Terminal.</>
            )}
          </div>
        )}
        {history.map(job => (
          <div key={job.job_id} style={{
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: 'var(--space-sm) var(--space-md)',
              background: 'rgba(83, 189, 250, 0.08)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 'var(--space-sm)'
            }}>
              <code style={{ fontSize: '0.85rem' }}>
                {job.ssh_host && <span style={{ color: 'var(--text-secondary)' }}>[{job.ssh_user}@{job.ssh_host}] </span>}
                $ {job.command}
              </code>
              <div style={{ fontSize: '0.75rem', display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
                {statusBadge(job.status)}
                {job.exit_code !== undefined && job.exit_code !== null && (
                  <span style={{ color: 'var(--text-secondary)' }}>exit {job.exit_code}</span>
                )}
              </div>
            </div>
            {(job.stdout || job.stderr) && (
              <pre style={{
                margin: 0,
                padding: 'var(--space-sm) var(--space-md)',
                fontSize: '0.8rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                maxHeight: '300px',
                overflowY: 'auto'
              }}>
                {job.stdout && <span style={{ color: 'var(--text-primary, #b3b1ad)' }}>{job.stdout}</span>}
                {job.stderr && <span style={{ color: '#ea6c73' }}>{job.stdout ? '\n' : ''}{job.stderr}</span>}
              </pre>
            )}
          </div>
        ))}
      </div>

      <div style={{
        display: 'flex',
        gap: 'var(--space-sm)',
        padding: 'var(--space-md)',
        borderTop: '1px solid var(--border-color)'
      }}>
        <textarea
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Befehl eingeben (Enter zum Senden, Shift+Enter für neue Zeile)..."
          className="halo-mono"
          rows={1}
          style={{
            flex: 1,
            resize: 'none',
            padding: 'var(--space-sm)',
            background: 'rgba(0,0,0,0.2)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'inherit',
            fontSize: '0.85rem'
          }}
        />
        <button onClick={sendCommand} disabled={sending || !command.trim()} className="halo-button">
          {sending ? '⏳' : '📤'} Senden
        </button>
      </div>
    </div>
  );
}

export default AiExecTab;
