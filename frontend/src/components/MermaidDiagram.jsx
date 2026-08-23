import { memo, useEffect, useRef, useState } from 'react';

let mermaidIdCounter = 0;

// Renders a mermaid diagram (flowchart, sequence, etc.) from source text.
// Mermaid is loaded on demand so pages/messages without diagrams pay
// nothing. Originally lived inline in MarkdownMessage.jsx (chat-only);
// extracted so ArchitecturePage.jsx can reuse the same rendering technique
// for standalone diagrams outside of chat.
const MermaidDiagram = memo(({ code }) => {
  const [svg, setSvg] = useState(null);
  const [error, setError] = useState(null);
  const idRef = useRef(`mermaid-${++mermaidIdCounter}`);

  useEffect(() => {
    let active = true;
    setSvg(null);
    setError(null);

    import('mermaid').then(async ({ default: mermaid }) => {
      if (!active) return null;
      const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
      mermaid.initialize({ startOnLoad: false, theme: isDark ? 'dark' : 'default', securityLevel: 'strict' });

      // mermaid.render() resolves with a rendered "bomb" error SVG for
      // invalid syntax instead of rejecting - which fires on every partial
      // code block while the message is still streaming in. Validate first
      // so an incomplete/invalid block quietly falls back to plain text
      // (retried automatically as `code` grows) instead of flashing an
      // alarming error graphic mid-stream.
      const valid = await mermaid.parse(code, { suppressErrors: true });
      if (!valid) return null;

      return mermaid.render(idRef.current, code);
    }).then((result) => {
      if (!active) return;
      if (!result) {
        setError('pending');
        return;
      }
      setSvg(result.svg);
    }).catch((err) => {
      if (!active) return;
      setError(err?.message || 'Diagramm konnte nicht gerendert werden.');
    });

    return () => { active = false; };
  }, [code]);

  if (error) {
    return (
      <pre className="code-fallback">
        <code>{code}</code>
      </pre>
    );
  }

  if (!svg) {
    return <div className="mermaid-loading">Diagramm wird gerendert…</div>;
  }

  // eslint-disable-next-line react/no-danger -- mermaid.render output, securityLevel 'strict' sanitizes it
  return <div className="mermaid-diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
});
MermaidDiagram.displayName = 'MermaidDiagram';

export default MermaidDiagram;
