import { useState, useEffect } from 'react';
import { calendarAPI, moodAPI } from '../services/api';
import './Calendar.css';

function Calendar() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState(localStorage.getItem('calendar_view') || 'week');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [newEvent, setNewEvent] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'meeting',
  });
  const [mood, setMood] = useState(null);
  const [hoveredEvent, setHoveredEvent] = useState(null);

  useEffect(() => {
    fetchEvents();
    fetchMood();
  }, [view]);

  // Close editors when view changes
  useEffect(() => {
    closeEditor();
  }, [view]);

  // ESC key handler
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeEditor();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, []);

  const isToday = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const groupEventsByDay = (events) => {
    const grouped = {};
    events.forEach(event => {
      const dateKey = new Date(event.start_time).toDateString();
      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(event);
    });
    return grouped;
  };

  // Central function to close all editors
  const closeEditor = () => {
    setShowCreateForm(false);
    setEditingEvent(null);
    setNewEvent({
      title: '',
      description: '',
      start_time: '',
      end_time: '',
      location: '',
      event_type: 'meeting',
    });
  };

  // Save view preference
  useEffect(() => {
    localStorage.setItem('calendar_view', view);
  }, [view]);

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Failed to fetch mood:', error);
    }
  };

  const fetchEvents = async () => {
    setLoading(true);
    try {
      let data;
      if (view === 'today') {
        data = await calendarAPI.getToday();
      } else if (view === 'week') {
        data = await calendarAPI.getWeek();
      } else {
        data = await calendarAPI.getAll();
      }
      setEvents(data.events || []);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    }
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newEvent.title.trim() || !newEvent.start_time || !newEvent.end_time) return;

    try {
      await calendarAPI.create(newEvent);
      closeEditor();
      fetchEvents();
    } catch (error) {
      console.error('Failed to create event:', error);
      alert('Fehler beim Erstellen: ' + error.message);
    }
  };

  const handleDelete = async (eventId) => {
    if (!confirm('Event wirklich löschen?')) return;
    
    try {
      await calendarAPI.delete(eventId);
      // Optimistic update
      setEvents(events.filter(e => e.id !== eventId));
      await fetchEvents();
    } catch (error) {
      console.error('Failed to delete event:', error);
      await fetchEvents();
    }
  };

  const handleEdit = (event) => {
    setShowCreateForm(false);
    setEditingEvent({
      ...event,
      start_time: new Date(event.start_time).toISOString().slice(0, 16),
      end_time: new Date(event.end_time).toISOString().slice(0, 16),
    });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingEvent.title.trim() || !editingEvent.start_time || !editingEvent.end_time) return;

    try {
      await calendarAPI.update(editingEvent.id, {
        title: editingEvent.title,
        description: editingEvent.description,
        start_time: editingEvent.start_time,
        end_time: editingEvent.end_time,
        location: editingEvent.location,
        event_type: editingEvent.event_type,
      });
      closeEditor();
      fetchEvents();
    } catch (error) {
      console.error('Failed to update event:', error);
      alert('Fehler beim Aktualisieren: ' + error.message);
    }
  };

  const formatDateTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getEventIcon = (type) => {
    const icons = {
      meeting: '👥',
      reminder: '⏰',
      appointment: '📅',
    };
    return icons[type] || '📅';
  };

  const getEventColor = (type) => {
    const colors = {
      meeting: '#667eea',      // Blau - Meetings
      reminder: '#F59E0B',     // Orange - Erinnerungen
      appointment: '#10B981',  // Grün - Termine
      work: '#8B5CF6',         // Lila - Arbeit
      personal: '#EC4899',     // Pink - Privat
      travel: '#06B6D4',       // Cyan - Reisen
      health: '#EF4444',       // Rot - Gesundheit
    };
    return colors[type] || '#667eea';
  };

  const handleQuickAdd = async (e) => {
    e.preventDefault();
    if (!quickAdd.trim()) return;

    const event = parseQuickEvent(quickAdd);
    
    try {
      await calendarAPI.create(event);
      setQuickAdd('');
      fetchEvents();
    } catch (error) {
      console.error('Failed to create quick event:', error);
    }
  };

  const parseQuickEvent = (text) => {
    const now = new Date();
    let startTime = new Date(now);
    startTime.setHours(now.getHours() + 1, 0, 0, 0);
    let endTime = new Date(startTime);
    endTime.setHours(startTime.getHours() + 1);

    // Zeitparse: "14:00" oder "14 Uhr"
    const timeMatch = text.match(/(\d{1,2}):?(\d{2})?\s?(uhr)?/i);
    if (timeMatch) {
      const hour = parseInt(timeMatch[1]);
      const minute = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
      startTime.setHours(hour, minute, 0, 0);
      endTime = new Date(startTime);
      endTime.setHours(startTime.getHours() + 1);
    }

    // Datumsparse: "morgen", "übermorgen"
    if (text.toLowerCase().includes('morgen') && !text.toLowerCase().includes('übermorgen')) {
      startTime.setDate(startTime.getDate() + 1);
      endTime.setDate(endTime.getDate() + 1);
    } else if (text.toLowerCase().includes('übermorgen')) {
      startTime.setDate(startTime.getDate() + 2);
      endTime.setDate(endTime.getDate() + 2);
    }

    // Location extraction
    let location = null;
    const locationMatch = text.match(/(?:in|@)\s+([A-Za-zäöüß\s]+?)(?:\s+um|\s+\d|$)/i);
    if (locationMatch) {
      location = locationMatch[1].trim();
    }

    return {
      title: text,
      description: '',
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      location: location,
      event_type: 'meeting'
    };
  };

  const getMoodSuggestion = () => {
    if (!mood) return null;
    
    const primary = mood.current_mood?.tone?.primary;
    if (!primary) return null;

    if (primary.stressed > 0.6) return '🧘 Zeit für Pausen einplanen?';
    if (primary.focused > 0.7) return '⏰ Optimal für wichtige Termine';
    if (primary.social > 0.7) return '👥 Meetings planen?';
    return null;
  };

  return (
    <div className="calendar-container">
      <div className="calendar-header">
        <div className="header-left">
          <h2>📅 Kalender</h2>
          <div className="view-selector">
            <button 
              className={`view-btn ${view === 'today' ? 'active' : ''}`}
              onClick={() => setView('today')}
              title="Tagesansicht"
            >
              📆 Heute
            </button>
            <button 
              className={`view-btn ${view === 'week' ? 'active' : ''}`}
              onClick={() => setView('week')}
              title="Wochenansicht"
            >
              📅 Woche
            </button>
            <button 
              className={`view-btn ${view === 'month' ? 'active' : ''}`}
              onClick={() => setView('month')}
              title="Monatsansicht"
            >
              📊 Monat
            </button>
            <button 
              className={`view-btn ${view === 'all' ? 'active' : ''}`}
              onClick={() => setView('all')}
              title="Alle Termine"
            >
              📋 Alle
            </button>
          </div>
        </div>
        <button 
          className="create-button"
          onClick={() => setShowCreateForm(true)}
          disabled={showCreateForm || editingEvent}
        >
          ➕ Neuer Termin
        </button>
      </div>

      {mood && getMoodSuggestion() && (
        <div className="mood-suggestion">
          {getMoodSuggestion()}
        </div>
      )}

      {showCreateForm && (
        <div className="create-form-panel">
          <div className="panel-header">
            <h3>➕ Neuer Termin</h3>
            <button className="panel-close" onClick={closeEditor} title="Schließen (ESC)">
              ✕
            </button>
          </div>
          <form onSubmit={handleCreate} className="event-form">
            <input
              type="text"
              className="form-input"
              placeholder="Titel *"
              value={newEvent.title}
              onChange={(e) => setNewEvent({ ...newEvent, title: e.target.value })}
              required
              autoFocus
            />
            <div className="form-row">
              <input
                type="datetime-local"
                className="form-input"
                value={newEvent.start_time}
                onChange={(e) => setNewEvent({ ...newEvent, start_time: e.target.value })}
                required
              />
              <input
                type="datetime-local"
                className="form-input"
                value={newEvent.end_time}
                onChange={(e) => setNewEvent({ ...newEvent, end_time: e.target.value })}
                required
              />
            </div>
            <div className="form-row">
              <input
                type="text"
                className="form-input"
                placeholder="Ort (optional)"
                value={newEvent.location}
                onChange={(e) => setNewEvent({ ...newEvent, location: e.target.value })}
              />
              <select
                className="form-select"
                value={newEvent.event_type}
                onChange={(e) => setNewEvent({ ...newEvent, event_type: e.target.value })}
              >
                <option value="meeting">👥 Meeting</option>
                <option value="reminder">⏰ Erinnerung</option>
                <option value="appointment">📅 Termin</option>
                <option value="work">💼 Arbeit</option>
                <option value="personal">🏠 Privat</option>
                <option value="travel">✈️ Reise</option>
                <option value="health">🏥 Gesundheit</option>
              </select>
            </div>
            <textarea
              className="form-textarea"
              placeholder="Beschreibung (optional)"
              value={newEvent.description}
              onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })}
              rows="2"
            />
            <div className="form-actions">
              <button type="submit" className="btn-primary">
                ✅ Termin erstellen
              </button>
              <button type="button" className="btn-secondary" onClick={closeEditor}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      {editingEvent && (
        <div className="create-form-panel">
          <div className="panel-header">
            <h3>✏️ Termin bearbeiten</h3>
            <button className="panel-close" onClick={closeEditor} title="Schließen (ESC)">
              ✕
            </button>
          </div>
          <form onSubmit={handleUpdate}>
            <div className="form-group">
              <label>Titel *</label>
              <input
                type="text"
                value={editingEvent.title}
                onChange={(e) => setEditingEvent({...editingEvent, title: e.target.value})}
                placeholder="Titel des Termins"
                required
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Start *</label>
                <input
                  type="datetime-local"
                  value={editingEvent.start_time}
                  onChange={(e) => setEditingEvent({...editingEvent, start_time: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Ende *</label>
                <input
                  type="datetime-local"
                  value={editingEvent.end_time}
                  onChange={(e) => setEditingEvent({...editingEvent, end_time: e.target.value})}
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Ort</label>
                <input
                  type="text"
                  value={editingEvent.location || ''}
                  onChange={(e) => setEditingEvent({...editingEvent, location: e.target.value})}
                  placeholder="Ort/Link"
                />
              </div>
              <div className="form-group">
                <label>Typ</label>
                <select 
                  value={editingEvent.event_type}
                  onChange={(e) => setEditingEvent({...editingEvent, event_type: e.target.value})}
                >
                  <option value="meeting">👥 Meeting</option>
                  <option value="reminder">⏰ Erinnerung</option>
                  <option value="appointment">📅 Termin</option>
                  <option value="work">💼 Arbeit</option>
                  <option value="personal">🏠 Privat</option>
                  <option value="travel">✈️ Reise</option>
                  <option value="health">🏥 Gesundheit</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Beschreibung</label>
              <textarea
                value={editingEvent.description || ''}
                onChange={(e) => setEditingEvent({...editingEvent, description: e.target.value})}
                placeholder="Details..."
                rows="2"
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn-primary">
                💾 Speichern
              </button>
              <button type="button" className="btn-secondary" onClick={closeEditor}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="events-list">
        {loading ? (
          <div className="loading">Lade Events...</div>
        ) : events.length === 0 ? (
          <div className="no-events">Keine Events gefunden</div>
        ) : (
          events.map((event) => (
            <div 
              key={event.id} 
              className={`event-item ${isToday(event.start_time) ? 'event-today' : ''}`}
              style={{ borderLeftColor: getEventColor(event.event_type) }}
              onMouseEnter={() => setHoveredEvent(event.id)}
              onMouseLeave={() => setHoveredEvent(null)}
            >
              {hoveredEvent === event.id && (
                <div className="event-tooltip">
                  <div className="tooltip-header">
                    {getEventIcon(event.event_type)} {event.title}
                  </div>
                  {event.description && (
                    <div className="tooltip-description">{event.description}</div>
                  )}
                  <div className="tooltip-time">
                    🕐 {formatTime(event.start_time)} – {formatTime(event.end_time)}
                  </div>
                  <div className="tooltip-duration">
                    ⏱️ {Math.round((new Date(event.end_time) - new Date(event.start_time)) / 60000)} Minuten
                  </div>
                  {event.location && (
                    <div className="tooltip-location">📍 {event.location}</div>
                  )}
                  <div className="tooltip-category">
                    <span 
                      className="category-badge" 
                      style={{ backgroundColor: getEventColor(event.event_type) }}
                    >
                      {event.event_type}
                    </span>
                  </div>
                </div>
              )}
              
              <div className="event-icon">
                {getEventIcon(event.event_type)}
              </div>
              
              <div className="event-content">
                <div className="event-title-row">
                  <h3>{event.title}</h3>
                  {isToday(event.start_time) && (
                    <span className="today-badge">Heute</span>
                  )}
                </div>
                
                <div className="event-time">
                  🕐 {formatTime(event.start_time)} - {formatTime(event.end_time)}
                  <span className="event-date">({formatDateTime(event.start_time)})</span>
                </div>
                
                {event.location && (
                  <div className="event-location">
                    📍 {event.location}
                  </div>
                )}
                
                {event.description && (
                  <p className="event-description">{event.description}</p>
                )}
              </div>
              
              <div className="event-actions">
                <button 
                  className="event-edit"
                  onClick={() => handleEdit(event)}
                  title="Bearbeiten"
                >
                  ✏️
                </button>
                <button 
                  className="event-delete"
                  onClick={() => handleDelete(event.id)}
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

export default Calendar;
