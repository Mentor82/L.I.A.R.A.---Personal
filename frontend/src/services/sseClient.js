/**
 * 📡 Centralized Chunk-Safe SSE Client (Issue #18, Issue #19, Issue #25)
 * 
 * Provides robust Server-Sent Events stream parsing over fetch() response bodies.
 * 
 * Features:
 * - Persistent buffer across network chunks (preserves split lines/JSON across reader.read() boundaries)
 * - Standard SSE multiline event support (accumulates multiple data: lines per event until empty line delimiter)
 * - Uses TextDecoder stream mode ({ stream: true })
 * - Ignores SSE comment lines (e.g. ": keep-alive") without corrupting event buffer
 * - Cleanly parses and dispatches structured JSON events
 * - Propagates backend 'error' events to callers instead of swallowing them
 * - Seamless 401 token refresh & retry before stream starts
 * - Single-flight refresh deduplication to prevent 401 storms
 */

import { refreshAccessToken } from './api.js';

/**
 * Async generator that reads raw chunks from an SSE response reader
 * and yields parsed event objects according to the SSE standard.
 * 
 * Protocol contract:
 * - Event blocks are delimited by empty lines (\n\n).
 * - Lines starting with 'data: ' are accumulated with \n joins.
 * - Comments starting with ':' are ignored / dispatched to onComment.
 * - '[DONE]' sentinel terminates the stream cleanly.
 * 
 * @param {ReadableStreamDefaultReader<Uint8Array>} reader
 * @param {Object} [options]
 * @param {Function} [options.onComment] Optional callback for comment lines (: keep-alive)
 * @param {AbortSignal} [options.signal] Optional abort signal
 * @returns {AsyncGenerator<Object, void, undefined>}
 */
export async function* parseSSEStream(reader, options = {}) {
  const { onComment } = options;
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let currentEventLines = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode with stream: true to properly handle multi-byte characters split across chunks
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      // The last element is either empty (if chunk ended with \n) or an incomplete line fragment
      buffer = lines.pop() ?? '';

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, '');

        // Empty line signals end of an SSE event block
        if (!line) {
          if (currentEventLines.length > 0) {
            const dataStr = currentEventLines.join('\n');
            currentEventLines = [];
            if (dataStr === '[DONE]') {
              return;
            }
            try {
              const parsed = JSON.parse(dataStr);
              yield parsed;
            } catch (jsonErr) {
              console.warn('[SSE] Non-JSON or incomplete data block:', dataStr, jsonErr);
            }
          }
          continue;
        }

        // Ignore comment lines (e.g. ": keep-alive")
        if (line.startsWith(':')) {
          onComment?.(line.slice(1).trim());
          continue;
        }

        if (line.startsWith('data: ') || line === 'data:') {
          const dataChunk = line.startsWith('data: ') ? line.slice(6) : '';
          currentEventLines.push(dataChunk);
        }
      }
    }

    // Flush any remaining decoder state
    buffer += decoder.decode();
    if (buffer.trim()) {
      const line = buffer.replace(/\r$/, '');
      if (line.startsWith('data: ') || line === 'data:') {
        currentEventLines.push(line.startsWith('data: ') ? line.slice(6) : '');
      }
    }

    if (currentEventLines.length > 0) {
      const dataStr = currentEventLines.join('\n');
      if (dataStr && dataStr !== '[DONE]') {
        try {
          const parsed = JSON.parse(dataStr);
          yield parsed;
        } catch (jsonErr) {
          console.warn('[SSE] Trailing non-JSON data block:', dataStr, jsonErr);
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Ignore release error if already closed
    }
  }
}

/**
 * Executes a streaming chat request with automatic token refresh,
 * chunk-safe SSE parsing, and proper error propagation.
 * 
 * @param {string} endpoint - API endpoint (e.g. '/api/chat/stream')
 * @param {Object} bodyPayload - Request body JSON object
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @param {Function} [options.onEvent] - Called for every parsed SSE event
 * @param {Function} [options.onActivity] - Called when data arrives (resets stall timers)
 * @returns {Promise<void>}
 */
export async function streamChatSSE(endpoint, bodyPayload, options = {}) {
  const { signal, onEvent, onActivity } = options;

  let token = localStorage.getItem('liara_token');
  let response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(bodyPayload),
    signal
  });

  // Handle 401 Unauthorized before stream begins: try single refresh & retry
  if (response.status === 401 && !endpoint.includes('/auth/')) {
    console.warn('[SSE] Token expired before stream start, attempting refresh...');
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      token = localStorage.getItem('liara_token');
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(bodyPayload),
        signal
      });
    } else {
      throw new Error('Authentication required');
    }
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errData = await response.json();
      if (errData.detail) errorDetail = errData.detail;
    } catch {
      // Not a JSON error body
    }
    throw new Error(errorDetail);
  }

  const reader = response.body.getReader();

  for await (const event of parseSSEStream(reader, { signal, onComment: () => onActivity?.() })) {
    onActivity?.();

    if (event.type === 'error') {
      const errMsg = typeof event.error === 'string'
        ? event.error
        : (event.error?.message || 'Unbekannter Serverfehler während des Streamings');
      throw new Error(errMsg);
    }

    if (onEvent) {
      await onEvent(event);
    }
  }
}
