"""
Notes API Router - CRUD Operations für Notizen-System.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from core.database import get_db
from core.dependencies import get_current_user, require_user_or_admin
from api.models.base_models import Note, User, UserRole
from api.schemas.note_schemas import NoteCreate, NoteUpdate, NoteResponse, NoteList, NoteSearchResult
from services.memory_integration import store_in_4d_memory


router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("/", response_model=NoteResponse, status_code=201)
def create_note(
    note: NoteCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Erstelle eine neue Notiz + speichere in 4D Memory.
    
    - **title**: Notiz-Titel (erforderlich)
    - **content**: Notiz-Inhalt (erforderlich)
    - **category**: Kategorie (optional)
    - **tags**: Liste von Tags (optional)
    """
    if note.parent_id is not None:
        _get_owned_note(db, note.parent_id, current_user)  # 404s if missing/not owned

    db_note = Note(**note.model_dump(), user_id=current_user.id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    
    # Store in 4D Memory
    try:
        content_text = f"{note.title}. {note.content}"
        store_in_4d_memory(
            db=db,
            user_id=current_user.id,
            content_type='note',
            content_id=db_note.id,
            content_text=content_text,
            additional_context={
                'category': note.category,
                'tags': note.tags
            }
        )
    except Exception as e:
        print(f"4D Memory storage failed for note {db_note.id}: {e}")
    
    return db_note


@router.get("/", response_model=NoteList)
def get_notes(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    pinned_only: bool = Query(False, description="Show only pinned notes"),
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Liste alle Notizen mit optionalen Filtern.
    
    Filter-Optionen:
    - **category**: Nur Notizen dieser Kategorie
    - **tag**: Nur Notizen mit diesem Tag
    - **pinned_only**: true - nur angepinnte Notizen
    - **archived**: true/false - archivierte/aktive Notizen
    - **limit**: Anzahl der Ergebnisse (max 500)
    - **offset**: Pagination-Offset
    """
    query = db.query(Note)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Note.user_id == current_user.id)
    
    # Apply filters
    if category:
        query = query.filter(Note.category == category)
    
    if tag:
        query = query.filter(Note.tags.contains([tag]))
    
    if pinned_only:
        query = query.filter(Note.is_pinned == True)
    
    if archived is not None:
        query = query.filter(Note.is_archived == archived)
    
    # Get counts
    total = query.count()
    count_query = db.query(Note)
    if current_user.role != UserRole.ADMIN:
        count_query = count_query.filter(Note.user_id == current_user.id)
    pinned_count = count_query.filter(Note.is_pinned == True).count()
    archived_count = count_query.filter(Note.is_archived == True).count()
    
    # Sort: pinned first, then by update time
    notes = query.order_by(
        Note.is_pinned.desc(), 
        Note.updated_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "notes": notes,
        "total": total,
        "pinned_count": pinned_count,
        "archived_count": archived_count
    }


@router.get("/tree", response_model=List[NoteResponse])
def get_notes_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Hole alle Notizen als hierarchische Baumstruktur.
    
    Gibt nur Root-Notizen (parent_id=None) zurück, mit verschachtelten Children.
    Frontend kann diese rekursiv rendern.
    """
    def build_tree(parent_id: Optional[int] = None) -> List[NoteResponse]:
        query = db.query(Note).filter(Note.parent_id == parent_id)
        
        if current_user.role != UserRole.ADMIN:
            query = query.filter(Note.user_id == current_user.id)
        
        notes = query.filter(Note.is_archived == False).order_by(Note.order_index, Note.created_at).all()
        
        result = []
        for note in notes:
            note_dict = {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'category': note.category,
                'tags': note.tags or [],
                'parent_id': note.parent_id,
                'is_pinned': note.is_pinned,
                'is_archived': note.is_archived,
                'is_expanded': note.is_expanded,
                'order_index': note.order_index,
                'created_at': note.created_at,
                'updated_at': note.updated_at,
                'children': build_tree(note.id)  # Recursive
            }
            result.append(note_dict)
        
        return result
    
    return build_tree(None)


@router.get("/search", response_model=NoteSearchResult)
def search_notes(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Durchsuche Notizen (Titel + Inhalt).
    
    Verwendet case-insensitive Suche in Titel und Content.
    """
    search_pattern = f"%{q}%"
    
    query = db.query(Note).filter(
        and_(
            Note.is_archived == False,
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern)
            )
        )
    )
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Note.user_id == current_user.id)
    
    notes = query.order_by(Note.updated_at.desc()).limit(limit).all()
    
    return {
        "notes": notes,
        "total": len(notes),
        "query": q
    }


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole alle verwendeten Kategorien.
    """
    query = db.query(Note.category).distinct().filter(Note.category.isnot(None))
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Note.user_id == current_user.id)
    
    categories = query.all()
    return [cat[0] for cat in categories if cat[0]]


@router.get("/tags", response_model=List[str])
def get_tags(db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole alle verwendeten Tags.
    """
    # Get all notes with tags
    query = db.query(Note.tags).filter(Note.tags.isnot(None))
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Note.user_id == current_user.id)
    
    notes = query.all()
    
    # Flatten tags list
    all_tags = set()
    for note in notes:
        if note[0]:  # note.tags
            all_tags.update(note[0])
    
    return sorted(list(all_tags))


def _get_owned_note(db: Session, note_id: int, current_user: User) -> Note:
    """
    Lade eine Notiz, beschränkt auf die des aktuellen Users (Admins sehen alle).
    Wirft 404 sowohl wenn die Notiz nicht existiert als auch wenn sie einem
    anderen User gehört - ein 403 würde stattdessen verraten, dass die ID
    existiert, nur eben nicht einem selbst gehört.
    """
    query = db.query(Note).filter(Note.id == note_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Note.user_id == current_user.id)
    note = query.first()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return note


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole eine einzelne Notiz per ID.
    """
    return _get_owned_note(db, note_id, current_user)


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, note_update: NoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Update eine Notiz.

    Alle Felder sind optional - nur angegebene Felder werden aktualisiert.
    """
    db_note = _get_owned_note(db, note_id, current_user)

    update_data = note_update.model_dump(exclude_unset=True)

    if "parent_id" in update_data and update_data["parent_id"] is not None:
        new_parent_id = update_data["parent_id"]
        if new_parent_id == note_id:
            raise HTTPException(status_code=400, detail="Eine Notiz kann nicht ihr eigener Parent sein")

        parent_note = _get_owned_note(db, new_parent_id, current_user)

        # Ancestor-Kette hochlaufen: taucht note_id dabei auf, ist note_id ein
        # Vorfahre von parent_note - der neue Parent würde einen Zyklus bilden.
        visited = set()
        current = parent_note
        while current.parent_id is not None:
            if current.parent_id == note_id:
                raise HTTPException(
                    status_code=400,
                    detail="Ziel-Parent ist eine eigene Unternotiz - würde einen Zyklus erzeugen"
                )
            if current.parent_id in visited:
                break  # Absicherung gegen eine bereits bestehende Zyklus-Altlast
            visited.add(current.parent_id)
            current = db.query(Note).filter(Note.id == current.parent_id).first()
            if current is None:
                break

    for field, value in update_data.items():
        setattr(db_note, field, value)

    db.commit()
    db.refresh(db_note)
    return db_note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Lösche eine Notiz.
    """
    db_note = _get_owned_note(db, note_id, current_user)
    db.delete(db_note)
    db.commit()
    return None


@router.post("/{note_id}/pin", response_model=NoteResponse)
def pin_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Pinne eine Notiz (oben in der Liste).
    """
    db_note = _get_owned_note(db, note_id, current_user)
    db_note.is_pinned = True
    db.commit()
    db.refresh(db_note)
    return db_note


@router.post("/{note_id}/unpin", response_model=NoteResponse)
def unpin_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Entferne Pin von einer Notiz.
    """
    db_note = _get_owned_note(db, note_id, current_user)
    db_note.is_pinned = False
    db.commit()
    db.refresh(db_note)
    return db_note


@router.post("/{note_id}/archive", response_model=NoteResponse)
def archive_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Archiviere eine Notiz.
    """
    db_note = _get_owned_note(db, note_id, current_user)
    db_note.is_archived = True
    db.commit()
    db.refresh(db_note)
    return db_note


@router.post("/{note_id}/unarchive", response_model=NoteResponse)
def unarchive_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole Notiz aus Archiv zurück.
    """
    db_note = _get_owned_note(db, note_id, current_user)
    db_note.is_archived = False
    db.commit()
    db.refresh(db_note)
    return db_note
