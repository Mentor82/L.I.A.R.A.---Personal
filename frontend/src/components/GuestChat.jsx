import { useState, useEffect, useRef } from 'react';
import { guestAPI } from '../services/guestApi';
import SearchingIndicator from './SearchingIndicator';
import WebSearchResults from './WebSearchResults';
import MarkdownMessage from './MarkdownMessage';
import './Chat.css';

function GuestChat() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchIntent, setSearchIntent] = useState(null);
  const [welcomeData, setWelcomeData] = useState(null);
  const [messageCount, setMessageCount] = useState(0);
  const [guestModeDisabled, setGuestModeDisabled] = useState(false);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Lade Begrüßungsnachricht
  useEffect(() => {
    const fetchWelcome = async () => {
      try {
        const data = await guestAPI.getWelcome();
        setWelcomeData(data);
        
        // Zeige Begrüßung als erste Nachricht
        setMessages([{
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toISOString(),
          isWelcome: true
        }]);
      } catch (error) {
        console.error('Error loading welcome message:', error);
        
        // Prüfe ob Gast-Modus deaktiviert ist (HTTP 403)
        if (error.message?.includes('403') || error.status === 403) {
          setGuestModeDisabled(true);
          setMessages([{
            role: 'system',
            content: '🔒 Der Gast-Modus ist derzeit deaktiviert. Bitte registriere dich für den vollen Zugriff.',
            timestamp: new Date().toISOString()
          }]);
        }
      }
    };

    fetchWelcome();
  }, []);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    setSearching(false);
    
    // Add system message about stopped request
    setMessages(prev => [...prev, {
      role: 'system',
      content: '⚠️ Anfrage wurde abgebrochen.',
      timestamp: new Date().toISOString()
    }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const userMessage = message.trim();
    if (!userMessage) return;

    // Prüfe Nachrichtenlimit
    if (welcomeData && messageCount >= welcomeData.limitations.max_messages_per_session) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `🚫 Du hast das Limit von ${welcomeData.limitations.max_messages_per_session} Nachrichten erreicht. Registriere dich für unbegrenzte Gespräche!`,
        timestamp: new Date().toISOString()
      }]);
      return;
    }

    // Prüfe Länge
    if (welcomeData && userMessage.length > welcomeData.limitations.max_message_length) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `⚠️ Nachricht zu lang! Maximum: ${welcomeData.limitations.max_message_length} Zeichen. Du hast ${userMessage.length} Zeichen.`,
        timestamp: new Date().toISOString()
      }]);
      return;
    }

    const userMsg = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setMessage('');
    setMessageCount(prev => prev + 1);

    // Streaming-Nachricht initialisieren
    const assistantMsgId = Date.now();
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      model: 'llama3.2:1b',
      webSearchResults: null,
      searchType: null,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, assistantMsg]);

    try {
      // Create abort controller
      abortControllerRef.current = new AbortController();

      let firstContentReceived = false;

      await guestAPI.streamMessage(
        userMessage,
        // onChunk
        (data) => {
          if (data.type === 'web_search') {
            setSearching(true);
            setSearchIntent(data.intent);
          } else if (data.type === 'web_results') {
            setSearching(false);
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, webSearchResults: data.results, searchType: data.search_type }
                : msg
            ));
          } else if (data.type === 'content') {
            // Erster Chunk: Loading-Indikator ausblenden, sonst läuft die
            // "denkt nach..."-Bubble parallel zur bereits sichtbaren,
            // live wachsenden Antwort weiter bis der Stream fertig ist.
            if (!firstContentReceived) {
              firstContentReceived = true;
              setLoading(false);
            }
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: msg.content + data.text }
                : msg
            ));
          }
        },
        // onError
        (error) => {
          console.error('Stream error:', error);
          setMessages(prev => [...prev, {
            role: 'error',
            content: error || 'Fehler bei der Kommunikation mit Liara.',
            timestamp: new Date().toISOString()
          }]);
          setLoading(false);
          setSearching(false);
        },
        // onDone
        () => {
          setLoading(false);
          setSearching(false);
        },
        // abortSignal
        abortControllerRef.current?.signal
      );

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
        return;
      }
      
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'error',
        content: error.message || 'Fehler bei der Kommunikation mit Liara.',
        timestamp: new Date().toISOString()
      }]);
      setLoading(false);
      setSearching(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleCopyMessage = async (content, index) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageIndex(index);
      setTimeout(() => setCopiedMessageIndex(prev => (prev === index ? null : prev)), 1500);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-title">
          <h2>🌙 Chat mit Liara (Gast-Modus)</h2>
          {welcomeData && (
            <span className="guest-mode-badge">
              👋 Gast • {messageCount}/{welcomeData.limitations.max_messages_per_session} Nachrichten
            </span>
          )}
        </div>
      </div>

      <div className="guest-info-banner">
        <span>💡 Du bist im eingeschränkten Gast-Modus</span>
        <span>• Max. {welcomeData?.limitations.max_message_length || 500} Zeichen pro Nachricht</span>
        <span>• {welcomeData?.limitations.max_messages_per_session || 10} Nachrichten insgesamt</span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-bubble message-${msg.role}`}>
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
                    onClick={() => handleCopyMessage(msg.content, idx)}
                    title="Nachricht kopieren"
                  >
                    {copiedMessageIndex === idx ? '✅' : '📋'}
                  </button>
                </span>
              </div>
              <div className="bubble-text">
                <MarkdownMessage content={msg.content} />
              </div>
              
              {/* Web Search Results anzeigen */}
              {msg.webSearchResults && (
                <WebSearchResults 
                  results={msg.webSearchResults} 
                  type={msg.searchType}
                  riskScore={null}
                />
              )}
              
              {msg.hint && (
                <div className="bubble-hint">
                  {msg.hint}
                </div>
              )}
              {msg.model && !msg.isWelcome && (
                <div className="bubble-footer">
                  <span className="bubble-model">🤖 {msg.model}</span>
                  <span className="guest-mode-indicator">👋 Gast-Modus</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Searching Indicator */}
        {searching && (
          <SearchingIndicator query={message} type={searchIntent} />
        )}

        {loading && (
          <div className="message-bubble message-assistant loading-bubble">
            <div className="bubble-avatar">🌙</div>
            <div className="bubble-content">
              <div className="bubble-header">
                <span className="bubble-sender">Liara</span>
              </div>
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="guest-loading-hint">
                <small>⚡ Schnelle Antwort dank Streaming...</small>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={guestModeDisabled ? "Gast-Modus deaktiviert" : `Schreibe eine Nachricht... (max ${welcomeData?.limitations.max_message_length || 500} Zeichen)`}
          disabled={guestModeDisabled || loading || (welcomeData && messageCount >= welcomeData.limitations.max_messages_per_session)}
          className="chat-input"
          rows="1"
          maxLength={welcomeData?.limitations.max_message_length || 500}
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
            disabled={guestModeDisabled || !message.trim() || (welcomeData && messageCount >= welcomeData.limitations.max_messages_per_session)}
            className="chat-submit"
            title="Senden"
          >
            🚀
          </button>
        )}
      </form>

      {welcomeData && messageCount >= welcomeData.limitations.max_messages_per_session && (
        <div className="limit-reached-banner">
          <p>🚫 Nachrichtenlimit erreicht!</p>
          <p>Registriere dich kostenlos für unbegrenzte Gespräche und erweiterte Funktionen.</p>
        </div>
      )}
    </div>
  );
}

export default GuestChat;
