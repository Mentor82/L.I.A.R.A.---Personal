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
    // No `lng` here deliberately - setting it forces that language on every
    // init and skips LanguageDetector entirely (per i18next's own docs),
    // which is why a persisted liara_language selection never survived a
    // reload. Detector below (order: localStorage -> navigator) now
    // actually gets to run; fallbackLng above still covers "detected
    // nothing"/unsupported-language cases.
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
