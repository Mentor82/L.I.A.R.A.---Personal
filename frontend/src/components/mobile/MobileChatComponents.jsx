import React, { useState, useEffect, useRef } from 'react';
import MarkdownMessage from '../MarkdownMessage';
import {
  AgentStepsBlock,
  WebSourcesBlock,
  WorkspaceProposalsBlock,
  WorkspaceArtifactsBlock
} from '../chat/ChatCards';

export function MobileThinkingBlock({ thinking, isAnswering, labelThinking, labelDone }) {
  const [expanded, setExpanded] = useState(!isAnswering);
  const autoCollapsedRef = useRef(isAnswering);

  useEffect(() => {
    if (isAnswering && !autoCollapsedRef.current) {
      autoCollapsedRef.current = true;
      // One-time auto-collapse latch - no render-time equivalent, since after
      // this the user's own manual toggle must be free to override `expanded`.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setExpanded(false);
    }
  }, [isAnswering]);

  if (!thinking) return null;

  return (
    <div className="mobile-thinking-block">
      <button type="button" className="mobile-thinking-toggle" onClick={() => setExpanded((v) => !v)}>
        <span>🧠 {isAnswering ? labelDone : labelThinking}</span>
        <span className="mobile-thinking-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && <div className="mobile-thinking-content">{thinking}</div>}
    </div>
  );
}

export function MobileBubbleFooter({ model, mood, tokens, content, thinking }) {
  if (!model && !tokens && !content) return null;

  let tok = tokens;
  if (!tok && (content || thinking)) {
    const cLen = (content || '').length;
    const tLen = (thinking || '').length;
    const outTok = Math.max(1, Math.round(cLen / 3.8));
    const thinkTok = tLen > 0 ? Math.max(1, Math.round(tLen / 3.8)) : 0;
    const inTok = Math.max(60, outTok + thinkTok);
    tok = {
      in: inTok,
      think: thinkTok,
      out: outTok,
      total: inTok + thinkTok + outTok
    };
  }

  return (
    <div className="mobile-bubble-footer">
      <div className="mobile-bubble-footer-left">
        {model && <span className="mobile-bubble-model">🤖 {model.split(':')[0]}</span>}
        {mood && <span className="mobile-bubble-mood"> · 🌙 {mood}</span>}
      </div>
      {tok && (
        <div
          className="mobile-bubble-tokens"
          title={`Tokens: ${tok.in ?? 0} in, ${tok.think ?? 0} think, ${tok.out ?? 0} out, ${tok.total ?? ((tok.in || 0) + (tok.think || 0) + (tok.out || 0))} gesamt`}
        >
          <span className="token-item"><span className="token-lbl">in:</span> {tok.in ?? 0}</span>
          {Number(tok.think) > 0 && (
            <>
              <span className="token-dot">·</span>
              <span className="token-item"><span className="token-lbl">think:</span> {tok.think}</span>
            </>
          )}
          <span className="token-dot">·</span>
          <span className="token-item"><span className="token-lbl">out:</span> {tok.out ?? 0}</span>
          <span className="token-dot">·</span>
          <span className="token-item token-total-item"><span className="token-lbl">gesamt:</span> {tok.total ?? ((tok.in || 0) + (tok.think || 0) + (tok.out || 0))}</span>
        </div>
      )}
    </div>
  );
}

export function MobileDrawer({
  isOpen,
  onClose,
  onNewChat,
  searchQuery,
  onSearchChange,
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  t
}) {
  if (!isOpen) return null;

  return (
    <div className="mobile-drawer-overlay" onClick={onClose}>
      <aside className="mobile-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="mobile-drawer-header">
          <button className="mobile-new-chat-btn" onClick={onNewChat}>
            <span>➕</span>
            <span>{t('mobile.newChat')}</span>
          </button>
          <button className="mobile-icon-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="mobile-drawer-search">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t('mobile.searchChats')}
          />
        </div>

        <div className="mobile-drawer-list">
          {sessions.length === 0 ? (
            <div className="mobile-drawer-empty">{t('mobile.noChatsFound')}</div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`mobile-session-item ${session.id === activeSessionId ? 'active' : ''}`}
                onClick={() => onSelectSession(session.id)}
              >
                <span className="mobile-session-icon">💬</span>
                <span className="mobile-session-title">{session.title || t('mobile.newChat')}</span>
                <button
                  className="mobile-session-delete"
                  onClick={(e) => onDeleteSession(session.id, e)}
                  title="Löschen"
                >
                  🗑️
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

export function MobileTopBar({
  onOpenDrawer,
  selectedModel,
  modelPickerOpen,
  setModelPickerOpen,
  models,
  onSelectModel,
  onNewChat,
  menuOpen,
  setMenuOpen,
  onSwitchDesktop,
  onNavigateWorkspace,
  onNavigateConfig,
  onLogout,
  t
}) {
  return (
    <header className="mobile-topbar">
      <button className="mobile-icon-btn" onClick={onOpenDrawer} title={t('mobile.history')}>
        ☰
      </button>

      <div className="mobile-model-pill-wrapper">
        <button className="mobile-model-pill" onClick={() => setModelPickerOpen((v) => !v)}>
          <span>{selectedModel.split(':')[0]}</span>
          <span className="mobile-pill-arrow">▾</span>
        </button>

        {modelPickerOpen && (
          <div className="mobile-model-dropdown">
            <div className="mobile-dropdown-header">{t('mobile.model')}</div>
            {models.length === 0 ? (
              <div className="mobile-dropdown-item active">{selectedModel}</div>
            ) : (
              models.map((m) => {
                const name = m.name || m;
                return (
                  <button
                    key={name}
                    className={`mobile-dropdown-item ${name === selectedModel ? 'active' : ''}`}
                    onClick={() => onSelectModel(name)}
                  >
                    <span>{name}</span>
                    {name === selectedModel && <span>✓</span>}
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>

      <div className="mobile-topbar-right">
        <button className="mobile-icon-btn" onClick={onNewChat} title={t('mobile.newChat')}>
          ➕
        </button>
        <button className="mobile-icon-btn" onClick={() => setMenuOpen((v) => !v)} title={t('mobile.settings')}>
          ⋮
        </button>

        {menuOpen && (
          <div className="mobile-menu-dropdown">
            <button className="mobile-menu-item" onClick={onSwitchDesktop}>
              <span>🖥️</span>
              <span>{t('mobile.switchDesktop')}</span>
            </button>
            <button className="mobile-menu-item" onClick={onNavigateWorkspace}>
              <span>🗂️</span>
              <span>{t('mobile.workspace')}</span>
            </button>
            <button className="mobile-menu-item" onClick={onNavigateConfig}>
              <span>⚙️</span>
              <span>{t('mobile.settings')}</span>
            </button>
            {onLogout && (
              <button className="mobile-menu-item danger" onClick={onLogout}>
                <span>🚪</span>
                <span>{t('mobile.logout')}</span>
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
