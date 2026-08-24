/**
 * Liara API Client
 * 
 * Kommuniziert mit dem FastAPI Backend über Vite Proxy (/api -> localhost:8100)
 */

const API_BASE = '/api';

/**
 * Parst eine Response als JSON, ohne bei leerem Body (z.B. 204 No Content
 * von DELETE-Endpoints) mit "Unexpected end of JSON input" zu crashen.
 */
async function parseJsonSafe(response) {
  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

/**
 * Generic fetch wrapper mit Error Handling und Authentication
 */
async function apiFetch(endpoint, options = {}) {
  try {
    // Get JWT token from localStorage
    const token = localStorage.getItem('liara_token');
    
    // Build headers with authentication
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers,
      ...options,
    });

    // Handle 401 Unauthorized - try to refresh token
    if (response.status === 401 && !endpoint.includes('/auth/')) {
      console.warn('Token expired - attempting refresh');
      
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry original request with new token
        const newToken = localStorage.getItem('liara_token');
        headers['Authorization'] = `Bearer ${newToken}`;
        
        const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
          headers,
          ...options,
        });
        
        if (retryResponse.ok) {
          return await parseJsonSafe(retryResponse);
        }
      }
      
      // Refresh failed - clear and reload
      console.warn('Token refresh failed - forcing re-login');
      localStorage.removeItem('liara_token');
      localStorage.removeItem('liara_refresh_token');
      localStorage.removeItem('liara_user');
      window.location.reload();
      throw new Error('Authentication required');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
    }

    return await parseJsonSafe(response);
  } catch (error) {
    console.error('API Fetch Error:', error);
    throw error;
  }
}

/**
 * Refresh access token using refresh token
 * @returns {Promise<boolean>} true if successful
 */
async function refreshAccessToken() {
  try {
    const refreshToken = localStorage.getItem('liara_refresh_token');
    if (!refreshToken) {
      return false;
    }
    
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    
    if (!response.ok) {
      return false;
    }
    
    const data = await response.json();
    
    // Store new tokens
    localStorage.setItem('liara_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('liara_refresh_token', data.refresh_token);
    }
    localStorage.setItem('liara_user', JSON.stringify(data.user));
    
    console.log('Token refreshed successfully');
    return true;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
}

/**
 * Chat API
 */
export const chatAPI = {
  /**
   * Sende Nachricht an Liara
   * @param {string} message - User-Nachricht
   * @param {string} context - Optional: Zusätzlicher Kontext
   * @returns {Promise<{response: string, model_used: string}>}
   */
  async sendMessage(message, context = null) {
    return apiFetch('/chat/message', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  },

  /**
   * Hole verfügbare Modelle
   */
  async getModels() {
    return apiFetch('/chat/models');
  },

  /**
   * Hole Chat-Status
   */
  async getStatus() {
    return apiFetch('/chat/status');
  },

  /**
   * Hole alle Chat-Sessions des Nutzers (echte DB-Zeilen, nicht der
   * localStorage-Cache in Chat.jsx) - genutzt für die Session-Auswahl im
   * Workspace-Tab, wo ein echter session_id gebraucht wird.
   */
  async getSessions() {
    return apiFetch('/chat/sessions');
  },
};

/**
 * Mood System API
 */
export const moodAPI = {
  /**
   * Hole aktuellen Mood-Status
   */
  async getStatus() {
    return apiFetch('/mood/status');
  },

  /**
   * Hole Mood-History
   * @param {number} limit - Max Anzahl Einträge (default: 10)
   */
  async getHistory(limit = 10) {
    return apiFetch(`/mood/history?limit=${limit}`);
  },

  /**
   * Hole Trait-Modifiers
   */
  async getModifiers() {
    return apiFetch('/mood/modifiers');
  },

  /**
   * Hole verfügbare Mood-States
   */
  async getStates() {
    return apiFetch('/mood/states');
  },

  /**
   * Reset Mood zu Neutral
   */
  async reset() {
    return apiFetch('/mood/reset', { method: 'POST' });
  },

  /**
   * Update Mood manuell
   * @param {string} interactionType - Art der Interaktion
   * @param {number} intensity - Intensität (0.0-1.0)
   */
  async updateMood(interactionType, intensity = 0.5) {
    return apiFetch('/mood/update', {
      method: 'POST',
      body: JSON.stringify({ interaction_type: interactionType, intensity }),
    });
  },

  /**
   * Erkenne Mood aus Message
   * @param {string} message - User-Nachricht
   */
  async detectMood(message) {
    return apiFetch('/mood/detect', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },
};

/**
 * Tasks API
 */
export const tasksAPI = {
  /**
   * Erstelle neue Aufgabe
   */
  async create(taskData) {
    return apiFetch('/tasks/', {
      method: 'POST',
      body: JSON.stringify(taskData),
    });
  },

  /**
   * Hole alle Tasks mit optionalen Filtern
   */
  async getAll(filters = {}) {
    const params = new URLSearchParams(filters);
    return apiFetch(`/tasks/?${params}`);
  },

  /**
   * Hole Tasks für heute
   */
  async getDaily() {
    return apiFetch('/tasks/daily');
  },

  /**
   * Hole Tasks für diese Woche
   */
  async getWeekly() {
    return apiFetch('/tasks/weekly');
  },

  /**
   * Hole einzelne Task
   */
  async getById(id) {
    return apiFetch(`/tasks/${id}`);
  },

  /**
   * Update Task
   */
  async update(id, taskData) {
    return apiFetch(`/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(taskData),
    });
  },

  /**
   * Lösche Task
   */
  async delete(id) {
    return apiFetch(`/tasks/${id}`, { method: 'DELETE' });
  },

  /**
   * Markiere Task als erledigt
   */
  async complete(id) {
    return apiFetch(`/tasks/${id}/complete`, { method: 'POST' });
  },

  /**
   * Markiere Task als offen
   */
  async uncomplete(id) {
    return apiFetch(`/tasks/${id}/uncomplete`, { method: 'POST' });
  },
};

/**
 * Calendar API
 */
export const calendarAPI = {
  /**
   * Erstelle neues Event
   */
  async create(eventData) {
    return apiFetch('/calendar/', {
      method: 'POST',
      body: JSON.stringify(eventData),
    });
  },

  /**
   * Hole alle Events mit Filtern
   */
  async getAll(filters = {}) {
    const params = new URLSearchParams(filters);
    return apiFetch(`/calendar/?${params}`);
  },

  /**
   * Hole Events für heute
   */
  async getToday() {
    return apiFetch('/calendar/today');
  },

  /**
   * Hole Events für diese Woche
   */
  async getWeek() {
    return apiFetch('/calendar/week');
  },

  /**
   * Prüfe Konflikte
   */
  async checkConflicts(startTime, endTime, excludeId = null) {
    const params = new URLSearchParams({
      start_time: startTime,
      end_time: endTime,
    });
    if (excludeId) params.append('exclude_id', excludeId);
    return apiFetch(`/calendar/conflicts?${params}`);
  },

  /**
   * Finde freie Zeitfenster
   */
  async getFreeSlots(date, workStart = '09:00', workEnd = '18:00') {
    const params = new URLSearchParams({ date, work_start: workStart, work_end: workEnd });
    return apiFetch(`/calendar/free?${params}`);
  },

  /**
   * Hole einzelnes Event
   */
  async getById(id) {
    return apiFetch(`/calendar/${id}`);
  },

  /**
   * Update Event
   */
  async update(id, eventData) {
    return apiFetch(`/calendar/${id}`, {
      method: 'PUT',
      body: JSON.stringify(eventData),
    });
  },

  /**
   * Lösche Event
   */
  async delete(id) {
    return apiFetch(`/calendar/${id}`, { method: 'DELETE' });
  },
};

/**
 * Notes API
 */
export const notesAPI = {
  /**
   * Erstelle neue Notiz
   */
  async create(noteData) {
    return apiFetch('/notes/', {
      method: 'POST',
      body: JSON.stringify(noteData),
    });
  },

  /**
   * Hole alle Notizen als Baumstruktur
   */
  async getTree() {
    return apiFetch('/notes/tree');
  },

  /**
   * Hole alle Notizen mit Filtern
   */
  async getAll(filters = {}) {
    const params = new URLSearchParams(filters);
    return apiFetch(`/notes/?${params}`);
  },

  /**
   * Suche in Notizen
   */
  async search(query) {
    return apiFetch(`/notes/search?q=${encodeURIComponent(query)}`);
  },

  /**
   * Hole alle Kategorien
   */
  async getCategories() {
    return apiFetch('/notes/categories');
  },

  /**
   * Hole alle Tags
   */
  async getTags() {
    return apiFetch('/notes/tags');
  },

  /**
   * Hole einzelne Notiz
   */
  async getById(id) {
    return apiFetch(`/notes/${id}`);
  },

  /**
   * Update Notiz
   */
  async update(id, noteData) {
    return apiFetch(`/notes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(noteData),
    });
  },

  /**
   * Lösche Notiz
   */
  async delete(id) {
    return apiFetch(`/notes/${id}`, { method: 'DELETE' });
  },

  /**
   * Pinne Notiz
   */
  async pin(id) {
    return apiFetch(`/notes/${id}/pin`, { method: 'POST' });
  },

  /**
   * Entferne Pin
   */
  async unpin(id) {
    return apiFetch(`/notes/${id}/unpin`, { method: 'POST' });
  },

  /**
   * Archiviere Notiz
   */
  async archive(id) {
    return apiFetch(`/notes/${id}/archive`, { method: 'POST' });
  },

  /**
   * Hole aus Archiv zurück
   */
  async unarchive(id) {
    return apiFetch(`/notes/${id}/unarchive`, { method: 'POST' });
  },
};

/**
 * Liara Persona API
 */
export const personaAPI = {
  /**
   * Hole Persona-Daten
   */
  async getPersona() {
    return apiFetch('/liara/persona');
  },

  /**
   * Hole System-Status
   */
  async getStatus() {
    return apiFetch('/liara/status');
  },

  /**
   * Hole Health-Status
   */
  async getHealth() {
    return apiFetch('/liara/health');
  },
};

/**
 * User Preferences API - thin wrapper matching this file's convention;
 * UserPreferences.jsx itself still uses raw fetch() calls (pre-existing,
 * unrelated to this addition), this is just for App.jsx's nav-gating check.
 */
export const preferencesAPI = {
  async get() {
    return apiFetch('/user/preferences');
  },
};

/**
 * Code Execution API (chat "Run" button for Python/Julia code blocks)
 */
export const codeExecAPI = {
  /**
   * Führt Code sandboxed auf dem Server aus.
   */
  async run(sessionId, language, code) {
    return apiFetch('/code-exec/run', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, language, code }),
    });
  },

  /**
   * Listet die Workspace-Dateien einer Session.
   */
  async listFiles(sessionId) {
    return apiFetch(`/code-exec/sessions/${sessionId}/files`);
  },

  /**
   * Lädt eine Workspace-Datei herunter (Blob, kein JSON - apiFetch passt hier nicht).
   */
  async downloadFile(sessionId, filename) {
    const token = localStorage.getItem('liara_token');
    const response = await fetch(`${API_BASE}/code-exec/sessions/${sessionId}/files/${encodeURIComponent(filename)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new Error(`Download fehlgeschlagen: ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};

/**
 * Workspace API (Workspace v1 - file create/save/rename/delete + chat-
 * context selection). Reuses codeExecAPI.run/downloadFile for execution
 * and downloads - this only covers the file-CRUD endpoints codeExecAPI
 * doesn't have.
 */
export const workspaceAPI = {
  async listFiles(sessionId) {
    return apiFetch(`/workspace/sessions/${sessionId}/files`);
  },

  /**
   * Lädt den Textinhalt einer Workspace-Datei für den Editor - reuses the
   * existing code-exec download endpoint as plain text (fetch() ignores
   * Content-Disposition, so the same "attachment" endpoint works fine here
   * without needing a second backend route).
   */
  async getFileContent(sessionId, filename) {
    const token = localStorage.getItem('liara_token');
    const response = await fetch(`${API_BASE}/code-exec/sessions/${sessionId}/files/${encodeURIComponent(filename)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new Error(`Datei konnte nicht geladen werden: ${response.status}`);
    }
    return response.text();
  },

  async createFile(sessionId, filename, content = '') {
    return apiFetch(`/workspace/sessions/${sessionId}/files`, {
      method: 'POST',
      body: JSON.stringify({ filename, content }),
    });
  },

  async saveFile(sessionId, filename, content) {
    return apiFetch(`/workspace/sessions/${sessionId}/files/${encodeURIComponent(filename)}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  async renameFile(sessionId, filename, newName) {
    return apiFetch(`/workspace/sessions/${sessionId}/files/${encodeURIComponent(filename)}/rename`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    });
  },

  async deleteFile(sessionId, filename) {
    return apiFetch(`/workspace/sessions/${sessionId}/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
  },

  async setContextSelection(sessionId, filenames) {
    return apiFetch(`/workspace/sessions/${sessionId}/context`, {
      method: 'PUT',
      body: JSON.stringify({ filenames }),
    });
  },

  /**
   * LIARA's proposed-but-not-yet-applied changes (Agent-Vorbereitung v1).
   */
  async listProposals(sessionId, status = null) {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiFetch(`/workspace/sessions/${sessionId}/proposals${query}`);
  },

  async approveProposal(sessionId, proposalId) {
    return apiFetch(`/workspace/sessions/${sessionId}/proposals/${proposalId}/approve`, {
      method: 'POST',
    });
  },

  async rejectProposal(sessionId, proposalId) {
    return apiFetch(`/workspace/sessions/${sessionId}/proposals/${proposalId}/reject`, {
      method: 'POST',
    });
  },
};

/**
 * System API
 */
export const systemAPI = {
  /**
   * Hole System-Info
   */
  async getInfo() {
    return apiFetch('/info');
  },

  /**
   * Hole Dashboard-Info
   */
  async getDashboard() {
    return apiFetch('/dashboard/info');
  },

  /**
   * Hole vollständigen Health-Status
   */
  async getFullHealth() {
    return apiFetch('/health/full');
  },
};
