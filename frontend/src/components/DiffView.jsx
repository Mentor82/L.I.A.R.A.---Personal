import './DiffView.css';

/**
 * Minimal unified-diff renderer - no diff library, matches the existing
 * "stay lean" precedent (CodeMirror over Monaco). Just colors +/-/context
 * lines; hunk headers (@@ ... @@) get their own subtle style.
 */
function DiffView({ diff }) {
  if (!diff) return <p className="diff-empty">Kein Unterschied (leere Datei oder identischer Inhalt).</p>;

  const lines = diff.split('\n');

  return (
    <pre className="diff-view">
      {lines.map((line, i) => {
        let className = 'diff-line-context';
        if (line.startsWith('+++') || line.startsWith('---')) {
          className = 'diff-line-file';
        } else if (line.startsWith('@@')) {
          className = 'diff-line-hunk';
        } else if (line.startsWith('+')) {
          className = 'diff-line-add';
        } else if (line.startsWith('-')) {
          className = 'diff-line-remove';
        }
        return (
          <div key={i} className={className}>{line || ' '}</div>
        );
      })}
    </pre>
  );
}

export default DiffView;
