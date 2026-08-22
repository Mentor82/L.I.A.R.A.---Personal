import { useState, useEffect } from 'react';
import { notesAPI, moodAPI } from '../services/api';
import './NotesTree.css';

function NotesTree() {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createParentId, setCreateParentId] = useState(null);
  const [newNote, setNewNote] = useState({
    title: '',
    content: '',
    category: '',
    tags: [],
    parent_id: null
  });
  const [draggedNote, setDraggedNote] = useState(null);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [selectedNote, setSelectedNote] = useState(null);
  const [mood, setMood] = useState(null);
  const [error, setError] = useState('');
  const [noteToDelete, setNoteToDelete] = useState(null);

  useEffect(() => {
    fetchTree();
    fetchMood();
  }, []);

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Failed to fetch mood:', error);
    }
  };

  const fetchTree = async () => {
    setLoading(true);
    try {
      const data = await notesAPI.getTree();
      console.log('Notes tree data:', data);
      setTree(data);
      // Auto-expand root level
      const rootIds = data.map(n => n.id);
      setExpandedNodes(new Set(rootIds));
    } catch (error) {
      console.error('Failed to fetch notes tree:', error);
      setError('Fehler beim Laden der Notizen: ' + error.message);
    }
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newNote.title.trim() || !newNote.content.trim()) return;

    try {
      await notesAPI.create({
        ...newNote,
        parent_id: createParentId
      });
      setNewNote({ title: '', content: '', category: '', tags: [], parent_id: null });
      setShowCreateForm(false);
      setCreateParentId(null);
      fetchTree();
    } catch (error) {
      console.error('Failed to create note:', error);
      setError('Fehler beim Erstellen: ' + error.message);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingNote.title.trim() || !editingNote.content.trim()) return;

    try {
      await notesAPI.update(editingNote.id, {
        title: editingNote.title,
        content: editingNote.content,
        category: editingNote.category,
        tags: editingNote.tags,
        parent_id: editingNote.parent_id
      });
      setEditingNote(null);
      fetchTree();
    } catch (error) {
      console.error('Failed to update note:', error);
      setError('Fehler beim Aktualisieren: ' + error.message);
    }
  };

  const handleDelete = (note) => {
    setNoteToDelete(note);
  };

  const confirmDelete = async () => {
    if (!noteToDelete) return;
    try {
      await notesAPI.delete(noteToDelete.id);
      fetchTree();
    } catch (error) {
      console.error('Failed to delete note:', error);
      setError('Fehler beim Löschen: ' + error.message);
    } finally {
      setNoteToDelete(null);
    }
  };

  const handleEdit = (note) => {
    setEditingNote({
      id: note.id,
      title: note.title,
      content: note.content,
      category: note.category || '',
      tags: note.tags || [],
      parent_id: note.parent_id
    });
    setShowCreateForm(false);
    setSelectedNote(null);
  };

  const handleAddChild = (parentId) => {
    setCreateParentId(parentId);
    setShowCreateForm(true);
    setEditingNote(null);
  };

  const toggleExpand = (noteId) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(noteId)) {
      newExpanded.delete(noteId);
    } else {
      newExpanded.add(noteId);
    }
    setExpandedNodes(newExpanded);
  };

  const handleDragStart = (e, note) => {
    setDraggedNote(note);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, targetNote) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!draggedNote || draggedNote.id === targetNote.id) return;
    
    // Prevent dropping a parent into its own child
    if (isDescendant(draggedNote, targetNote)) {
      setError('Kann keine Notiz in ihre eigene Unternotiz verschieben!');
      setDraggedNote(null);
      return;
    }

    try {
      await notesAPI.update(draggedNote.id, {
        parent_id: targetNote.id
      });
      fetchTree();
    } catch (error) {
      console.error('Failed to move note:', error);
    }
    
    setDraggedNote(null);
  };

  const handleDropAsRoot = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!draggedNote) return;

    try {
      await notesAPI.update(draggedNote.id, {
        parent_id: null
      });
      fetchTree();
    } catch (error) {
      console.error('Failed to move note:', error);
    }
    
    setDraggedNote(null);
  };

  const isDescendant = (parent, potentialChild) => {
    if (!parent.children || parent.children.length === 0) return false;
    
    for (const child of parent.children) {
      if (child.id === potentialChild.id) return true;
      if (isDescendant(child, potentialChild)) return true;
    }
    
    return false;
  };

  const renderNote = (note, level = 0) => {
    const isExpanded = expandedNodes.has(note.id);
    const hasChildren = note.children && note.children.length > 0;
    const isSelected = selectedNote?.id === note.id;

    return (
      <div key={note.id} className="tree-node-container">
        <div 
          className={`tree-node level-${level} ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 20}px` }}
          draggable
          onDragStart={(e) => handleDragStart(e, note)}
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, note)}
          onClick={() => setSelectedNote(note)}
        >
          <div className="tree-node-content">
            <button 
              className="expand-btn"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(note.id);
              }}
            >
              {hasChildren ? (isExpanded ? '📂' : '📁') : '📄'}
            </button>
            
            <div className="node-info">
              <span className="node-title">{note.title}</span>
              {note.category && (
                <span className="node-category">{note.category}</span>
              )}
              {note.tags && note.tags.length > 0 && (
                <div className="node-tags">
                  {note.tags.map(tag => (
                    <span key={tag} className="node-tag">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="node-actions">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                handleAddChild(note.id);
              }}
              title="Unternotiz hinzufügen"
            >
              ➕
            </button>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(note);
              }}
              title="Bearbeiten"
            >
              ✏️
            </button>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(note);
              }}
              title="Löschen"
            >
              🗑️
            </button>
          </div>
        </div>

        {hasChildren && isExpanded && (
          <div className="tree-children">
            {note.children.map(child => renderNote(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  const MOOD_EMOJI = {
    neutral: '😌', energetic: '⚡', calm: '🌙', supportive: '💜', focused: '🎯', playful: '🎨',
  };

  return (
    <div className="notes-tree-container page-container">
      {error && (
        <div className="tree-error-banner" onClick={() => setError('')}>
          ⚠️ {error} <span className="tree-error-dismiss">✕</span>
        </div>
      )}
      <div className="notes-tree-header page-header">
        <div className="header-left">
          <h2>📓 Notizen</h2>
          {mood && (
            <div className="mood-indicator-small">
              <span className="mood-emoji-small">{MOOD_EMOJI[mood.current_mood] || '😌'}</span>
              <span>{mood.current_mood}</span>
            </div>
          )}
        </div>
        <div className="header-right">
          <button 
            className="btn-primary"
            onClick={() => {
              setShowCreateForm(true);
              setCreateParentId(null);
              setEditingNote(null);
            }}
          >
            + Neue Notiz
          </button>
        </div>
      </div>

      <div className="tree-layout">
        <div 
          className="tree-view"
          onDragOver={handleDragOver}
          onDrop={handleDropAsRoot}
        >
          {loading ? (
            <div className="loading">Lade Notizen...</div>
          ) : tree.length === 0 ? (
            <div className="empty-tree">
              <p>📝 Keine Notizen vorhanden</p>
              <p>Erstelle deine erste Notiz mit dem Button oben rechts!</p>
            </div>
          ) : (
            tree.map(note => renderNote(note, 0))
          )}
        </div>

        <div className="detail-panel">
          {showCreateForm && (
            <div className="note-form">
              <h3>➕ Neue Notiz {createParentId && '(Unternotiz)'}</h3>
              <form onSubmit={handleCreate}>
                <input
                  type="text"
                  placeholder="Titel *"
                  value={newNote.title}
                  onChange={(e) => setNewNote({...newNote, title: e.target.value})}
                  required
                  autoFocus
                />
                <textarea
                  placeholder="Inhalt *"
                  value={newNote.content}
                  onChange={(e) => setNewNote({...newNote, content: e.target.value})}
                  required
                  rows="8"
                />
                <input
                  type="text"
                  placeholder="Kategorie (optional)"
                  value={newNote.category}
                  onChange={(e) => setNewNote({...newNote, category: e.target.value})}
                />
                <div className="form-actions">
                  <button type="submit" className="btn-primary">💾 Speichern</button>
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={() => {
                      setShowCreateForm(false);
                      setCreateParentId(null);
                    }}
                  >
                    Abbrechen
                  </button>
                </div>
              </form>
            </div>
          )}

          {editingNote && (
            <div className="note-form">
              <h3>✏️ Notiz bearbeiten</h3>
              <form onSubmit={handleUpdate}>
                <input
                  type="text"
                  placeholder="Titel *"
                  value={editingNote.title}
                  onChange={(e) => setEditingNote({...editingNote, title: e.target.value})}
                  required
                  autoFocus
                />
                <textarea
                  placeholder="Inhalt *"
                  value={editingNote.content}
                  onChange={(e) => setEditingNote({...editingNote, content: e.target.value})}
                  required
                  rows="8"
                />
                <input
                  type="text"
                  placeholder="Kategorie (optional)"
                  value={editingNote.category}
                  onChange={(e) => setEditingNote({...editingNote, category: e.target.value})}
                />
                <div className="form-actions">
                  <button type="submit" className="btn-primary">💾 Speichern</button>
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={() => setEditingNote(null)}
                  >
                    Abbrechen
                  </button>
                </div>
              </form>
            </div>
          )}

          {selectedNote && !editingNote && !showCreateForm && (
            <div className="note-preview">
              <h3>{selectedNote.title}</h3>
              {selectedNote.category && (
                <div className="preview-category">📁 {selectedNote.category}</div>
              )}
              {selectedNote.tags && selectedNote.tags.length > 0 && (
                <div className="preview-tags">
                  {selectedNote.tags.map(tag => (
                    <span key={tag} className="preview-tag">{tag}</span>
                  ))}
                </div>
              )}
              <div className="preview-content">
                {selectedNote.content}
              </div>
              <div className="preview-meta">
                <small>Erstellt: {new Date(selectedNote.created_at).toLocaleString('de-DE')}</small>
                <small>Geändert: {new Date(selectedNote.updated_at).toLocaleString('de-DE')}</small>
              </div>
            </div>
          )}
        </div>
      </div>

      {noteToDelete && (
        <div className="modal-overlay" onClick={() => setNoteToDelete(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Notiz löschen?</h3>
              <button className="modal-close" onClick={() => setNoteToDelete(null)}>×</button>
            </div>
            <div style={{ padding: '0 2rem 1.5rem' }}>
              <p>
                Möchtest du "<strong>{noteToDelete.title}</strong>" und alle Unternotizen wirklich löschen?
              </p>
            </div>
            <div className="modal-actions" style={{ padding: '0 2rem 2rem' }}>
              <button type="button" className="btn-secondary" onClick={() => setNoteToDelete(null)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDelete}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotesTree;
