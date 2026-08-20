/**
 * Liara Backend Router - Zentrale Port-Auswahl mit Healthcheck
 * 
 * Verwaltet die Auswahl zwischen zwei Backend-Instanzen (Port 8100/8101)
 * basierend auf Healthchecks. Stellt sicher, dass pro Request immer nur
 * ein Backend verwendet wird.
 */

// Verfügbare Backend-Ports
// TODO: Port 8101 aktivieren wenn zweite Backend-Instanz läuft
const BACKEND_PORTS = [8100];

// Aktuell ausgewählter Port (Cache)
let currentBackendPort = null;

// Healthcheck-Cache (TTL: 30 Sekunden)
const healthCache = new Map();
const HEALTH_CACHE_TTL = 30000; // 30 Sekunden

// Healthcheck-Timeout
const HEALTH_CHECK_TIMEOUT = 2000; // 2 Sekunden

/**
 * Schneller TCP-Ping zu einem Port (prüft nur Erreichbarkeit)
 * @param {number} port - Backend-Port
 * @returns {Promise<boolean>} true wenn Port erreichbar
 */
async function pingPort(port) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 500); // Nur 500ms für Ping

    // Verwende HEAD-Request für minimalen Overhead
    const response = await fetch(`http://${window.location.hostname}:${port}/`, {
      method: 'HEAD',
      signal: controller.signal,
      mode: 'no-cors' // Ignoriere CORS für Ping
    });

    clearTimeout(timeoutId);
    return true; // Port ist erreichbar (Response egal)
  } catch (error) {
    // Timeout oder Verbindungsfehler = Port nicht erreichbar
    return false;
  }
}

/**
 * Prüfe ob ein Backend-Port gesund ist
 * @param {number} port - Backend-Port (8100 oder 8101)
 * @returns {Promise<boolean>} true wenn gesund
 */
async function probePort(port) {
  // Cache-Check
  const cached = healthCache.get(port);
  if (cached && (Date.now() - cached.timestamp < HEALTH_CACHE_TTL)) {
    return cached.healthy;
  }

  // STUFE 1: Schneller Ping - ist Port überhaupt erreichbar?
  const reachable = await pingPort(port);
  if (!reachable) {
    console.warn(`[BackendRouter] Port ${port} not reachable (ping failed)`);
    
    // Cache negative result (kurz: 5 Sekunden)
    healthCache.set(port, {
      healthy: false,
      timestamp: Date.now() - (HEALTH_CACHE_TTL - 5000)
    });
    
    return false;
  }

  // STUFE 2: HTTP-Healthcheck - funktioniert das Backend?
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT);

    // Verwende Root-Endpoint "/" (kompatibel mit älteren Backend-Versionen)
    const response = await fetch(`http://${window.location.hostname}:${port}/`, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    clearTimeout(timeoutId);

    const healthy = response.ok;
    
    // Cache result
    healthCache.set(port, {
      healthy,
      timestamp: Date.now()
    });

    if (healthy) {
      console.log(`[BackendRouter] Port ${port} is healthy`);
    } else {
      console.warn(`[BackendRouter] Port ${port} responded but unhealthy (HTTP ${response.status})`);
    }

    return healthy;
  } catch (error) {
    console.warn(`[BackendRouter] Port ${port} health check failed:`, error.message);
    
    // Cache negative result (kurz: 5 Sekunden)
    healthCache.set(port, {
      healthy: false,
      timestamp: Date.now() - (HEALTH_CACHE_TTL - 5000)
    });
    
    return false;
  }
}

/**
 * Wähle gesunden Backend-Port
 * 
 * Strategie:
 * 1. Wenn aktueller Port noch gesund ist, behalte ihn
 * 2. Sonst teste Ports in Reihenfolge [8100, 8101]
 * 3. Fallback: Verwende 8100 auch wenn unhealthy
 * 
 * @returns {Promise<number>} Ausgewählter Port
 */
export async function pickHealthyPort() {
  // 1. Preferiere aktuellen Port wenn noch gesund
  if (currentBackendPort) {
    const stillHealthy = await probePort(currentBackendPort);
    if (stillHealthy) {
      console.log(`[BackendRouter] Using cached port ${currentBackendPort}`);
      return currentBackendPort;
    } else {
      console.warn(`[BackendRouter] Cached port ${currentBackendPort} is now unhealthy`);
      currentBackendPort = null; // Invalidate cache
    }
  }

  // 2. Teste alle Ports der Reihe nach
  for (const port of BACKEND_PORTS) {
    const healthy = await probePort(port);
    if (healthy) {
      currentBackendPort = port;
      console.log(`[BackendRouter] Selected healthy port ${port}`);
      return port;
    }
  }

  // 3. Fallback: Verwende ersten Port (8100) auch wenn unhealthy
  currentBackendPort = BACKEND_PORTS[0];
  console.warn(`[BackendRouter] No healthy port found, falling back to ${currentBackendPort}`);
  return currentBackendPort;
}

/**
 * Baue Backend-URL für einen Endpoint
 * @param {string} endpoint - API Endpoint (z.B. '/chat/stream')
 * @returns {Promise<string>} Vollständige Backend-URL
 */
export async function buildBackendURL(endpoint) {
  const port = await pickHealthyPort();
  const hostname = window.location.hostname;
  
  // Entferne führenden Slash falls vorhanden
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  const url = `http://${hostname}:${port}${cleanEndpoint}`;
  console.log(`[BackendRouter] Built URL: ${url}`);
  return url;
}

/**
 * Invalidiere Port-Cache (z.B. nach Fehler)
 */
export function invalidatePortCache() {
  console.log('[BackendRouter] Port cache invalidated');
  currentBackendPort = null;
  healthCache.clear();
}

/**
 * Hole aktuellen Port (ohne Healthcheck)
 * @returns {number|null} Aktuell gecachter Port oder null
 */
export function getCurrentPort() {
  return currentBackendPort;
}

/**
 * Setze Port manuell (für Testing/Override)
 * @param {number} port - Port (8100 oder 8101)
 */
export function setPort(port) {
  if (!BACKEND_PORTS.includes(port)) {
    throw new Error(`Invalid port ${port}. Must be one of ${BACKEND_PORTS.join(', ')}`);
  }
  currentBackendPort = port;
  console.log(`[BackendRouter] Port manually set to ${port}`);
}

/**
 * Periodischer Health-Refresh (optional)
 * Rufe dies auf um alle 30 Sekunden automatisch zu prüfen
 */
export function startHealthMonitoring(intervalMs = 30000) {
  const intervalId = setInterval(async () => {
    if (currentBackendPort) {
      const healthy = await probePort(currentBackendPort);
      if (!healthy) {
        console.warn(`[BackendRouter] Port ${currentBackendPort} became unhealthy during monitoring`);
        currentBackendPort = null;
      }
    }
  }, intervalMs);

  // Return cleanup function
  return () => clearInterval(intervalId);
}
