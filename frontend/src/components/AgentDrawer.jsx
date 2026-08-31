import { useState, useEffect, useRef } from 'react';
import { agentAPI, chatAPI } from '../services/api';
import MarkdownMessage from './MarkdownMessage';
import './AgentDrawer.css';

export default function AgentDrawer({ sessionId, onClose, onFilesChanged }) {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('code');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [taskPrompt, setTaskPrompt] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [stepEvents, setStepEvents] = useState([]);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const eventsEndRef = useRef(null);

  // 1. Agenten-Profile & verfügbare Modelle laden
  useEffect(() => {
    agentAPI.getTypes()
      .then((data) => {
        if (data?.agents?.length) {
          setAgents(data.agents);
          const defaultAgent = data.agents[0];
          setSelectedAgent(defaultAgent.id);
          setSelectedModel(defaultAgent.default_model);
        }
      })
      .catch((err) => console.error('Fehler beim Laden der Agenten-Typen:', err));

    chatAPI.getModels()
      .then((data) => setModels(data?.models || []))
      .catch(() => setModels([]));
  }, []);

  // Automatisch zum letzten Event scrollen
  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [stepEvents, finalAnswer]);

  const handleAgentChange = (agentId) => {
    setSelectedAgent(agentId);
    const profile = agents.find((a) => a.id === agentId);
    if (profile) {
      setSelectedModel(profile.default_model);
    }
  };

  const startTask = async () => {
    if (!taskPrompt.trim() || isRunning) return;

    setError(null);
    setFinalAnswer(null);
    setStepEvents([]);
    setCurrentStep(0);
    setIsRunning(true);

    try {
      // 1. Task im Backend starten
      const res = await agentAPI.runTask({
        agent_id: selectedAgent,
        task: taskPrompt,
        session_id: sessionId,
        model: selectedModel || undefined,
        max_steps: 15,
      });

      if (!res?.task_id) {
        throw new Error('Keine Task-ID vom Server erhalten.');
      }

      const taskId = res.task_id;
      setCurrentTaskId(taskId);

      // 2. SSE Stream abhören
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
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Unvollständigen Rest behalten

        for (const block of lines) {
          const trimmed = block.trim();
          if (!trimmed || trimmed.startsWith(':')) continue; // Keep-alive ignorieren

          const dataLine = trimmed.split('\n').find((l) => l.startsWith('data: '));
          if (!dataLine) continue;

          try {
            const eventPayload = JSON.parse(dataLine.slice(6));
            handleIncomingEvent(eventPayload);
          } catch (e) {
            console.warn('Fehler beim Parsen des SSE Events:', e);
          }
        }
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
      setIsRunning(false);
    } else if (type === 'error') {
      setError(data.error);
      setIsRunning(false);
    } else if (type === 'timeout') {
      setError(data.message);
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
    <aside className="agent-drawer">
      {/* Header */}
      <div className="agent-drawer-header">
        <div className="agent-drawer-title">
          <span className="agent-drawer-icon">{currentProfile.icon || '🤖'}</span>
          <div>
            <h3>Autonomous Agents</h3>
            <p className="agent-drawer-subtitle">{currentProfile.name || 'Liara Agent Engine'}</p>
          </div>
        </div>
        <button className="agent-drawer-close" onClick={onClose} title="Schließen">✕</button>
      </div>

      {/* Profile & Model Config */}
      <div className="agent-drawer-config">
        <div className="agent-profile-selector">
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={`agent-profile-btn ${selectedAgent === agent.id ? 'active' : ''}`}
              onClick={() => handleAgentChange(agent.id)}
              disabled={isRunning}
            >
              <span className="profile-btn-icon">{agent.icon}</span>
              <span className="profile-btn-label">{agent.name}</span>
            </button>
          ))}
        </div>

        <div className="agent-model-row">
          <label htmlFor="agent-model-select">Modell:</label>
          <select
            id="agent-model-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={isRunning}
          >
            {models.length > 0 ? (
              models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name} {m.details?.parameter_size ? `(${m.details.parameter_size})` : ''}
                </option>
              ))
            ) : (
              <option value={selectedModel}>{selectedModel || 'qwen2.5-coder:7b'}</option>
            )}
          </select>
        </div>

        <div className="agent-tools-preview">
          <span className="tools-preview-label">ACI Tools:</span>
          <div className="tools-tag-list">
            {(currentProfile.tools || []).map((tool) => (
              <span key={tool} className="tool-tag">
                {tool}
              </span>
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
              ? 'z. B. "Analysiere helper.py, behebe den Fehler in add() und prüfe die Syntax."'
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
          ) : (
            <button className="agent-btn primary" onClick={startTask} disabled={!taskPrompt.trim()}>
              ▶ Task ausführen <kbd>Ctrl+Enter</kbd>
            </button>
          )}
        </div>
      </div>

      {/* Execution Trace Timeline */}
      <div className="agent-trace-container">
        <div className="agent-trace-header">
          <span>Ausführungs-Protokoll</span>
          {isRunning && <span className="agent-status-badge running">⚡ Schritt {currentStep} läuft...</span>}
          {!isRunning && finalAnswer && <span className="agent-status-badge done">✅ Abgeschlossen</span>}
          {!isRunning && error && <span className="agent-status-badge error">❌ Fehler</span>}
        </div>

        <div className="agent-trace-list">
          {stepEvents.length === 0 && !isRunning && !finalAnswer && !error && (
            <div className="agent-trace-empty">
              <p>Noch keine Task-Ausführung aktiv.</p>
              <span className="trace-hint">Gib oben eine Aufgabe ein und starte den Agenten.</span>
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
                <MarkdownMessage content={finalAnswer} />
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="trace-error-card">
              <span className="trace-icon">⚠️</span>
              <p>{error}</p>
            </div>
          )}

          <div ref={eventsEndRef} />
        </div>
      </div>
    </aside>
  );
}
