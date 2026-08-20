#!/bin/bash
# Setzt das Passwort für den Benutzer 'admin' in der Liara-Datenbank (argon2-Hash)

DB_NAME="liara_db"
DB_USER="liara"
NEW_PASSWORD="admin123"

# Erzeuge argon2-Hash
HASHED_PW=$(python3 -c "from passlib.hash import argon2; print(argon2.hash('$NEW_PASSWORD'))")

PGPASSWORD="liaras_own" psql -U $DB_USER -h localhost -d $DB_NAME -c "UPDATE users SET hashed_password = '$HASHED_PW' WHERE username = 'admin';"

echo "✅ Passwort für admin erfolgreich neu gesetzt!"
