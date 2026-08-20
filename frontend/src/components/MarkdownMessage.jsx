import { memo, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MarkdownMessage.css';

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
      import('react-syntax-highlighter/dist/esm/prism-async'),
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

const MarkdownMessage = memo(({ content }) => {
  const { syntaxHighlighter: SyntaxHighlighter, syntaxStyle, ensureLanguage } = useLazySyntax();

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Custom Code Block Renderer
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          const [languageReady, setLanguageReady] = useState(false);
          const normalizedLanguage = language.toLowerCase();
          
          const codeText = String(children).replace(/\n$/, '');

          useEffect(() => {
            let active = true;
            if (!normalizedLanguage) {
              setLanguageReady(false);
              return () => { active = false; };
            }

            ensureLanguage(normalizedLanguage).then((ready) => {
              if (!active) return;
              setLanguageReady(ready);
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
                <button 
                  className="code-copy-btn"
                  onClick={() => {
                    navigator.clipboard.writeText(codeText);
                  }}
                  title="Code kopieren"
                >
                  📋 Kopieren
                </button>
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
      {content}
    </ReactMarkdown>
  );
});

MarkdownMessage.displayName = 'MarkdownMessage';

export default MarkdownMessage;
