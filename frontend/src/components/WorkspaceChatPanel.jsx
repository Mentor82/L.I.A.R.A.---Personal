import { useState, useEffect, useRef, useCallback } from 'react';
import { chatAPI } from '../services/api';
import { streamChatSSE } from '../services/sseClient';
import { getSessionMessages } from '../services/chatService';
import MarkdownMessage from './MarkdownMessage';
import './WorkspaceChatPanel.css';

/**
 * VS Code / code-server Copilot-Style Chat Panel for the Workspace.
 * 
 * Features:
 * - Scoped to the current workspace session with full canonical conversation history.
 * - Context reuse: Automatically detects the currently active editor tab (activeTabData)
 *   and attaches its filename + code as prompt context without manual copy-pasting.
 * - Context badges: Displays active file & context-selected files with easy toggling.
 * - Does NOT create cluttering .md files for normal answers.
 * - Code actions: "In Editor einfügen" & "Kopieren" directly on assistant responses.
 * - Auto-expanding multi-line textarea with Shift+Enter / Enter shortcuts.
 */
export default function WorkspaceChatPanel({
  sessionId,
  activeTab,
  activeTabData,
  files = [],
  onToggleContext,
  onOpenFile,
  onInsertCode,
  onClose,
  onWorkspaceProposal
}) {
  const [messages, setMessages] = useState([]); // [{id, role: 'user'|'assistant', content, contextFile}]
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState(null);
  const [includeActiveFile, setIncludeActiveFile] = useState(true);
  const [showPicker, setShowPicker] = useState(false);
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Model selection (persisted to localStorage)
  const [models, setModels] = useState([]);
  const [model, setModel] = useState(() => localStorage.getItem('liara_selected_model') || 'llama3.2:3b');

  useEffect(() => {
    chatAPI.getModels()
      .then((data) => setModels(data?.models || []))
      .catch(() => setModels([]));
  }, []);

  const changeModel = (value) => {
    setModel(value);
    localStorage.setItem('liara_selected_model', value);
  };

  // Load conversation history for current session
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingHistory(true);
    getSessionMessages(sessionId)
      .then((list) => {
        if (!cancelled) {
          setMessages((list || []).map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content
          })));
        }
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Auto-scroll on new messages or streaming chunks
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  // Auto-adjust textarea height
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const contextFiles = files.filter((f) => f.type === 'file' && f.selected_for_context);

  const sendMessage = async (overridePrompt) => {
    const text = (overridePrompt || input).trim();
    if (!text || sending || !sessionId) return;

    setError(null);
    if (!overridePrompt) setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // Build context payload if active file is attached
    let extraContext = '';
    const attachedFilename = (includeActiveFile && activeTabData?.name) ? activeTabData.name : null;

    if (attachedFilename && activeTabData.content !== undefined) {
      const ext = attachedFilename.split('.').pop() || '';
      extraContext = `Aktuell im Editor geöffnete Datei (${attachedFilename}):\n\`\`\`${ext}\n${activeTabData.content}\n\`\`\``;
    }

    // Add user message with metadata tag
    const userMsg = {
      id: 'usr_' + Date.now(),
      role: 'user',
      content: text,
      contextFile: attachedFilename
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    const assistantMsgId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : 'ws_msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);

    let assistantContent = '';

    const updateAssistantMsg = (newContent) => {
      assistantContent = newContent;
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === assistantMsgId);
        if (idx === -1) {
          return [...prev, { id: assistantMsgId, role: 'assistant', content: assistantContent }];
        }
        const copy = [...prev];
        copy[idx] = { ...copy[idx], content: assistantContent };
        return copy;
      });
    };

    try {
      abortControllerRef.current = new AbortController();

      await streamChatSSE('/api/chat/stream', {
        message: text,
        model,
        session_id: sessionId,
        context: extraContext || undefined
      }, {
        signal: abortControllerRef.current?.signal,
        onEvent: (parsed) => {
          if (parsed.type === 'content') {
            updateAssistantMsg(assistantContent + (parsed.text || ''));
          } else if (parsed.type === 'workspace_artifact') {
            // If any model still emits artifact content, show it inline in the chat
            if (parsed.content) {
              const formatted = `\n\n### ${parsed.title || 'Plan'}\n${parsed.content}\n`;
              updateAssistantMsg(assistantContent + formatted);
            }
          } else if (parsed.type === 'workspace_proposal') {
            onWorkspaceProposal?.();
          }
        }
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        const errorMsg = err.message || 'Fehler bei der Kommunikation mit LIARA.';
        setError(errorMsg);
        setMessages((prev) => [
          ...prev,
          { id: assistantMsgId, role: 'assistant', content: `⚠️ ${errorMsg}` }
        ]);
      }
    } finally {
      setSending(false);
      abortControllerRef.current = null;
    }
  };

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setSending(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleClearHistory = () => {
    if (window.confirm('Möchtest du den Chat-Verlauf in dieser Ansicht leeren?')) {
      setMessages([]);
    }
  };

  // Helper to extract code from assistant markdown and insert into editor
  const handleInsertLatestCode = (content) => {
    if (!onInsertCode) return;
    const match = content.match(/```[\w-]*\n([\s\S]*?)```/);
    if (match && match[1]) {
      onInsertCode(match[1]);
    } else {
      onInsertCode(content);
    }
  };

  const assistantIsReplying = messages.length > 0 && messages[messages.length - 1].role === 'assistant';

  return (
    <aside className="workspace-chat-panel">
      {/* Header */}
      <div className="workspace-chat-header">
        <div className="workspace-chat-title-group">
          <span className="workspace-chat-sparkle">✨</span>
          <span>Copilot Chat</span>
        </div>

        <div className="workspace-chat-header-actions">
          <select
            className="workspace-chat-model-select"
            value={model}
            onChange={(e) => changeModel(e.target.value)}
            title="Modell für Workspace-Chat auswählen"
          >
            {models.length === 0 && <option value={model}>{model}</option>}
            {models.map((m) => (
              <option key={m.name} value={m.name}>{m.name} {m.speed}</option>
            ))}
          </select>

          <button
            className="workspace-chat-icon-btn"
            title="Neuer Chat / Verlauf zurücksetzen"
            onClick={handleClearHistory}
          >
            +
          </button>

          <button
            className="workspace-chat-icon-btn"
            title="Chat-Panel schließen"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Context Attachment Bar (VS Code style) */}
      <div className="workspace-chat-context-bar">
        <div className="workspace-chat-context-chips">
          {/* Active editor file chip */}
          {activeTabData ? (
            <div
              className={`workspace-chat-chip ${includeActiveFile ? 'active' : 'inactive'}`}
              onClick={() => setIncludeActiveFile((v) => !v)}
              title={includeActiveFile ? 'Aktive Datei ist im Kontext (klicken zum Deaktivieren)' : 'Aktive Datei ignorieren (klicken zum Aktivieren)'}
            >
              <span>{includeActiveFile ? '✓' : '○'}</span>
              <span>📄 {activeTabData.name}</span>
              {activeTabData.dirty && <span title="Ungespeicherte Änderungen">●</span>}
            </div>
          ) : (
            <span className="workspace-chat-chip inactive" title="Keine Datei im Editor geöffnet">
              <span>📄 Keine Datei geöffnet</span>
            </span>
          )}

          {/* Additional files selected for workspace context */}
          {contextFiles.map((file) => (
            <div
              key={file.path}
              className="workspace-chat-chip"
              onClick={() => onOpenFile?.(file.path)}
              title={`Datei im Kontext: ${file.path}`}
            >
              <span>📎 {file.name}</span>
              <button
                className="workspace-chat-chip-remove"
                title="Aus Kontext entfernen"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleContext?.(file.path);
                }}
              >
                ✕
              </button>
            </div>
          ))}

          {/* Quick Add Context button */}
          <button
            className="workspace-chat-add-context-btn"
            onClick={() => setShowPicker((v) => !v)}
            title="Workspace-Datei zum Kontext hinzufügen"
          >
            + Kontext
          </button>
        </div>

        {/* Quick Context File Picker Dropdown */}
        {showPicker && (
          <div className="workspace-chat-picker-dropdown">
            {files.filter((f) => f.type === 'file').map((f) => (
              <button
                key={f.path}
                className="workspace-chat-picker-item"
                onClick={() => {
                  onToggleContext?.(f.path);
                  setShowPicker(false);
                }}
              >
                <span>{f.selected_for_context ? '✓' : '+'} {f.path}</span>
                <span style={{ opacity: 0.6, fontSize: '0.7rem' }}>
                  {f.selected_for_context ? 'entfernen' : 'hinzufügen'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="workspace-chat-body" ref={scrollRef}>
        {loadingHistory && <p className="workspace-hint">Lade Verlauf…</p>}

        {!loadingHistory && messages.length === 0 && (
          <div className="workspace-chat-empty">
            <div className="workspace-chat-empty-icon">🤖</div>
            <p className="workspace-chat-empty-title">Wie kann ich dir helfen?</p>
            <p className="workspace-chat-empty-subtitle">
              Stelle Fragen zu deinem Workspace, lass dir Code erklären oder generiere Lösungen.
            </p>

            <div className="workspace-chat-suggestions">
              {activeTabData && (
                <button
                  className="workspace-chat-suggestion-chip"
                  onClick={() => sendMessage(`Erkläre mir den Aufbau und Zweck von ${activeTabData.name}`)}
                >
                  <span>📄</span> {activeTabData.name} erklären
                </button>
              )}
              <button
                className="workspace-chat-suggestion-chip"
                onClick={() => sendMessage("Gibt es in der aktuellen Datei potenzielle Bugs oder Schwachstellen?")}
              >
                <span>🔍</span> Bugs & Schwachstellen finden
              </button>
              <button
                className="workspace-chat-suggestion-chip"
                onClick={() => sendMessage("Schreibe passende Unit-Tests für diesen Code")}
              >
                <span>🧪</span> Unit-Tests generieren
              </button>
              <button
                className="workspace-chat-suggestion-chip"
                onClick={() => sendMessage("Wie kann dieser Code refaktorisiert und optimiert werden?")}
              >
                <span>✨</span> Code refaktorisieren
              </button>
            </div>
          </div>
        )}

        {!loadingHistory && messages.length > 0 && (
          <div className="workspace-chat-messages">
            {messages.map((m, i) => (
              <div key={m.id || i} className={`workspace-chat-message-row ${m.role}`}>
                {m.role === 'user' ? (
                  <>
                    <div className="workspace-chat-message-meta">
                      <span>👤 Du</span>
                      {m.contextFile && (
                        <span className="workspace-chat-context-badge" title="Mit dieser Datei im Kontext gesendet">
                          📄 {m.contextFile}
                        </span>
                      )}
                    </div>
                    <div className="workspace-chat-bubble user">
                      {m.content}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="workspace-chat-message-meta">
                      <span>🤖 Liara</span>
                    </div>
                    <div className="workspace-chat-bubble assistant">
                      <MarkdownMessage content={m.content} sessionId={sessionId} />
                      <div className="workspace-chat-message-actions">
                        <button
                          className="workspace-chat-action-btn"
                          title="Antworttext in die Zwischenablage kopieren"
                          onClick={() => navigator.clipboard?.writeText(m.content)}
                        >
                          📋 Kopieren
                        </button>
                        {onInsertCode && activeTabData && (
                          <button
                            className="workspace-chat-action-btn"
                            title={`Code in ${activeTabData.name} an aktueller Cursor-Position einfügen`}
                            onClick={() => handleInsertLatestCode(m.content)}
                          >
                            📥 In Editor einfügen
                          </button>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}

            {sending && !assistantIsReplying && (
              <div className="workspace-chat-typing-row">
                <span>Liara denkt nach…</span>
                <button className="workspace-chat-stop-btn" onClick={stopGeneration}>
                  ■ Stoppen
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="workspace-error" style={{ margin: '0 0.85rem 0.5rem' }}>
          {error} <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Input Box (Copilot style) */}
      <div className="workspace-chat-input-container">
        <div className="workspace-chat-input-box">
          <textarea
            ref={textareaRef}
            className="workspace-chat-textarea"
            placeholder={activeTabData ? `Frage zu ${activeTabData.name} stellen…` : 'Frage an Liara stellen…'}
            value={input}
            disabled={sending || !sessionId}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <div className="workspace-chat-input-toolbar">
            <div className="workspace-chat-active-indicator">
              {includeActiveFile && activeTabData ? (
                <span title="Aktive Datei wird als Kontext mitgesendet">
                  📄 {activeTabData.name}
                </span>
              ) : (
                <span style={{ opacity: 0.6 }}>Kontext: Session #{sessionId}</span>
              )}
            </div>

            {sending ? (
              <button
                className="workspace-chat-stop-btn"
                onClick={stopGeneration}
                title="Generierung abbrechen"
              >
                ■ Stopp
              </button>
            ) : (
              <button
                className="workspace-chat-send-btn"
                disabled={sending || !input.trim() || !sessionId}
                onClick={() => sendMessage()}
                title="Senden (Enter)"
              >
                <span>Senden</span> ↵
              </button>
            )}
          </div>
        </div>

        <div className="workspace-chat-hints">
          <span>Enter ↵ senden · Shift+Enter ↵ Zeilenumbruch</span>
          <span>Modell: {model}</span>
        </div>
      </div>
    </aside>
  );
}
