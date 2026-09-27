import { useState, useEffect } from 'react';
import { chatAPI } from '../services/api';
import WorkspaceChatView from './WorkspaceChatView';
import WorkspaceAgentHubView from './WorkspaceAgentHubView';
import './WorkspaceChatPanel.css';

/**
 * Unified Workspace Copilot & Agent Panel.
 * 
 * Provides a single, cohesive sidebar panel with two complementary modes:
 * - 💬 Chat: Conversational Copilot for questions, code discussions, unit tests, and inline edits.
 * - 🤖 Agent Hub: Autonomous ReAct Agent for multi-step tasks, file exploration, code edits, and tools.
 */
export default function WorkspaceChatPanel({
  sessionId,
  initialMode = 'chat',
  activeTab,
  activeTabData,
  files = [],
  onToggleContext,
  onOpenFile,
  onInsertCode,
  onClose,
  onWorkspaceProposal,
  onApproveProposal,
  onRejectProposal,
  onFilesChanged,
  onSessionCreated,
}) {
  const [mode, setMode] = useState(initialMode);
  const [transferredMessage, setTransferredMessage] = useState(null);

  // Model selection (persisted to localStorage)
  const [models, setModels] = useState([]);
  const [model, setModel] = useState(() => localStorage.getItem('liara_selected_model') || 'llama3.2:3b');

  useEffect(() => {
    chatAPI.getModels()
      .then((data) => setModels(data?.models || []))
      .catch(() => setModels([]));
  }, []);

  useEffect(() => {
    if (initialMode) {
      setMode(initialMode);
    }
  }, [initialMode]);

  const changeModel = (value) => {
    setModel(value);
    localStorage.setItem('liara_selected_model', value);
  };

  const handleNewSession = async () => {
    try {
      const fresh = await chatAPI.createSession('Workspace Chat');
      if (fresh?.id && onSessionCreated) {
        onSessionCreated(fresh);
      }
    } catch (err) {
      console.error('Fehler beim Erstellen einer neuen Chat-Session:', err);
    }
  };

  const handleTransferToChat = (task, answer) => {
    setTransferredMessage({ task, answer });
    setMode('chat');
  };

  return (
    <aside className="workspace-chat-panel">
      {/* Header with Mode Tabs */}
      <div className="workspace-chat-header">
        <div className="workspace-copilot-tabs">
          <button
            className={`workspace-copilot-tab-btn ${mode === 'chat' ? 'active' : ''}`}
            onClick={() => setMode('chat')}
            title="Chat-Modus für Fragen und Erklärungen"
          >
            <span>💬 Chat</span>
          </button>
          <button
            className={`workspace-copilot-tab-btn ${mode === 'agent' ? 'active' : ''}`}
            onClick={() => setMode('agent')}
            title="Autonome Agenten für mehrschrittige Aufgaben"
          >
            <span>🤖 Agent Hub</span>
          </button>
        </div>

        <div className="workspace-chat-header-actions">
          <select
            className="workspace-chat-model-select"
            value={model}
            onChange={(e) => changeModel(e.target.value)}
            title="Modell auswählen"
          >
            {models.length === 0 && <option value={model}>{model}</option>}
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} {m.details?.parameter_size ? `(${m.details.parameter_size})` : ''}
              </option>
            ))}
          </select>

          {mode === 'chat' && (
            <button
              className="workspace-chat-icon-btn"
              title="Neue Chat-Session starten"
              onClick={handleNewSession}
            >
              +
            </button>
          )}

          <button
            className="workspace-chat-icon-btn"
            title="Copilot-Panel schließen"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {mode === 'chat' ? (
        <WorkspaceChatView
          sessionId={sessionId}
          model={model}
          activeTab={activeTab}
          activeTabData={activeTabData}
          files={files}
          onToggleContext={onToggleContext}
          onOpenFile={onOpenFile}
          onInsertCode={onInsertCode}
          onWorkspaceProposal={onWorkspaceProposal}
          onApproveProposal={onApproveProposal}
          onRejectProposal={onRejectProposal}
          transferredMessage={transferredMessage}
          onClearTransferredMessage={() => setTransferredMessage(null)}
        />
      ) : (
        <WorkspaceAgentHubView
          sessionId={sessionId}
          models={models}
          selectedModel={model}
          onModelChange={changeModel}
          onOpenFile={onOpenFile}
          onFilesChanged={onFilesChanged}
          onTransferToChat={handleTransferToChat}
        />
      )}
    </aside>
  );
}
