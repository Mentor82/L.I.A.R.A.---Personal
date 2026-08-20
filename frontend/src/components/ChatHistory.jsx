import { useState, useEffect } from 'react';
import { chatSessionAPI } from '../services/api';
import './ChatHistory.css';

/**
 * ChatHistory - Baumstruktur für Chat-Verläufe
 * Rechts im Chatbereich als aufklappbare Liste
 */
function ChatHistory({ chats, activeChatId, onSelectChat }) {
  const [expanded, setExpanded] = useState({});

  // Optional: Backend reload (compact)
  useEffect(() => {
    chatSessionAPI.list().then(() => {});
  }, []);

  const toggleExpand = chatId => setExpanded(e => ({ ...e, [chatId]: !e[chatId] }));

  return (
    <aside className="chat-history">
      <h2 className="chat-history-title">Chat-Verlauf</h2>
      <ul className="chat-history-list">
        {chats.map(chat => (
          <li key={chat.id} className={`chat-history-item${activeChatId === chat.id ? ' active' : ''}`}>
            <div className="chat-history-header" onClick={() => onSelectChat(chat.id)}>
              <span className="chat-history-label">{chat.title || `Chat ${chat.id}`}</span>
              <button className="chat-history-toggle" onClick={e => { e.stopPropagation(); toggleExpand(chat.id); }}>
                {expanded[chat.id] ? '▼' : '▶'}
              </button>
            </div>
            {expanded[chat.id] && chat.messages && (
              <ul className="chat-history-messages">
                {chat.messages.map((msg, idx) => (
                  <li key={idx} className="chat-history-message">
                    <span className="chat-history-msg-role">{msg.role}:</span>
                    <span className="chat-history-msg-content">{msg.content.slice(0, 40)}{msg.content.length > 40 ? '...' : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}

export default ChatHistory;
