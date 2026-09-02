import { useState, useEffect } from 'react';
import { calendarAPI, moodAPI } from '../services/api';
import './CalendarView.css';

function CalendarView() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [view, setView] = useState(localStorage.getItem('calendar_view') || 'month');
  const [selectedDate, setSelectedDate] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [newEvent, setNewEvent] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'meeting',
    all_day: false
  });
  const [mood, setMood] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [eventToDelete, setEventToDelete] = useState(null);

  useEffect(() => {
    fetchEvents();
    fetchMood();
  }, [currentDate, view]);

  useEffect(() => {
    localStorage.setItem('calendar_view', view);
  }, [view]);

  // Close sidebar when view changes
  useEffect(() => {
    setSelectedDate(null);
  }, [view]);

  // ESC key handler for sidebar and modal
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        if (showCreateForm) {
          setShowCreateForm(false);
          setEditingEvent(null);
        } else if (selectedDate) {
          setSelectedDate(null);
        }
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [selectedDate, showCreateForm]);

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Failed to fetch mood:', error);
    }
  };

  // Date range actually visible for the current view, so fetchEvents can
  // scope its query instead of relying on the backend's default
  // limit=100 (ordered earliest-first) - previously the fetch never
  // passed any date filter at all, so once a user passed ~100 total
  // events (across all history), events in later months would silently
  // stop appearing because they fell outside that fixed 100-event window.
  const getVisibleRange = () => {
    if (view === 'day') {
      const start = new Date(currentDate);
      start.setHours(0, 0, 0, 0);
      const end = new Date(currentDate);
      end.setHours(23, 59, 59, 999);
      return { start, end };
    }

    if (view === 'week') {
      const start = getWeekStart(currentDate);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      end.setHours(23, 59, 59, 999);
      return { start, end };
    }

    // Month view: matches generateCalendarDays()'s 42-cell (6-week) grid
    // exactly, so days from the adjacent month shown in the grid are
    // covered too.
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const firstDayOfWeek = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    const start = new Date(year, month, 1 - firstDayOfWeek);
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(start.getDate() + 41);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  };

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const { start, end } = getVisibleRange();
      const data = await calendarAPI.getAll({
        start_date: toLocalDateTimeInput(start),
        end_date: toLocalDateTimeInput(end),
        limit: 500,
      });
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
      if (editingEvent) {
        // Update existing event
        await calendarAPI.update(editingEvent.id, newEvent);
      } else {
        // Create new event
        await calendarAPI.create(newEvent);
      }
      setNewEvent({
        title: '',
        description: '',
        start_time: '',
        end_time: '',
        location: '',
        event_type: 'meeting',
        all_day: false
      });
      setShowCreateForm(false);
      setEditingEvent(null);
      fetchEvents();
    } catch (error) {
      console.error('Failed to save event:', error);
      setErrorMessage('Fehler beim Speichern: ' + error.message);
    }
  };

  const handleDelete = (event) => {
    setEventToDelete(event);
  };

  const confirmDeleteEvent = async () => {
    if (!eventToDelete) return;
    const eventId = eventToDelete.id;
    try {
      await calendarAPI.delete(eventId);
      setEvents(events.filter(e => e.id !== eventId));
      setSelectedDate(null);
      setShowCreateForm(false);
      setEditingEvent(null);
    } catch (error) {
      console.error('Failed to delete event:', error);
      setErrorMessage('Fehler beim Löschen: ' + error.message);
    } finally {
      setEventToDelete(null);
    }
  };

  // Format a Date as "YYYY-MM-DDTHH:MM" using its LOCAL fields, for
  // datetime-local inputs. toISOString() converts to UTC first, which
  // shifts the displayed time by the timezone offset (e.g. 19:00 CEST
  // showed as 17:00) every time an event was edited or a new one created
  // by clicking a time slot.
  const toLocalDateTimeInput = (date) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const handleEditEvent = (event) => {
    // Convert ISO strings to datetime-local format
    const startTime = toLocalDateTimeInput(new Date(event.start_time));
    const endTime = toLocalDateTimeInput(new Date(event.end_time));
    
    setNewEvent({
      title: event.title || '',
      description: event.description || '',
      start_time: startTime,
      end_time: endTime,
      location: event.location || '',
      event_type: event.event_type || 'meeting',
      all_day: event.all_day || false
    });
    setEditingEvent(event);
    setShowCreateForm(true);
    setSelectedDate(null);
  };

  // Central event editor opener
  const openEventEditor = ({ date, startHour = null, startMinute = 0 }) => {
    const selectedDateTime = new Date(date);
    
    // If no specific time provided, use next full/half hour
    if (startHour === null) {
      const now = new Date();
      const minutes = now.getMinutes();
      startHour = now.getHours();
      startMinute = minutes < 30 ? 30 : 0;
      if (minutes >= 30) startHour++;
    }
    
    selectedDateTime.setHours(startHour, startMinute, 0, 0);
    const startTime = toLocalDateTimeInput(selectedDateTime);

    const endDateTime = new Date(selectedDateTime);
    endDateTime.setMinutes(endDateTime.getMinutes() + 30);
    const endTime = toLocalDateTimeInput(endDateTime);
    
    // Reset form with fresh data (don't spread old newEvent)
    setNewEvent({
      title: '',
      description: '',
      start_time: startTime,
      end_time: endTime,
      location: '',
      event_type: 'meeting',
      all_day: false
    });
    setShowCreateForm(true);
    setSelectedDate(null); // Close sidebar if open
  };

  // Handle quick add from selected date
  const handleQuickAdd = (date) => {
    openEventEditor({ date, source: 'sidebar' });
  };

  // Handle slot click in day/week view
  const handleSlotClick = (date, hour, minute) => {
    openEventEditor({ date, startHour: hour, startMinute: minute, source: 'grid' });
  };

  // Generate week days (7 days starting from Monday)
  const generateTimeSlots = () => {
    const slots = [];
    for (let hour = 0; hour < 24; hour++) {
      slots.push({ hour, minute: 0, label: `${String(hour).padStart(2, '0')}:00` });
      slots.push({ hour, minute: 30, label: `${String(hour).padStart(2, '0')}:30` });
    }
    return slots;
  };

  const timeSlots = generateTimeSlots();

  // Generate week days (7 days starting from Monday)
  const generateWeekDays = () => {
    const weekStart = getWeekStart(currentDate);
    const days = [];
    
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart);
      date.setDate(weekStart.getDate() + i);
      days.push({
        date,
        day: date.getDate(),
        isToday: isToday(date),
        events: getEventsForDate(date)
      });
    }
    
    return days;
  };

  // Get week start (Monday)
  const getWeekStart = (date) => {
    const day = date.getDay();
    const diff = day === 0 ? -6 : 1 - day; // Monday as start
    const weekStart = new Date(date);
    weekStart.setDate(date.getDate() + diff);
    weekStart.setHours(0, 0, 0, 0);
    return weekStart;
  };

  // Get week number
  const getWeekNumber = (date) => {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    return weekNo;
  };

  // Get all events for a day (sorted by time)
  const getDayEvents = (date) => {
    const dayEvents = events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === date.toDateString();
    });
    
    return dayEvents.sort((a, b) => {
      return new Date(a.start_time) - new Date(b.start_time);
    });
  };

  // Calculate event position in timeline (60px per hour for 30-min slots)
  const getEventPosition = (event) => {
    const start = new Date(event.start_time);
    const end = new Date(event.end_time);
    
    const startMinutes = start.getHours() * 60 + start.getMinutes();
    const duration = (end - start) / (1000 * 60); // minutes
    
    const pixelsPerHour = 60; // 60px = 2 slots à 30px
    
    return {
      top: `${(startMinutes / 60) * pixelsPerHour}px`,
      height: `${Math.max((duration / 60) * pixelsPerHour, 20)}px` // Minimum 20px height
    };
  };

  // Navigation
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const goToPreviousWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() - 7);
    setCurrentDate(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() + 7);
    setCurrentDate(newDate);
  };

  const goToPreviousDay = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() - 1);
    setCurrentDate(newDate);
  };

  const goToNextDay = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() + 1);
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Calendar Grid Generation
  const generateCalendarDays = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // Start from Monday (1) instead of Sunday (0)
    const firstDayOfWeek = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    const daysInMonth = lastDay.getDate();
    
    const days = [];
    
    // Previous month days
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      days.push({
        day: prevMonthLastDay - i,
        isCurrentMonth: false,
        date: new Date(year, month - 1, prevMonthLastDay - i)
      });
    }
    
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      days.push({
        day,
        isCurrentMonth: true,
        date: new Date(year, month, day)
      });
    }
    
    // Next month days (fill to 42 cells = 6 weeks)
    const remainingDays = 42 - days.length;
    for (let day = 1; day <= remainingDays; day++) {
      days.push({
        day,
        isCurrentMonth: false,
        date: new Date(year, month + 1, day)
      });
    }
    
    return days;
  };

  // Get events for a specific date
  const getEventsForDate = (date) => {
    return events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === date.toDateString();
    });
  };

  // Check if date is today
  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  // Check if date is selected
  const isSelected = (date) => {
    if (!selectedDate) return false;
    return date.toDateString() === selectedDate.toDateString();
  };

  // Format date for display
  const formatMonthYear = () => {
    return currentDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });
  };

  const formatWeekRange = () => {
    const weekStart = getWeekStart(currentDate);
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    
    return `KW ${getWeekNumber(currentDate)}: ${weekStart.toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })} - ${weekEnd.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })}`;
  };

  const formatDayDate = () => {
    return currentDate.toLocaleDateString('de-DE', { 
      weekday: 'long', 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    });
  };

  const formatTime = (dateStr) => {
    return new Date(dateStr).toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getEventTypeColor = (type) => {
    const colors = {
      meeting: '#667eea',
      private: '#EC4899',
      other: '#10B981'
    };
    return colors[type] || colors.other;
  };

  const getEventTypeIcon = (type) => {
    const icons = {
      meeting: '💼',
      private: '🏠',
      other: '📌'
    };
    return icons[type] || icons.other;
  };

  return (
    <div className="calendar-view-container">
      {errorMessage && (
        <div className="calendar-error-banner" onClick={() => setErrorMessage('')}>
          ⚠️ {errorMessage} <span className="calendar-error-dismiss">✕</span>
        </div>
      )}
      {/* Header */}
      <div className="calendar-header">
        <div className="calendar-title">
          <h2>📅 Kalender</h2>
          {mood && (
            <span className="calendar-mood">Mood: {mood.current_mood}</span>
          )}
        </div>

        <div className="calendar-controls">
          <div className="view-switcher">
            <button
              className={view === 'day' ? 'active' : ''}
              onClick={() => setView('day')}
              title="Tagesansicht"
            >
              Tag
            </button>
            <button
              className={view === 'week' ? 'active' : ''}
              onClick={() => setView('week')}
              title="Wochenansicht"
            >
              Woche
            </button>
            <button
              className={view === 'month' ? 'active' : ''}
              onClick={() => setView('month')}
              title="Monatsansicht"
            >
              Monat
            </button>
          </div>

          <button 
            onClick={() => openEventEditor({ date: currentDate, source: 'button' })}
            className="btn-create"
            title="Neuer Termin"
          >
            ➕ Termin
          </button>
        </div>
      </div>

      {/* Month Navigation */}
      <div className="month-navigation">
        <button 
          onClick={view === 'month' ? goToPreviousMonth : view === 'week' ? goToPreviousWeek : goToPreviousDay} 
          className="nav-btn"
        >
          ◀ Zurück
        </button>
        <div className="current-month">
          <h3>
            {view === 'month' && formatMonthYear()}
            {view === 'week' && formatWeekRange()}
            {view === 'day' && formatDayDate()}
          </h3>
        </div>
        <button onClick={goToToday} className="nav-btn today-btn">
          Heute
        </button>
        <button 
          onClick={view === 'month' ? goToNextMonth : view === 'week' ? goToNextWeek : goToNextDay} 
          className="nav-btn"
        >
          Weiter ▶
        </button>
      </div>

      {/* Create/Edit Form Modal */}
      {showCreateForm && (
        <div className="event-modal-overlay" onClick={() => {
          setShowCreateForm(false);
          setEditingEvent(null);
        }}>
          <div className="event-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingEvent ? '✏️ Termin bearbeiten' : '➕ Neuer Termin'}</h3>
              <button 
                type="button" 
                className="modal-close-btn"
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingEvent(null);
                }}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-row">
                <input
                  type="text"
                  placeholder="Titel *"
                  value={newEvent.title}
                  onChange={(e) => setNewEvent({...newEvent, title: e.target.value})}
                  required
                />
                <select
                  value={newEvent.event_type}
                  onChange={(e) => setNewEvent({...newEvent, event_type: e.target.value})}
                >
                  <option value="meeting">💼 Meeting</option>
                  <option value="private">🏠 Privat</option>
                  <option value="other">📌 Sonstiges</option>
                </select>
              </div>

              <div className="form-row all-day-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={newEvent.all_day}
                    onChange={(e) => {
                      const isAllDay = e.target.checked;
                      if (isAllDay) {
                        // Set to full day (00:00 to 23:59)
                        const date = newEvent.start_time ? new Date(newEvent.start_time) : new Date();
                        const startOfDay = new Date(date);
                        startOfDay.setHours(0, 0, 0, 0);
                        const endOfDay = new Date(date);
                        endOfDay.setHours(23, 59, 0, 0);
                        setNewEvent({
                          ...newEvent,
                          all_day: true,
                          start_time: toLocalDateTimeInput(startOfDay),
                          end_time: toLocalDateTimeInput(endOfDay)
                        });
                      } else {
                        setNewEvent({...newEvent, all_day: false});
                      }
                    }}
                  />
                  <span>Ganztägig</span>
                </label>
              </div>

              {!newEvent.all_day && (
                <div className="form-row">
                  <input
                    type="datetime-local"
                    value={newEvent.start_time}
                    onChange={(e) => setNewEvent({...newEvent, start_time: e.target.value})}
                    required
                  />
                  <input
                    type="datetime-local"
                    value={newEvent.end_time}
                    onChange={(e) => setNewEvent({...newEvent, end_time: e.target.value})}
                    required
                  />
                </div>
              )}

              {newEvent.all_day && (
                <div className="form-row all-day-date">
                  <input
                    type="date"
                    value={newEvent.start_time.slice(0, 10)}
                    onChange={(e) => {
                      const dateStr = e.target.value;
                      const startOfDay = new Date(dateStr + 'T00:00:00');
                      const endOfDay = new Date(dateStr + 'T23:59:00');
                      setNewEvent({
                        ...newEvent,
                        start_time: toLocalDateTimeInput(startOfDay),
                        end_time: toLocalDateTimeInput(endOfDay)
                      });
                    }}
                    required
                  />
                </div>
              )}

              <input
                type="text"
                placeholder="Ort"
                value={newEvent.location}
                onChange={(e) => setNewEvent({...newEvent, location: e.target.value})}
              />

              <textarea
                placeholder="Beschreibung"
                value={newEvent.description}
                onChange={(e) => setNewEvent({...newEvent, description: e.target.value})}
                rows={3}
              />

              <div className="form-actions">
                <button type="submit" className="btn-submit">
                  {editingEvent ? 'Speichern' : 'Erstellen'}
                </button>
                <button 
                  type="button" 
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingEvent(null);
                  }} 
                  className="btn-cancel"
                >
                  Abbrechen
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Calendar Grid */}
      <div className="calendar-grid-container">
        {/* Month View */}
        {view === 'month' && (
          <>
            {/* Weekday Headers */}
            <div className="weekday-headers">
              {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map(day => (
                <div key={day} className="weekday-header">{day}</div>
              ))}
            </div>

            {/* Calendar Days */}
            <div className="calendar-grid">
              {generateCalendarDays().map((dayInfo, index) => {
                const dayEvents = getEventsForDate(dayInfo.date);
                const isTodayDate = isToday(dayInfo.date);
                const isSelectedDate = isSelected(dayInfo.date);

                return (
                  <div
                    key={index}
                    className={`calendar-day ${!dayInfo.isCurrentMonth ? 'other-month' : ''} ${isTodayDate ? 'today' : ''} ${isSelectedDate ? 'selected' : ''}`}
                    onClick={() => setSelectedDate(dayInfo.date)}
                    onDoubleClick={() => handleQuickAdd(dayInfo.date)}
                  >
                    <div className="day-number">{dayInfo.day}</div>
                    <div className="day-events">
                      {dayEvents.slice(0, 3).map(event => (
                        <div
                          key={event.id}
                          className="day-event"
                          style={{ borderLeftColor: getEventTypeColor(event.event_type) }}
                          title={`${event.title} ${formatTime(event.start_time)}`}
                        >
                          <span className="event-icon">{getEventTypeIcon(event.event_type)}</span>
                          <span className="event-time">{formatTime(event.start_time)}</span>
                          <span className="event-title">{event.title}</span>
                        </div>
                      ))}
                      {dayEvents.length > 3 && (
                        <div className="more-events">+{dayEvents.length - 3} mehr</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Week View */}
        {view === 'week' && (
          <div className="week-view">
            <div className="time-axis">
              <div className="time-header">Zeit</div>
              {timeSlots.map((slot, index) => (
                <div key={index} className="time-slot">
                  {slot.label}
                </div>
              ))}
            </div>

            <div className="week-days-grid">
              {generateWeekDays().map((dayInfo, dayIndex) => (
                <div key={dayIndex} className="week-day-column">
                  <div className={`week-day-header ${dayInfo.isToday ? 'today' : ''}`}>
                    <div className="week-day-name">
                      {dayInfo.date.toLocaleDateString('de-DE', { weekday: 'short' })}
                    </div>
                    <div className="week-day-number">{dayInfo.day}</div>
                  </div>

                  <div className="week-day-timeline">
                    {timeSlots.map((slot, slotIndex) => (
                      <div 
                        key={slotIndex} 
                        className="week-hour-slot"
                        onClick={() => handleSlotClick(dayInfo.date, slot.hour, slot.minute)}
                        title={`Termin am ${dayInfo.date.toLocaleDateString('de-DE')} um ${slot.label} erstellen`}
                      ></div>
                    ))}

                    {/* Events */}
                    {dayInfo.events.map(event => {
                      const position = getEventPosition(event);
                      return (
                        <div
                          key={event.id}
                          className="week-event"
                          style={{
                            top: position.top,
                            height: position.height,
                            backgroundColor: getEventTypeColor(event.event_type),
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDate(dayInfo.date);
                          }}
                        >
                          <div className="week-event-time">
                            {formatTime(event.start_time)}
                          </div>
                          <div className="week-event-title">
                            {getEventTypeIcon(event.event_type)} {event.title}
                          </div>
                          {event.location && (
                            <div className="week-event-location">📍 {event.location}</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Day View */}
        {view === 'day' && (
          <div className="day-view">
            <div className="day-timeline">
              <div className="day-time-axis">
                {timeSlots.map((slot, index) => (
                  <div key={index} className="day-time-slot">
                    {slot.label && <span className="day-hour-label">{slot.label}</span>}
                  </div>
                ))}
              </div>

              <div className="day-events-column">
                {timeSlots.map((slot, index) => (
                  <div 
                    key={index} 
                    className="day-hour-block"
                    onClick={() => handleSlotClick(currentDate, slot.hour, slot.minute)}
                    title={`Termin um ${slot.label} erstellen`}
                  ></div>
                ))}

                {/* Events */}
                {getDayEvents(currentDate).map(event => {
                  const position = getEventPosition(event);
                  return (
                    <div
                      key={event.id}
                      className="day-event-block"
                      style={{
                        top: position.top,
                        height: position.height,
                        backgroundColor: getEventTypeColor(event.event_type),
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedDate(currentDate);
                      }}
                    >
                      <div className="day-event-header">
                        <span className="day-event-icon">{getEventTypeIcon(event.event_type)}</span>
                        <span className="day-event-time">
                          {formatTime(event.start_time)} - {formatTime(event.end_time)}
                        </span>
                      </div>
                      <div className="day-event-title">{event.title}</div>
                      {event.location && (
                        <div className="day-event-location">📍 {event.location}</div>
                      )}
                      {event.description && (
                        <div className="day-event-description">{event.description}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Selected Date Sidebar */}
      {selectedDate && (
        <div className="selected-date-sidebar">
          <div className="sidebar-header">
            <h3>
              {selectedDate.toLocaleDateString('de-DE', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
                year: 'numeric'
              })}
            </h3>
            <button onClick={() => setSelectedDate(null)} className="close-btn" title="Schließen (ESC)">
              ✕
            </button>
          </div>

          <div className="sidebar-events">
            {getEventsForDate(selectedDate).length === 0 ? (
              <div className="no-events">
                <p>Keine Termine</p>
                <button onClick={() => handleQuickAdd(selectedDate)} className="btn-add-event">
                  ➕ Termin hinzufügen
                </button>
              </div>
            ) : (
              getEventsForDate(selectedDate).map(event => (
                <div key={event.id} className="sidebar-event">
                  <div className="event-header">
                    <span className="event-type-icon">{getEventTypeIcon(event.event_type)}</span>
                    <h4>{event.title}</h4>
                  </div>
                  <div className="event-details">
                    <div className="event-time-range">
                      🕐 {formatTime(event.start_time)} - {formatTime(event.end_time)}
                    </div>
                    {event.location && (
                      <div className="event-location">📍 {event.location}</div>
                    )}
                    {event.description && (
                      <div className="event-description">{event.description}</div>
                    )}
                  </div>
                  <div className="event-actions">
                    <button
                      onClick={() => handleEditEvent(event)}
                      className="btn-edit-event"
                      title="Bearbeiten"
                    >
                      ✏️ Bearbeiten
                    </button>
                    <button
                      onClick={() => handleDelete(event)}
                      className="btn-delete-event"
                      title="Löschen"
                    >
                      🗑️ Löschen
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
        </div>
      )}

      {/* Delete Confirmation Modal - not window.confirm(), which some
          browsers silently suppress after repeated dialogs, leaving the
          delete button looking like it does nothing */}
      {eventToDelete && (
        <div className="event-modal-overlay" onClick={() => setEventToDelete(null)}>
          <div className="event-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Termin löschen?</h3>
              <button type="button" className="modal-close-btn" onClick={() => setEventToDelete(null)}>
                ✕
              </button>
            </div>
            <div style={{ padding: '0 1.5rem 1.5rem' }}>
              <p>Möchtest du "<strong>{eventToDelete.title}</strong>" wirklich löschen?</p>
            </div>
            <div className="form-actions" style={{ padding: '0 1.5rem 1.5rem' }}>
              <button type="button" className="btn-cancel" onClick={() => setEventToDelete(null)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDeleteEvent}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CalendarView;
