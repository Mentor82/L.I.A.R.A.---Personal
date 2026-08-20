/**
 * Chat Persistence Service
 * Handles saving chat sessions and messages to database
 */

const API_BASE = '/api';

/**
 * Create a new chat session
 */
export async function createSession(title = 'Neue Konversation') {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/sessions/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title })
  });
  
  if (!response.ok) {
    throw new Error('Failed to create session');
  }
  
  return await response.json();
}

/**
 * Get all sessions for current user
 */
export async function getSessions() {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/sessions/`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch sessions');
  }
  
  return await response.json();
}

/**
 * Update session title
 */
export async function updateSessionTitle(sessionId, title) {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}?title=${encodeURIComponent(title)}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to update session title');
  }
  
  return await response.json();
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId) {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to delete session');
  }
  
  return await response.json();
}

/**
 * Save a message to database
 */
export async function saveMessage(messageData) {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/messages/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(messageData)
  });
  
  if (!response.ok) {
    console.error('Failed to save message:', await response.text());
    throw new Error('Failed to save message');
  }
  
  return await response.json();
}

/**
 * Get all messages for a session
 */
export async function getMessages(sessionId) {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/messages/session/${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch messages');
  }
  
  return await response.json();
}

/**
 * Delete a message
 */
export async function deleteMessage(messageId) {
  const token = localStorage.getItem('liara_token');
  
  const response = await fetch(`${API_BASE}/chat/messages/${messageId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to delete message');
  }
  
  return await response.json();
}
