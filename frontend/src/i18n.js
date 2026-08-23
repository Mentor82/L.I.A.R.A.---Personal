import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translations
import deTranslation from './locales/de.json';
import enTranslation from './locales/en.json';

const resources = {
  de: {
    translation: deTranslation
  },
  en: {
    translation: enTranslation
  }
};

i18n
  .use(LanguageDetector) // Detects user language
  .use(initReactI18next) // Passes i18n down to react-i18next
  .init({
    resources,
    fallbackLng: 'de', // Default language
    lng: 'de', // Force German as initial language
    debug: false,
    
    interpolation: {
      escapeValue: false // React already does escaping
    },
    
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'liara_language'
    }
  });

// Keep <html lang> in sync with the active UI language - previously never
// set at all (index.html's lang="en" was static regardless of the
// selected locale). Covers both the initial load and every later switch
// via LanguageSwitcher.jsx (which already calls i18n.changeLanguage(),
// firing this same event) with no changes needed there.
document.documentElement.lang = i18n.language;
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng;
});

export default i18n;
