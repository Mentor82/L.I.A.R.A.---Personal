/**
 * Guest API - Endpoints ohne Authentifizierung
 */

const API_BASE = '/api';  // Nginx proxied /api/* zum Backend

export const guestAPI = {
  /**
   * Hole Begrüßungsnachricht für Gäste
   */
  async getWelcome() {
    const response = await fetch(`${API_BASE}/chat/guest/welcome`);
    if (!response.ok) {
      const error = { status: response.status, message: await response.text() };
      throw error;
    }
    return await response.json();
  },

  /**
   * Sende Nachricht als Gast (limitiert) - LEGACY, non-streaming
   */
  async sendMessage(message) {
    const response = await fetch(`${API_BASE}/chat/guest/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Chat error');
    }

    return await response.json();
  },

  /**
   * Sende Nachricht als Gast mit SSE Streaming (schneller!)
   */
  async streamMessage(message, onChunk, onError, onDone, abortSignal = null) {
    const response = await fetch(`${API_BASE}/chat/guest/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
      signal: abortSignal
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Chat error');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr || dataStr === '[DONE]') continue;
            
            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === 'error') {
                onError(data.error);
              } else if (data.type === 'done') {
                onDone();
              } else if (data.type === 'content') {
                onChunk(data);
              } else if (data.type === 'web_search') {
                onChunk(data);
              } else if (data.type === 'web_results') {
                onChunk(data);
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError, 'Line:', dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
};
