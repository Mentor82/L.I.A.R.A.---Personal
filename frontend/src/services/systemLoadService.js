/**
 * System Load Service - Adaptive SSE decision-making
 */

const API_BASE = '/api';

let loadCache = null;
let cacheTimestamp = 0;
const CACHE_TTL = 5000; // 5 seconds

/**
 * Get current system load
 */
export async function getSystemLoad() {
  const now = Date.now();
  
  // Return cached data if fresh
  if (loadCache && (now - cacheTimestamp) < CACHE_TTL) {
    return loadCache;
  }
  
  try {
    const response = await fetch(`${API_BASE}/system/load`);
    
    if (!response.ok) {
      // Fallback: assume SSE is OK if endpoint fails
      return { recommendation: 'sse', cpu_percent: 0, memory_percent: 0 };
    }
    
    const data = await response.json();
    
    // Update cache
    loadCache = data;
    cacheTimestamp = now;
    
    return data;
  } catch (error) {
    console.warn('Failed to fetch system load, defaulting to SSE:', error);
    // Fallback to SSE on error
    return { recommendation: 'sse', cpu_percent: 0, memory_percent: 0 };
  }
}

/**
 * Should use SSE based on system load?
 */
export async function shouldUseSSE() {
  const load = await getSystemLoad();
  return load.recommendation === 'sse';
}
