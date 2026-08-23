import { useState } from 'react';
import { codeExecAPI } from '../services/api';
import ImageLightbox from './ImageLightbox';

// Result of a "Run" button click: success/error badge (reusing Chat.jsx's
// action-result convention) plus stdout/stderr, inline images, and a
// download-linked list for any other produced files. Shared between
// MarkdownMessage.jsx's inline chat run button and WorkspacePage.jsx, so
// both render a run identically instead of duplicating this JSX.
const CodeRunResult = ({ result, sessionId }) => {
  const [downloadError, setDownloadError] = useState(null);
  const [lightboxSrc, setLightboxSrc] = useState(null);

  if (result.error) {
    return (
      <div className="action-result error">
        <span className="action-icon">❌</span>
        <span className="action-message">{result.error}</span>
      </div>
    );
  }

  const success = !result.timed_out && result.exit_code === 0;
  const files = result.files || [];
  const inlineImages = files.filter((f) => f.inline && f.inline_base64);
  const otherFiles = files.filter((f) => !(f.inline && f.inline_base64));

  const handleDownload = async (filename) => {
    try {
      await codeExecAPI.downloadFile(sessionId, filename);
    } catch (err) {
      setDownloadError(err.message || 'Download fehlgeschlagen.');
    }
  };

  return (
    <div className="code-run-result">
      <div className={`action-result ${success ? 'success' : 'error'}`}>
        <span className="action-icon">{success ? '✅' : '❌'}</span>
        <span className="action-message">
          {result.timed_out
            ? 'Zeitüberschreitung - Ausführung abgebrochen.'
            : success
              ? 'Erfolgreich ausgeführt.'
              : `Fehlgeschlagen (Exit-Code ${result.exit_code}).`}
        </span>
      </div>
      {(result.stdout || result.stderr) && (
        <pre className="code-run-output">
          {result.stdout}
          {result.stderr && <span className="code-run-stderr">{result.stderr}</span>}
        </pre>
      )}
      {inlineImages.map((f) => (
        <div className="markdown-image-wrapper" key={f.name}>
          <img
            src={f.inline_base64}
            alt={f.name}
            className="markdown-image"
            onClick={() => setLightboxSrc(f.inline_base64)}
            title="Klicken zum Vergrößern"
          />
          <p className="markdown-image-caption">
            {f.name}{' '}
            <button className="code-file-download-btn" onClick={() => handleDownload(f.name)}>
              ⬇ Download
            </button>
          </p>
        </div>
      ))}
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} alt="Ausführungsergebnis" onClose={() => setLightboxSrc(null)} />
      )}
      {otherFiles.length > 0 && (
        <ul className="code-run-files">
          {otherFiles.map((f) => (
            <li key={f.name}>
              <button className="code-file-download-btn" onClick={() => handleDownload(f.name)}>
                ⬇ {f.name} ({Math.ceil(f.size / 1024)} KB)
              </button>
            </li>
          ))}
        </ul>
      )}
      {downloadError && <div className="action-result error"><span className="action-message">{downloadError}</span></div>}
    </div>
  );
};

export default CodeRunResult;
