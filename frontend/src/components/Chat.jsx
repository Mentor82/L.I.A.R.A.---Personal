import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { chatAPI, moodAPI } from '../services/api';
import { chatArchiveAPI } from '../services/chatArchiveService';
import { getChatSessions, createChatSession, getSessionMessages, deleteChatSession, updateMessageTaskItem } from '../services/chatService';
import { streamChatSSE } from '../services/sseClient';
import WebSearchResults from './WebSearchResults';
import MarkdownMessage from './MarkdownMessage';
import SentimentIndicator, { SentimentBadge } from './SentimentIndicator';
import { MemoryIndicator, MemoryBadge } from './MemoryIndicator';
import liaraLogo from '../assets/LIARA-LOGO.png';
import { compressAndFormatImage } from '../utils/imageCompressor';
import './Chat.css';

// Collapsible display for reasoning-model output (deepseek-r1 etc.), kept
// separate from the answer by the backend's thinking_splitter. Auto-expanded
// while the answer hasn't started yet (so the user sees it "thinking" live),
// then auto-collapses once - after that, the user's own toggle sticks.
function ThinkingBlock({ thinking, isAnswering }) {
  const [expanded, setExpanded] = useState(!isAnswering);
  const autoCollapsedRef = useRef(isAnswering);

  useEffect(() => {
    if (isAnswering && !autoCollapsedRef.current) {
      autoCollapsedRef.current = true;
      // One-time auto-collapse latch - no render-time equivalent, since after
      // this the user's own manual toggle must be free to override `expanded`.
      // eslint-disable-next-line react-hooks/set-state-in-effect
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

import {
  TaskListBlock,
  AgentStepsBlock,
  WebSourcesBlock,
  ImageResultsBlock,
  FactCheckBlock,
  WorkspaceProposalsBlock,
  WorkspaceArtifactsBlock,
  ChatBubbleFooter,
  SessionContextBar
} from './chat/ChatCards';
import {
  AGENT_STEP_ICON,
  formatSourceDate,
  FACTCHECK_ICON,
  PROPOSAL_ACTION_LABELS
} from './chat/chatCardHelpers';
import { analyzeSentimentDebounced } from '../services/sentimentService';

function Chat() {
  const [message, setMessage] = useState('');
  const [chatSessions, setChatSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('liara_chat_sessions');
      return saved ? JSON.parse(saved) : [{ id: Date.now(), title: 'Neue Konversation', messages: [], timestamp: new Date().toISOString() }];
    } catch {
      return [{ id: Date.now(), title: 'Neue Konversation', messages: [], timestamp: new Date().toISOString() }];
    }
  });
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const saved = localStorage.getItem('liara_active_session');
    return saved ? parseInt(saved) : chatSessions[0]?.id;
  });
  const [historySidebarOpen, setHistorySidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  // Separate from `loading`: `loading` only covers the gap before the FIRST
  // SSE event of any kind arrives and disappears the moment one does. Once
  // that happens, whether anything visibly updates again depends entirely
  // on which event types the model happens to emit - a reasoning model that
  // shows its "decide to search" thinking but then composes the final
  // answer with no further thinking/content tokens for a stretch left the
  // whole bubble looking frozen with no sign it was still working. This
  // stays true for the entire request (set with `loading`, cleared with it
  // in the same finally block) so a persistent indicator can be shown on
  // whichever message is currently being generated, independent of which
  // specific sub-block last updated.
  const [generating, setGenerating] = useState(false);
  // How long since the last SSE event of any kind before the UI tells the
  // user this is taking unusually long - distinct from `generating`, which
  // only says "still open," not "still open and quiet for a suspicious
  // while." Observed live: a request can sit with zero events for minutes
  // under heavy server load (CPU-bound local inference contending with
  // other concurrent requests) with no error and no content - from the
  // user's seat that's indistinguishable from "broken" unless something
  // says otherwise.
  const STALL_THRESHOLD_MS = 45000;
  const [stalled, setStalled] = useState(false);
  const lastActivityRef = useRef(Date.now());
  const [, setIsSending] = useState(false); // Mehrfachklick-Schutz
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
  // Real, post-compaction prompt size for the active session's most recent
  // turn (from the SSE 'metadata' event's context_tokens/context_limit) -
  // SessionContextBar prefers this over its own client-side sum-over-all-
  // messages estimate, which never reflected that server-side compaction
  // keeps the actual prompt bounded. null until the first turn in this
  // session has round-tripped since page load, and reset on session switch
  // so a stale reading from a different session's model/limit never shows.
  const [contextInfo, setContextInfo] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);  // Hochgeladenes Bild
  const [selectedImageBase64, setSelectedImageBase64] = useState(null); // Base64 für Vision
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
  const [isArchiving, setIsArchiving] = useState(false);
  const [archiveBanner, setArchiveBanner] = useState(null);
  
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

  // Polls (not a single timeout) so a late-arriving event within the
  // request's own lifetime clears `stalled` again via the touch in the SSE
  // loop above - the request isn't given up on, this is purely informational.
  useEffect(() => {
    if (!generating) return undefined;
    const interval = setInterval(() => {
      if (Date.now() - lastActivityRef.current > STALL_THRESHOLD_MS) {
        setStalled(true);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [generating]);

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

  // Catch-all for activeSessionId changing via any path (new session,
  // mount-time restore, etc.) - switchSession's own explicit reset above
  // covers the common case, this covers the rest so a stale reading from a
  // different session's model/limit never lingers.
  useEffect(() => {
    setContextInfo(null);
  }, [activeSessionId]);

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
          // id: the chat/vision/hailo-vision endpoints persist server-side
          // using this session_id, and silently skip persistence (only
          // logged, never surfaced) when the id doesn't exist in
          // chat_sessions - so a fake local id would let a user's very
          // first conversation look fine in the UI while never actually
          // being persisted.
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

  const handleArchiveToWorkspace = async () => {
    if (!activeSessionId) return;
    setIsArchiving(true);
    try {
      const res = await chatArchiveAPI.archiveToWorkspace(activeSessionId);
      if (res && res.ok) {
        setArchiveBanner({ type: 'success', text: `💾 ${res.message || 'Erfolgreich im Workspace archiviert'}` });
        setTimeout(() => setArchiveBanner(null), 5000);
      }
    } catch (err) {
      console.error('Archivierung fehlgeschlagen:', err);
      setArchiveBanner({ type: 'error', text: `Archivierung fehlgeschlagen: ${err.message || err}` });
      setTimeout(() => setArchiveBanner(null), 5000);
    } finally {
      setIsArchiving(false);
    }
  };

  const handleExportMarkdown = async () => {
    if (!activeSessionId) return;
    try {
      await chatArchiveAPI.exportSession(activeSessionId, 'markdown');
      setArchiveBanner({ type: 'success', text: '⬇️ Markdown-Export heruntergeladen' });
      setTimeout(() => setArchiveBanner(null), 4000);
    } catch (err) {
      console.error('Export fehlgeschlagen:', err);
      setArchiveBanner({ type: 'error', text: `Export fehlgeschlagen: ${err.message || err}` });
      setTimeout(() => setArchiveBanner(null), 5000);
    }
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
    
    const currentImageBase64 = selectedImageBase64;
    const currentImagePreview = imagePreview;
    const trimmedMessage = message.trim() || (currentImageBase64 ? 'Beschreibe dieses Bild und erkläre die Details.' : '');
    if (!trimmedMessage) return;

    // Reset image preview state
    removeImage();

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
      timestamp: new Date().toISOString(),
      hasImage: Boolean(currentImageBase64),
      imagePreview: currentImagePreview
    };
    
    setChatSessions(prev => prev.map(session =>
      session.id === activeSessionId
        ? { ...session, messages: [...session.messages, userMessage], timestamp: new Date().toISOString() }
        : session
    ));

    setLoading(true);
    setGenerating(true);
    lastActivityRef.current = Date.now();
    setStalled(false);
    setSearching(false);
    setSearchIntent(null);
    setMemoryContext(null);  // Reset memory context
    setLiveSentiment(null);  // Reset live sentiment
    setMessage('');

    // Create NEW abort controller for THIS request
    abortControllerRef.current = new AbortController();
    const requestAbortController = abortControllerRef.current;

    // Generate unique ID for this assistant streaming message
    const assistantMessageId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : 'msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);

    let liaraMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      model: modelToUse,
      timestamp: new Date().toISOString(),
      webSearchResults: null,
      searchType: null,
      riskScore: null
    };

    let messageAdded = false;

    const updateAssistantMessage = (patch) => {
      setLoading(false);
      liaraMessage = { ...liaraMessage, ...patch };
      setChatSessions(prev => prev.map(session => {
        if (session.id !== activeSessionId) return session;
        const msgIndex = session.messages.findIndex(m => m.id === assistantMessageId);
        if (msgIndex === -1) {
          return { ...session, messages: [...session.messages, liaraMessage] };
        }
        const nextMessages = [...session.messages];
        nextMessages[msgIndex] = liaraMessage;
        return { ...session, messages: nextMessages };
      }));
    };

    try {
      console.log('[Chat] SSE STREAM START: Connecting to /api/chat/stream');
      console.log(`[FRONTEND_LOG] ${timestamp} - SSE_START - Connecting to /api/chat/stream`);

      await streamChatSSE('/api/chat/stream', {
        message: trimmedMessage,
        model: modelToUse,
        session_id: activeSessionId,
        images: currentImageBase64 ? [currentImageBase64] : undefined
      }, {
        signal: requestAbortController.signal,
        onActivity: () => {
          lastActivityRef.current = Date.now();
          setStalled(false);
        },
        onEvent: async (parsed) => {
          if (parsed.type === 'metadata') {
            updateAssistantMessage({ model: parsed.model, mood: parsed.mood });
            if (parsed.context_tokens != null && parsed.context_limit != null) {
              setContextInfo({ tokens: parsed.context_tokens, limit: parsed.context_limit });
            }
          } else if (parsed.type === 'memory_context') {
            setMemoryContext(parsed.data);
            updateAssistantMessage({ memoryContext: parsed.data });
          } else if (parsed.type === 'action_result') {
            updateAssistantMessage({ actionResult: parsed.result });
          } else if (parsed.type === 'web_search') {
            setSearching(true);
            setSearchIntent(parsed.intent || 'general');
          } else if (parsed.type === 'web_results') {
            setSearching(false);
            updateAssistantMessage({
              webSearchResults: parsed.results,
              searchType: parsed.search_type,
              riskScore: parsed.risk_score
            });
          } else if (parsed.type === 'thinking') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({
              thinking: (liaraMessage.thinking || '') + (parsed.text || '')
            });
          } else if (parsed.type === 'tasks') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({ tasks: parsed.items });
          } else if (parsed.type === 'agent_steps') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({ agentSteps: parsed.items });
          } else if (parsed.type === 'web_sources') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({ webSources: parsed.items });
          } else if (parsed.type === 'image_results') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({ imageResults: parsed.items });
          } else if (parsed.type === 'factcheck') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({ factcheck: parsed.items });
          } else if (parsed.type === 'workspace_proposal') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({
              workspaceProposals: [...(liaraMessage.workspaceProposals || []), parsed]
            });
          } else if (parsed.type === 'workspace_artifact') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({
              workspaceArtifacts: [...(liaraMessage.workspaceArtifacts || []), parsed]
            });
          } else if (parsed.type === 'content') {
            setLoading(false);
            if (!messageAdded) {
              messageAdded = true;
            }
            updateAssistantMessage({
              content: liaraMessage.content + (parsed.text || '')
            });
          } else if (parsed.type === 'usage') {
            const usageData = parsed.usage || {
              in: parsed.tokens_in,
              think: parsed.tokens_think,
              out: parsed.tokens_out,
              total: parsed.tokens_total
            };
            updateAssistantMessage({ tokens: usageData });
          } else if (parsed.type === 'done') {
            setLoading(false);
            setSearching(false);
            if (parsed.usage) {
              updateAssistantMessage({ tokens: parsed.usage });
            }
          } else if (parsed.type === 'persisted') {
            // Real DB id, only now known - lets a just-finished message's
            // <tasks> checklist become checkable without needing a reload
            // first (see the messageId prop passed to TaskListBlock below).
            updateAssistantMessage(
              parsed.message_id ? { persisted: parsed.success, id: parsed.message_id } : { persisted: parsed.success }
            );
          }
        }
      });

      // Mood-Refresh nach erfolgreicher Antwort
      try {
        const moodData = await moodAPI.getStatus();
        setCurrentMood(moodData.current_mood);
      } catch (moodError) {
        console.error('[Chat] Mood-Status-Refresh fehlgeschlagen (nicht kritisch):', moodError);
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('[Chat] Request aborted by user');
        console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_ABORTED`);
        return;
      }
      
      console.error('[Chat] Error:', error);
      console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_ERROR - ${error.message}`);
      setErrorMessage(error.message || 'Fehler bei der Kommunikation mit Liara');
      setChatSessions(prev => prev.map(session => 
        session.id === activeSessionId 
          ? { 
              ...session, 
              messages: [...session.messages, { 
                role: 'error', 
                content: error.message || 'Fehler bei der Kommunikation mit Liara. Ist das Backend erreichbar?',
                timestamp: new Date().toISOString()
              }]
            }
          : session
      ));
    } finally {
      console.log(`[FRONTEND_LOG] ${timestamp} - REQUEST_COMPLETE - Cleanup started`);
      setLoading(false);
      setGenerating(false);
      setStalled(false);
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

  // Plain-text rendering of everything a message bubble can show, not just
  // msg.content - the copy button used to silently drop Denkprozess/Agent/
  // Quellen/Faktencheck/Aufgaben, which only ever lived in the bubble's own
  // separate collapsible blocks. Mirrors the bubble's own render order
  // (ThinkingBlock -> AgentStepsBlock -> WebSourcesBlock -> ImageResultsBlock ->
  // FactCheckBlock -> WorkspaceProposalsBlock -> TaskListBlock -> content ->
  // footer) so the
  // copied text reads the same top-to-bottom as the bubble itself.
  const buildFullMessageText = (msg) => {
    const parts = [];

    if (msg.thinking) {
      parts.push(`🧠 Denkprozess:\n${msg.thinking}`);
    }
    if (msg.agentSteps && msg.agentSteps.length > 0) {
      const lines = msg.agentSteps.map((s) => `${AGENT_STEP_ICON[s.status] || '•'} ${s.label}`);
      parts.push(`⚙️ Agent:\n${lines.join('\n')}`);
    }
    if (msg.webSources && msg.webSources.length > 0) {
      const lines = msg.webSources.map((s, i) => {
        const date = s.dated ? formatSourceDate(s.published_at) : 'kein Datum';
        return `${i + 1}. ${s.title || s.url} (${s.domain}, ${date})\n   ${s.url}`;
      });
      parts.push(`📚 Quellen:\n${lines.join('\n')}`);
    }
    if (msg.imageResults && msg.imageResults.length > 0) {
      const lines = msg.imageResults.map((img, i) => `${i + 1}. ${img.title || img.url}\n   ${img.url}`);
      parts.push(`🖼️ Bilder:\n${lines.join('\n')}`);
    }
    if (msg.factcheck && msg.factcheck.length > 0) {
      const lines = msg.factcheck.map((item) => {
        const icon = FACTCHECK_ICON[item.confidence] || '•';
        const source = item.source ? ` — ${item.source}` : '';
        return `${icon} [${item.confidence}] ${item.label}${source}`;
      });
      parts.push(`🔎 Faktencheck:\n${lines.join('\n')}`);
    }
    if (msg.workspaceProposals && msg.workspaceProposals.length > 0) {
      const lines = msg.workspaceProposals.map((p) => `- ${p.filename} (${PROPOSAL_ACTION_LABELS[p.action] || p.action})`);
      parts.push(`📝 Workspace-Vorschläge:\n${lines.join('\n')}`);
    }
    if (msg.tasks && msg.tasks.length > 0) {
      const lines = msg.tasks.map((t) => `[${t.done ? 'x' : ' '}] ${t.label}`);
      parts.push(`📋 Aufgaben:\n${lines.join('\n')}`);
    }
    if (msg.content) {
      parts.push(msg.content);
    }
    if (msg.model) {
      parts.push(`— ${msg.model}${msg.mood ? ` · ${msg.mood}` : ''}`);
    }

    return parts.join('\n\n');
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
    setContextInfo(null);
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

  // Toggles one <tasks> checklist item's done-state on a persisted assistant
  // message and saves it, so the check survives navigating away and back
  // (previously the checklist was display-only and lived only in this
  // session's React state). Optimistic local update first, since the
  // model's own initial done/undone marks already showed as unresponsive
  // input before this - a round-trip-before-feedback toggle would feel the
  // same way.
  const handleTaskToggle = async (messageId, itemId, done) => {
    setChatSessions(prev => prev.map(session => {
      if (session.id !== activeSessionId) return session;
      return {
        ...session,
        messages: session.messages.map(m =>
          m.id === messageId && m.tasks
            ? { ...m, tasks: m.tasks.map(t => (t.id === itemId ? { ...t, done } : t)) }
            : m
        )
      };
    }));

    try {
      await updateMessageTaskItem(messageId, itemId, done);
    } catch (error) {
      console.error('Failed to save task toggle:', error);
      // Revert on failure - the server never saw the change.
      setChatSessions(prev => prev.map(session => {
        if (session.id !== activeSessionId) return session;
        return {
          ...session,
          messages: session.messages.map(m =>
            m.id === messageId && m.tasks
              ? { ...m, tasks: m.tasks.map(t => (t.id === itemId ? { ...t, done: !done } : t)) }
              : m
          )
        };
      }));
    }
  };

  // 🖼️ Bild-Upload Handler
  const handleImageSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validierung
    if (!file.type.startsWith('image/') && !file.name.match(/\.(jpg|jpeg|png|webp|heic|heif|bmp|gif)$/i)) {
      setErrorMessage('Bitte nur Bilddateien hochladen (JPG, PNG, WEBP, HEIC)');
      return;
    }

    try {
      const compressed = await compressAndFormatImage(file, 1280, 0.82);
      setSelectedImage(file);
      setSelectedImageBase64(compressed.base64);
      setImagePreview(compressed.previewUrl);
    } catch (err) {
      console.warn('Image compressor fallback:', err);
      setSelectedImage(file);
      const previewUrl = URL.createObjectURL(file);
      setImagePreview(previewUrl);
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
            setSelectedImage(file);
            setSelectedImageBase64(compressed.base64);
            setImagePreview(compressed.previewUrl);
          } catch (err) {
            console.warn('Paste image compressor fallback:', err);
          }
          break;
        }
      }
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    const files = e.dataTransfer?.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    if (file.type.startsWith('image/')) {
      try {
        const compressed = await compressAndFormatImage(file, 1280, 0.82);
        setSelectedImage(file);
        setSelectedImageBase64(compressed.base64);
        setImagePreview(compressed.previewUrl);
      } catch (err) {
        console.warn('Drop image compressor fallback:', err);
      }
    }
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
    if (imagePreview && imagePreview.startsWith('blob:')) {
      URL.revokeObjectURL(imagePreview);
    }
    setSelectedImage(null);
    setSelectedImageBase64(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImageAnalysis = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    handleSubmit(e || { preventDefault: () => {} });
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
      formData.append('task', hailoTask);
      formData.append('model', hailoModel);
      if (hailoTask === 'detect') {
        formData.append('confidence', hailoConfidence);
      }
      formData.append('message', message.trim());
      formData.append('session_id', activeSessionId);

      const token = localStorage.getItem('liara_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const response = await fetch('/api/chat/hailo-vision', {
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
            <h2><img src={liaraLogo} alt="LIARA" className="chat-title-logo" /> {activeSession?.title || 'Chat mit Liara'}</h2>
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
            <>
              <SessionContextBar messages={messages} modelName={selectedModel} contextInfo={contextInfo} />
              <span className="chat-message-count" title="Nachrichten im Verlauf">
                💬 {messages.length}
              </span>
              <button 
                onClick={handleArchiveToWorkspace} 
                className="btn-archive" 
                title="Im Workspace archivieren (chat_archives/)"
                disabled={isArchiving}
              >
                {isArchiving ? '⏳' : '💾'}
              </button>
              <button 
                onClick={handleExportMarkdown} 
                className="btn-export" 
                title="Chat als Markdown herunterladen"
              >
                ⬇️
              </button>
            </>
          )}
          <button onClick={createNewChat} className="btn-new-chat" title="Neue Konversation">
            ➕
          </button>
          <button onClick={clearChat} className="btn-clear" title="Chat löschen">
            🗑️
          </button>
        </div>
      </div>

      {archiveBanner && (
        <div className={`chat-banner ${archiveBanner.type === 'error' ? 'chat-banner-error' : 'chat-banner-success'}`}>
          <span>{archiveBanner.text}</span>
          <button type="button" className="chat-banner-dismiss" onClick={() => setArchiveBanner(null)}>✕</button>
        </div>
      )}

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
              {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? (
                <img src={liaraLogo} alt="LIARA" className="bubble-avatar-logo" />
              ) : '⚠️'}
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
                    onClick={() => handleCopyMessage(buildFullMessageText(msg), index)}
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
                <AgentStepsBlock steps={msg.agentSteps} />
              )}
              {msg.role === 'assistant' && (
                <WebSourcesBlock sources={msg.webSources} />
              )}
              {msg.role === 'assistant' && (
                <ImageResultsBlock images={msg.imageResults} />
              )}
              {msg.role === 'assistant' && (
                <FactCheckBlock items={msg.factcheck} />
              )}
              {msg.role === 'assistant' && (
                <WorkspaceProposalsBlock proposals={msg.workspaceProposals} />
              )}
              {msg.role === 'assistant' && (
                <WorkspaceArtifactsBlock artifacts={msg.workspaceArtifacts} />
              )}
              {msg.role === 'assistant' && (
                <TaskListBlock
                  tasks={msg.tasks}
                  onToggle={
                    typeof msg.id === 'number'
                      ? (itemId, done) => handleTaskToggle(msg.id, itemId, done)
                      : undefined
                  }
                />
              )}
              {!msg.actionResult?.success && (
                <div className="bubble-text">
                  <MarkdownMessage content={msg.content} sessionId={activeSessionId} />
                </div>
              )}
              {/* Persistent "still working" cue for whichever message is
                  currently being generated - independent of ThinkingBlock/
                  AgentStepsBlock, which only update when the model actually
                  emits that specific event type. A reasoning model that
                  shows its "decide to search" thinking but then composes
                  the final answer with no further thinking/content tokens
                  for a stretch otherwise leaves the bubble looking frozen
                  with no sign anything is still happening. */}
              {generating && index === messages.length - 1 && msg.role === 'assistant' && (
                <div className="still-generating-indicator" aria-label="Liara arbeitet noch">
                  <span></span><span></span><span></span>
                </div>
              )}
              {stalled && generating && index === messages.length - 1 && msg.role === 'assistant' && (
                <div className="stall-notice">
                  ⏳ Das dauert ungewöhnlich lange - möglicherweise hohe Serverlast oder ein Limit beim Modell.
                  Ich warte noch, du kannst aber auch abbrechen und es später erneut versuchen.
                </div>
              )}
              <ChatBubbleFooter
                model={msg.model}
                mood={msg.mood}
                tokens={msg.tokens}
                content={msg.content}
                thinking={msg.thinking}
              />
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
            <div className="bubble-avatar thinking">
              <img src={liaraLogo} alt="LIARA" className="bubble-avatar-logo" />
            </div>
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
              {stalled && (
                <div className="stall-notice">
                  ⏳ Das dauert ungewöhnlich lange - möglicherweise hohe Serverlast oder ein Limit beim Modell.
                  Ich warte noch, du kannst aber auch abbrechen und es später erneut versuchen.
                </div>
              )}
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

        <div className="chat-input-wrapper" onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
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
            onPaste={handlePaste}
            placeholder={selectedImage ? "Beschreibe das Bild oder stelle eine Frage..." : "Schreibe eine Nachricht... (Enter zum Senden, Shift+Enter für neue Zeile, Bild einfügen mit Strg+V)"}
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
                disabled={!message.trim() && !selectedImageBase64}
                className="chat-submit vision-submit"
                title="Multimodale Bildanalyse (Qwen 3.5 Vision Sensor ➔ Chat-Modell)"
              >
                📷 Qwen Vision
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
