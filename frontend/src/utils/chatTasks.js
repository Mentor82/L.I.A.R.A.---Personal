// Persist task choices only; legacy model IDs cannot be used by Personal's key.
export const DEFAULT_CHAT_TASK = 'task:tool';
export const FALLBACK_CHAT_TASKS = [
  { name: DEFAULT_CHAT_TASK, recommended: true, speed: 'Werkzeuge & Chat' },
  { name: 'task:fast', recommended: false, speed: 'Schnell' },
];

export function normalizeChatTask(value) {
  return typeof value === 'string' && /^task:[a-zA-Z0-9_-]+$/.test(value)
    ? value : DEFAULT_CHAT_TASK;
}

export function chatTaskOptions(models) {
  const tasks = (models || []).filter(m => normalizeChatTask(m.name) === m.name);
  return tasks.length ? tasks : FALLBACK_CHAT_TASKS;
}

export function modelDisplayName(model) {
  return model.startsWith('task:') ? model : model.split(':')[0];
}

export const selectOptimalModel = (text) => {
  const lower = text.toLowerCase();

  // Entscheidungsmatrix
  const matrix = {
    // Komplexe Aufgaben → task:tool
    complex: [
      'erkläre', 'explain', 'schreibe', 'write', 'code', 'funktion', 'function',
      'programmier', 'develop', 'erstelle eine', 'create a', 'implementier',
      'analyse', 'analyze', 'vergleiche', 'compare', 'zusammenfass', 'summarize',
      'übersetze', 'translate', 'berechne', 'calculate', 'löse', 'solve'
    ],

    // Schnelle Antworten → task:fast
    quick: [
      'hallo', 'hi', 'hey', 'guten tag', 'wie geht', 'danke', 'thanks',
      'ok', 'okay', 'ja', 'yes', 'nein', 'no', 'was ist', 'what is',
      'kurz', 'quick', 'einfach', 'simple'
    ],

    // Code-Generierung → task:tool
    code: [
      'javascript', 'python', 'php', 'html', 'css', 'sql', 'bash',
      'react', 'vue', 'django', 'flask', 'laravel', 'node',
      'class', 'def ', 'function', 'const ', 'let ', 'var '
    ]
  };

  // Prüfe Code-Keywords (höchste Priorität)
  if (matrix.code.some(kw => lower.includes(kw))) {
    return 'task:tool';
  }

  // Prüfe komplexe Aufgaben
  if (matrix.complex.some(kw => lower.includes(kw))) {
    return 'task:tool';
  }

  // Prüfe schnelle Anfragen
  if (matrix.quick.some(kw => lower.includes(kw))) {
    return 'task:fast';
  }

  // Länge als Fallback-Kriterium
  // Kurze Messages (<20 Wörter) → schnelles Model
  // Lange Messages (>20 Wörter) → großes Model
  const wordCount = text.split(/\s+/).length;
  return wordCount < 20 ? 'task:fast' : 'task:tool';
};
