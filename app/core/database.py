"""
Database Configuration für Liara.

SQLAlchemy Setup mit PostgreSQL Support.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

# Database URL aus .env
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://liara:liara_secure_2025@localhost/liara_db"
)

# Engine erstellen
# Multi-Worker optimized pool settings (v2.7.0)
# pool_size=50: Base connection pool for 17 workers
# max_overflow=100: Additional connections during load spikes
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Test Connection vor Nutzung
    pool_size=50,
    max_overflow=100,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # SQL-Logging (True für Debug)
)

# Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base für Models
Base = declarative_base()


def get_db():
    """
    Dependency für FastAPI.
    
    Nutze als:
        @router.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context Manager für manuelle DB-Nutzung.
    
    Nutze als:
        with get_db_context() as db:
            result = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Erstelle alle Tables (nur für lokales Development/Bootstrap, NIE gegen
    Produktion) - issue #12 item 5.

    Alembic ist die einzige autoritative Schema-Quelle für Produktion
    (`alembic upgrade head`). create_all() erstellt fehlende Tables anhand
    der aktuellen Model-Definitionen, versioniert aber nichts und würde ein
    unvollständiges/abweichendes Schema stillschweigend "reparieren" statt
    die Abweichung sichtbar zu machen - das genaue Gegenteil von dem, was
    ein Migrations-Tool leisten soll. Nur aus dem Standalone-Skript
    `app/init_db.py` aufgerufen, nicht aus main.py's Startup.
    """
    Base.metadata.create_all(bind=engine)


def check_connection():
    """
    Prüfe DB-Connection.
    
    Returns:
        bool: True wenn Connection erfolgreich
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
