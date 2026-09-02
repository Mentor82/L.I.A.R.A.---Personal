import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import MarkdownMessage from '../MarkdownMessage';
import {
  renderInlineMarkdown,
  AGENT_STEP_ICON,
  formatSourceDate,
  FACTCHECK_ICON,
  PROPOSAL_ACTION_LABELS,
  getModelContextLimit
} from './chatCardHelpers';

// `onToggle` is only wired up once the message has a real DB id (persisted -
// see Chat.jsx's 'persisted' SSE handler) so a checklist still being
// streamed live can't be checked off into a message that doesn't exist yet.
export function TaskListBlock({ tasks, onToggle }) {
  const [expanded, setExpanded] = useState(true);
  if (!tasks || tasks.length === 0) return null;

  return (
    <div className="task-list-block">
      <button type="button" className="task-list-toggle" onClick={() => setExpanded((e) => !e)}>
        <span>📋 Aufgaben</span>
        <span className="task-list-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <ul className="task-list-content">
          {tasks.map((item) => (
            <li key={item.id} className={`task-list-item ${item.done ? 'done' : ''}`}>
              <input
                type="checkbox"
                checked={!!item.done}
                disabled={!onToggle}
                onChange={onToggle ? () => onToggle(item.id, !item.done) : undefined}
              />
              <span>{renderInlineMarkdown(item.label)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AgentStepsBlock({ steps }) {
  const [expanded, setExpanded] = useState(true);
  if (!steps || steps.length === 0) return null;

  return (
    <div className="agent-steps-block">
      <button type="button" className="agent-steps-toggle" onClick={() => setExpanded((e) => !e)}>
        <span>⚙️ Agent</span>
        <span className="agent-steps-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <ul className="agent-steps-content">
          {steps.map((step) => (
            <li key={step.id} className={`agent-steps-item ${step.status}`}>
              <span className="agent-steps-icon">{AGENT_STEP_ICON[step.status] || '•'}</span>
              <span>{step.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function WebSourcesBlock({ sources }) {
  const [expanded, setExpanded] = useState(true);
  if (!sources || sources.length === 0) return null;

  return (
    <div className="web-sources-block">
      <button type="button" className="web-sources-toggle" onClick={() => setExpanded((e) => !e)}>
        <span>📚 Quellen ({sources.length})</span>
        <span className="web-sources-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <ul className="web-sources-content">
          {sources.map((source) => (
            <li key={source.id} className="web-sources-item">
              <a href={source.url} target="_blank" rel="noopener noreferrer" className="web-sources-title">
                {source.title || source.url}
              </a>
              <div className="web-sources-meta">
                <span className="web-sources-domain">{source.domain}</span>
                {source.dated ? (
                  <span className="web-sources-date">{formatSourceDate(source.published_at)}</span>
                ) : (
                  <span className="web-sources-date web-sources-undated">kein Datum</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const FACTCHECK_CLASS = { 'bestätigt': 'confirmed', 'teilweise': 'partial', 'unbestätigt': 'unverified' };

export function FactCheckBlock({ items }) {
  const [userToggled, setUserToggled] = useState(null);
  if (!items || items.length === 0) return null;

  const hasLowerConfidence = items.some((item) => item.confidence !== 'bestätigt');
  const expanded = userToggled !== null ? userToggled : hasLowerConfidence;

  return (
    <div className="factcheck-block">
      <button type="button" className="factcheck-toggle" onClick={() => setUserToggled(!expanded)}>
        <span>🔎 Faktencheck ({items.length})</span>
        <span className="factcheck-caret">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <ul className="factcheck-content">
          {items.map((item) => (
            <li key={item.id} className={`factcheck-item ${FACTCHECK_CLASS[item.confidence] || ''}`}>
              <span className="factcheck-icon">{FACTCHECK_ICON[item.confidence] || '•'}</span>
              <span className="factcheck-label">{renderInlineMarkdown(item.label)}</span>
              {item.source && <span className="factcheck-source">{item.source}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function WorkspaceProposalsBlock({ proposals }) {
  if (!proposals || proposals.length === 0) return null;

  return (
    <div className="web-sources-block">
      <div className="web-sources-toggle" style={{ cursor: 'default' }}>
        <span>📝 Workspace-Vorschläge ({proposals.length})</span>
      </div>
      <ul className="web-sources-content">
        {proposals.map((p) => (
          <li key={p.proposal_id} className="web-sources-item">
            <span className="web-sources-title">
              {p.filename} {PROPOSAL_ACTION_LABELS[p.action] || p.action}
            </span>
            <div className="web-sources-meta">
              <Link to="/workspace" className="web-sources-domain">Im Workspace prüfen →</Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function WorkspaceArtifactsBlock({ artifacts }) {
  if (!artifacts || artifacts.length === 0) return null;

  return (
    <div className="web-sources-block">
      <div className="web-sources-toggle" style={{ cursor: 'default' }}>
        <span>📄 Erstellte Dokumente ({artifacts.length})</span>
      </div>
      <ul className="web-sources-content">
        {artifacts.map((a, i) => (
          <li key={i} className="web-sources-item">
            <span className="web-sources-title">{a.title}</span>
            <div className="web-sources-meta">
              {a.filename ? (
                <Link to="/workspace" state={{ openWorkspaceFile: a.filename }} className="web-sources-domain">
                  {a.filename} im Workspace öffnen →
                </Link>
              ) : (
                <MarkdownMessage content={a.content} />
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ChatBubbleFooter({ model, mood, tokens, content, thinking }) {
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
    <div className="bubble-footer">
      <div className="bubble-footer-left">
        {model && <span className="bubble-model">🤖 {model}</span>}
        {mood && <span className="bubble-mood"> · 🌙 {mood}</span>}
      </div>
      {tok && (
        <div
          className="bubble-tokens"
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

export function SessionContextBar({ messages, modelName, contextInfo }) {
  // contextInfo (from the backend's own ContextBudgetManager, via the SSE
  // 'metadata' event) is the real, post-compaction prompt size for the last
  // turn - preferred whenever available. The client-side sum-over-all-
  // messages estimate below is only a fallback for before the first turn in
  // this session has round-tripped since page load (a fresh page load, or a
  // session just switched to) - it never reflected server-side compaction,
  // so it only ever grew, even long after compaction kept the real prompt
  // bounded.
  const usingRealValue = contextInfo?.tokens != null && contextInfo?.limit != null;
  const limit = usingRealValue ? contextInfo.limit : getModelContextLimit(modelName);

  let totalTokens = 0;
  if (usingRealValue) {
    totalTokens = contextInfo.tokens;
  } else if (messages && messages.length > 0) {
    totalTokens = messages.reduce((acc, m) => {
      if (m.tokens?.total) return acc + m.tokens.total;
      if (m.tokens?.in || m.tokens?.out) return acc + (m.tokens.in || 0) + (m.tokens.out || 0) + (m.tokens.think || 0);
      const textLen = (m.content || m.text || '').length + (m.thinking || '').length;
      return acc + Math.max(1, Math.round(textLen / 3.8)) + 4;
    }, 0);
  }

  const fillRatio = Math.min(1.0, totalTokens / limit);
  const percent = Math.round(fillRatio * 100);
  const thresholdPercent = 70;
  const thresholdTokens = Math.round(limit * 0.7);

  let statusText = 'Normal (< 55%)';
  let fillColor = 'linear-gradient(90deg, #00e5ff, #3b82f6)';
  if (percent >= 70) {
    statusText = 'Kompaktierung aktiv (≥ 70%)';
    fillColor = 'linear-gradient(90deg, #ec4899, #8b5cf6)';
  } else if (percent >= 55) {
    statusText = 'Vorbereitung (55–70%)';
    fillColor = 'linear-gradient(90deg, #f59e0b, #eab308)';
  }

  const formatTok = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);

  const sourceNote = usingRealValue
    ? 'tatsächlicher Prompt-Umfang nach Kompaktierung (Server)'
    : 'grobe Schätzung - wird nach der ersten Antwort in dieser Session durch den echten Wert ersetzt';
  const tooltip = `📊 Kontext-Budget & Auto-Summarize:\n• Aktuell: ${totalTokens.toLocaleString()} / ${limit.toLocaleString()} Tokens (${percent}%)\n• Quelle: ${sourceNote}\n• Status: ${statusText}\n• Auto-Kompaktierung: Aktiv ab ${thresholdPercent}% (${thresholdTokens.toLocaleString()} Tokens)\n• Modell: ${modelName || 'Standard'}`;

  return (
    <div className="session-context-bar" title={tooltip}>
      <span className="context-bar-icon">🧠</span>
      <div className="context-bar-track">
        <div
          className="context-bar-fill"
          style={{ width: `${Math.max(4, percent)}%`, background: fillColor }}
        />
        <div className="context-bar-threshold-marker" title="Auto-Kompaktierungs-Grenze (70%)" />
      </div>
      <span className="context-bar-label">{formatTok(totalTokens)}/{formatTok(limit)}</span>
    </div>
  );
}
