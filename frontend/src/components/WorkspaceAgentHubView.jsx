import { useState, useEffect, useRef } from 'react';
import { agentAPI, chatAPI } from '../services/api';
import { parseSSEStream } from '../services/sseClient';
import MarkdownMessage from './MarkdownMessage';

/**
 * Autonomous Agent Hub tab for the Workspace Copilot Panel.
 * Runs multi-step autonomous tasks (Code, Research, Vision, Productivity).
 */
export default function WorkspaceAgentHubView({
  sessionId,
  models = [],
  selectedModel,
  onModelChange,
  onOpenFile,
  onFilesChanged,
  onTransferToChat
}) {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('code');
  const [taskPrompt, setTaskPrompt] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [stepEvents, setStepEvents] = useState([]);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [finalAnswerFile, setFinalAnswerFile] = useState(null);
  const [error, setError] = useState(null);
  const [paused, setPaused] = useState(false);
  const [pauseSummary, setPauseSummary] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const eventsEndRef = useRef(null);

  useEffect(() => {
    agentAPI.getTypes()
      .then((data) => {
        if (data?.agents?.length) {
          setAgents(data.agents);
          const defaultAgent = data.agents[0];
          setSelectedAgent(defaultAgent.id);
          if (defaultAgent.default_model && onModelChange) {
            onModelChange(defaultAgent.default_model);
          }
        }
      })
      .catch((err) => console.error('Fehler beim Laden der Agenten-Typen:', err));
  }, []);

  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [stepEvents, finalAnswer, isRunning]);

  const handleAgentChange = (agentId) => {
    setSelectedAgent(agentId);
    const profile = agents.find((a) => a.id === agentId);
    if (profile?.default_model && onModelChange) {
      onModelChange(profile.default_model);
    }
  };

  const startTask = async ({ resume = false } = {}) => {
    if (isRunning) return;
    if (!resume && !taskPrompt.trim()) return;

    setError(null);
    setFinalAnswer(null);
    setFinalAnswerFile(null);
    setPaused(false);
    setPauseSummary(null);
    if (!resume) {
      setStepEvents([]);
      setCurrentStep(0);
    }
    setIsRunning(true);

    try {
      const res = await agentAPI.runTask({
        agent_id: selectedAgent,
        task: taskPrompt,
        session_id: sessionId,
        model: selectedModel || undefined,
        max_steps: 15,
        resume,
      });

      if (!res?.task_id) {
        throw new Error('Keine Task-ID vom Server erhalten.');
      }

      const taskId = res.task_id;
      setCurrentTaskId(taskId);

      const token = localStorage.getItem('liara_token');
      const response = await fetch(`/api/agents/tasks/${taskId}/stream`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });

      if (!response.ok) {
        throw new Error(`SSE Verbindung fehlgeschlagen (HTTP ${response.status})`);
      }

      const reader = response.body.getReader();
      for await (const eventPayload of parseSSEStream(reader)) {
        handleIncomingEvent(eventPayload);
      }
    } catch (err) {
      console.error('Agent Task Fehler:', err);
      setError(err.message || 'Fehler beim Ausführen des Agenten.');
    } finally {
      setIsRunning(false);
      onFilesChanged?.();
    }
  };

  const handleIncomingEvent = (event) => {
    const { event: type, data, timestamp } = event;

    if (type === 'step_start') {
      setCurrentStep(data.step);
    } else if (type === 'thought') {
      setStepEvents((prev) => [...prev, { type: 'thought', text: data.thought, step: data.step, timestamp }]);
    } else if (type === 'tool_call') {
      setStepEvents((prev) => [
        ...prev,
        { type: 'tool_call', tool: data.tool, args: data.arguments, step: data.step, timestamp },
      ]);
    } else if (type === 'tool_result') {
      setStepEvents((prev) => [
        ...prev,
        { type: 'tool_result', tool: data.tool, result: data.result, step: data.step, timestamp },
      ]);
    } else if (type === 'done') {
      setFinalAnswer(data.answer);
      setFinalAnswerFile(data.answer_file || null);
      setIsRunning(false);
    } else if (type === 'error') {
      setError(data.error);
      setIsRunning(false);
    } else if (type === 'paused') {
      setPaused(true);
      setPauseSummary(data.summary || null);
      setIsRunning(false);
    }
  };

  const cancelTask = async () => {
    if (!currentTaskId || !isRunning) return;
    try {
      await agentAPI.cancelTask(currentTaskId);
      setIsRunning(false);
      setError('Task durch Benutzer abgebrochen.');
    } catch (err) {
      console.error('Fehler beim Abbrechen:', err);
    }
  };

  const currentProfile = agents.find((a) => a.id === selectedAgent) || {};

  return (
    <div className="workspace-agent-hub-view">
      {/* Profile Selector */}
      <div className="agent-hub-config">
        <div className="agent-profile-selector">
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={`agent-profile-btn ${selectedAgent === agent.id ? 'active' : ''}`}
              onClick={() => handleAgentChange(agent.id)}
              disabled={isRunning}
              title={agent.description}
            >
              <span className="profile-btn-icon">{agent.icon}</span>
              <span className="profile-btn-label">{agent.name}</span>
            </button>
          ))}
        </div>

        <div className="agent-tools-preview">
          <span className="tools-preview-label">Fähigkeiten:</span>
          <div className="tools-tag-list">
            {(currentProfile.tools || []).map((tool) => (
              <span key={tool} className="tool-tag">{tool}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Task Prompt Input */}
      <div className="agent-prompt-section">
        <textarea
          className="agent-prompt-input"
          placeholder={
            selectedAgent === 'code'
              ? 'z. B. "Analysiere helper.py, behebe den Syntaxfehler und teste das Skript."'
              : 'z. B. "Recherchiere die Unterschiede zwischen FastAPI und Flask mit Quellen."'
          }
          value={taskPrompt}
          onChange={(e) => setTaskPrompt(e.target.value)}
          disabled={isRunning}
          rows={3}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              startTask();
            }
          }}
        />
        <div className="agent-prompt-actions">
          {isRunning ? (
            <button className="agent-btn danger" onClick={cancelTask}>
              ⏹ Stoppen (Schritt {currentStep})
            </button>
          ) : paused ? (
            <>
              <button className="agent-btn primary" onClick={() => startTask({ resume: true })}>
                ▶ Fortsetzen
              </button>
              <button className="agent-btn secondary" onClick={() => startTask()} disabled={!taskPrompt.trim()}>
                Neue Aufgabe starten
              </button>
            </>
          ) : (
            <button className="agent-btn primary" onClick={() => startTask()} disabled={!taskPrompt.trim()}>
              ▶ Task ausführen <kbd>Ctrl+↵</kbd>
            </button>
          )}
        </div>
      </div>

      {/* Execution Trace Timeline */}
      <div className="agent-trace-container">
        <div className="agent-trace-header">
          <span>Ausführungs-Protokoll</span>
          {isRunning && <span className="agent-status-badge running">⚡ Schritt {currentStep} läuft…</span>}
          {!isRunning && finalAnswer && <span className="agent-status-badge done">✅ Abgeschlossen</span>}
          {!isRunning && paused && <span className="agent-status-badge paused">⏸ Pausiert</span>}
          {!isRunning && error && !paused && <span className="agent-status-badge error">❌ Fehler</span>}
        </div>

        <div className="agent-trace-list">
          {stepEvents.length === 0 && !isRunning && !finalAnswer && !error && !paused && (
            <div className="agent-trace-empty">
              <p>Noch keine Task-Ausführung aktiv.</p>
              <span className="trace-hint">Gib oben eine Aufgabe ein und starte den Agenten.</span>
            </div>
          )}

          {paused && !isRunning && (
            <div className="trace-paused-card">
              <p><strong>Schritt-Budget erreicht.</strong></p>
              {pauseSummary && <p className="trace-pause-summary">{pauseSummary}</p>}
              <span className="trace-hint">Klick "Fortsetzen" - der Agent knüpft am gespeicherten Stand an.</span>
            </div>
          )}

          {stepEvents.map((evt, idx) => (
            <div key={idx} className={`trace-event-card ${evt.type}`}>
              {evt.type === 'thought' && (
                <div className="trace-thought">
                  <div className="trace-event-title">
                    <span className="trace-icon">🧠</span>
                    <strong>Gedanke (Schritt {evt.step}):</strong>
                  </div>
                  <p className="trace-thought-text">{evt.text}</p>
                </div>
              )}

              {evt.type === 'tool_call' && (
                <div className="trace-tool-call">
                  <div className="trace-event-title">
                    <span className="trace-icon">🛠</span>
                    <strong>Tool: <code>{evt.tool}</code></strong>
                  </div>
                  <pre className="trace-args-code">{JSON.stringify(evt.args, null, 2)}</pre>
                </div>
              )}

              {evt.type === 'tool_result' && (
                <div className="trace-tool-result">
                  <div className="trace-event-title">
                    <span className="trace-icon">📋</span>
                    <strong>Observation: <code>{evt.tool}</code></strong>
                  </div>
                  <pre className="trace-result-code">
                    {typeof evt.result === 'object' ? JSON.stringify(evt.result, null, 2) : evt.result}
                  </pre>
                </div>
              )}
            </div>
          ))}

          {/* Final Answer */}
          {finalAnswer && (
            <div className="trace-final-answer">
              <div className="trace-event-title success">
                <span className="trace-icon">🎯</span>
                <strong>Endergebnis:</strong>
              </div>
              <div className="trace-final-content">
                <MarkdownMessage content={finalAnswer} sessionId={sessionId} />
              </div>

              <div className="trace-final-actions">
                {finalAnswerFile && (
                  <button
                    className="agent-btn secondary"
                    onClick={() => onOpenFile?.(finalAnswerFile)}
                  >
                    📄 {finalAnswerFile} im Editor öffnen
                  </button>
                )}
                {onTransferToChat && (
                  <button
                    className="agent-btn primary"
                    onClick={() => onTransferToChat(taskPrompt, finalAnswer)}
                    title="Ergebnis als Nachricht in den Chatverlauf übernehmen für Anschlussfragen"
                  >
                    💬 In Chatverlauf übernehmen
                  </button>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="trace-error-card">
              <span className="trace-icon">⚠️</span>
              <p>{error}</p>
            </div>
          )}

          <div ref={eventsEndRef} />
        </div>
      </div>
    </div>
  );
}
