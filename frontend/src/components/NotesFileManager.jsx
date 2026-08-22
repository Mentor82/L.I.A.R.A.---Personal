import React, { useState, useEffect } from 'react';
import { notesAPI, moodAPI } from '../services/api';
import LexicalEditor from './LexicalEditor';
import './NotesFileManager.css';

const NotesFileManager = () => {
  const [notes, setNotes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [filteredNotes, setFilteredNotes] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: '',
    subcategory: ''
  });
  const [editingId, setEditingId] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState(new Set(['all']));
  const [mood, setMood] = useState(null);
  const [viewNote, setViewNote] = useState(null);
  const [sortBy, setSortBy] = useState('date-desc'); // date-desc, date-asc, title-asc, category
  const [showPinnedOnly, setShowPinnedOnly] = useState(false);
  const [showArchivedOnly, setShowArchivedOnly] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [noteToDelete, setNoteToDelete] = useState(null);

  useEffect(() => {
    fetchNotes();
    fetchMood();
  }, []);

  useEffect(() => {
    filterNotesByCategory();
  }, [selectedCategory, notes, sortBy, showPinnedOnly, showArchivedOnly]);

  const fetchNotes = async () => {
    try {
      const data = await notesAPI.getAll();
      console.log('Fetched notes:', data);
      const notesArray = Array.isArray(data) ? data : (data.notes || []);
      setNotes(notesArray);
      buildCategoryTree(notesArray);
    } catch (error) {
      console.error('Error fetching notes:', error);
    }
  };

  const fetchMood = async () => {
    try {
      const data = await moodAPI.getStatus();
      setMood(data);
    } catch (error) {
      console.error('Error fetching mood:', error);
    }
  };

  const buildCategoryTree = (notesList) => {
    const categoryMap = new Map();
    
    notesList.forEach(note => {
      if (note.category) {
        const parts = note.category.split('/').filter(p => p.trim());
        let path = '';
        
        parts.forEach((part, index) => {
          const parentPath = path;
          path = path ? `${path}/${part}` : part;
          
          if (!categoryMap.has(path)) {
            categoryMap.set(path, {
              name: part,
              path: path,
              parent: parentPath || null,
              children: [],
              level: index
            });
          }
        });
      }
    });

    const tree = [];
    categoryMap.forEach((category) => {
      if (category.parent) {
        const parent = categoryMap.get(category.parent);
        if (parent) {
          parent.children.push(category);
        }
      } else {
        tree.push(category);
      }
    });

    setCategories(tree);
  };

  const filterNotesByCategory = () => {
    let filtered = [];
    
    if (selectedCategory === 'all') {
      filtered = [...notes];
    } else {
      filtered = notes.filter(note => {
        if (!note.category) return false;
        return note.category === selectedCategory || 
               note.category.startsWith(selectedCategory + '/');
      });
    }

    // Apply filters
    if (showPinnedOnly) {
      filtered = filtered.filter(note => note.is_pinned);
    }
    if (showArchivedOnly) {
      filtered = filtered.filter(note => note.is_archived);
    } else {
      // By default, hide archived notes
      filtered = filtered.filter(note => !note.is_archived);
    }

    // Apply sorting
    filtered = sortNotes(filtered);
    
    setFilteredNotes(filtered);
  };

  const sortNotes = (notesList) => {
    const sorted = [...notesList];
    
    // Always put pinned notes first
    sorted.sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      
      // Then apply selected sorting
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at);
        case 'date-asc':
          return new Date(a.updated_at || a.created_at) - new Date(b.updated_at || b.created_at);
        case 'title-asc':
          return (a.title || '').localeCompare(b.title || '');
        case 'category':
          return (a.category || '').localeCompare(b.category || '');
        default:
          return 0;
      }
    });
    
    return sorted;
  };

  const toggleCategory = (path) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedCategories(newExpanded);
  };

  const renderCategoryTree = (categoryList, level = 0) => {
    return categoryList.map(category => {
      const isExpanded = expandedCategories.has(category.path);
      const isSelected = selectedCategory === category.path;
      const hasChildren = category.children && category.children.length > 0;
      const noteCount = notes.filter(n => 
        n.category === category.path || n.category?.startsWith(category.path + '/')
      ).length;

      return (
        <div key={category.path} className="category-item">
          <div
            className={`category-label ${isSelected ? 'selected' : ''}`}
            style={{ paddingLeft: `${level * 20 + 10}px` }}
            onClick={() => setSelectedCategory(category.path)}
          >
            {hasChildren && (
              <span
                className="category-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleCategory(category.path);
                }}
              >
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
            <span className="category-icon">📁</span>
            <span className="category-name">{category.name}</span>
            <span className="category-count">{noteCount}</span>
          </div>
          {hasChildren && isExpanded && (
            <div className="category-children">
              {renderCategoryTree(category.children, level + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  const handleCreateNote = () => {
    setModalMode('create');
    setFormData({
      title: '',
      content: '',
      category: selectedCategory !== 'all' ? selectedCategory : '',
      subcategory: ''
    });
    setShowModal(true);
  };

  const handleEditNote = (note) => {
    setModalMode('edit');
    setEditingId(note.id);
    const categoryParts = note.category ? note.category.split('/') : [];
    const mainCategory = categoryParts.slice(0, -1).join('/') || note.category || '';
    const subcategory = categoryParts.length > 1 ? categoryParts[categoryParts.length - 1] : '';
    
    setFormData({
      title: note.title || '',
      content: note.content || '',
      category: mainCategory,
      subcategory: subcategory
    });
    setShowModal(true);
  };

  const handleDeleteNote = (note) => {
    setNoteToDelete(note);
  };

  const confirmDeleteNote = async () => {
    if (!noteToDelete) return;
    try {
      await notesAPI.delete(noteToDelete.id);
      fetchNotes();
    } catch (error) {
      console.error('Error deleting note:', error);
    } finally {
      setNoteToDelete(null);
    }
  };

  const handleArchiveNote = async (note) => {
    try {
      await notesAPI.update(note.id, { is_archived: !note.is_archived });
      fetchNotes();
    } catch (error) {
      console.error('Error archiving note:', error);
    }
  };

  const handlePinNote = async (note) => {
    try {
      await notesAPI.update(note.id, { is_pinned: !note.is_pinned });
      fetchNotes();
    } catch (error) {
      console.error('Error pinning note:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;

    const fullCategory = formData.subcategory
      ? `${formData.category}/${formData.subcategory}`.replace(/^\/+|\/+$/g, '')
      : formData.category;

    const noteData = {
      title: formData.title,
      content: formData.content,
      category: fullCategory
    };

    setIsSubmitting(true);
    try {
      if (modalMode === 'create') {
        await notesAPI.create(noteData);
      } else {
        await notesAPI.update(editingId, noteData);
      }
      setShowModal(false);
      fetchNotes();
    } catch (error) {
      console.error('Error saving note:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const truncateContent = (html, maxLength = 120) => {
    if (!html) return '';
    
    // Convert HTML to plain text
    const temp = document.createElement('div');
    temp.innerHTML = html;
    let text = temp.textContent || temp.innerText || '';
    
    // Clean up whitespace
    text = text.replace(/\s+/g, ' ').trim();
    
    // If short enough, return as is
    if (text.length <= maxLength) {
      return text;
    }
    
    // Trim to maxLength and find last word boundary
    let trimmed = text.substring(0, maxLength);
    const lastSpace = trimmed.lastIndexOf(' ');
    
    // Cut at word boundary if found within reasonable distance
    if (lastSpace > maxLength * 0.8) {
      trimmed = trimmed.substring(0, lastSpace);
    }
    
    return trimmed + '…';
  };

  const getMoodEmoji = () => {
    if (!mood) return '😐';
    const score = mood.mood_score || 0;
    if (score >= 0.6) return '😊';
    if (score >= 0.2) return '🙂';
    if (score >= -0.2) return '😐';
    if (score >= -0.6) return '😕';
    return '😞';
  };

  const getMoodColor = () => {
    if (!mood) return '#6c757d';
    const score = mood.mood_score || 0;
    if (score >= 0.6) return '#28a745';
    if (score >= 0.2) return '#20c997';
    if (score >= -0.2) return '#ffc107';
    if (score >= -0.6) return '#fd7e14';
    return '#dc3545';
  };

  return (
    <div className="notes-file-manager">
      <div className="file-manager-header">
        <div className="header-left">
          <h2>📝 Notizen</h2>
          <div className="mood-indicator" style={{ backgroundColor: getMoodColor() }}>
            <span className="mood-emoji">{getMoodEmoji()}</span>
            {mood && (
              <span className="mood-text">
                {mood.dominant_emotion || 'Neutral'}
              </span>
            )}
          </div>
        </div>
        <button className="btn-create" onClick={handleCreateNote}>
          + Neue Notiz
        </button>
      </div>

      <div className="file-manager-layout">
        <div className="sidebar">
          <div className="sidebar-header">
            <h3>Kategorien</h3>
          </div>
          <div className="category-tree">
            <div
              className={`category-label ${selectedCategory === 'all' ? 'selected' : ''}`}
              onClick={() => setSelectedCategory('all')}
            >
              <span className="category-icon">📚</span>
              <span className="category-name">Alle Notizen</span>
              <span className="category-count">{notes.length}</span>
            </div>
            {renderCategoryTree(categories)}
          </div>
        </div>

        <div className="main-content">
          <div className="content-header">
            <div className="header-left">
              <h3>
                {selectedCategory === 'all' 
                  ? 'Alle Notizen' 
                  : selectedCategory}
              </h3>
              <span className="note-count">
                {filteredNotes.length} {filteredNotes.length === 1 ? 'Notiz' : 'Notizen'}
              </span>
            </div>
            <div className="header-controls">
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value)}
                className="sort-select"
              >
                <option value="date-desc">Neueste zuerst</option>
                <option value="date-asc">Älteste zuerst</option>
                <option value="title-asc">Titel A-Z</option>
                <option value="category">Nach Kategorie</option>
              </select>
              <button 
                className={`filter-btn ${showPinnedOnly ? 'active' : ''}`}
                onClick={() => setShowPinnedOnly(!showPinnedOnly)}
                title="Nur angepinnte"
              >
                📌
              </button>
              <button 
                className={`filter-btn ${showArchivedOnly ? 'active' : ''}`}
                onClick={() => setShowArchivedOnly(!showArchivedOnly)}
                title="Nur archivierte"
              >
                📦
              </button>
            </div>
          </div>

          <div className="notes-grid">
            {filteredNotes.map(note => (
              <div key={note.id} className={`note-card ${note.is_pinned ? 'pinned' : ''}`}>
                {note.is_pinned && (
                  <div className="pin-indicator">📌</div>
                )}
                <div className="note-card-header">
                  <h4 className="note-title" onClick={() => setViewNote(note)}>
                    {note.title}
                  </h4>
                  <div className="note-actions">
                    <button
                      className="action-btn primary"
                      onClick={() => setViewNote(note)}
                      title="Vorschau"
                    >
                      👁️
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => handleEditNote(note)}
                      title="Bearbeiten"
                    >
                      ✏️
                    </button>
                    <div className="action-separator"></div>
                    <button
                      className={`action-btn ${note.is_pinned ? 'active' : ''}`}
                      onClick={() => handlePinNote(note)}
                      title={note.is_pinned ? 'Loslösen' : 'Anheften'}
                    >
                      📌
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => handleArchiveNote(note)}
                      title="Archivieren"
                    >
                      📦
                    </button>
                    <button
                      className="action-btn delete"
                      onClick={() => handleDeleteNote(note)}
                      title="Löschen"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
                <div className="note-card-content">
                  <div className="note-preview">
                    {truncateContent(note.content || '', 120)}
                  </div>
                </div>
                <div className="note-card-footer">
                  <span className="note-category">
                    📁 {note.category || 'Unkategorisiert'}
                  </span>
                  <span className="note-separator">·</span>
                  <span className="note-date">
                    {new Date(note.updated_at || note.created_at).toLocaleDateString('de-DE')}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {filteredNotes.length === 0 && (
            <div className="empty-state">
              <p>Keine Notizen in dieser Kategorie</p>
              <button className="btn-create" onClick={handleCreateNote}>
                Erste Notiz erstellen
              </button>
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalMode === 'create' ? 'Neue Notiz' : 'Notiz bearbeiten'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Titel</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder="Notiz-Titel eingeben..."
                  required
                />
              </div>

              <div className="form-group">
                <label>Kategorie</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                >
                  <option value="">Keine Kategorie</option>
                  {categories.map(cat => (
                    <option key={cat.path} value={cat.path}>
                      {cat.path}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Unterkategorie (optional)</label>
                <input
                  type="text"
                  value={formData.subcategory}
                  onChange={(e) => setFormData({...formData, subcategory: e.target.value})}
                  placeholder="z.B. 'Meeting' oder 'Ideen'"
                />
              </div>

              <div className="form-group">
                <label>Inhalt</label>
                <LexicalEditor
                  value={formData.content || ''}
                  onChange={(html) => setFormData({...formData, content: html})}
                  placeholder="Notiz-Inhalt eingeben..."
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)} disabled={isSubmitting}>
                  Abbrechen
                </button>
                <button type="submit" className="btn-save" disabled={isSubmitting}>
                  {isSubmitting
                    ? (modalMode === 'create' ? 'Erstelle...' : 'Speichere...')
                    : (modalMode === 'create' ? 'Erstellen' : 'Speichern')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Note Modal */}
      {viewNote && (
        <div className="modal-overlay" onClick={() => setViewNote(null)}>
          <div className="modal-content view-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{viewNote.title}</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn-edit" onClick={() => {
                  setViewNote(null);
                  handleEditNote(viewNote);
                }}>
                  ✏️ Bearbeiten
                </button>
                <button className="modal-close" onClick={() => setViewNote(null)}>
                  ×
                </button>
              </div>
            </div>
            <div className="view-content">
              <div 
                className="view-html-content"
                dangerouslySetInnerHTML={{ __html: viewNote.content || 'Kein Inhalt' }}
              />
              <div className="view-meta">
                {viewNote.category && (
                  <div className="view-category">
                    📁 <strong>Kategorie:</strong> {viewNote.category}
                  </div>
                )}
                {viewNote.tags && viewNote.tags.length > 0 && (
                  <div className="view-tags">
                    🏷️ <strong>Tags:</strong> {viewNote.tags.join(', ')}
                  </div>
                )}
                <div className="view-dates">
                  <div>📅 <strong>Erstellt:</strong> {new Date(viewNote.created_at).toLocaleString('de-DE')}</div>
                  {viewNote.updated_at && (
                    <div>🔄 <strong>Aktualisiert:</strong> {new Date(viewNote.updated_at).toLocaleString('de-DE')}</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal - not window.confirm(), which some
          browsers silently suppress after repeated dialogs, leaving the
          delete button looking like it does nothing */}
      {noteToDelete && (
        <div className="modal-overlay" onClick={() => setNoteToDelete(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Notiz löschen?</h3>
              <button className="modal-close" onClick={() => setNoteToDelete(null)}>
                ×
              </button>
            </div>
            <div style={{ padding: '0 2rem 1.5rem' }}>
              <p>Möchtest du "<strong>{noteToDelete.title}</strong>" wirklich löschen?</p>
            </div>
            <div className="modal-actions" style={{ padding: '0 2rem 2rem' }}>
              <button type="button" className="btn-cancel" onClick={() => setNoteToDelete(null)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDeleteNote}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotesFileManager;
