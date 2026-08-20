import { useState, useRef, useEffect } from 'react';

// AI-friendly terminal tab: plain JSON request/response instead of an
// interactive xterm PTY, so a command's result can be read/verified
// programmatically without simulating keystrokes into a canvas terminal.
function AiExecTab() {
  const [history, setHistory] = useState([]);
  const [command, setCommand] = useState('');
  const [sending, setSending] = useState(false);
  const pollTimers = useRef({});
  const scrollRef = useRef(null);

  const authHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('liara_token')}`,
    'Content-Type': 'application/json'
  });

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
        const res = await fetch(`/api/admin/terminal/exec/${jobId}`, { headers: authHeaders() });
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
      const res = await fetch('/api/admin/terminal/exec', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ command: cmd })
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        ref={scrollRef}
        className="halo-mono"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--space-md)',
          display: 'grid',
          gap: 'var(--space-md)',
          alignContent: 'start'
        }}
      >
        {history.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            🤖 AI-Exec-Tab — Befehl unten eingeben und senden. Läuft asynchron im Hintergrund,
            Ergebnis erscheint hier als JSON-Antwort statt interaktivem Terminal.
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
              <code style={{ fontSize: '0.85rem' }}>$ {job.command}</code>
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
