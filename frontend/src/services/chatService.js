/**
 * Chat Persistence Service
 * 
 * Manages chat sessions and messages in the database
 */

const API_BASE = '/api'

/**
 * Get all chat sessions for current user
 */
export async function getChatSessions() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/sessions`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch chat sessions')
  }
  
  return await response.json()
}

/**
 * Create a new chat session
 */
export async function createChatSession(title = 'Neue Konversation') {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/sessions/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title })
  })
  
  if (!response.ok) {
    throw new Error('Failed to create chat session')
  }
  
  return await response.json()
}

/**
 * Get all messages for a session
 */
export async function getSessionMessages(sessionId) {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch messages')
  }
  
  return await response.json()
}

/**
 * Save a chat message to database
 */
export async function saveChatMessage(messageData) {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/messages/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(messageData)
  })
  
  if (!response.ok) {
    throw new Error('Failed to save message')
  }
  
  return await response.json()
}

/**
 * Delete a chat session
 */
export async function deleteChatSession(sessionId) {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to delete session')
  }
  
  return await response.json()
}

/**
 * Update session title
 */
export async function updateSessionTitle(sessionId, title) {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title })
  })
  
  if (!response.ok) {
    throw new Error('Failed to update session title')
  }
  
  return await response.json()
}
