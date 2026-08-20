import { useState, useEffect } from 'react';
import { tasksAPI, moodAPI, calendarAPI } from '../services/api';
import './Tasks.css';

function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState(localStorage.getItem('tasks_filter') || 'all');
  const [sortBy, setSortBy] = useState(localStorage.getItem('tasks_sort') || 'dueDate');
  const [hideCompleted, setHideCompleted] = useState(localStorage.getItem('tasks_hide_completed') === 'true');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    list: 'Allgemein',
    priority: 'medium',
    due_date: '',
    tags: []
  });
  const [mood, setMood] = useState(null);
  const [availableLists, setAvailableLists] = useState(['Allgemein', 'Arbeit', 'Privat', 'Urlaub']);

  useEffect(() => {
    fetchTasks();
    fetchMood();
  }, [filter]);

  // Save filter and sort preferences
  useEffect(() => {
    localStorage.setItem('tasks_filter', filter);
  }, [filter]);

  useEffect(() => {
    localStorage.setItem('tasks_sort', sortBy);
  }, [sortBy]);

  useEffect(() => {
    localStorage.setItem('tasks_hide_completed', hideCompleted);
  }, [hideCompleted]);

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Failed to fetch mood:', error);
    }
  };

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const filters = {};
      if (filter === 'pending') filters.completed = false;
      if (filter === 'completed') filters.completed = true;
      
      const data = await tasksAPI.getAll(filters);
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newTask.title.trim()) return;

    try {
      await tasksAPI.create(newTask);
      setNewTask({ title: '', description: '', priority: 'medium', tags: [] });
      setShowCreateForm(false);
      fetchTasks();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleComplete = async (taskId, currentStatus) => {
    try {
      // Optimistic update
      setTasks(tasks.map(t => 
        t.id === taskId ? { ...t, completed: !currentStatus } : t
      ));
      
      if (currentStatus) {
        await tasksAPI.uncomplete(taskId);
      } else {
        await tasksAPI.complete(taskId);
      }
      await fetchTasks();
    } catch (error) {
      console.error('Failed to toggle task:', error);
      await fetchTasks(); // Rollback
    }
  };

  const handleDelete = async (taskId) => {
    if (!confirm('Task wirklich löschen?')) return;
    try {
      await tasksAPI.delete(taskId);
      // Optimistic update
      setTasks(tasks.filter(t => t.id !== taskId));
      await fetchTasks();
    } catch (error) {
      console.error('Failed to delete task:', error);
      await fetchTasks();
    }
  };

  const handleEdit = (task) => {
    setEditingTask({
      ...task,
      tags: task.tags || []
    });
    setShowCreateForm(false);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingTask.title.trim()) return;

    try {
      await tasksAPI.update(editingTask.id, {
        title: editingTask.title,
        description: editingTask.description,
        priority: editingTask.priority,
        tags: editingTask.tags
      });
      setEditingTask(null);
      fetchTasks();
    } catch (error) {
      console.error('Failed to update task:', error);
      alert('Fehler beim Aktualisieren: ' + error.message);
    }
  };

  const getMoodEmoji = (moodName) => {
    const emojis = {
      happy: '😊',
      focused: '🎯',
      playful: '😄',
      helpful: '🤝',
      neutral: '😌'
    };
    return emojis[moodName] || '😌';
  };

  const getMoodSuggestion = () => {
    if (!mood) return null;
    const suggestions = {
      focused: { icon: '🎯', text: 'Du bist fokussiert - perfekt für wichtige Tasks!' },
      playful: { icon: '😄', text: 'Spiele mit den Tasks herum - organisiere nach Lust!' },
      helpful: { icon: '🤝', text: 'Denk an Tasks die anderen helfen könnten!' },
      happy: { icon: '😊', text: 'Nutze die gute Laune für produktive Tasks!' }
    };
    return suggestions[mood.current_mood];
  };

  return (
    <div className="tasks-container">
      <div className="tasks-header">
        <div className="header-left">
          <h2>✅ Aufgaben</h2>
          {mood && (
            <div className="mood-indicator-small">
              <span className="mood-emoji-small">{getMoodEmoji(mood.current_mood)}</span>
              <span>{mood.current_mood}</span>
            </div>
          )}
        </div>
        <button 
          className="create-button"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? '✕ Schließen' : '➕ Neue Aufgabe'}
        </button>
      </div>

      {getMoodSuggestion() && (
        <div className="mood-suggestion">
          <span className="mood-suggestion-icon">{getMoodSuggestion().icon}</span>
          <span className="mood-suggestion-text">{getMoodSuggestion().text}</span>
        </div>
      )}

      {showCreateForm && (
        <div className="create-form-panel">
          <form onSubmit={handleCreate} className="task-form">
            <div className="form-row">
              <input
                type="text"
                className="form-input"
                placeholder="Aufgaben-Titel *"
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                required
                autoFocus
              />
              <select
                className="form-select"
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
              >
                <option value="low">🟢 Niedrig</option>
                <option value="medium">🟡 Mittel</option>
                <option value="high">🔴 Hoch</option>
              </select>
            </div>
            <textarea
              className="form-textarea"
              placeholder="Beschreibung (optional)"
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              rows="3"
            />
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={!newTask.title.trim()}>
                ✅ Aufgabe erstellen
              </button>
              <button type="button" className="btn-secondary" onClick={() => setShowCreateForm(false)}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      {editingTask && (
        <div className="create-form-panel">
          <h3>✏️ Aufgabe bearbeiten</h3>
          <form onSubmit={handleUpdate} className="task-form">
            <div className="form-row">
              <input
                type="text"
                className="form-input"
                placeholder="Aufgaben-Titel *"
                value={editingTask.title}
                onChange={(e) => setEditingTask({ ...editingTask, title: e.target.value })}
                required
                autoFocus
              />
              <select
                className="form-select"
                value={editingTask.priority}
                onChange={(e) => setEditingTask({ ...editingTask, priority: e.target.value })}
              >
                <option value="low">🟢 Niedrig</option>
                <option value="medium">🟡 Mittel</option>
                <option value="high">🔴 Hoch</option>
              </select>
            </div>
            <textarea
              className="form-textarea"
              placeholder="Beschreibung (optional)"
              value={editingTask.description || ''}
              onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
              rows="3"
            />
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={!editingTask.title.trim()}>
                💾 Speichern
              </button>
              <button type="button" className="btn-secondary" onClick={() => setEditingTask(null)}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="tasks-list">
        {loading ? (
          <div className="tasks-loading">⏳ Lade Aufgaben...</div>
        ) : tasks.length === 0 ? (
          <div className="tasks-empty">
            <div className="tasks-empty-icon">📋</div>
            <p>Keine Aufgaben vorhanden</p>
            <p style={{fontSize: '0.9rem', color: '#9ca3af'}}>
              Erstelle deine erste Aufgabe mit dem "➕ Neue Aufgabe" Button!
            </p>
          </div>
        ) : (
          tasks.map((task) => (
            <div 
              key={task.id} 
              className={`task-item priority-${task.priority} ${task.completed ? 'completed' : ''}`}
            >
              <input
                type="checkbox"
                className="task-checkbox"
                checked={task.completed}
                onChange={() => handleComplete(task.id, task.completed)}
              />
              
              <div className="task-content">
                <div className="task-title">{task.title}</div>
                {task.description && (
                  <div className="task-description">{task.description}</div>
                )}
                <div className="task-meta">
                  <span className={`task-priority ${task.priority}`}>
                    {task.priority === 'high' ? '🔴' : task.priority === 'medium' ? '🟡' : '🟢'} 
                    {task.priority}
                  </span>
                  {task.tags && task.tags.length > 0 && (
                    task.tags.map((tag, idx) => (
                      <span key={idx} className="task-tag">{tag}</span>
                    ))
                  )}
                </div>
              </div>
              
              <div className="task-actions">
                <button 
                  className="task-btn edit" 
                  onClick={() => handleEdit(task)}
                  title="Bearbeiten"
                >
                  ✏️
                </button>
                <button 
                  className="task-btn delete" 
                  onClick={() => handleDelete(task.id)}
                  title="Löschen"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Tasks;
