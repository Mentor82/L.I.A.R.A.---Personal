import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { codeExecAPI } from '../services/api';
import MermaidDiagram from './MermaidDiagram';
import ImageLightbox from './ImageLightbox';
import CodeRunResult from './CodeRunResult';
import './MarkdownMessage.css';

// Languages the "Run" button supports - matches the sandboxed executor's
// language aliases on the backend (app/services/code_sandbox.py).
const RUNNABLE_LANGUAGES = new Set([
  'python', 'py', 'python3', 'python3.11', 'python3.12', 'python3.13', 'python3.14',
  'py311', 'py312', 'py313', 'py314', 'julia', 'jl'
]);

// Matches Mermaid's own first-line diagram declarations - used to recognize
// a diagram in a code fence that has no (or the wrong) language tag, since
// models routinely drop the ```mermaid tag despite writing valid Mermaid
// syntax underneath. Anchored to the start of the trimmed text so it can't
// false-positive on these words appearing later, mid-explanation.
const MERMAID_DIAGRAM_KEYWORDS_RE = /^\s*(flowchart|graph|sequenceDiagram|classDiagram(-v2)?|stateDiagram(-v2)?|erDiagram|journey|gantt|pie|quadrantChart|requirementDiagram|gitGraph|C4(Context|Container|Component|Dynamic|Deployment)|mindmap|timeline|sankey(-beta)?|block-beta|packet-beta|architecture-beta|xychart-beta|kanban)\b/;

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
    let loader = prismLanguageImports[normalized];
    if (!loader && (normalized.startsWith('py') || normalized.startsWith('python'))) {
      loader = prismLanguageImports.python;
    }
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
          // Models routinely write a Mermaid diagram in a fence with no (or
          // the wrong) language tag - confirmed live, a ```-only fence full
          // of `flowchart TD` content rendered as a bare paragraph instead
          // of a diagram, since it never even reached the isMermaid check
          // below (see the inline/no-language early return further down).
          // Sniffing the first real line for a known Mermaid diagram
          // keyword catches that case without needing the model to get the
          // fence tag right.
          const isMermaid = normalizedLanguage === 'mermaid'
            || (!inline && !language && MERMAID_DIAGRAM_KEYWORDS_RE.test(codeText));
          const isRunnable = RUNNABLE_LANGUAGES.has(normalizedLanguage) && !!sessionId;
          const [running, setRunning] = useState(false);
          const [runResult, setRunResult] = useState(null);

          const handleRun = async () => {
            setRunning(true);
            setRunResult(null);
            try {
              let targetLang = normalizedLanguage;
              if (['python', 'py', 'python3'].includes(targetLang)) {
                targetLang = localStorage.getItem('liara_sandbox_python_version') || 'python3.14';
              }
              const result = await codeExecAPI.run(sessionId, targetLang, codeText);
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

          if (isMermaid) {
            return <MermaidDiagram code={codeText} />;
          }

          // If no block or language, render inline code.
          if (inline || !language) {
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
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
          const [lightboxOpen, setLightboxOpen] = useState(false);
          return (
            <div className="markdown-image-wrapper">
              <img
                src={src}
                alt={alt || 'Generiertes Bild'}
                className="markdown-image"
                loading="lazy"
                onClick={() => setLightboxOpen(true)}
                title="Klicken zum Vergrößern"
              />
              {alt && <p className="markdown-image-caption">{alt}</p>}
              {lightboxOpen && (
                <ImageLightbox src={src} alt={alt} onClose={() => setLightboxOpen(false)} />
              )}
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
