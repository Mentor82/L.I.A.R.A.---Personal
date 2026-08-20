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

export default i18n;
