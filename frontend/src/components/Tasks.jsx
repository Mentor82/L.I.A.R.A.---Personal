import { useState, useEffect, useRef } from 'react';
import { tasksAPI, moodAPI, calendarAPI } from '../services/api';
import './Tasks.css';

// TaskCard Component with modern design
function TaskCard({ task, onComplete, onEdit, onDelete, onCreateEvent }) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  const getListFromTags = (tags) => {
    if (!tags || tags.length === 0) return 'Allgemein';
    const availableLists = ['Allgemein', 'Arbeit', 'Privat', 'Urlaub', 'Einkaufen', 'Gesundheit'];
    const listTag = tags.find(tag => availableLists.includes(tag));
    return listTag || tags[0] || 'Allgemein';
  };

  const formatDueDate = (dueDateStr) => {
    if (!dueDateStr) return null;
    const dueDate = new Date(dueDateStr);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
    const dueDay = new Date(dueDate.getFullYear(), dueDate.getMonth(), dueDate.getDate());

    let dateStr = '';
    if (dueDay.getTime() === today.getTime()) {
      dateStr = 'Heute';
    } else if (dueDay.getTime() === tomorrow.getTime()) {
      dateStr = 'Morgen';
    } else {
      dateStr = dueDate.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    const timeStr = dueDate.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    const isOverdue = dueDate < now && !task.completed;
    
    return { dateStr, timeStr, isOverdue };
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: '#EF4444',
      medium: '#F59E0B',
      low: '#10B981'
    };
    return colors[priority] || colors.medium;
  };

  const getPriorityLabel = (priority) => {
    const labels = {
      high: 'Hoch',
      medium: 'Mittel',
      low: 'Niedrig'
    };
    return labels[priority] || 'Mittel';
  };

  const taskList = getListFromTags(task.tags);
  const dueInfo = formatDueDate(task.due_date);
  const categoryColor = '#667eea'; // Default blue for category

  return (
    <div
      className={`task-card ${task.completed ? 'task-card-completed' : ''} ${dueInfo?.isOverdue ? 'task-card-overdue' : ''} ${showMenu ? 'task-card-menu-active' : ''}`}
      style={{ '--priority-color': getPriorityColor(task.priority) }}
    >
      {/* Left Zone: Checkbox + Content */}
      <div className="task-card-main" onClick={() => !showMenu && onComplete(task.id, task.completed)}>
        <div className="task-checkbox-wrapper">
          <input
            type="checkbox"
            className="task-checkbox-modern"
            checked={task.completed}
            onChange={(e) => {
              e.stopPropagation();
              onComplete(task.id, task.completed);
            }}
          />
        </div>

        <div className="task-card-content">
          {/* Project/List Name - Small, above title */}
          <div className="task-card-list">{taskList}</div>

          {/* Title - Main focus */}
          <div className="task-card-title">{task.title}</div>

          {/* Description - Secondary line */}
          {task.description && (
            <div className="task-card-description">{task.description}</div>
          )}

          {/* Meta Badges */}
          <div className="task-card-badges">
            {/* Category Badge */}
            <span className="task-badge task-badge-category" style={{ backgroundColor: `${categoryColor}20`, color: categoryColor, borderColor: `${categoryColor}40` }}>
              📁 Allgemein
            </span>

            {/* Priority Badge */}
            <span 
              className="task-badge task-badge-priority" 
              style={{ 
                backgroundColor: `${getPriorityColor(task.priority)}20`,
                color: getPriorityColor(task.priority),
                borderColor: `${getPriorityColor(task.priority)}40`
              }}
            >
              {task.priority === 'high' ? '🔴' : task.priority === 'medium' ? '🟡' : '🟢'} {getPriorityLabel(task.priority)}
            </span>

            {/* Due Date Badge */}
            {dueInfo && (
              <span 
                className={`task-badge task-badge-due ${dueInfo.isOverdue ? 'task-badge-overdue' : ''}`}
                style={!dueInfo.isOverdue ? {
                  backgroundColor: '#10B98120',
                  color: '#10B981',
                  borderColor: '#10B98140'
                } : {}}
              >
                🕐 {dueInfo.dateStr}, {dueInfo.timeStr}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right Zone: Actions Menu */}
      <div className="task-card-actions" ref={menuRef}>
        <button 
          className="task-menu-trigger"
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
        >
          ⋯
        </button>

        {showMenu && (
          <div className="task-menu-dropdown">
            {task.due_date && !task.completed && (
              <button 
                className="task-menu-item"
                onClick={(e) => {
                  e.stopPropagation();
                  onCreateEvent(task.id);
                  setShowMenu(false);
                }}
              >
                <span className="menu-icon">📅</span>
                <span>Kalendereintrag</span>
              </button>
            )}
            <button 
              className="task-menu-item"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(task);
                setShowMenu(false);
              }}
            >
              <span className="menu-icon">✏️</span>
              <span>Bearbeiten</span>
            </button>
            <button 
              className="task-menu-item task-menu-item-delete"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(task.id);
                setShowMenu(false);
              }}
            >
              <span className="menu-icon">🗑️</span>
              <span>Löschen</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Main Tasks Component
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
  const [availableLists] = useState(['Allgemein', 'Arbeit', 'Privat', 'Urlaub', 'Einkaufen', 'Gesundheit']);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [taskToDelete, setTaskToDelete] = useState(null);

  // Format a Date as "YYYY-MM-DDTHH:MM" using its LOCAL fields, for
  // datetime-local inputs. toISOString() converts to UTC first, which
  // shifts the displayed/sent time by the timezone offset (same bug
  // already fixed in CalendarView.jsx).
  const toLocalDateTimeInput = (date) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  useEffect(() => {
    fetchTasks();
    fetchMood();
  }, [filter]);

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
      // "today"/"week" have their own server-side endpoints (already
      // correctly filtered by due_date) - using them instead of getAll()
      // avoids the same pagination cliff already fixed in the calendar:
      // getAll() defaults to the 100 most-recently-created tasks, so an
      // older-but-still-due task could silently fall outside that window
      // and never show up in these views.
      let data;
      if (filter === 'today') {
        data = await tasksAPI.getDaily();
      } else if (filter === 'week') {
        data = await tasksAPI.getWeekly();
      } else {
        const filters = { limit: 500 };
        if (filter === 'pending') filters.completed = false;
        if (filter === 'completed') filters.completed = true;
        data = await tasksAPI.getAll(filters);
      }
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
      const tags = newTask.list && !newTask.tags.includes(newTask.list) 
        ? [...newTask.tags, newTask.list] 
        : newTask.tags;

      await tasksAPI.create({
        ...newTask,
        tags,
        due_date: newTask.due_date || null
      });
      
      setNewTask({ 
        title: '', 
        description: '', 
        list: 'Allgemein',
        priority: 'medium', 
        due_date: '',
        tags: [] 
      });
      setShowCreateForm(false);
      fetchTasks();
    } catch (error) {
      console.error('Failed to create task:', error);
      setErrorMessage('Fehler beim Erstellen: ' + error.message);
    }
  };

  const handleComplete = async (taskId, currentStatus) => {
    try {
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
      await fetchTasks();
    }
  };

  const handleDelete = (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    setTaskToDelete(task || { id: taskId, title: `Aufgabe #${taskId}` });
  };

  const confirmDeleteTask = async () => {
    if (!taskToDelete) return;
    const taskId = taskToDelete.id;
    try {
      await tasksAPI.delete(taskId);
      setTasks(tasks.filter(t => t.id !== taskId));
      await fetchTasks();
    } catch (error) {
      console.error('Failed to delete task:', error);
      setErrorMessage('Fehler beim Löschen: ' + error.message);
      await fetchTasks();
    } finally {
      setTaskToDelete(null);
    }
  };

  const handleEdit = (task) => {
    const list = task.tags && task.tags.length > 0 ? task.tags[0] : 'Allgemein';
    
    setEditingTask({
      ...task,
      list,
      due_date: task.due_date ? toLocalDateTimeInput(new Date(task.due_date)) : '',
      tags: task.tags || []
    });
    setShowCreateForm(false);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingTask.title.trim()) return;

    try {
      const tags = editingTask.list && !editingTask.tags.includes(editingTask.list) 
        ? [...editingTask.tags.filter(t => !availableLists.includes(t)), editingTask.list] 
        : editingTask.tags;

      await tasksAPI.update(editingTask.id, {
        title: editingTask.title,
        description: editingTask.description,
        priority: editingTask.priority,
        due_date: editingTask.due_date || null,
        tags
      });
      setEditingTask(null);
      fetchTasks();
    } catch (error) {
      console.error('Failed to update task:', error);
      setErrorMessage('Fehler beim Aktualisieren: ' + error.message);
    }
  };

  const createCalendarEventFromTask = async (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task || !task.due_date) {
      setErrorMessage('Diese Aufgabe hat kein Fälligkeitsdatum. Bitte füge erst ein Datum hinzu.');
      return;
    }

    try {
      const dueDate = new Date(task.due_date);
      // Same naive-local convention CalendarView.jsx's own create flow
      // uses - toISOString() here would convert to UTC first and shift
      // the event by the timezone offset.
      const eventData = {
        title: `📋 ${task.title}`,
        description: task.description || '',
        start_time: toLocalDateTimeInput(dueDate),
        end_time: toLocalDateTimeInput(new Date(dueDate.getTime() + 60 * 60 * 1000)),
        event_type: 'other',
        all_day: false,
        location: ''
      };

      await calendarAPI.create(eventData);
      setSuccessMessage(`✅ Kalendereintrag "${task.title}" erstellt!`);

    } catch (error) {
      console.error('Failed to create calendar event:', error);
      setErrorMessage('Fehler beim Erstellen des Kalendereintrags: ' + error.message);
    }
  };

  const getFilteredTasks = () => {
    let filtered = [...tasks];

    if (hideCompleted) {
      filtered = filtered.filter(t => !t.completed);
    }

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

    if (filter === 'today') {
      filtered = filtered.filter(t => {
        if (!t.due_date) return false;
        const dueDate = new Date(t.due_date);
        return dueDate >= today && dueDate < new Date(today.getTime() + 24 * 60 * 60 * 1000);
      });
    } else if (filter === 'week') {
      filtered = filtered.filter(t => {
        if (!t.due_date) return false;
        const dueDate = new Date(t.due_date);
        return dueDate >= today && dueDate < weekFromNow;
      });
    } else if (filter === 'pending') {
      filtered = filtered.filter(t => !t.completed);
    } else if (filter === 'completed') {
      filtered = filtered.filter(t => t.completed);
    }

    return filtered;
  };

  const getSortedTasks = () => {
    const filtered = getFilteredTasks();

    return filtered.sort((a, b) => {
      if (sortBy === 'dueDate') {
        if (!a.due_date && !b.due_date) return 0;
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date) - new Date(b.due_date);
      } else if (sortBy === 'priority') {
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      } else if (sortBy === 'list') {
        const listA = a.tags && a.tags.length > 0 ? a.tags[0] : '';
        const listB = b.tags && b.tags.length > 0 ? b.tags[0] : '';
        return listA.localeCompare(listB);
      } else if (sortBy === 'created') {
        return new Date(b.created_at) - new Date(a.created_at);
      }
      return 0;
    });
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
      focused: { icon: '🎯', text: 'Du bist fokussiert - perfekt für wichtige Aufgaben!' },
      playful: { icon: '😄', text: 'Spiele mit den Aufgaben herum - organisiere nach Lust!' },
      helpful: { icon: '🤝', text: 'Denk an Aufgaben die anderen helfen könnten!' },
      happy: { icon: '😊', text: 'Nutze die gute Laune für produktive Aufgaben!' }
    };
    return suggestions[mood.current_mood];
  };

  const displayTasks = getSortedTasks();

  return (
    <div className="tasks-container">
      {errorMessage && (
        <div className="tasks-error-banner" onClick={() => setErrorMessage('')}>
          ⚠️ {errorMessage} <span className="tasks-banner-dismiss">✕</span>
        </div>
      )}
      {successMessage && (
        <div className="tasks-success-banner" onClick={() => setSuccessMessage('')}>
          {successMessage} <span className="tasks-banner-dismiss">✕</span>
        </div>
      )}
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
          onClick={() => {
            setShowCreateForm(!showCreateForm);
            setEditingTask(null);
          }}
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

      {/* Filters and Sort */}
      <div className="tasks-controls">
        <div className="filter-group">
          <label>Filter:</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="filter-select">
            <option value="all">Alle</option>
            <option value="pending">Offen</option>
            <option value="completed">Erledigt</option>
            <option value="today">Heute fällig</option>
            <option value="week">Diese Woche fällig</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Sortieren:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="filter-select">
            <option value="dueDate">Nach Fälligkeit</option>
            <option value="priority">Nach Priorität</option>
            <option value="list">Nach Liste</option>
            <option value="created">Nach Erstellungsdatum</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={hideCompleted} 
              onChange={(e) => setHideCompleted(e.target.checked)}
            />
            <span>Erledigte ausblenden</span>
          </label>
        </div>
      </div>

      {/* Create/Edit Form Modal */}
      {(showCreateForm || editingTask) && (
        <div className="task-modal-overlay" onClick={() => {
          setShowCreateForm(false);
          setEditingTask(null);
        }}>
          <div className="task-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingTask ? '✏️ Aufgabe bearbeiten' : '➕ Neue Aufgabe'}</h3>
              <button 
                type="button" 
                className="modal-close-btn"
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingTask(null);
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={editingTask ? handleUpdate : handleCreate} className="task-form">
              <div className="form-row">
                <input
                  type="text"
                  className="form-input"
                  placeholder="Aufgaben-Titel *"
                  value={editingTask ? editingTask.title : newTask.title}
                  onChange={(e) => editingTask 
                    ? setEditingTask({ ...editingTask, title: e.target.value })
                    : setNewTask({ ...newTask, title: e.target.value })
                  }
                  required
                  autoFocus
                />
              </div>

              <div className="form-row">
                <select
                  className="form-select"
                  value={editingTask ? editingTask.list : newTask.list}
                  onChange={(e) => editingTask
                    ? setEditingTask({ ...editingTask, list: e.target.value })
                    : setNewTask({ ...newTask, list: e.target.value })
                  }
                >
                  {availableLists.map(list => (
                    <option key={list} value={list}>{list}</option>
                  ))}
                </select>

                <select
                  className="form-select"
                  value={editingTask ? editingTask.priority : newTask.priority}
                  onChange={(e) => editingTask
                    ? setEditingTask({ ...editingTask, priority: e.target.value })
                    : setNewTask({ ...newTask, priority: e.target.value })
                  }
                >
                  <option value="low">🟢 Niedrig</option>
                  <option value="medium">🟡 Mittel</option>
                  <option value="high">🔴 Hoch</option>
                </select>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label>Fälligkeit (optional):</label>
                  <input
                    type="datetime-local"
                    className="form-input"
                    value={editingTask ? editingTask.due_date : newTask.due_date}
                    onChange={(e) => editingTask
                      ? setEditingTask({ ...editingTask, due_date: e.target.value })
                      : setNewTask({ ...newTask, due_date: e.target.value })
                    }
                  />
                </div>
              </div>

              <textarea
                className="form-textarea"
                placeholder="Beschreibung (optional)"
                value={editingTask ? (editingTask.description || '') : newTask.description}
                onChange={(e) => editingTask
                  ? setEditingTask({ ...editingTask, description: e.target.value })
                  : setNewTask({ ...newTask, description: e.target.value })
                }
                rows="3"
              />

              <div className="form-actions">
                <button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={editingTask ? !editingTask.title.trim() : !newTask.title.trim()}
                >
                  {editingTask ? '💾 Speichern' : '✅ Aufgabe erstellen'}
                </button>
                <button 
                  type="button" 
                  className="btn-secondary" 
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingTask(null);
                  }}
                >
                  Abbrechen
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tasks List */}
      <div className="tasks-list-modern">
        {loading ? (
          <div className="tasks-loading">⏳ Lade Aufgaben...</div>
        ) : displayTasks.length === 0 ? (
          <div className="tasks-empty">
            <div className="tasks-empty-icon">📋</div>
            <p className="empty-title">Keine Aufgaben vorhanden</p>
            <p className="empty-subtitle">
              Lege deine erste Aufgabe an und starte produktiv durch!
            </p>
          </div>
        ) : (
          displayTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onComplete={handleComplete}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onCreateEvent={createCalendarEventFromTask}
            />
          ))
        )}
      </div>

      {/* Task Stats */}
      {tasks.length > 0 && (
        <div className="tasks-stats">
          <div className="stat-item">
            <span className="stat-label">Gesamt:</span>
            <span className="stat-value">{tasks.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Offen:</span>
            <span className="stat-value">{tasks.filter(t => !t.completed).length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Erledigt:</span>
            <span className="stat-value">{tasks.filter(t => t.completed).length}</span>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal - not window.confirm(), which some
          browsers silently suppress after repeated dialogs, leaving the
          delete button looking like it does nothing */}
      {taskToDelete && (
        <div className="task-modal-overlay" onClick={() => setTaskToDelete(null)}>
          <div className="task-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Aufgabe löschen?</h3>
              <button type="button" className="modal-close-btn" onClick={() => setTaskToDelete(null)}>
                ✕
              </button>
            </div>
            <div style={{ padding: '0 1.5rem 1.5rem' }}>
              <p>Möchtest du "<strong>{taskToDelete.title}</strong>" wirklich löschen?</p>
            </div>
            <div className="form-actions" style={{ padding: '0 1.5rem 1.5rem' }}>
              <button type="button" className="btn-secondary" onClick={() => setTaskToDelete(null)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDeleteTask}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Tasks;
