import { apiFetch, API_BASE } from './api';

/**
 * Chat Archive & Export API Service (Issue #22)
 */
export const chatArchiveAPI = {
  /**
   * Archiviert eine Chat-Sitzung persistent im Workspace (chat_archives/)
   * @param {number} sessionId
   */
  async archiveToWorkspace(sessionId) {
    return apiFetch(`/chat/sessions/${sessionId}/archive-to-workspace`, {
      method: 'POST',
    });
  },

  /**
   * Exportiert eine Chat-Sitzung als Download (Markdown oder JSON)
   * @param {number} sessionId
   * @param {string} format - 'markdown' oder 'json'
   */
  async exportSession(sessionId, format = 'markdown') {
    const token = localStorage.getItem('liara_token');
    const url = `${API_BASE}/chat/sessions/${sessionId}/export?format=${format}`;
    const response = await fetch(url, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Export fehlgeschlagen: ${response.statusText}`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') || '';
    let filename = `chat_export_${sessionId}.${format === 'json' ? 'json' : 'md'}`;
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
    return { ok: true, filename };
  },
};
