import { useState, useEffect, useRef } from 'react';
import { streamChatSSE } from '../services/sseClient';
import { getSessionMessages } from '../services/chatService';
import MarkdownMessage from './MarkdownMessage';

/**
 * Interactive Copilot Chat view for Workspace Copilot Panel.
 * Supports thinking accordions, agent steps, inline file proposals,
 * active editor context, and code insertion actions.
 */
export default function WorkspaceChatView({
  sessionId,
  model,
  activeTab,
  activeTabData,
  files = [],
  onToggleContext,
  onOpenFile,
  onInsertCode,
  onWorkspaceProposal,
  onApproveProposal,
  onRejectProposal,
  transferredMessage,
  onClearTransferredMessage
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState(null);
  const [includeActiveFile, setIncludeActiveFile] = useState(true);
  const [showPicker, setShowPicker] = useState(false);
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);

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
            content: m.content,
            thinking: m.thinking || null,
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

  // Handle incoming transfer from Agent Hub
  useEffect(() => {
    if (transferredMessage) {
      setMessages((prev) => [
        ...prev,
        {
          id: 'user_xfer_' + Date.now(),
          role: 'user',
          content: `[Agent-Aufgabe]: ${transferredMessage.task}`,
        },
        {
          id: 'asst_xfer_' + Date.now(),
          role: 'assistant',
          content: transferredMessage.answer,
        }
      ]);
      onClearTransferredMessage?.();
    }
  }, [transferredMessage, onClearTransferredMessage]);

  // Auto-scroll on new messages or streaming chunks
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

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

    let extraContext = '';
    const attachedFilename = (includeActiveFile && activeTabData?.name) ? activeTabData.name : null;

    if (attachedFilename && activeTabData.content !== undefined) {
      const ext = attachedFilename.split('.').pop() || '';
      extraContext = `Aktuell im Editor geöffnete Datei (${attachedFilename}):\n\`\`\`${ext}\n${activeTabData.content}\n\`\`\``;
    }

    const userMsg = {
      id: 'usr_' + Date.now(),
      role: 'user',
      content: text,
      contextFile: attachedFilename,
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    const assistantMsgId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : 'ws_msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);

    let assistantContent = '';
    let assistantThinking = '';
    let assistantSteps = [];
    let assistantProposals = [];

    const updateAssistantMsg = () => {
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === assistantMsgId);
        const item = {
          id: assistantMsgId,
          role: 'assistant',
          content: assistantContent,
          thinking: assistantThinking || null,
          agentSteps: assistantSteps,
          workspaceProposals: assistantProposals,
        };
        if (idx === -1) {
          return [...prev, item];
        }
        const copy = [...prev];
        copy[idx] = item;
        return copy;
      });
    };

    try {
      abortControllerRef.current = new AbortController();

      await streamChatSSE('/api/chat/stream', {
        message: text,
        model,
        session_id: sessionId,
        context: extraContext || undefined,
      }, {
        signal: abortControllerRef.current?.signal,
        onEvent: (parsed) => {
          if (parsed.type === 'content') {
            assistantContent += (parsed.text || '');
            updateAssistantMsg();
          } else if (parsed.type === 'thinking') {
            assistantThinking += (parsed.text || '');
            updateAssistantMsg();
          } else if (parsed.type === 'agent_steps') {
            assistantSteps = parsed.items || [];
            updateAssistantMsg();
          } else if (parsed.type === 'workspace_proposal') {
            assistantProposals = [...assistantProposals, parsed];
            updateAssistantMsg();
            onWorkspaceProposal?.();
          } else if (parsed.type === 'workspace_artifact') {
            if (parsed.content) {
              const formatted = `\n\n### ${parsed.title || 'Dokument'}\n${parsed.content}\n`;
              assistantContent += formatted;
              updateAssistantMsg();
            }
          }
        },
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        const errorMsg = err.message || 'Fehler bei der Kommunikation mit LIARA.';
        setError(errorMsg);
        setMessages((prev) => [
          ...prev,
          { id: assistantMsgId, role: 'assistant', content: `⚠️ ${errorMsg}` },
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
    <div className="workspace-chat-view">
      {/* Context Attachment Bar */}
      <div className="workspace-chat-context-bar">
        <div className="workspace-chat-context-chips">
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

          <button
            className="workspace-chat-add-context-btn"
            onClick={() => setShowPicker((v) => !v)}
            title="Workspace-Datei zum Kontext hinzufügen"
          >
            + Kontext
          </button>
        </div>

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
              Stelle Fragen zu deinem Code, generiere Lösungen oder lass dir Funktionen erklären.
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
              {[
                { icon: '🔍', label: 'Bugs & Schwachstellen finden', prompt: 'Gibt es in der aktuellen Datei potenzielle Bugs oder Schwachstellen?' },
                { icon: '🧪', label: 'Unit-Tests generieren', prompt: 'Schreibe passende Unit-Tests für diesen Code' },
                { icon: '✨', label: 'Code refaktorisieren', prompt: 'Wie kann dieser Code refaktorisiert und optimiert werden?' }
              ].map((s, idx) => (
                <button
                  key={idx}
                  className="workspace-chat-suggestion-chip"
                  onClick={() => sendMessage(s.prompt)}
                >
                  <span>{s.icon}</span> {s.label}
                </button>
              ))}
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
                      <span>🤖 Liara Copilot</span>
                    </div>
                    <div className="workspace-chat-bubble assistant">
                      {/* Collapsible Thinking Accordion */}
                      {m.thinking && (
                        <details className="workspace-chat-thinking-accordion" open={sending && !m.content}>
                          <summary className="workspace-chat-thinking-summary">
                            <span>🧠 Denkprozess</span>
                            {sending && !m.content && <span className="workspace-chat-thinking-pulse">denkt nach…</span>}
                          </summary>
                          <div className="workspace-chat-thinking-body">
                            <pre>{m.thinking}</pre>
                          </div>
                        </details>
                      )}

                      {/* Executed Agent / Tool Steps */}
                      {m.agentSteps && m.agentSteps.length > 0 && (
                        <div className="workspace-chat-steps-container">
                          <span className="workspace-chat-steps-title">🛠 Ausgeführte Schritte:</span>
                          {m.agentSteps.map((step, idx) => (
                            <div key={idx} className="workspace-chat-step-item">
                              <span>✓</span> {typeof step === 'string' ? step : JSON.stringify(step)}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Main Message Content */}
                      {m.content && (
                        <MarkdownMessage content={m.content} sessionId={sessionId} />
                      )}

                      {/* Inline Workspace Proposals */}
                      {m.workspaceProposals && m.workspaceProposals.map((prop, idx) => (
                        <div key={prop.id || idx} className="workspace-chat-inline-proposal">
                          <div className="workspace-chat-proposal-info">
                            <span className="workspace-chat-proposal-icon">
                              {prop.action === 'create' ? '➕' : prop.action === 'delete' ? '🗑️' : '✏️'}
                            </span>
                            <div>
                              <strong>{prop.filename || 'Datei'}</strong>
                              <span className="workspace-chat-proposal-action">{prop.action || 'Änderung'}</span>
                            </div>
                          </div>
                          <div className="workspace-chat-proposal-actions">
                            {onApproveProposal && prop.id && (
                              <button
                                className="workspace-chat-proposal-btn approve"
                                onClick={() => onApproveProposal(prop.id)}
                              >
                                ✓ Übernehmen
                              </button>
                            )}
                            {onRejectProposal && prop.id && (
                              <button
                                className="workspace-chat-proposal-btn reject"
                                onClick={() => onRejectProposal(prop.id)}
                              >
                                ✕ Ablehnen
                              </button>
                            )}
                          </div>
                        </div>
                      ))}

                      {/* Message Actions */}
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

      {/* Input Box */}
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
    </div>
  );
}
