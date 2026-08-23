import { useState, useEffect, useRef } from 'react';
import { chatAPI, moodAPI } from '../services/api';
import { getChatSessions, createChatSession, saveChatMessage, getSessionMessages, deleteChatSession } from '../services/chatService';
import { analyzeSentimentDebounced } from '../services/sentimentService';
import { shouldUseSSE } from '../services/systemLoadService';
import SearchingIndicator from './SearchingIndicator';
import WebSearchResults from './WebSearchResults';
import MarkdownMessage from './MarkdownMessage';
import SentimentIndicator, { SentimentBadge } from './SentimentIndicator';
import { MemoryIndicator, MemoryBadge } from './MemoryIndicator';
import './Chat.css';

// Collapsible display for reasoning-model output (deepseek-r1 etc.), kept
// separate from the answer by the backend's thinking_splitter. Auto-expanded
// while the answer hasn't started yet (so the user sees it "thinking" live),
// then auto-collapses once - after that, the user's own toggle sticks.
function ThinkingBlock({ thinking, isAnswering }) {
  const [expanded, setExpanded] = useState(true);
  const autoCollapsedRef = useRef(false);

  useEffect(() => {
    if (isAnswering && !autoCollapsedRef.current) {
      autoCollapsedRef.current = true;
      setExpanded(false);
    }
  }, [isAnswering]);

  if (!thinking) return null;

  return (
    <div className="thinking-block">
      <button type="button" className="thinking-toggle" onClick={() => setExpanded((e) => !e)}>
        <span>🧠 {isAnswering ? 'Denkprozess' : 'Denkt nach…'}</span>
        <span className="thinking-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && <div className="thinking-content">{thinking}</div>}
    </div>
  );
}

// Collapsible checklist from the model's <tasks> block(s) - see
// task_splitter.py. This is a MODEL-AUTHORED plan display, not a verified
// execution record: a checked item only means the model claims to have
// covered that step in its own text, not that anything actually ran. Stays
// expanded by default and doesn't auto-collapse like ThinkingBlock does -
// watching it update as the model re-emits a fresher state is the point.
function TaskListBlock({ tasks }) {
  const [expanded, setExpanded] = useState(true);

  if (!tasks || tasks.length === 0) return null;

  return (
    <div className="task-list-block">
      <button type="button" className="task-list-toggle" onClick={() => setExpanded((e) => !e)}>
        <span>📋 Aufgaben</span>
        <span className="task-list-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <ul className="task-list-content">
          {tasks.map((item) => (
            <li key={item.id} className={`task-list-item ${item.done ? 'done' : ''}`}>
              <input type="checkbox" checked={item.done} disabled readOnly />
              <span>{item.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

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
  const [isSending, setIsSending] = useState(false); // Mehrfachklick-Schutz
  const [errorMessage, setErrorMessage] = useState('');
  const [chatToDelete, setChatToDelete] = useState(null);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchIntent, setSearchIntent] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('liara_selected_model') || 'llama3.2:3b';
  });
  const [autoModelSelection, setAutoModelSelection] = useState(() => {
    const saved = localStorage.getItem('liara_auto_model');
    return saved ? JSON.parse(saved) : false;
  });
  const [currentMood, setCurrentMood] = useState(null);
  const [liveSentiment, setLiveSentiment] = useState(null);  // Live-Sentiment während Eingabe
  const [memoryContext, setMemoryContext] = useState(null);  // Memory-Context von Neo4j
  const [selectedImage, setSelectedImage] = useState(null);  // Hochgeladenes Bild
  const [imagePreview, setImagePreview] = useState(null);    // Bild-Vorschau URL
  const [hailoTask, setHailoTask] = useState('detect');       // hailo task: detect|pose|segment
  const [hailoModel, setHailoModel] = useState('yolov8n');    // hailo model selection
  const [hailoConfidence, setHailoConfidence] = useState(0.5); // hailo confidence (detect only)
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const fileInputRef = useRef(null);
  const isSendingRef = useRef(false);  // Atomarer Flag gegen Race Conditions
  // Guards against the mount-time session loader (loadSessions, below)
  // clobbering a session the user explicitly created/switched to in the
  // meantime - both are async and unordered, so without this, whichever one
  // resolves last wins and silently reinstates the old conversation history
  // on top of a just-created "new chat".
  const sessionActionTakenRef = useRef(false);
  
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
        // The user already created/switched a session while this was in
        // flight - applying this stale result now would silently revert
        // them back to whatever was previously active.
        if (sessionActionTakenRef.current) return;
        if (dbSessions && dbSessions.length > 0) {
          // Convert DB sessions to local format with preview
          const sessions = dbSessions.map(s => ({
            id: s.id,
            title: s.title,
            messages: [], // Will be loaded when needed
            timestamp: s.last_message_time || s.updated_at,
            messageCount: s.message_count || 0,
            lastMessage: s.last_message || null
          }));
          setChatSessions(sessions);

          // Set active session to most recent and load its messages
          const savedActiveId = localStorage.getItem('liara_active_session');
          const activeId = (savedActiveId && sessions.find(s => s.id === parseInt(savedActiveId)))
            ? parseInt(savedActiveId)
            : sessions[0].id;

          setActiveSessionId(activeId);

          // Load messages for active session
          if (activeId && sessions.find(s => s.id === activeId)?.messageCount > 0) {
            try {
              const messages = await getSessionMessages(activeId);
              if (sessionActionTakenRef.current) return;
              setChatSessions(prev => prev.map(s =>
                s.id === activeId ? { ...s, messages } : s
              ));
            } catch (error) {
              console.error('Failed to load active session messages:', error);
            }
          }
        } else {
          // The DB is the source of truth. An empty result here must
          // replace whatever local/localStorage state we started with -
          // otherwise a browser previously used by a different account
          // keeps showing that account's cached sessions indefinitely,
          // since nothing else would ever clear them for an account
          // that genuinely has zero sessions of its own.
          //
          // This must be a real DB session, not a client-only Date.now()
          // id: saveMessageToDB() posts to /chat/messages/ with the active
          // session's id, and that endpoint 404s (silently, since the
          // failure is only logged, never surfaced) when the id doesn't
          // exist in chat_sessions - so a fake local id would let a user's
          // very first conversation look fine in the UI while never
          // actually being persisted.
          const dbSession = await createChatSession('Neue Konversation');
          if (sessionActionTakenRef.current) return;
          const freshSession = { id: dbSession.id, title: dbSession.title, messages: [], timestamp: dbSession.created_at };
          setChatSessions([freshSession]);
          setActiveSessionId(freshSession.id);
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
    console.log('[Chat] Stop button pressed - aborting request');
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // UI-State komplett zurücksetzen
    setLoading(false);
    setSearching(false);
    setIsSending(false);
    setSearchIntent(null);
    
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

    // 🔍 FRONTEND DEBUG LOG: Function entry
    const timestamp = new Date().toISOString();
    console.log(`[FRONTEND_LOG] ${timestamp} - SUBMIT_ENTER - Message: "${trimmedMessage}" | isSendingRef: ${isSendingRef.current}`);

    // 🚨 ATOMARER Mehrfachklick-Schutz mit useRef (kein Race Condition)
    if (isSendingRef.current) {
      console.log(`[FRONTEND_LOG] ${timestamp} - SUBMIT_BLOCKED - Duplicate submission prevented`);
      console.log('[Chat] Request already in progress (atomic check), ignoring duplicate submit');
      return;
    }
    
    // Setze Flag SOFORT (atomar)
    isSendingRef.current = true;
    setIsSending(true);
    console.log(`[FRONTEND_LOG] ${timestamp} - SUBMIT_PROCEED - Flag set, starting request`);

    // 🚨 KRITISCH: Abbrechen aller laufenden Requests BEVOR neuer Request startet
    if (abortControllerRef.current) {
      console.log('[Chat] Aborting previous request');
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

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

    setLoading(true);
    setSearching(false);
    setSearchIntent(null);
    setMemoryContext(null);  // Reset memory context
    setLiveSentiment(null);  // Reset live sentiment
    setMessage('');

    // Create NEW abort controller for THIS request
    abortControllerRef.current = new AbortController();
    const requestAbortController = abortControllerRef.current;

    try {
      const token = localStorage.getItem('liara_token');
      
      // ⚡ Adaptive SSE: Check system load first
      const useSSE = await shouldUseSSE();
      console.log(`[Chat] Using ${useSSE ? 'SSE' : 'SYNC'} mode based on system load`);
      console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_MODE - Using ${useSSE ? 'SSE' : 'SYNC'}`);
      
      if (!useSSE) {
        // ====== SYNC MODE: High system load, use traditional request/response ======
        console.log('[Chat] SYNC MODE: Using /api/chat/message');
        console.log(`[FRONTEND_LOG] ${timestamp} - HTTP_START - Sending POST to /api/chat/message`);

        // /chat/message (chat.py) doesn't persist messages server-side like
        // /chat/stream now does, so this path still needs to save it itself.
        saveMessageToDB(activeSessionId, userMessage);

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
          signal: requestAbortController.signal
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
          toolResult: data.tool_result,  // Tool-Call Ergebnis
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
      
      // ====== SSE MODE: Normal load, use streaming ======
      console.log('[Chat] SSE MODE: Using /api/chat/stream');
      console.log(`[FRONTEND_LOG] ${timestamp} - SSE_START - Connecting to /api/chat/stream`);
      
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: trimmedMessage,
          model: modelToUse,
          // Without this, the backend could never tell which session a
          // message belonged to and created a brand-new orphaned session
          // for every single message instead of continuing this one.
          session_id: activeSessionId
        }),
        signal: requestAbortController.signal
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
      
      let messageAdded = false;  // Track ob Message bereits hinzugefügt wurde

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
              } else if (parsed.type === 'thinking') {
                // Reasoning-model output (deepseek-r1 etc.) - kept separate
                // from liaraMessage.content so it renders as its own
                // collapsible block instead of leaking into the answer text.
                liaraMessage.thinking = (liaraMessage.thinking || '') + parsed.text;

                if (!messageAdded) {
                  messageAdded = true;
                  setLoading(false);
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? { ...session, messages: [...session.messages, liaraMessage] }
                      : session
                  ));
                } else {
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? { ...session, messages: [...session.messages.slice(0, -1), liaraMessage] }
                      : session
                  ));
                }
              } else if (parsed.type === 'tasks') {
                // Model-authored plan checklist (see task_splitter.py) - each
                // event carries the FULL current state, so it replaces
                // liaraMessage.tasks wholesale rather than accumulating like
                // 'thinking' does.
                liaraMessage.tasks = parsed.items;

                if (!messageAdded) {
                  messageAdded = true;
                  setLoading(false);
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? { ...session, messages: [...session.messages, liaraMessage] }
                      : session
                  ));
                } else {
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? { ...session, messages: [...session.messages.slice(0, -1), liaraMessage] }
                      : session
                  ));
                }
              } else if (parsed.type === 'content') {
                // Append content chunk
                liaraMessage.content += parsed.text;

                // Beim ersten Content: Message hinzufügen und Loading-Indikator
                // ausblenden - sonst läuft die "denkt nach..."-Bubble parallel
                // zur bereits sichtbaren, live wachsenden Antwort weiter, bis
                // der komplette Stream fertig ist.
                if (!messageAdded) {
                  messageAdded = true;
                  setLoading(false);
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? { ...session, messages: [...session.messages, liaraMessage] }
                      : session
                  ));
                } else {
                  // Update: Ersetze die LETZTE Message im Array
                  setChatSessions(prev => prev.map(session =>
                    session.id === activeSessionId
                      ? {
                          ...session,
                          messages: [
                            ...session.messages.slice(0, -1),  // Alle außer letzte
                            liaraMessage  // Neue Version der letzten Message
                          ]
                        }
                      : session
                  ));
                }
              } else if (parsed.type === 'done') {
                setLoading(false);
                setSearching(false);
                // /chat/stream now persists both sides of the exchange
                // itself (see chat_streaming.py) - saving it again here
                // duplicated the message with a NULL user_id.
              } else if (parsed.type === 'persisted') {
                // Fires once the DB write actually commits, separately from
                // (and slightly after) 'done' - 'done' only means Ollama
                // finished generating, not that the reply is safely saved
                // yet. Tracked on the message for now (e.g. future "still
                // saving" UI); not surfaced visually yet.
                liaraMessage.persisted = parsed.success;
                setChatSessions(prev => prev.map(session =>
                  session.id === activeSessionId
                    ? { ...session, messages: [...session.messages.slice(0, -1), liaraMessage] }
                    : session
                ));
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
        console.log('[Chat] Request aborted by user');
        console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_ABORTED`);
        return;
      }
      
      console.error('[Chat] Error:', error);
      console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_ERROR - ${error.message}`);
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
      console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_COMPLETE - Cleanup started`);
      setLoading(false);
      setSearching(false);
      setIsSending(false); // Gebe Sende-Flag frei
      isSendingRef.current = false; // 🚨 ATOMARER Reset (kein Race Condition)
      
      // Cleanup: Nur wenn es DIESER Request war
      if (abortControllerRef.current === requestAbortController) {
        abortControllerRef.current = null;
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      // Trigger form submit event (verhindert doppelte Ausführung)
      e.target.form.requestSubmit();
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
    setChatToDelete(activeSession);
  };

  const confirmClearChat = async () => {
    if (!chatToDelete) return;
    const sessionIdToDelete = chatToDelete.id;
    setChatToDelete(null);

    try {
      // Delete from database
      await deleteChatSession(sessionIdToDelete);

      // Remove from local state
      setChatSessions(prev => prev.filter(s => s.id !== sessionIdToDelete));

      // Switch to another session or create new one
      if (chatSessions.length > 1) {
        const remaining = chatSessions.filter(s => s.id !== sessionIdToDelete);
        setActiveSessionId(remaining[0].id);
      } else {
        // Create new session
        await createNewChat();
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
      setErrorMessage('Fehler beim Löschen des Chats');
    }
  };

  const handleCopyMessage = async (content, index) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageIndex(index);
      setTimeout(() => setCopiedMessageIndex(prev => (prev === index ? null : prev)), 1500);
    } catch (error) {
      console.error('Failed to copy message:', error);
      setErrorMessage('Kopieren fehlgeschlagen');
    }
  };

  const createNewChat = async () => {
    sessionActionTakenRef.current = true;
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

  const switchSession = async (sessionId) => {
    sessionActionTakenRef.current = true;
    setActiveSessionId(sessionId);
    setHistorySidebarOpen(false);
    
    // Load messages for this session if not already loaded
    const session = chatSessions.find(s => s.id === sessionId);
    if (session && (!session.messages || session.messages.length === 0)) {
      try {
        const messages = await getSessionMessages(sessionId);
        setChatSessions(prev => prev.map(s => 
          s.id === sessionId ? { ...s, messages } : s
        ));
      } catch (error) {
        console.error('Failed to load messages:', error);
      }
    }
  };

  // 🖼️ Bild-Upload Handler
  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validierung
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Bitte nur Bilddateien hochladen (JPG, PNG, WEBP)');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('Bild zu groß. Maximum: 10 MB');
      return;
    }

    // Setze Bild und erstelle Vorschau
    setSelectedImage(file);
    const previewUrl = URL.createObjectURL(file);
    setImagePreview(previewUrl);
  };

  // Hailo Vision Modelle pro Task
  const hailoModelOptions = {
    detect: ['yolov8n', 'yolov8s', 'yolov10n', 'yolov11n'],
    pose: ['yolov8s_pose'],
    segment: ['yolov5n_seg', 'yolov5s_seg']
  };

  const handleHailoTaskChange = (task) => {
    setHailoTask(task);
    const options = hailoModelOptions[task];
    if (options && !options.includes(hailoModel)) {
      setHailoModel(options[0]);
    }
  };

  const removeImage = () => {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImageAnalysis = async () => {
    if (!selectedImage || !message.trim()) {
      setErrorMessage('Bitte Bild auswählen und Frage eingeben');
      return;
    }

    setLoading(true);
    setIsSending(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedImage);
      formData.append('message', message.trim());

      const token = localStorage.getItem('liara_token');
      const response = await fetch('/api/vision/chat', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Vision API error: ${response.status}`);
      }

      const data = await response.json();

      // User message mit Bild-Indikator
      const userMessage = {
        role: 'user',
        content: message.trim(),
        timestamp: new Date().toISOString(),
        hasImage: true,
        imagePreview: imagePreview
      };

      // Liara response
      const liaraMessage = {
        role: 'assistant',
        content: data.response,
        model: data.model_used || 'llava:7b',
        timestamp: new Date().toISOString(),
        isVisionResponse: true
      };

      // Add both messages
      setChatSessions(prev => prev.map(session =>
        session.id === activeSessionId
          ? { ...session, messages: [...session.messages, userMessage, liaraMessage] }
          : session
      ));

      // Save to DB
      saveMessageToDB(activeSessionId, userMessage);
      saveMessageToDB(activeSessionId, liaraMessage);

      // Reset
      setMessage('');
      removeImage();

    } catch (error) {
      console.error('Image analysis failed:', error);
      setErrorMessage('Bildanalyse fehlgeschlagen: ' + error.message);
    } finally {
      setLoading(false);
      setIsSending(false);
    }
  };

  const handleHailoVision = async () => {
    if (!selectedImage) {
      setErrorMessage('Bitte ein Bild auswählen');
      return;
    }

    setLoading(true);
    setIsSending(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedImage);

      const token = localStorage.getItem('liara_token');
      const params = new URLSearchParams();
      params.append('model', hailoModel);
      if (hailoTask === 'detect') {
        params.append('confidence', hailoConfidence);
      }

      const endpointMap = {
        detect: '/api/hailo/vision/detect',
        pose: '/api/hailo/vision/pose',
        segment: '/api/hailo/vision/segment'
      };

      const endpoint = endpointMap[hailoTask] || endpointMap.detect;
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const response = await fetch(`${endpoint}?${params.toString()}` , {
        method: 'POST',
        headers,
        body: formData
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Hailo API error ${response.status}: ${text}`);
      }

      const data = await response.json();

      const userMessage = {
        role: 'user',
        content: message.trim() || `Bildanalyse (Hailo ${hailoTask}, ${hailoModel})`,
        timestamp: new Date().toISOString(),
        hasImage: true,
        imagePreview: imagePreview
      };

      const assistantContent = data.output
        ? data.output
        : JSON.stringify(data, null, 2);

      const hailoMessage = {
        role: 'assistant',
        content: assistantContent,
        model: `hailo:${hailoModel}`,
        timestamp: new Date().toISOString(),
        isVisionResponse: true,
        hailoTask,
        rpi5Status: data.rpi5_status
      };

      setChatSessions(prev => prev.map(session =>
        session.id === activeSessionId
          ? { ...session, messages: [...session.messages, userMessage, hailoMessage] }
          : session
      ));

      saveMessageToDB(activeSessionId, userMessage);
      saveMessageToDB(activeSessionId, hailoMessage);

      setMessage('');
      removeImage();
    } catch (error) {
      console.error('Hailo Vision failed:', error);
      setErrorMessage('Hailo Vision fehlgeschlagen: ' + error.message);
    } finally {
      setLoading(false);
      setIsSending(false);
    }
  };

  return (
    <div className="chat-layout">
      {errorMessage && (
        <div className="chat-error-banner" onClick={() => setErrorMessage('')}>
          ⚠️ {errorMessage} <span className="chat-banner-dismiss">✕</span>
        </div>
      )}

      {/* Sidebar Toggle Tab */}
      <button 
        className={`sidebar-toggle-tab ${historySidebarOpen ? 'open' : ''}`}
        onClick={() => setHistorySidebarOpen(!historySidebarOpen)}
        aria-label="Chat-Verlauf"
      >
        <span className="sidebar-toggle-icon">➤</span>
      </button>

      {/* Overlay für Mobile */}
      {historySidebarOpen && (
        <div 
          className="sidebar-overlay active" 
          onClick={() => setHistorySidebarOpen(false)}
        />
      )}

      {/* History Sidebar - Hover to reveal */}
      <div 
        className={`chat-history-sidebar ${historySidebarOpen ? 'open' : ''}`}
      >
        <div className="history-header">
          <h3>💬 Chat-Verlauf</h3>
          <button onClick={createNewChat} className="btn-new-chat" title="Neue Konversation">
            ➕
          </button>
        </div>
        <div className="history-list">
          {chatSessions.map(session => {
            const hasMessages = session.messageCount > 0 || (session.messages && session.messages.length > 0);
            const messageCount = session.messageCount || session.messages?.length || 0;
            
            return (
              <div 
                key={session.id}
                className={`history-item ${session.id === activeSessionId ? 'active' : ''}`}
                onClick={() => switchSession(session.id)}
              >
                <div className="history-item-header">
                  <div className="history-item-title">{session.title}</div>
                  <span className="history-item-time">
                    {new Date(session.timestamp).toLocaleDateString('de-DE', { 
                      day: '2-digit', 
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                
                {hasMessages ? (
                  <>
                    {session.lastMessage && (
                      <div className="history-item-preview">
                        {session.lastMessage}
                      </div>
                    )}
                    <div className="history-item-count">
                      💬 {messageCount} {messageCount === 1 ? 'Nachricht' : 'Nachrichten'}
                    </div>
                  </>
                ) : (
                  <div className="history-item-empty">
                    Neue Konversation – noch keine Nachrichten
                  </div>
                )}
              </div>
            );
          })}
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
                const value = e.target.checked;
                setAutoModelSelection(value);
                localStorage.setItem('liara_auto_model', JSON.stringify(value));
              }}
            />
            <span className="toggle-label">🤖 Auto</span>
          </label>
          {messages.length > 0 && (
            <span className="chat-message-count" title="Nachrichten im Verlauf">
              💬 {messages.length}
            </span>
          )}
          <button onClick={createNewChat} className="btn-new-chat" title="Neue Konversation">
            ➕
          </button>
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
                <span className="bubble-header-right">
                  <span className="bubble-time">
                    {new Date(msg.timestamp).toLocaleTimeString('de-DE', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                  <button
                    type="button"
                    className="bubble-copy-btn"
                    onClick={() => handleCopyMessage(msg.content, index)}
                    title="Nachricht kopieren"
                  >
                    {copiedMessageIndex === index ? '✅' : '📋'}
                  </button>
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
              
              {/* 🔧 Tool Call Indicator */}
              {msg.toolResult && (
                <div className={`tool-result ${msg.toolResult.success ? 'success' : 'error'}`}>
                  <span className="tool-icon">
                    {msg.toolResult.tool === 'web_search' && '🔍'}
                    {msg.toolResult.tool === 'get_weather' && '🌤️'}
                    {msg.toolResult.tool === 'detect_location' && '📍'}
                    {msg.toolResult.tool === 'wikipedia_search' && '📖'}
                    {msg.toolResult.tool === 'get_current_time' && '🕐'}
                    {!['web_search', 'get_weather', 'detect_location', 'wikipedia_search', 'get_current_time'].includes(msg.toolResult.tool) && '🔧'}
                  </span>
                  <span className="tool-name">
                    {msg.toolResult.tool === 'web_search' && 'Web-Suche'}
                    {msg.toolResult.tool === 'get_weather' && 'Wetter'}
                    {msg.toolResult.tool === 'detect_location' && 'Standort'}
                    {msg.toolResult.tool === 'wikipedia_search' && 'Wikipedia'}
                    {msg.toolResult.tool === 'get_current_time' && 'Uhrzeit'}
                    {!['web_search', 'get_weather', 'detect_location', 'wikipedia_search', 'get_current_time'].includes(msg.toolResult.tool) && msg.toolResult.tool}
                  </span>
                  {msg.toolResult.execution_time_ms !== undefined && (
                    <span className="tool-time">⚡ {msg.toolResult.execution_time_ms}ms</span>
                  )}
                </div>
              )}
              
              {/* Web Search Results */}
              {msg.webSearchResults && (
                <WebSearchResults 
                  results={msg.webSearchResults}
                  type={msg.searchType}
                  riskScore={msg.riskScore}
                />
              )}
              
              {/* When an action succeeded, its confirmation text is already
                  shown above via the styled action-result badge - the
                  backend puts the identical message in msg.content too
                  (chat.py: response=action_result['message']), so showing
                  both duplicated the same line twice in the same bubble. */}
              {msg.role === 'assistant' && (
                <ThinkingBlock thinking={msg.thinking} isAnswering={!!msg.content} />
              )}
              {msg.role === 'assistant' && (
                <TaskListBlock tasks={msg.tasks} />
              )}
              {!msg.actionResult?.success && (
                <div className="bubble-text">
                  <MarkdownMessage content={msg.content} sessionId={activeSessionId} />
                </div>
              )}
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

        {/* 🖼️ Bild-Vorschau */}
        {imagePreview && (
          <div className="image-preview-container">
            <img 
              src={imagePreview} 
              alt="Upload Preview" 
              className="image-preview"
            />
            <button 
              type="button"
              onClick={removeImage}
              className="remove-image-btn"
              title="Bild entfernen"
            >
              ❌
            </button>
            <div className="image-info">
              📸 {selectedImage?.name} ({(selectedImage?.size / 1024).toFixed(0)} KB)
            </div>
            <div className="vision-model-hint">
              ℹ️ Bildanalyse läuft immer über llava:7b bzw. Hailo-8L – die Modellauswahl oben gilt nur für Text-Chats.
            </div>
          </div>
        )}

        {/* Hailo Vision Einstellungen */}
        {selectedImage && (
          <div className="hailo-vision-controls">
            <div className="hailo-control">
              <label>Task</label>
              <select
                value={hailoTask}
                onChange={(e) => handleHailoTaskChange(e.target.value)}
                disabled={loading}
              >
                <option value="detect">Object Detection</option>
                <option value="pose">Pose Estimation</option>
                <option value="segment">Instance Segmentation</option>
              </select>
            </div>

            <div className="hailo-control">
              <label>Modell</label>
              <select
                value={hailoModel}
                onChange={(e) => setHailoModel(e.target.value)}
                disabled={loading}
              >
                {hailoModelOptions[hailoTask].map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            {hailoTask === 'detect' && (
              <div className="hailo-control">
                <label>Confidence</label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={hailoConfidence}
                  onChange={(e) => setHailoConfidence(parseFloat(e.target.value) || 0.5)}
                  disabled={loading}
                />
              </div>
            )}
          </div>
        )}
        
        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageSelect}
          accept="image/*"
          style={{ display: 'none' }}
        />

        <div className="chat-input-wrapper">
          {/* 🖼️ Bild-Upload Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="image-upload-btn"
            title="Bild hochladen"
            disabled={loading}
          >
            📎
          </button>

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
            placeholder={selectedImage ? "Beschreibe das Bild oder stelle eine Frage..." : "Schreibe eine Nachricht... (Enter zum Senden, Shift+Enter für neue Zeile)"}
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
          ) : selectedImage ? (
            <div className="vision-actions">
              <button
                type="button"
                onClick={handleImageAnalysis}
                disabled={!message.trim()}
                className="chat-submit vision-submit"
                title="LLM-Bildanalyse (llava:7b, unabhängig vom oben gewählten Modell)"
              >
                🖼️ LLM
              </button>
              <button
                type="button"
                onClick={handleHailoVision}
                disabled={loading}
                className="chat-submit vision-submit hailo-submit"
                title="Hailo-8L Vision (dediziertes NPU-Backend, unabhängig vom oben gewählten Modell)"
              >
                ⚡ Hailo
              </button>
            </div>
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
        </div>
      </form>
    </div>

    {/* Delete Confirmation Modal - not window.confirm(), which some
        browsers silently suppress after repeated dialogs, leaving the
        delete button looking like it does nothing */}
    {chatToDelete && (
      <div className="chat-modal-overlay" onClick={() => setChatToDelete(null)}>
        <div className="chat-modal" onClick={(e) => e.stopPropagation()}>
          <div className="chat-modal-header">
            <h3>Chat löschen?</h3>
            <button type="button" className="chat-modal-close-btn" onClick={() => setChatToDelete(null)}>
              ✕
            </button>
          </div>
          <div className="chat-modal-body">
            <p>Möchtest du "<strong>{chatToDelete.title}</strong>" wirklich löschen?</p>
          </div>
          <div className="chat-form-actions">
            <button type="button" className="chat-btn-secondary" onClick={() => setChatToDelete(null)}>
              Abbrechen
            </button>
            <button type="button" className="chat-btn-danger" onClick={confirmClearChat}>
              Löschen
            </button>
          </div>
        </div>
      </div>
    )}
    </div>
  );
}

export default Chat;
