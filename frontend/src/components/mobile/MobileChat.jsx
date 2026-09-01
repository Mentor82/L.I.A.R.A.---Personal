import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useViewMode } from '../../contexts/ViewModeContext';
import { chatAPI } from '../../services/api';
import { getChatSessions, createChatSession, getSessionMessages, deleteChatSession } from '../../services/chatService';
import { streamChatSSE } from '../../services/sseClient';
import MarkdownMessage from '../MarkdownMessage';
import {
  AgentStepsBlock,
  WebSourcesBlock,
  WorkspaceProposalsBlock,
  WorkspaceArtifactsBlock
} from '../chat/ChatCards';
import liaraLogo from '../../assets/LIARA-LOGO.png';
import { compressAndFormatImage } from '../../utils/imageCompressor';
import './MobileChat.css';

function MobileThinkingBlock({ thinking, isAnswering, labelThinking, labelDone }) {
  const [expanded, setExpanded] = useState(!isAnswering);
  const autoCollapsedRef = useRef(isAnswering);

  useEffect(() => {
    if (isAnswering && !autoCollapsedRef.current) {
      autoCollapsedRef.current = true;
      setExpanded(false);
    }
  }, [isAnswering]);

  if (!thinking) return null;

  return (
    <div className="mobile-thinking-block">
      <button type="button" className="mobile-thinking-toggle" onClick={() => setExpanded((v) => !v)}>
        <span>🧠 {isAnswering ? labelDone : labelThinking}</span>
        <span className="mobile-thinking-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && <div className="mobile-thinking-content">{thinking}</div>}
    </div>
  );
}

export default function MobileChat({ user, onLogout }) {
  const { t } = useTranslation();
  const { setViewMode } = useViewMode();
  const navigate = useNavigate();

  const [message, setMessage] = useState('');
  const [attachedImage, setAttachedImage] = useState(null); // { name, base64, previewUrl }
  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('liara_chat_sessions');
      return saved ? JSON.parse(saved) : [{ id: Date.now(), title: t('mobile.newChat'), messages: [], timestamp: new Date().toISOString() }];
    } catch {
      return [{ id: Date.now(), title: t('mobile.newChat'), messages: [], timestamp: new Date().toISOString() }];
    }
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const saved = localStorage.getItem('liara_active_session');
    return saved ? parseInt(saved, 10) : null;
  });

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('liara_selected_model') || 'llama3.2:3b';
  });

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Load chat sessions from backend/DB on mount
  const loadSessions = useCallback(async () => {
    try {
      const dbSessions = await getChatSessions();
      if (dbSessions && dbSessions.length > 0) {
        const sessions = dbSessions.map((s) => ({
          id: s.id,
          title: s.title,
          messages: [],
          timestamp: s.last_message_time || s.updated_at,
          messageCount: s.message_count || 0,
        }));
        setChatSessions(sessions);

        const savedId = localStorage.getItem('liara_active_session');
        const validActiveId = savedId && sessions.some((s) => s.id === parseInt(savedId, 10))
          ? parseInt(savedId, 10)
          : sessions[0].id;

        setActiveSessionId(validActiveId);
        localStorage.setItem('liara_active_session', validActiveId.toString());

        // Load messages for the active session
        try {
          const msgs = await getSessionMessages(validActiveId);
          setChatSessions((prev) =>
            prev.map((s) => (s.id === validActiveId ? { ...s, messages: msgs } : s))
          );
        } catch (msgErr) {
          console.warn('Could not load session messages:', msgErr);
        }
      }
    } catch (e) {
      console.warn('Could not load sessions from backend:', e);
    }
  }, []);

  // Load available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await chatAPI.getModels();
        if (res?.models && res.models.length > 0) {
          setModels(res.models);
        } else {
          setModels([
            { name: 'llama3.2:3b', speed: '⚡ Schnell', recommended: true },
            { name: 'llama3.2:1b', speed: '⚡⚡ Sehr schnell', recommended: false },
          ]);
        }
      } catch {
        setModels([
          { name: 'llama3.2:3b', speed: '⚡ Schnell', recommended: true },
          { name: 'llama3.2:1b', speed: '⚡⚡ Sehr schnell', recommended: false },
        ]);
      }
    };
    fetchModels();
    loadSessions();
  }, [loadSessions]);

  // Load messages when selecting a session
  const handleSelectSession = async (sessionId) => {
    setActiveSessionId(sessionId);
    localStorage.setItem('liara_active_session', sessionId.toString());
    setDrawerOpen(false);

    const target = chatSessions.find((s) => s.id === sessionId);
    if (target && (!target.messages || target.messages.length === 0)) {
      try {
        const msgs = await getSessionMessages(sessionId);
        setChatSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, messages: msgs } : s))
        );
      } catch (err) {
        console.warn('Failed to load session messages:', err);
      }
    }
  };

  // Auto-scroll on new messages
  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  const activeSession = chatSessions.find((s) => s.id === activeSessionId) || chatSessions[0];
  const messages = activeSession?.messages || [];

  useEffect(() => {
    scrollToBottom(false);
  }, [activeSessionId]);

  useEffect(() => {
    if (generating || loading) {
      scrollToBottom(true);
    }
  }, [messages, generating, loading]);

  // Handle textarea auto-grow
  const handleInputChange = (e) => {
    setMessage(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  // Handle file & image selection
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type.startsWith('image/') || file.name.match(/\.(jpg|jpeg|png|webp|heic|heif|bmp|gif)$/i)) {
      try {
        const compressed = await compressAndFormatImage(file, 1280, 0.82);
        setAttachedImage(compressed);
      } catch (err) {
        console.warn('Image compression fallback:', err);
        const reader = new FileReader();
        reader.onload = (ev) => {
          setAttachedImage({
            name: file.name,
            base64: ev.target.result,
            previewUrl: ev.target.result,
          });
        };
        reader.readAsDataURL(file);
      }
    } else {
      setMessage((prev) => `${prev} [Datei: ${file.name}] `);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          e.preventDefault();
          try {
            const compressed = await compressAndFormatImage(file, 1280, 0.82);
            setAttachedImage(compressed);
          } catch (err) {
            console.warn('Mobile paste image compression fallback:', err);
          }
          break;
        }
      }
    }
  };

  const handleNewChat = async () => {
    try {
      const newSession = await createChatSession(t('mobile.newChat'));
      const sessionObj = {
        id: newSession.id,
        title: newSession.title || t('mobile.newChat'),
        messages: [],
        timestamp: new Date().toISOString(),
      };
      setChatSessions((prev) => [sessionObj, ...prev]);
      setActiveSessionId(newSession.id);
      localStorage.setItem('liara_active_session', newSession.id.toString());
    } catch {
      const localId = Date.now();
      const localSession = { id: localId, title: t('mobile.newChat'), messages: [], timestamp: new Date().toISOString() };
      setChatSessions((prev) => [localSession, ...prev]);
      setActiveSessionId(localId);
      localStorage.setItem('liara_active_session', localId.toString());
    }
    setDrawerOpen(false);
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await deleteChatSession(sessionId);
    } catch {}
    setChatSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId);
      if (filtered.length > 0) {
        if (activeSessionId === sessionId) {
          setActiveSessionId(filtered[0].id);
          localStorage.setItem('liara_active_session', filtered[0].id.toString());
        }
        return filtered;
      }
      const fresh = [{ id: Date.now(), title: t('mobile.newChat'), messages: [], timestamp: new Date().toISOString() }];
      setActiveSessionId(fresh[0].id);
      return fresh;
    });
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    const trimmed = message.trim();
    if ((!trimmed && !attachedImage) || generating || loading) return;

    const textToSend = trimmed || (attachedImage ? 'Beschreibe dieses Bild und erkläre die Details.' : '');
    const imageToSend = attachedImage;
    setAttachedImage(null);

    // Ensure we have an active session id
    let currSessionId = activeSessionId;
    if (!currSessionId) {
      try {
        const fresh = await createChatSession(t('mobile.newChat'));
        currSessionId = fresh.id;
        setActiveSessionId(currSessionId);
        localStorage.setItem('liara_active_session', currSessionId.toString());
        setChatSessions((prev) => [{ id: fresh.id, title: fresh.title, messages: [] }, ...prev]);
      } catch {
        currSessionId = Date.now();
        setActiveSessionId(currSessionId);
        localStorage.setItem('liara_active_session', currSessionId.toString());
      }
    }

    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const timestamp = new Date().toISOString();
    const userMessage = {
      role: 'user',
      content: textToSend,
      timestamp,
      image: imageToSend?.previewUrl,
    };

    const liaraMessage = {
      role: 'assistant',
      content: '',
      thinking: '',
      timestamp,
      model: selectedModel,
      isStreaming: true,
    };

    setChatSessions((prev) =>
      prev.map((s) => {
        if (s.id !== currSessionId) return s;
        return {
          ...s,
          messages: [...(s.messages || []), userMessage, liaraMessage],
        };
      })
    );

    setLoading(true);
    setGenerating(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await streamChatSSE(
        '/api/chat/stream',
        {
          message: textToSend,
          model: selectedModel,
          session_id: currSessionId,
          images: imageToSend ? [imageToSend.base64] : undefined,
        },
        {
          signal: controller.signal,
          onEvent: async (parsed) => {
            if (parsed.type === 'thinking') {
              setLoading(false);
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      thinking: (last.thinking || '') + (parsed.text || ''),
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'content') {
              setLoading(false);
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      content: (last.content || '') + (parsed.text || ''),
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'metadata') {
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      model: parsed.model || last.model,
                      mood: parsed.mood || last.mood,
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'agent_steps') {
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      agentSteps: parsed.items,
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'web_sources') {
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      webSources: parsed.items,
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'workspace_proposal') {
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      workspaceProposals: [...(last.workspaceProposals || []), parsed],
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'workspace_artifact') {
              setChatSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currSessionId) return s;
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = {
                      ...last,
                      workspaceArtifacts: [...(last.workspaceArtifacts || []), parsed],
                    };
                  }
                  return { ...s, messages: msgs };
                })
              );
            } else if (parsed.type === 'done') {
              setLoading(false);
            }
          },
        }
      );
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Chat error:', err);
        setChatSessions((prev) =>
          prev.map((s) => {
            if (s.id !== currSessionId) return s;
            const msgs = [...s.messages];
            const last = msgs[msgs.length - 1];
            if (last && last.role === 'assistant') {
              msgs[msgs.length - 1] = {
                ...last,
                content: `⚠️ Fehler bei der Verbindung: ${err.message || 'Verbindungsabbruch'}`,
              };
            }
            return { ...s, messages: msgs };
          })
        );
      }
    } finally {
      setLoading(false);
      setGenerating(false);
      abortControllerRef.current = null;
      setChatSessions((prev) =>
        prev.map((s) => {
          if (s.id !== currSessionId) return s;
          const msgs = [...s.messages];
          const last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, isStreaming: false };
          }
          return { ...s, messages: msgs };
        })
      );
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    setGenerating(false);
  };

  const filteredSessions = chatSessions.filter((s) =>
    (s.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="mobile-chat-app">
      {/* Topbar (ChatGPT/Copilot Style) */}
      <header className="mobile-topbar">
        <button
          className="mobile-icon-btn"
          onClick={() => setDrawerOpen(true)}
          title={t('mobile.history')}
        >
          ☰
        </button>

        <div className="mobile-model-pill-wrapper">
          <button
            className="mobile-model-pill"
            onClick={() => setModelPickerOpen((v) => !v)}
          >
            <span>{selectedModel.split(':')[0]}</span>
            <span className="mobile-pill-arrow">▾</span>
          </button>

          {modelPickerOpen && (
            <div className="mobile-model-dropdown">
              <div className="mobile-dropdown-header">{t('mobile.model')}</div>
              {models.length === 0 ? (
                <div className="mobile-dropdown-item active">{selectedModel}</div>
              ) : (
                models.map((m) => (
                  <button
                    key={m.name || m}
                    className={`mobile-dropdown-item ${(m.name || m) === selectedModel ? 'active' : ''}`}
                    onClick={() => {
                      const name = m.name || m;
                      setSelectedModel(name);
                      localStorage.setItem('liara_selected_model', name);
                      setModelPickerOpen(false);
                    }}
                  >
                    <span>{m.name || m}</span>
                    {(m.name || m) === selectedModel && <span>✓</span>}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="mobile-topbar-right">
          <button className="mobile-icon-btn" onClick={handleNewChat} title={t('mobile.newChat')}>
            ➕
          </button>
          <button
            className="mobile-icon-btn"
            onClick={() => setMenuOpen((v) => !v)}
            title={t('mobile.settings')}
          >
            ⋮
          </button>

          {menuOpen && (
            <div className="mobile-menu-dropdown">
              <button
                className="mobile-menu-item"
                onClick={() => {
                  setViewMode('desktop');
                  setMenuOpen(false);
                }}
              >
                <span>🖥️</span>
                <span>{t('mobile.switchDesktop')}</span>
              </button>
              <button
                className="mobile-menu-item"
                onClick={() => {
                  navigate('/workspace');
                  setMenuOpen(false);
                }}
              >
                <span>🗂️</span>
                <span>{t('mobile.workspace')}</span>
              </button>
              <button
                className="mobile-menu-item"
                onClick={() => {
                  navigate('/config');
                  setMenuOpen(false);
                }}
              >
                <span>⚙️</span>
                <span>{t('mobile.settings')}</span>
              </button>
              {onLogout && (
                <button
                  className="mobile-menu-item danger"
                  onClick={() => {
                    onLogout();
                    setMenuOpen(false);
                  }}
                >
                  <span>🚪</span>
                  <span>{t('mobile.logout')}</span>
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* History Slide-over Drawer */}
      {drawerOpen && (
        <div className="mobile-drawer-overlay" onClick={() => setDrawerOpen(false)}>
          <aside className="mobile-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-drawer-header">
              <button className="mobile-new-chat-btn" onClick={handleNewChat}>
                <span>➕</span>
                <span>{t('mobile.newChat')}</span>
              </button>
              <button className="mobile-icon-btn" onClick={() => setDrawerOpen(false)}>
                ✕
              </button>
            </div>

            <div className="mobile-drawer-search">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('mobile.searchChats')}
              />
            </div>

            <div className="mobile-drawer-list">
              {filteredSessions.length === 0 ? (
                <div className="mobile-drawer-empty">{t('mobile.noChatsFound')}</div>
              ) : (
                filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    className={`mobile-session-item ${session.id === activeSessionId ? 'active' : ''}`}
                    onClick={() => handleSelectSession(session.id)}
                  >
                    <span className="mobile-session-icon">💬</span>
                    <span className="mobile-session-title">{session.title || t('mobile.newChat')}</span>
                    <button
                      className="mobile-session-delete"
                      onClick={(e) => handleDeleteSession(session.id, e)}
                      title="Löschen"
                    >
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="mobile-drawer-footer">
              <button
                className="mobile-footer-link"
                onClick={() => {
                  setViewMode('desktop');
                  setDrawerOpen(false);
                }}
              >
                <span>🖥️</span>
                <span>{t('mobile.switchDesktop')}</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Messages Feed */}
      <main className="mobile-chat-feed">
        {messages.length === 0 ? (
          <div className="mobile-chat-empty">
            <div className="mobile-empty-logo">
              <img src={liaraLogo} alt="LIARA" className="mobile-empty-logo-img" />
            </div>
            <h2>{t('app.name')}</h2>
            <p>{t('chat.emptyState.subtitle')}</p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === 'user' || msg.sender === 'user';
            const text = msg.content || msg.text || '';
            return (
              <div key={index} className={`mobile-msg-row ${isUser ? 'user-row' : 'assistant-row'}`}>
                {!isUser && (
                  <div className="mobile-msg-avatar">
                    <img src={liaraLogo} alt="LIARA" className="mobile-avatar-img" />
                  </div>
                )}
                <div className={`mobile-msg-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
                  {/* User Uploaded Image Preview */}
                  {isUser && msg.image && (
                    <img src={msg.image} alt="Upload" className="mobile-user-msg-image" />
                  )}

                  {/* Thinking Process if present */}
                  {msg.thinking && (
                    <MobileThinkingBlock
                      thinking={msg.thinking}
                      isAnswering={Boolean(text)}
                      labelThinking={t('mobile.thinking')}
                      labelDone={t('mobile.thinking')}
                    />
                  )}

                  {/* Message Content */}
                  {text ? (
                    <MarkdownMessage content={text} />
                  ) : msg.isStreaming || (loading && index === messages.length - 1) ? (
                    <div className="mobile-typing-indicator">
                      <span />
                      <span />
                      <span />
                    </div>
                  ) : null}

                  {/* Attached Action Cards */}
                  {msg.workspaceArtifacts && <WorkspaceArtifactsBlock artifacts={msg.workspaceArtifacts} />}
                  {msg.workspaceProposals && <WorkspaceProposalsBlock proposals={msg.workspaceProposals} />}
                  {msg.agentSteps && <AgentStepsBlock steps={msg.agentSteps} />}
                  {msg.webSources && <WebSourcesBlock sources={msg.webSources} />}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Floating Bottom Input Pill (ChatGPT/Copilot Style) */}
      <footer className="mobile-bottom-bar">
        {attachedImage && (
          <div className="mobile-attachment-preview-bar">
            <img src={attachedImage.previewUrl} alt="Preview" className="mobile-preview-thumb" />
            <div className="mobile-preview-info">
              <span className="mobile-preview-name">{attachedImage.name}</span>
              <span className="mobile-preview-badge">📷 Gemma Vision Worker</span>
            </div>
            <button
              type="button"
              className="mobile-preview-remove"
              onClick={() => setAttachedImage(null)}
              title="Entfernen"
            >
              ✕
            </button>
          </div>
        )}

        <form className="mobile-input-pill" onSubmit={handleSendMessage}>
          <button
            type="button"
            className="mobile-attach-btn"
            onClick={() => fileInputRef.current?.click()}
            title={t('mobile.uploadFile')}
          >
            📎
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf,.txt,.py,.js,.json"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          <textarea
            ref={textareaRef}
            rows={1}
            value={message}
            onChange={handleInputChange}
            onPaste={handlePaste}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder={attachedImage ? 'Frage zum Bild eingeben...' : t('mobile.inputPlaceholder')}
            className="mobile-textarea"
          />

          {generating || loading ? (
            <button
              type="button"
              className="mobile-send-btn stop"
              onClick={handleStopGeneration}
              title={t('mobile.stop')}
            >
              ⏹
            </button>
          ) : (
            <button
              type="submit"
              disabled={!message.trim() && !attachedImage}
              className="mobile-send-btn send"
              title={t('chat.send')}
            >
              ▲
            </button>
          )}
        </form>
      </footer>
    </div>
  );
}
