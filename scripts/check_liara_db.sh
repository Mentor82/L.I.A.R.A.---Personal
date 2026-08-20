#!/bin/bash
# Prüft, ob die wichtigsten Liara-Tabellen existieren und gibt Status aus

DB_NAME="liara_db"
DB_USER="liara"
DB_HOST="localhost"
DB_PORT="5432"

# Optional: Passwort aus Umgebungsvariable
if [ -z "$LIARA_DB_PASS" ]; then
  read -s -p "DB-Passwort für $DB_USER: " LIARA_DB_PASS
  echo
fi

export PGPASSWORD="$LIARA_DB_PASS"

function check_table {
  local table="$1"
  echo -n "Prüfe Tabelle '$table' ... "
  exists=$(psql -U "$DB_USER" -h "$DB_HOST" -d "$DB_NAME" -p "$DB_PORT" -tAc "SELECT to_regclass('$table');")
  if [[ "$exists" == "$table" ]]; then
    echo "OK"
  else
    echo "FEHLT!"
  fi
}

check_table "chat_sessions"
check_table "users"
check_table "chat_messages"

unset PGPASSWORD
