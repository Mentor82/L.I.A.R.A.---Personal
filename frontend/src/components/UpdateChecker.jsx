import { useState, useEffect } from 'react';

function UpdateChecker() {
  const [status, setStatus] = useState(null);
  const [patches, setPatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedPatch, setExpandedPatch] = useState(null);

  const authHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
  });

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, patchesRes] = await Promise.all([
        fetch('/api/admin/updater/status', { headers: authHeaders() }),
        fetch('/api/admin/updater/patches', { headers: authHeaders() })
      ]);
      if (!statusRes.ok) throw new Error(`Status HTTP ${statusRes.status}`);
      if (!patchesRes.ok) throw new Error(`Patches HTTP ${patchesRes.status}`);
      setStatus(await statusRes.json());
      setPatches(await patchesRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const formatDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString('de-DE');
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--color-text)' }}>
            🔄 Updates
          </h1>
          <p className="halo-mono" style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            Git-Status gegen origin und vorhandene Patch-Archive
          </p>
        </div>
        <button onClick={fetchStatus} className="halo-button" disabled={loading}>
          {loading ? '⏳ Prüfe...' : '🔄 Prüfen'}
        </button>
      </div>

      {error && (
        <div className="halo-panel" style={{ marginBottom: 'var(--space-lg)', borderColor: '#ea6c73' }}>
          <span style={{ color: '#ea6c73' }}>❌ {error}</span>
        </div>
      )}

      {loading && !status && (
        <div className="halo-panel">
          <p className="halo-mono">Lade Status...</p>
        </div>
      )}

      {status && (
        <div className="halo-panel" style={{ marginBottom: 'var(--space-lg)' }}>
          <h2 className="halo-header" style={{ fontSize: '1.2rem', marginBottom: 'var(--space-md)' }}>
            {status.up_to_date ? '✅ Aktuell' : `⚠️ ${status.behind_count} Commit${status.behind_count === 1 ? '' : 's'} hinter origin/${status.branch}`}
          </h2>

          {status.current_commit && (
            <div className="halo-mono" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
              Aktuell: <code>{status.current_commit.hash}</code> — {status.current_commit.message}
              {' '}({status.current_commit.author}, {formatDate(status.current_commit.date)})
            </div>
          )}

          {status.commits.length > 0 && (
            <div style={{ display: 'grid', gap: 'var(--space-sm)' }}>
              {status.commits.map(c => (
                <div
                  key={c.hash}
                  className="halo-mono"
                  style={{
                    fontSize: '0.85rem',
                    padding: 'var(--space-sm)',
                    background: 'rgba(83, 189, 250, 0.08)',
                    borderRadius: '4px',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  <code style={{ color: '#53bdfa' }}>{c.hash}</code> {c.message}
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
                    {c.author} · {formatDate(c.date)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="halo-panel">
        <h2 className="halo-header" style={{ fontSize: '1.2rem', marginBottom: 'var(--space-md)' }}>
          📦 Patch-Archive ({patches.length})
        </h2>

        {patches.length === 0 && (
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Keine Patches unter patches/ gefunden.
          </p>
        )}

        <div style={{ display: 'grid', gap: 'var(--space-sm)' }}>
          {patches.map(p => (
            <div
              key={p.name}
              style={{
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                overflow: 'hidden'
              }}
            >
              <div
                onClick={() => setExpandedPatch(expandedPatch === p.name ? null : p.name)}
                style={{
                  padding: 'var(--space-sm) var(--space-md)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-sm)',
                  background: 'rgba(0,0,0,0.15)'
                }}
              >
                <span className="halo-mono" style={{ flex: 1, fontSize: '0.85rem' }}>{p.name}</span>
                {p.has_migration && <span title="Enthält SQL-Migration">🗄️</span>}
                {p.has_rollback && <span title="Rollback verfügbar">↩️</span>}
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {expandedPatch === p.name ? '▲' : '▼'}
                </span>
              </div>
              {expandedPatch === p.name && (
                <pre
                  className="halo-mono"
                  style={{
                    margin: 0,
                    padding: 'var(--space-md)',
                    fontSize: '0.75rem',
                    whiteSpace: 'pre-wrap',
                    color: 'var(--text-secondary)',
                    borderTop: '1px solid var(--border-color)'
                  }}
                >
                  {p.info || '(keine PATCH_INFO.txt)'}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default UpdateChecker;
