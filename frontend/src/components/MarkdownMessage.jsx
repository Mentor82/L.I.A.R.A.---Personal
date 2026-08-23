import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { codeExecAPI } from '../services/api';
import './MarkdownMessage.css';

// Languages the "Run" button supports - matches the sandboxed executor's
// language aliases on the backend (app/services/code_sandbox.py).
const RUNNABLE_LANGUAGES = new Set(['python', 'py', 'python3', 'julia', 'jl']);

// LLMs commonly write LaTeX using \( \)/\[ \] (common in OpenAI-style
// training data) instead of the $ $/$$ $$ delimiters remark-math expects.
// Without this, those blocks are not just left unstyled - markdown's own
// backslash-escaping strips the backslashes, mangling "\(e\)" into "(e)"
// before it ever reaches the math renderer. Convert to $ syntax first.
const normalizeMathDelimiters = (text) => {
  if (!text) return text;
  return text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expr) => `$$${expr}$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, expr) => `$${expr}$`);
};

// Map of supported languages to on-demand imports so each language stays in its own tiny chunk.
const prismLanguageImports = {
  bash: () => import('react-syntax-highlighter/dist/esm/languages/prism/bash'),
  shell: () => import('react-syntax-highlighter/dist/esm/languages/prism/bash'),
  sh: () => import('react-syntax-highlighter/dist/esm/languages/prism/bash'),
  javascript: () => import('react-syntax-highlighter/dist/esm/languages/prism/javascript'),
  js: () => import('react-syntax-highlighter/dist/esm/languages/prism/javascript'),
  jsx: () => import('react-syntax-highlighter/dist/esm/languages/prism/jsx'),
  typescript: () => import('react-syntax-highlighter/dist/esm/languages/prism/typescript'),
  ts: () => import('react-syntax-highlighter/dist/esm/languages/prism/typescript'),
  tsx: () => import('react-syntax-highlighter/dist/esm/languages/prism/tsx'),
  json: () => import('react-syntax-highlighter/dist/esm/languages/prism/json'),
  python: () => import('react-syntax-highlighter/dist/esm/languages/prism/python'),
  go: () => import('react-syntax-highlighter/dist/esm/languages/prism/go'),
  rust: () => import('react-syntax-highlighter/dist/esm/languages/prism/rust'),
  java: () => import('react-syntax-highlighter/dist/esm/languages/prism/java'),
  c: () => import('react-syntax-highlighter/dist/esm/languages/prism/c'),
  cpp: () => import('react-syntax-highlighter/dist/esm/languages/prism/cpp'),
  csharp: () => import('react-syntax-highlighter/dist/esm/languages/prism/csharp'),
  cs: () => import('react-syntax-highlighter/dist/esm/languages/prism/csharp'),
  php: () => import('react-syntax-highlighter/dist/esm/languages/prism/php'),
  ruby: () => import('react-syntax-highlighter/dist/esm/languages/prism/ruby'),
  kotlin: () => import('react-syntax-highlighter/dist/esm/languages/prism/kotlin'),
  swift: () => import('react-syntax-highlighter/dist/esm/languages/prism/swift'),
  julia: () => import('react-syntax-highlighter/dist/esm/languages/prism/julia'),
  sql: () => import('react-syntax-highlighter/dist/esm/languages/prism/sql'),
  yaml: () => import('react-syntax-highlighter/dist/esm/languages/prism/yaml'),
  yml: () => import('react-syntax-highlighter/dist/esm/languages/prism/yaml'),
  markdown: () => import('react-syntax-highlighter/dist/esm/languages/prism/markdown'),
  md: () => import('react-syntax-highlighter/dist/esm/languages/prism/markdown'),
  html: () => import('react-syntax-highlighter/dist/esm/languages/prism/markup'),
  xml: () => import('react-syntax-highlighter/dist/esm/languages/prism/markup'),
  css: () => import('react-syntax-highlighter/dist/esm/languages/prism/css'),
  scss: () => import('react-syntax-highlighter/dist/esm/languages/prism/scss'),
  less: () => import('react-syntax-highlighter/dist/esm/languages/prism/less'),
  dockerfile: () => import('react-syntax-highlighter/dist/esm/languages/prism/docker'),
  powershell: () => import('react-syntax-highlighter/dist/esm/languages/prism/powershell'),
  ps1: () => import('react-syntax-highlighter/dist/esm/languages/prism/powershell'),
};

// Lazy-load the core highlighter and register languages on demand to keep chunks small.
const useLazySyntax = () => {
  const [syntaxHighlighter, setSyntaxHighlighter] = useState(null);
  const [syntaxStyle, setSyntaxStyle] = useState(null);
  const registeredLanguages = useRef(new Set());

  useEffect(() => {
    let mounted = true;
    Promise.all([
      // The "light" build supports registerLanguage() for the on-demand
      // per-language loading below; the full "prism-async" build bundles
      // every language via refractor/all and throws "Current syntax
      // highlighter doesn't support registration of languages" the moment
      // registerLanguage() is called on it - which was happening on every
      // single code block, silently leaving every one stuck in the plain
      // <pre> fallback since the resulting promise rejection was never
      // caught, so languageReady never flipped to true.
      import('react-syntax-highlighter/dist/esm/prism-async-light'),
      import('react-syntax-highlighter/dist/esm/styles/prism'),
    ]).then(([highlighterModule, styleModule]) => {
      if (!mounted) return;
      const PrismAsync =
        highlighterModule.PrismAsyncLight ||
        highlighterModule.PrismAsync ||
        highlighterModule.default ||
        highlighterModule.Prism;

      setSyntaxHighlighter(() => PrismAsync);
      setSyntaxStyle(styleModule.vscDarkPlus);
    });
    return () => { mounted = false; };
  }, []);

  const ensureLanguage = useCallback(async (language) => {
    if (!language) return false;
    const normalized = language.toLowerCase();

    if (!syntaxHighlighter) return false;
    if (registeredLanguages.current.has(normalized)) return true;

    const loader = prismLanguageImports[normalized];
    if (!loader) return false;

    const mod = await loader();
    if (mod?.default) {
      syntaxHighlighter.registerLanguage(normalized, mod.default);
      registeredLanguages.current.add(normalized);
      return true;
    }

    return false;
  }, [syntaxHighlighter]);

  return { syntaxHighlighter, syntaxStyle, ensureLanguage };
};

let mermaidIdCounter = 0;

// Renders a fenced ```mermaid block as an actual diagram (flowchart, sequence,
// etc.). Mermaid is loaded on demand so chats without diagrams pay nothing.
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

// Result of a "Run" button click: success/error badge (reusing Chat.jsx's
// action-result convention) plus stdout/stderr, inline images, and a
// download-linked list for any other produced files.
const CodeRunResult = ({ result, sessionId }) => {
  const [downloadError, setDownloadError] = useState(null);

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
            onClick={() => window.open(f.inline_base64, '_blank')}
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

const MarkdownMessage = memo(({ content, sessionId }) => {
  const { syntaxHighlighter: SyntaxHighlighter, syntaxStyle, ensureLanguage } = useLazySyntax();
  const normalizedContent = useMemo(() => normalizeMathDelimiters(content), [content]);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        // The `code` renderer below always supplies its own wrapper (a
        // <pre class="code-fallback">, a .code-block-wrapper div, or a
        // mermaid <div>) - without this override, react-markdown's default
        // `pre` wraps that in a second <pre>, nesting <pre><pre>...</pre></pre>.
        pre({ children }) {
          return <>{children}</>;
        },

        // Custom Code Block Renderer
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          const [languageReady, setLanguageReady] = useState(false);
          const normalizedLanguage = language.toLowerCase();
          
          const codeText = String(children).replace(/\n$/, '');
          const isMermaid = normalizedLanguage === 'mermaid';
          const isRunnable = RUNNABLE_LANGUAGES.has(normalizedLanguage) && !!sessionId;
          const [running, setRunning] = useState(false);
          const [runResult, setRunResult] = useState(null);

          const handleRun = async () => {
            setRunning(true);
            setRunResult(null);
            try {
              const result = await codeExecAPI.run(sessionId, normalizedLanguage, codeText);
              setRunResult(result);
            } catch (err) {
              setRunResult({ error: err.message || 'Ausführung fehlgeschlagen.' });
            } finally {
              setRunning(false);
            }
          };

          // Hooks below must run unconditionally on every render of this
          // component instance (Rules of Hooks) - the mermaid branch is
          // handled further down, after all hooks have been called, not
          // via an early return here.
          useEffect(() => {
            let active = true;
            if (!normalizedLanguage) {
              setLanguageReady(false);
              return () => { active = false; };
            }

            ensureLanguage(normalizedLanguage).then((ready) => {
              if (!active) return;
              setLanguageReady(ready);
            }).catch(() => {
              // Falls back to the plain <pre> block below instead of an
              // unhandled rejection silently leaving languageReady stuck
              // at false forever with no visible error.
              if (active) setLanguageReady(false);
            });

            return () => { active = false; };
          }, [ensureLanguage, normalizedLanguage]);

          // If no block or language, render inline code.
          if (inline || !language) {
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
          }

          if (isMermaid) {
            return <MermaidDiagram code={codeText} />;
          }

          // If the highlighter isn't loaded yet, render a simple pre block.
          if (!SyntaxHighlighter || !syntaxStyle || !languageReady) {
            return (
              <pre className="code-fallback" {...props}>
                <code>{codeText}</code>
              </pre>
            );
          }

          return (
            <div className="code-block-wrapper">
              <div className="code-block-header">
                <span className="code-language">{language}</span>
                <span className="code-block-actions">
                  {isRunnable && (
                    <button
                      className="code-run-btn"
                      onClick={handleRun}
                      disabled={running}
                      title="Code ausführen"
                    >
                      {running ? '⏳ Läuft…' : '▶ Ausführen'}
                    </button>
                  )}
                  <button
                    className="code-copy-btn"
                    onClick={() => {
                      navigator.clipboard.writeText(codeText);
                    }}
                    title="Code kopieren"
                  >
                    📋 Kopieren
                  </button>
                </span>
              </div>
              <SyntaxHighlighter
                style={syntaxStyle}
                language={normalizedLanguage}
                PreTag="div"
                className="code-highlighter"
                {...props}
              >
                {codeText}
              </SyntaxHighlighter>
              {running && (
                <div className="code-run-loading">
                  <div className="loading-dots"><span></span><span></span><span></span></div>
                  <span>Wird ausgeführt…</span>
                </div>
              )}
              {runResult && <CodeRunResult result={runResult} sessionId={sessionId} />}
            </div>
          );
        },
        
        // Custom Table Renderer
        table({ children }) {
          return (
            <div className="table-wrapper">
              <table className="markdown-table">{children}</table>
            </div>
          );
        },
        
        // Custom Blockquote Renderer
        blockquote({ children }) {
          return <blockquote className="markdown-blockquote">{children}</blockquote>;
        },
        
        // Custom Link Renderer (open in new tab)
        a({ href, children }) {
          return (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer"
              className="markdown-link"
            >
              {children} 🔗
            </a>
          );
        },
        
        // Custom Heading Renderers
        h1({ children }) {
          return <h1 className="markdown-h1">{children}</h1>;
        },
        h2({ children }) {
          return <h2 className="markdown-h2">{children}</h2>;
        },
        h3({ children }) {
          return <h3 className="markdown-h3">{children}</h3>;
        },
        h4({ children }) {
          return <h4 className="markdown-h4">{children}</h4>;
        },
        
        // Custom List Renderers
        ul({ children }) {
          return <ul className="markdown-ul">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="markdown-ol">{children}</ol>;
        },
        
        // Custom Image Renderer (für generierte Bilder)
        img({ src, alt }) {
          return (
            <div className="markdown-image-wrapper">
              <img 
                src={src} 
                alt={alt || 'Generiertes Bild'} 
                className="markdown-image"
                loading="lazy"
                onClick={() => window.open(src, '_blank')}
                title="Klicken zum Vergrößern"
              />
              {alt && <p className="markdown-image-caption">{alt}</p>}
            </div>
          );
        },
        
        // Custom Paragraph Renderer
        p({ children }) {
          return <p className="markdown-p">{children}</p>;
        }
      }}
    >
      {normalizedContent}
    </ReactMarkdown>
  );
});

MarkdownMessage.displayName = 'MarkdownMessage';

export default MarkdownMessage;
