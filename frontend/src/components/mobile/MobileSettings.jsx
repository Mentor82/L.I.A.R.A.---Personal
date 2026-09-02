import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useViewMode } from '../../contexts/useViewMode';
import LanguageSwitcher from '../LanguageSwitcher';
import ThemeToggle from '../ThemeToggle';
import liaraLogo from '../../assets/LIARA-LOGO.png';
import './MobileSettings.css';

export default function MobileSettings({ user, onLogout }) {
  const { t } = useTranslation();
  const { setViewMode } = useViewMode();
  const navigate = useNavigate();

  return (
    <div className="mobile-settings-app">
      <header className="mobile-settings-header">
        <button className="mobile-icon-btn" onClick={() => navigate('/')} title="Zurück">
          ← Chat
        </button>
        <span className="mobile-settings-title">⚙️ {t('mobile.settings')}</span>
        <div style={{ width: 32 }} />
      </header>

      <main className="mobile-settings-body">
        {/* User Card */}
        <section className="mobile-settings-card">
          <div className="mobile-user-row">
            <div className="mobile-avatar-big">
              <img src={liaraLogo} alt="LIARA" className="mobile-avatar-big-img" />
            </div>
            <div className="mobile-user-meta">
              <h3>{user?.username || 'Liara User'}</h3>
              <p>{user?.email || 'user@liara.local'}</p>
            </div>
          </div>
        </section>

        {/* View Mode Toggle */}
        <section className="mobile-settings-section">
          <div className="mobile-section-label">{t('mobile.viewMode')}</div>
          <div className="mobile-settings-card">
            <div className="mobile-setting-row" onClick={() => setViewMode('desktop')}>
              <div className="mobile-setting-icon">🖥️</div>
              <div className="mobile-setting-text">
                <span>{t('mobile.switchDesktop')}</span>
                <small>Volle Desktop-Oberfläche anzeigen</small>
              </div>
              <span className="mobile-setting-arrow">▸</span>
            </div>
            <div className="mobile-setting-row active">
              <div className="mobile-setting-icon">📱</div>
              <div className="mobile-setting-text">
                <span>{t('mobile.switchMobile')} (Aktiv)</span>
                <small>Kompakte Ansicht im ChatGPT-Stil</small>
              </div>
              <span className="mobile-check">✓</span>
            </div>
          </div>
        </section>

        {/* Navigation Shortcuts */}
        <section className="mobile-settings-section">
          <div className="mobile-section-label">Navigation</div>
          <div className="mobile-settings-card">
            <div className="mobile-setting-row" onClick={() => navigate('/workspace')}>
              <div className="mobile-setting-icon">🗂️</div>
              <div className="mobile-setting-text">
                <span>{t('mobile.workspace')}</span>
              </div>
              <span className="mobile-setting-arrow">▸</span>
            </div>
            <div className="mobile-setting-row" onClick={() => navigate('/tasks')}>
              <div className="mobile-setting-icon">✅</div>
              <div className="mobile-setting-text">
                <span>{t('tasks.title')}</span>
              </div>
              <span className="mobile-setting-arrow">▸</span>
            </div>
            <div className="mobile-setting-row" onClick={() => navigate('/health')}>
              <div className="mobile-setting-icon">🩺</div>
              <div className="mobile-setting-text">
                <span>{t('mobile.systemHealth')}</span>
              </div>
              <span className="mobile-setting-arrow">▸</span>
            </div>
          </div>
        </section>

        {/* Preferences */}
        <section className="mobile-settings-section">
          <div className="mobile-section-label">Präferenzen</div>
          <div className="mobile-settings-card">
            <div className="mobile-setting-row no-hover">
              <div className="mobile-setting-icon">🌐</div>
              <div className="mobile-setting-text">
                <span>{t('nav.language')}</span>
              </div>
              <LanguageSwitcher />
            </div>
            <div className="mobile-setting-row no-hover">
              <div className="mobile-setting-icon">🎨</div>
              <div className="mobile-setting-text">
                <span>{t('mobile.appearance')}</span>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </section>

        {/* Logout */}
        {onLogout && (
          <section className="mobile-settings-section">
            <button className="mobile-logout-btn" onClick={onLogout}>
              🚪 {t('mobile.logout')}
            </button>
          </section>
        )}
      </main>
    </div>
  );
}
