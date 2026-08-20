import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import { HeadingNode, QuoteNode, $createHeadingNode, $createQuoteNode } from '@lexical/rich-text';
import { ListNode, ListItemNode, INSERT_ORDERED_LIST_COMMAND, INSERT_UNORDERED_LIST_COMMAND } from '@lexical/list';
import { ListPlugin } from '@lexical/react/LexicalListPlugin';
import { CodeNode, CodeHighlightNode } from '@lexical/code';
import { LinkNode } from '@lexical/link';
import { $generateHtmlFromNodes, $generateNodesFromDOM } from '@lexical/html';
import { $getRoot, $insertNodes, $getSelection, $isRangeSelection, $createParagraphNode, FORMAT_TEXT_COMMAND } from 'lexical';
import { $setBlocksType } from '@lexical/selection';
import { useEffect, useState } from 'react';
import './LexicalEditor.css';

// Toolbar Component
function ToolbarPlugin() {
  const [editor] = useLexicalComposerContext();
  const [showPreview, setShowPreview] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');

  const formatText = (format) => {
    editor.dispatchCommand(FORMAT_TEXT_COMMAND, format);
  };

  const formatHeading = (headingTag) => {
    editor.update(() => {
      const selection = $getSelection();
      if ($isRangeSelection(selection)) {
        $setBlocksType(selection, () => $createHeadingNode(headingTag));
      }
    });
  };

  const formatParagraph = () => {
    editor.update(() => {
      const selection = $getSelection();
      if ($isRangeSelection(selection)) {
        $setBlocksType(selection, () => $createParagraphNode());
      }
    });
  };

  const formatQuote = () => {
    editor.update(() => {
      const selection = $getSelection();
      if ($isRangeSelection(selection)) {
        $setBlocksType(selection, () => $createQuoteNode());
      }
    });
  };

  const togglePreview = () => {
    if (!showPreview) {
      editor.getEditorState().read(() => {
        const html = $generateHtmlFromNodes(editor);
        setPreviewHtml(html);
      });
    }
    setShowPreview(!showPreview);
  };

  return (
    <>
      <div className="lexical-toolbar">
        <button
          type="button"
          onClick={() => formatHeading('h1')}
          className="toolbar-btn"
          title="Überschrift 1"
        >
          H1
        </button>
        <button
          type="button"
          onClick={() => formatHeading('h2')}
          className="toolbar-btn"
          title="Überschrift 2"
        >
          H2
        </button>
        <button
          type="button"
          onClick={() => formatHeading('h3')}
          className="toolbar-btn"
          title="Überschrift 3"
        >
          H3
        </button>
        <button
          type="button"
          onClick={formatParagraph}
          className="toolbar-btn"
          title="Normal"
        >
          P
        </button>
        <div className="toolbar-separator" />
        <button
          type="button"
          onClick={() => formatText('bold')}
          className="toolbar-btn"
          title="Fett"
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          onClick={() => formatText('italic')}
          className="toolbar-btn"
          title="Kursiv"
        >
          <em>I</em>
        </button>
        <button
          type="button"
          onClick={() => formatText('underline')}
          className="toolbar-btn"
          title="Unterstrichen"
        >
          <u>U</u>
        </button>
        <button
          type="button"
          onClick={() => formatText('strikethrough')}
          className="toolbar-btn"
          title="Durchgestrichen"
        >
          <s>S</s>
        </button>
        <button
          type="button"
          onClick={() => formatText('code')}
          className="toolbar-btn"
          title="Code"
        >
          {'</>'}
        </button>
        <div className="toolbar-separator" />
        <button
          type="button"
          onClick={() => editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND)}
          className="toolbar-btn"
          title="Aufzählung"
        >
          • Liste
        </button>
        <button
          type="button"
          onClick={() => editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND)}
          className="toolbar-btn"
          title="Nummerierte Liste"
        >
          1. Liste
        </button>
        <button
          type="button"
          onClick={formatQuote}
          className="toolbar-btn"
          title="Zitat"
        >
          " Zitat
        </button>
        <div className="toolbar-separator" />
        <button
          type="button"
          onClick={togglePreview}
          className={`toolbar-btn ${showPreview ? 'active' : ''}`}
          title="Vorschau"
        >
          👁 Vorschau
        </button>
      </div>
      
      {showPreview && (
        <div className="lexical-preview">
          <div className="preview-header">
            <span>Vorschau</span>
            <button onClick={togglePreview} className="preview-close">✕</button>
          </div>
          <div 
            className="preview-content"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        </div>
      )}
    </>
  );
}

// HTML Conversion Plugin
function HtmlPlugin({ initialHtml, onChange }) {
  const [editor] = useLexicalComposerContext();

  // Load initial HTML
  useEffect(() => {
    if (initialHtml) {
      editor.update(() => {
        const parser = new DOMParser();
        const dom = parser.parseFromString(initialHtml, 'text/html');
        const nodes = $generateNodesFromDOM(editor, dom);
        const root = $getRoot();
        root.clear();
        $insertNodes(nodes);
      });
    }
  }, [editor, initialHtml]);

  return (
    <OnChangePlugin
      onChange={(editorState) => {
        editorState.read(() => {
          const html = $generateHtmlFromNodes(editor);
          onChange(html);
        });
      }}
    />
  );
}

// Main Editor Component
export default function LexicalEditor({ value = '', onChange, placeholder = 'Notiz-Inhalt eingeben...' }) {
  const editorConfig = {
    namespace: 'LiaraNotesEditor',
    theme: {
      paragraph: 'lexical-paragraph',
      heading: {
        h1: 'lexical-h1',
        h2: 'lexical-h2',
        h3: 'lexical-h3',
      },
      quote: 'lexical-quote',
      list: {
        ol: 'lexical-ol',
        ul: 'lexical-ul',
        listitem: 'lexical-li',
      },
      text: {
        bold: 'lexical-bold',
        italic: 'lexical-italic',
        underline: 'lexical-underline',
        strikethrough: 'lexical-strikethrough',
        code: 'lexical-code',
      },
      link: 'lexical-link',
      code: 'lexical-code-block',
    },
    nodes: [
      HeadingNode,
      QuoteNode,
      ListNode,
      ListItemNode,
      CodeNode,
      CodeHighlightNode,
      LinkNode,
    ],
    onError(error) {
      console.error('Lexical Editor Error:', error);
    },
  };

  return (
    <LexicalComposer initialConfig={editorConfig}>
      <div className="lexical-editor-container">
        <ToolbarPlugin />
        <div className="lexical-editor-wrapper">
          <RichTextPlugin
            contentEditable={
              <ContentEditable className="lexical-content-editable" />
            }
            placeholder={
              <div className="lexical-placeholder">{placeholder}</div>
            }
            ErrorBoundary={LexicalErrorBoundary}
          />
          <HistoryPlugin />
          <ListPlugin />
          <HtmlPlugin initialHtml={value} onChange={onChange} />
        </div>
      </div>
    </LexicalComposer>
  );
}
