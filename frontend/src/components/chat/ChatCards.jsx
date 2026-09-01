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

export function ChatBubbleFooter({ model, mood, tokens }) {
  if (!model && !tokens) return null;

  return (
    <div className="bubble-footer">
      <div className="bubble-footer-left">
        {model && <span className="bubble-model">🤖 {model}</span>}
        {mood && <span className="bubble-mood"> · 🌙 {mood}</span>}
      </div>
      {tokens && (
        <div
          className="bubble-tokens"
          title={`Tokens: ${tokens.in ?? 0} in, ${tokens.think ?? 0} think, ${tokens.out ?? 0} out, ${tokens.total ?? ((tokens.in || 0) + (tokens.think || 0) + (tokens.out || 0))} gesamt`}
        >
          <span className="token-item"><span className="token-lbl">in:</span> {tokens.in ?? 0}</span>
          {Number(tokens.think) > 0 && (
            <>
              <span className="token-dot">·</span>
              <span className="token-item"><span className="token-lbl">think:</span> {tokens.think}</span>
            </>
          )}
          <span className="token-dot">·</span>
          <span className="token-item"><span className="token-lbl">out:</span> {tokens.out ?? 0}</span>
          <span className="token-dot">·</span>
          <span className="token-item token-total-item"><span className="token-lbl">gesamt:</span> {tokens.total ?? ((tokens.in || 0) + (tokens.think || 0) + (tokens.out || 0))}</span>
        </div>
      )}
    </div>
  );
}
