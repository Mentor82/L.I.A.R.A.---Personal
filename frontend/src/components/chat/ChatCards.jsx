import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import MarkdownMessage from '../MarkdownMessage';

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

export function TaskListBlock({ tasks }) {
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
              <input type="checkbox" checked={item.done} disabled readOnly />
              <span>{renderInlineMarkdown(item.label)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const AGENT_STEP_ICON = { running: '⏳', done: '✅', error: '❌' };

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

function formatSourceDate(published_at) {
  if (!published_at) return null;
  try {
    return new Date(published_at).toLocaleDateString('de-DE', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return null;
  }
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

const FACTCHECK_ICON = { 'bestätigt': '✓', 'teilweise': '△', 'unbestätigt': '✗' };
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

const PROPOSAL_ACTION_LABELS = {
  create: 'anlegen', update: 'überschreiben', delete: 'löschen',
  install: 'installieren', remove: 'entfernen',
};

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

export function SessionContextBar({ messages, modelName }) {
  const limit = getModelContextLimit(modelName);
  
  let totalTokens = 0;
  if (messages && messages.length > 0) {
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

  const tooltip = `📊 Kontext-Budget & Auto-Summarize:\n• Aktuell: ${totalTokens.toLocaleString()} / ${limit.toLocaleString()} Tokens (${percent}%)\n• Status: ${statusText}\n• Auto-Kompaktierung: Aktiv ab ${thresholdPercent}% (${thresholdTokens.toLocaleString()} Tokens)\n• Modell: ${modelName || 'Standard'}`;

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
