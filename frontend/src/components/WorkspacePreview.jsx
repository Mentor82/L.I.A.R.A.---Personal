import { useState } from 'react';
import { workspaceAPI } from '../services/api';
import './WorkspacePreview.css';

// Common dev-server default ports, offered as quick picks rather than
// making the user look one up - Vite (5173) is the most likely first guess
// given this exists to make `npm run dev`-style workflows viewable, but a
// plain `python3 -m http.server` or a custom Express app are just as valid.
const PORT_PRESETS = [
  { port: 5173, label: 'Vite' },
  { port: 3000, label: 'Node/React' },
  { port: 8000, label: 'http.server' },
  { port: 8080, label: 'sonstiges' },
];

export default function WorkspacePreview({ sessionId, onClose }) {
  const [insidePort, setInsidePort] = useState(5173);
  const [status, setStatus] = useState('idle'); // idle | starting | running | error
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  // Bumped on every reload click - changing an <iframe>'s key forces React
  // to remount it (a plain src reassignment to the same URL is a no-op),
  // the standard way to force-refresh an iframe's content.
  const [reloadNonce, setReloadNonce] = useState(0);

  const start = async () => {
    setStatus('starting');
    setError(null);
    try {
      const result = await workspaceAPI.startPreview(sessionId, insidePort);
      setPreviewUrl(result.preview_url);
      setStatus('running');
    } catch (err) {
      setError(err.message || 'Preview konnte nicht gestartet werden.');
      setStatus('error');
    }
  };

  const stop = async () => {
    try {
      await workspaceAPI.stopPreview(sessionId);
    } catch {
      // Best-effort - the daemon also self-terminates after its own idle
      // timeout even if this call fails, so there's nothing to recover here.
    }
    setPreviewUrl(null);
    setStatus('idle');
  };

  const reload = () => setReloadNonce((n) => n + 1);

  return (
    <div className="workspace-preview-panel">
      <div className="workspace-preview-header">
        <span className="workspace-preview-title">🌐 Live Preview</span>

        {status !== 'running' ? (
          <div className="workspace-preview-start-row">
            <select
              className="workspace-preview-port-select"
              value={insidePort}
              onChange={(e) => setInsidePort(Number(e.target.value))}
              disabled={status === 'starting'}
              title="Port, auf dem der Dev-Server im Workspace-Terminal läuft"
            >
              {PORT_PRESETS.map((p) => (
                <option key={p.port} value={p.port}>{p.port} ({p.label})</option>
              ))}
            </select>
            <input
              type="number"
              className="workspace-preview-port-input"
              value={insidePort}
              onChange={(e) => setInsidePort(Number(e.target.value) || 0)}
              disabled={status === 'starting'}
              min={1}
              max={65535}
              title="Eigenen Port eingeben"
            />
            <button
              className="workspace-btn-primary workspace-preview-start-btn"
              onClick={start}
              disabled={status === 'starting' || !insidePort}
            >
              {status === 'starting' ? '…' : '▶ Preview starten'}
            </button>
          </div>
        ) : (
          <div className="workspace-preview-running-row">
            <span className="workspace-preview-port-tag">Port {insidePort}</span>
            <button className="workspace-icon-btn" onClick={reload} title="Neu laden">🔄</button>
            <a
              className="workspace-icon-btn"
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="In neuem Tab öffnen"
            >↗</a>
            <button className="workspace-btn-danger-sm" onClick={stop} title="Preview stoppen">■ Stop</button>
          </div>
        )}

        <button className="workspace-icon-btn" onClick={onClose} title="Preview ausblenden">✕</button>
      </div>

      <div className="workspace-preview-body">
        {status === 'running' && previewUrl && (
          <iframe
            key={reloadNonce}
            className="workspace-preview-iframe"
            src={previewUrl}
            title="Workspace Live Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        )}

        {status !== 'running' && (
          <div className="workspace-preview-empty">
            <div className="workspace-preview-empty-icon">🌐</div>
            <p className="workspace-preview-empty-title">Noch keine Preview aktiv</p>
            <p className="workspace-preview-empty-subtitle">
              Erst im Terminal-Tab einen Dev-Server starten (z.B. <code>npm run dev</code> oder{' '}
              <code>python3 -m http.server 8000</code>), dann hier den passenden Port wählen und starten.
            </p>
            {error && <p className="workspace-error workspace-preview-error">{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
