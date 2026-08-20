#!/bin/bash
# Set PostgreSQL password for user 'liara' to 'liaras_own'

sudo -u postgres psql -c "ALTER USER liara WITH PASSWORD 'liaras_own';"

echo "✅ Passwort für Benutzer 'liara' wurde auf 'liaras_own' gesetzt."
