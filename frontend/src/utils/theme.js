/**
 * Shared theme storage/resolution/application - single source of truth so
 * ThemeToggle.jsx, UserPreferences.jsx and PageLayout.jsx stop each
 * maintaining their own (previously divergent - different localStorage
 * keys, one broken for "system") copy of this logic.
 *
 * The actual flash-of-wrong-theme fix is the blocking inline script in
 * index.html, which duplicates resolveEffectiveTheme's matchMedia logic in
 * plain JS (it must run before any module/bundle exists) - this module is
 * what keeps every React code path consistent with it afterward.
 */

export const THEME_STORAGE_KEY = 'liara_theme';

export function getStoredTheme() {
  return localStorage.getItem(THEME_STORAGE_KEY) || 'system';
}

export function resolveEffectiveTheme(preference) {
  if (preference === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return preference;
}

export function applyTheme(preference) {
  document.documentElement.setAttribute('data-theme', resolveEffectiveTheme(preference));
}
