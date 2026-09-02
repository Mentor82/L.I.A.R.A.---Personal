import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { notesAPI, moodAPI } from '../services/api';
import './Notes.css';

function Notes() {
  const navigate = useNavigate();

  // Chat.jsx's own mount-time session restore already reads this exact key
  // (see loadSessions there) - setting it before navigating reuses that
  // existing mechanism instead of building a second, parallel deep-link path.
  const openOriginChat = (sessionId) => {
    localStorage.setItem('liara_active_session', String(sessionId));
    navigate('/chat');
  };

  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  // setFilter has no UI wired to it yet (no All/Pinned/Archived control exists
  // below) - the pinned/archived branches in fetchNotes below stay ready for
  // when that control is added. Prefixed to satisfy no-unused-vars until then.
  const [filter, _setFilter] = useState(localStorage.getItem('notes_filter') || 'all');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [newNote, setNewNote] = useState({
    title: '',
    content: '',
    category: '',
    tags: [],
  });
  const [tagInput, setTagInput] = useState('');
  const [mood, setMood] = useState(null);

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Failed to fetch mood:', error);
    }
  };

  const fetchNotes = async () => {
    setLoading(true);
    try {
      const filters = {};
      if (filter === 'pinned') filters.pinned_only = true;
      if (filter === 'archived') filters.archived = true;

      const data = await notesAPI.getAll(filters);
      setNotes(data.notes || []);
    } catch (error) {
      console.error('Failed to fetch notes:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    // Initial/filter-change data fetch - the effect is the fetch itself (a
    // real external-system side effect), not a render-computable value.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchNotes();
    fetchMood();
  }, [filter]);

  // Save filter preference
  useEffect(() => {
    localStorage.setItem('notes_filter', filter);
  }, [filter]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchNotes();
      return;
    }

    setLoading(true);
    try {
      const data = await notesAPI.search(searchQuery);
      setNotes(data.notes || []);
    } catch (error) {
      console.error('Failed to search notes:', error);
    }
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newNote.title.trim() || !newNote.content.trim()) return;

    try {
      await notesAPI.create(newNote);
      setNewNote({ title: '', content: '', category: '', tags: [] });
      setTagInput('');
      fetchNotes();
    } catch (error) {
      console.error('Failed to create note:', error);
    }
  };

  const handleAddTag = () => {
    if (!tagInput.trim()) return;
    if (!newNote.tags.includes(tagInput.trim())) {
      setNewNote({ ...newNote, tags: [...newNote.tags, tagInput.trim()] });
    }
    setTagInput('');
  };

  const handleRemoveTag = (tag) => {
    setNewNote({ ...newNote, tags: newNote.tags.filter(t => t !== tag) });
  };

  const handlePin = async (noteId, isPinned) => {
    try {
      // Optimistic update
      setNotes(notes.map(n => 
        n.id === noteId ? { ...n, is_pinned: !isPinned } : n
      ));
      
      if (isPinned) {
        await notesAPI.unpin(noteId);
      } else {
        await notesAPI.pin(noteId);
      }
      await fetchNotes();
    } catch (error) {
      console.error('Failed to toggle pin:', error);
      await fetchNotes();
    }
  };

  const handleArchive = async (noteId, isArchived) => {
    try {
      // Optimistic update
      setNotes(notes.map(n => 
        n.id === noteId ? { ...n, is_archived: !isArchived } : n
      ));
      
      if (isArchived) {
        await notesAPI.unarchive(noteId);
      } else {
        await notesAPI.archive(noteId);
      }
      await fetchNotes();
    } catch (error) {
      console.error('Failed to toggle archive:', error);
      await fetchNotes();
    }
  };

  const handleDelete = async (noteId) => {
    if (!confirm('Notiz wirklich löschen?')) return;
    
    try {
      await notesAPI.delete(noteId);
      // Sofort aus State entfernen für instant feedback
      setNotes(notes.filter(n => n.id !== noteId));
      // Dann neu laden um sicher zu sein
      await fetchNotes();
    } catch (error) {
      console.error('Failed to delete note:', error);
      // Bei Fehler: State zurücksetzen
      await fetchNotes();
    }
  };

  const handleEdit = (note) => {
    setEditingNote({
      ...note,
      tags: note.tags || []
    });
    setShowCreateForm(false);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingNote.title.trim() || !editingNote.content.trim()) return;

    try {
      await notesAPI.update(editingNote.id, {
        title: editingNote.title,
        content: editingNote.content,
        category: editingNote.category,
        tags: editingNote.tags
      });
      setEditingNote(null);
      fetchNotes();
    } catch (error) {
      console.error('Failed to update note:', error);
      alert('Fehler beim Aktualisieren: ' + error.message);
    }
  };

  const handleAddEditTag = () => {
    if (!tagInput.trim()) return;
    if (!editingNote.tags.includes(tagInput.trim())) {
      setEditingNote({ ...editingNote, tags: [...editingNote.tags, tagInput.trim()] });
    }
    setTagInput('');
  };

  const handleRemoveEditTag = (tag) => {
    setEditingNote({ ...editingNote, tags: editingNote.tags.filter(t => t !== tag) });
  };

  const getMoodSuggestion = () => {
    if (!mood) return null;
    
    const primary = mood.current_mood?.tone?.primary;
    if (!primary) return null;

    if (primary.curious > 0.7) return '🔍 Dokumentiere deine Entdeckungen';
    if (primary.focused > 0.7) return '📝 Perfekt für detaillierte Notizen';
    if (primary.creative > 0.7) return '💡 Halte deine Ideen fest';
    if (primary.stressed > 0.6) return '🧘 Schreib deine Gedanken auf';
    return null;
  };

  return (
    <div className="notes-container">
      <div className="notes-header">
        <div className="header-left">
          <h2>📓 Notizen</h2>
          <div className="search-box">
            <input
              type="text"
              placeholder="🔍 Suchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="search-input"
            />
            {searchQuery && (
              <button 
                onClick={() => { setSearchQuery(''); fetchNotes(); }}
                className="clear-search"
              >
                ✕
              </button>
            )}
          </div>
        </div>
        <button 
          className="create-button"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? '✕ Schließen' : '➕ Neue Notiz'}
        </button>
      </div>

      {mood && getMoodSuggestion() && (
        <div className="mood-suggestion">
          {getMoodSuggestion()}
        </div>
      )}

      {showCreateForm && (
        <div className="create-form-panel">
          <form onSubmit={handleCreate} className="note-form">
            <input
              type="text"
              className="form-input"
              placeholder="Titel *"
              value={newNote.title}
              onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
              required
              autoFocus
            />
            <textarea
              className="form-textarea"
              placeholder="Inhalt *"
              value={newNote.content}
              onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
              required
              rows="6"
            />
            <div className="form-row">
              <input
                type="text"
                className="form-input"
                placeholder="Kategorie (optional)"
                value={newNote.category}
                onChange={(e) => setNewNote({ ...newNote, category: e.target.value })}
              />
              <div className="tag-input-group">
                <input
                  type="text"
                  className="form-input"
                  placeholder="Tag hinzufügen..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                />
                <button type="button" onClick={handleAddTag} className="add-tag-btn">+</button>
              </div>
            </div>
            {newNote.tags.length > 0 && (
              <div className="tags-display">
                {newNote.tags.map(tag => (
                  <span key={tag} className="tag">
                    {tag}
                    <button type="button" onClick={() => handleRemoveTag(tag)}>×</button>
                  </span>
                ))}
              </div>
            )}
            <div className="form-actions">
              <button type="submit" className="btn-primary">
                ✅ Notiz speichern
              </button>
              <button type="button" className="btn-secondary" onClick={() => setShowCreateForm(false)}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      {editingNote && (
        <div className="create-form-panel">
          <h3>✏️ Notiz bearbeiten</h3>
          <form onSubmit={handleUpdate} className="note-form">
            <input
              type="text"
              className="form-input"
              placeholder="Titel *"
              value={editingNote.title}
              onChange={(e) => setEditingNote({ ...editingNote, title: e.target.value })}
              required
              autoFocus
            />
            <textarea
              className="form-textarea"
              placeholder="Inhalt *"
              value={editingNote.content}
              onChange={(e) => setEditingNote({ ...editingNote, content: e.target.value })}
              required
              rows="6"
            />
            <div className="form-row">
              <input
                type="text"
                className="form-input"
                placeholder="Kategorie (optional)"
                value={editingNote.category || ''}
                onChange={(e) => setEditingNote({ ...editingNote, category: e.target.value })}
              />
              <div className="tag-input-group">
                <input
                  type="text"
                  className="form-input"
                  placeholder="Tag hinzufügen..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddEditTag())}
                />
                <button type="button" onClick={handleAddEditTag} className="add-tag-btn">+</button>
              </div>
            </div>
            {editingNote.tags && editingNote.tags.length > 0 && (
              <div className="tags-display">
                {editingNote.tags.map(tag => (
                  <span key={tag} className="tag">
                    {tag}
                    <button type="button" onClick={() => handleRemoveEditTag(tag)}>×</button>
                  </span>
                ))}
              </div>
            )}
            <div className="form-actions">
              <button type="submit" className="btn-primary">
                💾 Speichern
              </button>
              <button type="button" className="btn-secondary" onClick={() => setEditingNote(null)}>
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="notes-list">
        {loading ? (
          <div className="loading">Lade Notizen...</div>
        ) : notes.length === 0 ? (
          <div className="no-notes">Keine Notizen gefunden</div>
        ) : (
          <div className="notes-grid">
            {notes.map((note) => (
              <div 
                key={note.id} 
                className={`note-card ${note.is_pinned ? 'pinned' : ''} ${note.is_archived ? 'archived' : ''}`}
              >
                <div className="note-card-header">
                  <h3>{note.title}</h3>
                  <div className="note-actions">
                    <button 
                      onClick={() => handlePin(note.id, note.is_pinned)}
                      title={note.is_pinned ? 'Unpin' : 'Pin'}
                    >
                      {note.is_pinned ? '📌' : '📍'}
                    </button>
                    <button 
                      onClick={() => handleArchive(note.id, note.is_archived)}
                      title={note.is_archived ? 'Unarchive' : 'Archive'}
                    >
                      {note.is_archived ? '📤' : '📦'}
                    </button>
                    <button 
                      onClick={() => handleEdit(note)}
                      title="Bearbeiten"
                    >
                      ✏️
                    </button>
                    <button 
                      onClick={() => handleDelete(note.id)}
                      title="Löschen"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <p className="note-content">{note.content}</p>

                {note.category && (
                  <div className="note-category">
                    📁 {note.category}
                  </div>
                )}

                {note.tags && note.tags.length > 0 && (
                  <div className="note-tags">
                    {note.tags.map((tag, idx) => (
                      <span key={idx} className="note-tag">{tag}</span>
                    ))}
                  </div>
                )}

                <div className="note-footer">
                  <span className="note-date">
                    {new Date(note.updated_at).toLocaleDateString('de-DE')}
                  </span>
                  {note.session_id && (
                    <button
                      className="note-origin-chat-link"
                      onClick={() => openOriginChat(note.session_id)}
                      title="Zum Chat, aus dem diese Notiz entstanden ist"
                    >
                      💬 Ursprungschat öffnen
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Notes;
