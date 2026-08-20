#!/bin/bash
# Prüft Admin-Login gegen die Liara API
# Usage: ./check_admin_login.sh <username> <password>

API_URL="http://localhost:8000/auth/login"
USERNAME="$1"
PASSWORD="$2"

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: $0 <username> <password>"
  exit 1
fi

RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

if echo "$RESPONSE" | grep -q 'access_token'; then
  echo "✅ Login erfolgreich!"
  echo "$RESPONSE"
else
  echo "❌ Login fehlgeschlagen!"
  echo "$RESPONSE"
fi
