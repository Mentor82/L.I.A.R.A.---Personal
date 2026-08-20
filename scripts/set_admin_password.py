#!/usr/bin/env python3
"""
Setzt das Passwort für den Benutzer 'admin' in der Liara-Datenbank neu (argon2-Hash).
"""
import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DB_URL = os.getenv('LIARA_DB_URL', 'postgresql://liara:liaras_own@localhost/liara_db')
NEW_PASSWORD = 'admin123'  # Hier gewünschtes Passwort setzen

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4
)

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()

# User-Modell importieren (Pfad ggf. anpassen)
from api.models.base_models import User

admin = session.query(User).filter(User.username == 'admin').first()
if not admin:
    print('Admin-Benutzer nicht gefunden!')
    exit(1)

admin.hashed_password = pwd_context.hash(NEW_PASSWORD)
session.commit()
print('✅ Passwort für admin erfolgreich und korrekt mit Argon2id neu gesetzt!')
