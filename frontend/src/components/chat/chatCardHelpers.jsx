// Shared constants/formatters used by ChatCards.jsx's block components and by
// Chat.jsx's plain-text message export (buildFullMessageText) - kept out of
// ChatCards.jsx itself so that file can stay component-only (react-refresh
// needs a file to only export components for Fast Refresh to work reliably).

// Minimal inline markdown parser for task labels/claims (bold/code/italic only -
// avoid spinning up full react-markdown instances for short single-line labels).
export function renderInlineMarkdown(text) {
  if (!text) return null;
  const parts = [];
  const regex = /\*\*(.+?)\*\*|`([^`]+)`|\*([^*]+)\*/g;
  let lastIndex = 0;
  let match;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    if (match[1] !== undefined) parts.push(<strong key={key++}>{match[1]}</strong>);
    else if (match[2] !== undefined) parts.push(<code key={key++}>{match[2]}</code>);
    else if (match[3] !== undefined) parts.push(<em key={key++}>{match[3]}</em>);
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export const AGENT_STEP_ICON = { running: '⏳', done: '✅', error: '❌' };

export function formatSourceDate(published_at) {
  if (!published_at) return null;
  try {
    return new Date(published_at).toLocaleDateString('de-DE', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return null;
  }
}

export const FACTCHECK_ICON = { 'bestätigt': '✓', 'teilweise': '△', 'unbestätigt': '✗' };

export const PROPOSAL_ACTION_LABELS = {
  create: 'anlegen', update: 'überschreiben', delete: 'löschen',
  install: 'installieren', remove: 'entfernen',
};

const MODEL_LIMITS = {
  'llama3.2:1b': 8192,
  'llama3.2:3b': 8192,
  'llama3.1:8b': 16384,
  'qwen2.5:0.5b': 8192,
  'qwen2.5:1.5b': 16384,
  'qwen2.5:7b': 32768,
  'qwen3.5:0.8b': 16384,
  'gpt-oss:20b-cloud': 32768,
  'gemma4:cloud': 32768,
  'gpt-oss:120b-cloud': 65536,
  'deepseek-v4-flash:cloud': 65536,
  'qwen3.5:cloud': 131072,
  'nemotron-3-ultra:cloud': 131072,
  'kimi-k3:cloud': 131072,
  'deepseek-v4-pro:cloud': 131072,
};

export function getModelContextLimit(modelName) {
  if (!modelName) return 8192;
  const cleaned = modelName.trim().toLowerCase();
  if (MODEL_LIMITS[cleaned]) return MODEL_LIMITS[cleaned];
  for (const [key, limit] of Object.entries(MODEL_LIMITS)) {
    if (cleaned.startsWith(key.split(':')[0])) return limit;
  }
  return 8192;
}
