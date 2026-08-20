import { useState, useEffect, useRef } from 'react';
import { chatAPI, moodAPI } from '../services/api';
import { getChatSessions, createChatSession, saveChatMessage, getSessionMessages } from '../services/chatService';
import { analyzeSentimentDebounced } from '../services/sentimentService';
import { shouldUseSSE } from '../services/systemLoadService';
import SearchingIndicator from './SearchingIndicator';
import WebSearchResults from './WebSearchResults';
import MarkdownMessage from './MarkdownMessage';
import SentimentIndicator, { SentimentBadge } from './SentimentIndicator';
import { MemoryIndicator, MemoryBadge } from './MemoryIndicator';
import './Chat.css';

function Chat() {
  const [message, setMessage] = useState('');
  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('liara_chat_sessions');
      return saved ? JSON.parse(saved) : [{ id: Date.now(), title: 'Neue Konversation', messages: [], timestamp: new Date().toISOString() }];
    } catch (error) {
      return [{ id: Date.now(), title: 'Neue Konversation', messages: [], timestamp: new Date().toISOString() }];
    }
  });
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const saved = localStorage.getItem('liara_active_session');
    return saved ? parseInt(saved) : chatSessions[0]?.id;
  });
  const [historySidebarOpen, setHistorySidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchIntent, setSearchIntent] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('liara_selected_model') || 'llama3.2:3b';
  });
  const [autoModelSelection, setAutoModelSelection] = useState(() => {
    const saved = localStorage.getItem('liara_auto_model');
    return saved === 'true';
  });
  const [currentMood, setCurrentMood] = useState(null);
  const [liveSentiment, setLiveSentiment] = useState(null);  // Live-Sentiment während Eingabe
  const [memoryContext, setMemoryContext] = useState(null);  // Memory-Context von Neo4j
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  
  const activeSession = chatSessions.find(s => s.id === activeSessionId) || chatSessions[0];
  const messages = activeSession?.messages || [];

  // Auto-scroll zu neuester Nachricht
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    try {
      localStorage.setItem('liara_chat_sessions', JSON.stringify(chatSessions));
      localStorage.setItem('liara_active_session', activeSessionId.toString());
    } catch (error) {
      console.error('Error saving chat sessions:', error);
    }
  }, [chatSessions, activeSessionId]);

  // Speichere Model-Auswahl
  useEffect(() => {
    localStorage.setItem('liara_selected_model', selectedModel);
  }, [selectedModel]);

  // Lade verfügbare Models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await chatAPI.getModels();
        console.log('Models loaded:', data);
        if (data.models && data.models.length > 0) {
          setModels(data.models);
          
          // NUR setze empfohlenes Model wenn User noch KEIN Model gewählt hat
          const savedModel = localStorage.getItem('liara_selected_model');
          if (!savedModel) {
            const recommended = data.models.find(m => m.recommended);
            if (recommended) {
              setSelectedModel(recommended.name);
            }
          }
        } else {
          // Fallback: Zeige zumindest das aktuell ausgewählte Model
          console.warn('No models returned from API, using fallback');
          setModels([
            { name: 'llama3.2:3b', speed: '⚡ Schnell', recommended: true },
            { name: 'llama3.2:1b', speed: '⚡⚡ Sehr schnell', recommended: false }
          ]);
        }
      } catch (error) {
        console.error('Error loading models:', error);
        // Fallback bei Fehler
        setModels([
          { name: 'llama3.2:3b', speed: '⚡ Schnell', recommended: true },
          { name: 'llama3.2:1b', speed: '⚡⚡ Sehr schnell', recommended: false }
        ]);
      }
    };

    fetchModels();
  }, []);

  // Lade aktuellen Mood
  useEffect(() => {
    const fetchMood = async () => {
      try {
        const data = await moodAPI.getStatus();
        setCurrentMood(data.current_mood);
      } catch (error) {
        console.error('Error loading mood:', error);
      }
    };

    fetchMood();
    // Refresh alle 10 Sekunden
    const interval = setInterval(fetchMood, 10000);
    return () => clearInterval(interval);
  }, []);

  // Load chat sessions from database on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const dbSessions = await getChatSessions();
        if (dbSessions && dbSessions.length > 0) {
          // Convert DB sessions to local format
          const sessions = dbSessions.map(s => ({
            id: s.id,
            title: s.title,
            messages: [], // Will be loaded when needed
            timestamp: s.created_at
          }));
          setChatSessions(sessions);
          
          // Set active session to most recent
          const savedActiveId = localStorage.getItem('liara_active_session');
          if (savedActiveId && sessions.find(s => s.id === parseInt(savedActiveId))) {
            setActiveSessionId(parseInt(savedActiveId));
          } else {
            setActiveSessionId(sessions[0].id);
          }
        }
      } catch (error) {
        console.error('Failed to load sessions from DB, using localStorage:', error);
        // Keep localStorage sessions as fallback
      }
    };
    
    loadSessions();
  }, []);

  // Save message to database
  const saveMessageToDB = async (sessionId, messageData) => {
    try {
      await saveChatMessage({
        session_id: sessionId,
        role: messageData.role,
        content: messageData.content,
        model: messageData.model || null,
        mood: messageData.mood || null,
        web_search_results: messageData.webSearchResults || null,
        search_type: messageData.searchType || null,
        risk_score: messageData.riskScore || null,
        action_result: messageData.actionResult || null,
        timestamp: messageData.timestamp
      });
    } catch (error) {
      console.error('Failed to save message to DB:', error);
      // Continue anyway - localStorage has it
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    setSearching(false);
    
    // Add system message about stopped request
    setChatSessions(prev => prev.map(session => 
      session.id === activeSessionId 
        ? { 
            ...session, 
            messages: [...session.messages, {
              role: 'system',
              content: '⚠️ Anfrage wurde abgebrochen.',
              timestamp: new Date().toISOString()
            }]
          }
        : session
    ));
  };

  // Auto-Model-Selection: Wähle optimales Model basierend auf Anfrage
  const selectOptimalModel = (text) => {
    const lower = text.toLowerCase();
    
    // Entscheidungsmatrix
    const matrix = {
      // Komplexe Aufgaben → llama3.2:3b (größeres Model)
      complex: [
        'erkläre', 'explain', 'schreibe', 'write', 'code', 'funktion', 'function',
        'programmier', 'develop', 'erstelle eine', 'create a', 'implementier',
        'analyse', 'analyze', 'vergleiche', 'compare', 'zusammenfass', 'summarize',
        'übersetze', 'translate', 'berechne', 'calculate', 'löse', 'solve'
      ],
      
      // Schnelle Antworten → llama3.2:1b (kleineres Model)
      quick: [
        'hallo', 'hi', 'hey', 'guten tag', 'wie geht', 'danke', 'thanks',
        'ok', 'okay', 'ja', 'yes', 'nein', 'no', 'was ist', 'what is',
        'kurz', 'quick', 'einfach', 'simple'
      ],
      
      // Code-Generierung → llama3.2:3b
      code: [
        'javascript', 'python', 'php', 'html', 'css', 'sql', 'bash',
        'react', 'vue', 'django', 'flask', 'laravel', 'node',
        'class', 'def ', 'function', 'const ', 'let ', 'var '
      ]
    };
    
    // Prüfe Code-Keywords (höchste Priorität)
    if (matrix.code.some(kw => lower.includes(kw))) {
      return 'llama3.2:3b';
    }
    
    // Prüfe komplexe Aufgaben
    if (matrix.complex.some(kw => lower.includes(kw))) {
      return 'llama3.2:3b';
    }
    
    // Prüfe schnelle Anfragen
    if (matrix.quick.some(kw => lower.includes(kw))) {
      return 'llama3.2:1b';
    }
    
    // Länge als Fallback-Kriterium
    // Kurze Messages (<20 Wörter) → schnelles Model
    // Lange Messages (>20 Wörter) → großes Model
    const wordCount = text.split(/\s+/).length;
    return wordCount < 20 ? 'llama3.2:1b' : 'llama3.2:3b';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    // Auto-Model-Selection basierend auf Intent
    let modelToUse = selectedModel;
    if (autoModelSelection) {
      modelToUse = selectOptimalModel(trimmedMessage);
      console.log(`Auto-selected model: ${modelToUse} for message: "${trimmedMessage.substring(0, 50)}..."`);
    }

    // User-Message hinzufügen
    const userMessage = { 
      role: 'user', 
      content: trimmedMessage,
      timestamp: new Date().toISOString()
    };
    
    setChatSessions(prev => prev.map(session => 
      session.id === activeSessionId 
        ? { ...session, messages: [...session.messages, userMessage], timestamp: new Date().toISOString() }
        : session
    ));
    
    // Save user message to DB
    saveMessageToDB(activeSessionId, userMessage);
    
    setLoading(true);
    setSearching(false);
    setSearchIntent(null);
    setMemoryContext(null);  // Reset memory context
    setLiveSentiment(null);  // Reset live sentiment
    setMessage('');

    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();

    try {
      const token = localStorage.getItem('liara_token');
      
      // ⚡ Adaptive SSE: Check system load first
      const useSSE = await shouldUseSSE();
      console.log(`Using ${useSSE ? 'SSE' : 'SYNC'} mode based on system load`);
      
      if (!useSSE) {
        // SYNC MODE: High system load, use traditional request/response
        const response = await fetch('/api/chat/message', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            message: trimmedMessage,
            model: modelToUse
          }),
          signal: abortControllerRef.current.signal
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        
        // Add complete response message
        const liaraMessage = {
          role: 'assistant',
          content: data.response,
          model: data.model_used || modelToUse,
          timestamp: new Date().toISOString(),
          intent: data.intent,
          actionResult: data.action_result,
          mood: data.mood
        };
        
        setChatSessions(prev => prev.map(session => 
          session.id === activeSessionId 
            ? { ...session, messages: [...session.messages, liaraMessage] }
            : session
        ));
        
        saveMessageToDB(activeSessionId, liaraMessage);
        setLoading(false);
        
        // Update mood
        const moodData = await moodAPI.getStatus();
        setCurrentMood(moodData.current_mood);
        
        return;
      }
      
      // SSE MODE: Normal load, use streaming
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: trimmedMessage,
          model: selectedModel
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let liaraMessage = {
        role: 'assistant',
        content: '',
        model: modelToUse,
        timestamp: new Date().toISOString(),
        webSearchResults: null,
        searchType: null,
        riskScore: null
      };
      
      const messageIndex = activeSession.messages.length + 1; // +1 for user message
      let firstChunk = true;  // Flag um doppelte Anzeige zu vermeiden

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'metadata') {
                // Update model info
                liaraMessage.model = parsed.model;
                liaraMessage.mood = parsed.mood;
              } else if (parsed.type === 'memory_context') {
                // ✨ Memory Context from Neo4j
                setMemoryContext(parsed.data);
                liaraMessage.memoryContext = parsed.data;
              } else if (parsed.type === 'action_result') {
                // Action (event/task/note) was executed
                liaraMessage.actionResult = parsed.result;
              } else if (parsed.type === 'web_search') {
                // Show searching indicator
                setSearching(true);
                setSearchIntent(parsed.intent || 'general');
              } else if (parsed.type === 'web_results') {
                // Got search results
                setSearching(false);
                liaraMessage.webSearchResults = parsed.results;
                liaraMessage.searchType = parsed.search_type;
                liaraMessage.riskScore = parsed.risk_score;
              } else if (parsed.type === 'content') {
                // Append content chunk
                liaraMessage.content += parsed.text;
                
                // Beim ersten Chunk: Message hinzufügen, danach nur updaten
                if (firstChunk) {
                  firstChunk = false;
                  setChatSessions(prev => prev.map(session => 
                    session.id === activeSessionId 
                      ? { ...session, messages: [...session.messages, liaraMessage] }
                      : session
                  ));
                } else {
                  // Update message in state
                  setChatSessions(prev => prev.map(session => {
                    if (session.id !== activeSessionId) return session;
                    const newMessages = [...session.messages];
                    newMessages[messageIndex] = { ...liaraMessage };
                    return { ...session, messages: newMessages };
                  }));
                }
              } else if (parsed.type === 'done') {
                setLoading(false);
                setSearching(false);
                
                // Save assistant message to DB
                saveMessageToDB(activeSessionId, liaraMessage);
              } else if (parsed.type === 'error') {
                throw new Error(parsed.error);
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError);
            }
          }
        }
      }

      // Mood könnte sich geändert haben
      const moodData = await moodAPI.getStatus();
      setCurrentMood(moodData.current_mood);

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
        return;
      }
      
      console.error('Chat error:', error);
      setChatSessions(prev => prev.map(session => 
        session.id === activeSessionId 
          ? { 
              ...session, 
              messages: [...session.messages, { 
                role: 'error', 
                content: 'Fehler bei der Kommunikation mit Liara. Ist das Backend erreichbar?',
                timestamp: new Date().toISOString()
              }]
            }
          : session
      ));
    } finally {
      setLoading(false);
      setSearching(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const generateChatTitle = (messages) => {
    if (messages.length === 0) return 'Neue Konversation';
    
    // Finde erste User-Nachricht
    const firstUserMsg = messages.find(m => m.role === 'user');
    if (!firstUserMsg) return 'Neue Konversation';
    
    // Nehme erste 50 Zeichen
    let title = firstUserMsg.content.slice(0, 50);
    
    // Schneide bei Satzende ab, falls vorhanden
    const sentenceEnd = title.search(/[.!?]/);
    if (sentenceEnd > 10) {
      title = title.slice(0, sentenceEnd);
    }
    
    // Füge ... hinzu wenn gekürzt
    if (firstUserMsg.content.length > title.length) {
      title += '...';
    }
    
    return title || 'Neue Konversation';
  };

  // Auto-update Titel nach erster Nachricht
  useEffect(() => {
    if (activeSession && activeSession.messages.length > 0 && activeSession.title.startsWith('Chat ')) {
      const newTitle = generateChatTitle(activeSession.messages);
      setChatSessions(prev => prev.map(session => 
        session.id === activeSessionId 
          ? { ...session, title: newTitle }
          : session
      ));
    }
  }, [activeSession?.messages.length]);

  const clearChat = () => {
    if (confirm('Diese Konversation wirklich löschen?')) {
      setChatSessions(prev => prev.filter(s => s.id !== activeSessionId));
      if (chatSessions.length > 1) {
        const remaining = chatSessions.filter(s => s.id !== activeSessionId);
        setActiveSessionId(remaining[0].id);
      } else {
        const newSession = { id: Date.now(), title: 'Neue Konversation', messages: [], timestamp: new Date().toISOString() };
        setChatSessions([newSession]);
        setActiveSessionId(newSession.id);
      }
    }
  };

  const createNewChat = async () => {
    const title = `Chat ${chatSessions.length + 1}`;
    
    try {
      // Create session in database
      const dbSession = await createChatSession(title);
      
      const newSession = { 
        id: dbSession.id, // Use DB ID
        title: dbSession.title, 
        messages: [], 
        timestamp: dbSession.created_at 
      };
      setChatSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    } catch (error) {
      console.error('Failed to create session in DB, using local only:', error);
      // Fallback: Create local-only session
      const newSession = { 
        id: Date.now(), 
        title, 
        messages: [], 
        timestamp: new Date().toISOString() 
      };
      setChatSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    }
  };

  const switchSession = (sessionId) => {
    setActiveSessionId(sessionId);
    setHistorySidebarOpen(false);
  };

  return (
    <div className="chat-layout">
      {/* Hamburger Menu Button */}
      <button 
        className="hamburger-menu-btn" 
        onClick={() => setHistorySidebarOpen(!historySidebarOpen)}
        aria-label="Chat-Verlauf"
      >
        <span className={historySidebarOpen ? 'open' : ''}></span>
        <span className={historySidebarOpen ? 'open' : ''}></span>
        <span className={historySidebarOpen ? 'open' : ''}></span>
      </button>

      {/* Overlay für Mobile */}
      {historySidebarOpen && (
        <div 
          className="sidebar-overlay" 
          onClick={() => setHistorySidebarOpen(false)}
        />
      )}

      {/* History Sidebar */}
      <div className={`chat-history-sidebar ${historySidebarOpen ? 'open' : ''}`}>
        <div className="history-header">
          <h3>💬 Chat-Verlauf</h3>
          <button onClick={createNewChat} className="btn-new-chat" title="Neue Konversation">
            ➕
          </button>
        </div>
        <div className="history-list">
          {chatSessions.map(session => (
            <div 
              key={session.id}
              className={`history-item ${session.id === activeSessionId ? 'active' : ''}`}
              onClick={() => switchSession(session.id)}
            >
              <div className="history-item-title">{session.title}</div>
              <div className="history-item-meta">
                <span className="history-item-time">
                  {new Date(session.timestamp).toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })}
                </span>
                <span className="history-item-count">
                  {session.messages.length} {session.messages.length === 1 ? 'Nachricht' : 'Nachrichten'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Container */}
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-title">
            <h2>🌙 {activeSession?.title || 'Chat mit Liara'}</h2>
          {currentMood && (
            <span className="chat-mood-indicator">Mood: {currentMood}</span>
          )}
        </div>
        <div className="chat-controls">
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="model-select"
            title="Model auswählen"
            disabled={autoModelSelection}
          >
            {models.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name} {model.speed} {model.recommended ? '⭐' : ''}
              </option>
            ))}
          </select>
          <label className="auto-model-toggle" title="Automatische Modellwahl basierend auf Anfrage">
            <input 
              type="checkbox" 
              checked={autoModelSelection}
              onChange={(e) => {
                setAutoModelSelection(e.target.checked);
                localStorage.setItem('liara_auto_model', JSON.stringify(e.target.checked));
              }}
            />
            <span className="toggle-label">🤖 Auto</span>
          </label>
          {messages.length > 0 && (
            <span className="chat-message-count" title="Nachrichten im Verlauf">
              💬 {messages.length}
            </span>
          )}
          <button onClick={clearChat} className="btn-clear" title="Chat löschen">
            🗑️
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h3>Starte eine Konversation</h3>
            <p>Frag Liara nach Hilfe bei Aufgaben, Code, oder einfach zum Plaudern!</p>
            <div className="example-prompts">
              <button onClick={() => setMessage('Was kannst du alles?')} className="prompt-btn">
                Was kannst du alles?
              </button>
              <button onClick={() => setMessage('Zeige mir meine Tasks')} className="prompt-btn">
                Zeige mir meine Tasks
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message-bubble message-${msg.role}`}>
            <div className="bubble-avatar">
              {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🌙' : '⚠️'}
            </div>
            <div className="bubble-content">
              <div className="bubble-header">
                <span className="bubble-sender">
                  {msg.role === 'user' ? 'Du' : msg.role === 'assistant' ? 'Liara' : 'System'}
                </span>
                <span className="bubble-time">
                  {new Date(msg.timestamp).toLocaleTimeString('de-DE', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
              
              {/* Action Result Badge */}
              {msg.actionResult && (
                <div className={`action-result ${msg.actionResult.success ? 'success' : 'error'}`}>
                  <span className="action-icon">
                    {msg.actionResult.success ? '✅' : '❌'}
                  </span>
                  <span className="action-message">
                    {msg.actionResult.message}
                  </span>
                </div>
              )}
              
              {/* ✨ Memory Context Indicator */}
              {msg.memoryContext && msg.memoryContext.length > 0 && (
                <MemoryIndicator memoryContext={msg.memoryContext} />
              )}
              
              {/* Web Search Results */}
              {msg.webSearchResults && (
                <WebSearchResults 
                  results={msg.webSearchResults}
                  type={msg.searchType}
                  riskScore={msg.riskScore}
                />
              )}
              
              <div className="bubble-text">
                <MarkdownMessage content={msg.content} />
              </div>
              {msg.model && (
                <div className="bubble-footer">
                  <span className="bubble-model">🤖 {msg.model}</span>
                  {msg.mood && <span className="bubble-mood">🌙 {msg.mood}</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {searching && (
          <SearchingIndicator 
            query={message} 
            type={searchIntent}
          />
        )}

        {loading && (
          <div className="message-bubble message-assistant loading-bubble">
            <div className="bubble-avatar thinking">🌙</div>
            <div className="bubble-content">
              <div className="bubble-header">
                <span className="bubble-sender">Liara</span>
                <span className="thinking-status">denkt nach...</span>
              </div>
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        {/* Live-Sentiment-Badge */}
        {liveSentiment && (
          <div className="sentiment-container">
            <SentimentBadge sentiment={liveSentiment} />
          </div>
        )}
        
        {/* Memory-Context-Badge */}
        {memoryContext && memoryContext.length > 0 && (
          <div className="memory-container">
            <MemoryBadge memoryContext={memoryContext} />
          </div>
        )}
        
        <textarea
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            // Live-Sentiment-Analyse mit Debounce
            analyzeSentimentDebounced(e.target.value, (sentiment) => {
              setLiveSentiment(sentiment);
            }, 800);  // 800ms Debounce
          }}
          onKeyPress={handleKeyPress}
          placeholder="Schreibe eine Nachricht... (Enter zum Senden, Shift+Enter für neue Zeile)"
          disabled={loading}
          className="chat-input"
          rows="1"
        />
        {loading ? (
          <button 
            type="button"
            onClick={handleStop}
            className="chat-stop"
            title="Anfrage abbrechen"
          >
            ⬛ Stop
          </button>
        ) : (
          <button 
            type="submit" 
            disabled={!message.trim()} 
            className="chat-submit"
            title="Senden"
          >
            🚀
          </button>
        )}
      </form>
    </div>
    </div>
  );
}

export default Chat;
