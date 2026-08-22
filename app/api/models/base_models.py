"""
SQLAlchemy Models für Liara Core-Features.

Basis-Modelle für Tasks, Calendar, Notes, Memory und User.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from core.database import Base
import enum


class UserRole(str, enum.Enum):
    """User Roles für RBAC"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(Base):
    """User Model mit Role-Based Access Control"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)  # Pflichtfeld
    phone = Column(String(50), nullable=True)  # Optional: Telefonnummer
    date_of_birth = Column(DateTime, nullable=True)  # Optional: Geburtsdatum
    profile_picture = Column(String(500), nullable=True)  # Optional: URL/Path zu Profilbild
    
    # Security & Verification
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    totp_secret = Column(String(255), nullable=True)  # 2FA Secret
    totp_enabled = Column(Boolean, default=False)  # 2FA aktiviert?
    
    # JWT Tokens
    refresh_token = Column(String(500), nullable=True)  # Store current refresh token
    refresh_token_expires = Column(DateTime, nullable=True)
    
    # Privacy & Consent (DSGVO)
    privacy_accepted = Column(Boolean, default=False)  # Datenschutz akzeptiert
    privacy_accepted_at = Column(DateTime, nullable=True)
    newsletter_opt_in = Column(Boolean, default=False)  # Newsletter
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Task(Base):
    """Aufgaben-Model."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    priority = Column(String(20), default="medium")  # low, medium, high
    due_date = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)  # ["work", "urgent"]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', completed={self.completed})>"


class CalendarEvent(Base):
    """Kalender-Event Model."""
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=True)
    event_type = Column(String(50), default="meeting")  # meeting, reminder, appointment
    all_day = Column(Boolean, default=False)
    recurrence = Column(JSON, nullable=True)  # {"frequency": "weekly", "interval": 1}
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="calendar_events")
    
    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title='{self.title}', start={self.start_time})>"


class Note(Base):
    """Notizen-Model mit hierarchischer Baumstruktur."""
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("notes.id"), nullable=True, index=True)  # Hierarchie
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_expanded = Column(Boolean, default=True)  # Tree UI State
    order_index = Column(Integer, default=0)  # Sortierung innerhalb einer Ebene
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notes")
    # `remote_side` must be on the "one" (parent) side of a self-referential
    # adjacency list. Having it on `children` directly (as before) inverted
    # the whole relationship: `.children` resolved to a single parent object
    # and `.parent` resolved to the actual children list, and since cascade
    # delete followed that inverted "children" attribute, deleting any note
    # silently cascade-deleted its PARENT (and ancestors) instead of its
    # descendants - confirmed via a rolled-back DB test. `delete-orphan` now
    # correctly cascades downward, matching what NotesTree.jsx's delete
    # confirmation ("... und alle Unternotizen wirklich löschen?") expects.
    children = relationship(
        "Note",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}', parent_id={self.parent_id})>"


class Memory(Base):
    """Memory/Pattern Recognition Model."""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    memory_type = Column(String(50), nullable=False)  # routine, pattern, preference, fact
    key = Column(String(255), nullable=False, index=True)  # "sleep_pattern", "stress_trigger"
    value = Column(JSON, nullable=False)  # Structured data
    confidence = Column(Integer, default=50)  # 0-100 confidence score
    last_confirmed = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Memory(type='{self.memory_type}', key='{self.key}')>"


class PackingList(Base):
    """Packlisten für Reisen."""
    __tablename__ = "packing_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # "Kurztrip Wochenende", "Urlaub 2 Wochen"
    trip_type = Column(String(100), nullable=True)  # beach, city, business, hiking
    items = Column(JSON, nullable=False)  # [{"item": "Zahnbürste", "checked": false}]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PackingList(id={self.id}, name='{self.name}')>"


class Routine(Base):
    """Routinen und wiederkehrende Muster."""
    __tablename__ = "routines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    routine_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    time_of_day = Column(String(50), nullable=True)  # morning, afternoon, evening
    enabled = Column(Boolean, default=True)
    actions = Column(JSON, nullable=False)  # [{"action": "remind", "params": {...}}]
    last_executed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Routine(id={self.id}, name='{self.name}', type='{self.routine_type}')>"


class SystemConfig(Base):
    """Globale System-Konfiguration (Singleton)."""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # AI & Model Settings
    default_model = Column(String(100), default="llama3.2:3b", nullable=False)
    max_tokens = Column(Integer, default=2000, nullable=False)
    temperature = Column(Integer, default=70, nullable=False)  # 0-100 (wird zu 0.0-1.0)
    system_prompt = Column(Text, nullable=True)  # Globaler System Prompt
    
    # Rate Limits
    guest_message_limit = Column(Integer, default=20, nullable=False)
    guest_message_length = Column(Integer, default=500, nullable=False)
    user_message_limit = Column(Integer, default=100, nullable=False)
    rate_limit_window = Column(Integer, default=60, nullable=False)  # Sekunden
    
    # Features
    web_search_enabled = Column(Boolean, default=True, nullable=False)
    location_services_enabled = Column(Boolean, default=True, nullable=False)
    guest_mode_enabled = Column(Boolean, default=True, nullable=False)
    registration_enabled = Column(Boolean, default=True, nullable=False)
    
    # Privacy
    data_retention_days = Column(Integer, default=30, nullable=False)
    search_history_retention_days = Column(Integer, default=7, nullable=False)
    location_retention_days = Column(Integer, default=30, nullable=False)
    auto_delete_enabled = Column(Boolean, default=True, nullable=False)
    
    # Ollama Settings
    ollama_host = Column(String(255), default="http://localhost:11434", nullable=False)
    ollama_timeout = Column(Integer, default=120, nullable=False)
    ollama_pull_on_start = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(id={self.id}, model='{self.default_model}')>"
