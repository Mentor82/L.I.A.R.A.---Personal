#!/bin/bash
set -e

echo "🐍 Liara Virtual Environment Setup"
echo "===================================="
echo ""

# Prüfe ob als root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Bitte NICHT als root ausführen!"
    echo "   Führe aus als: bash setup-venv.sh"
    exit 1
fi

VENV_PATH="/opt/liara/venv"
APP_PATH="/opt/liara/app"

# 1. Virtual Environment erstellen (falls nicht vorhanden)
if [ -d "$VENV_PATH" ]; then
    echo "✓ Virtual Environment existiert bereits"
else
    echo "📦 Erstelle Virtual Environment..."
    python3 -m venv "$VENV_PATH"
    echo "✓ Virtual Environment erstellt"
fi
echo ""

# 2. Aktiviere venv
echo "🔧 Aktiviere Virtual Environment..."
source "$VENV_PATH/bin/activate"
echo "✓ Virtual Environment aktiviert"
echo ""

# 3. Upgrade pip
echo "⬆️  Upgrade pip..."
pip install --upgrade pip setuptools wheel
echo "✓ pip aktualisiert"
echo ""

# 4. Installiere Requirements
if [ -f "$APP_PATH/requirements.txt" ]; then
    echo "📚 Installiere Dependencies aus requirements.txt..."
    pip install -r "$APP_PATH/requirements.txt"
    echo "✓ Dependencies installiert"
else
    echo "⚠️  requirements.txt nicht gefunden, installiere manuell..."
    pip install fastapi uvicorn[standard] psutil pydantic pydantic-settings \
                sqlalchemy apscheduler python-multipart requests \
                psycopg2-binary asyncpg
    echo "✓ Dependencies installiert"
fi
echo ""

# 5. Liste installierte Pakete
echo "📋 Installierte Pakete:"
pip list | grep -E "(fastapi|uvicorn|psutil|pydantic|sqlalchemy|requests|psycopg)"
echo ""

echo "✅ Setup abgeschlossen!"
echo ""
echo "Zum Aktivieren des venv in Zukunft:"
echo "  source /opt/liara/venv/bin/activate"
echo ""
echo "Backend starten:"
echo "  cd /opt/liara/app"
echo "  source /opt/liara/venv/bin/activate"
echo "  uvicorn main:app --reload --host 0.0.0.0"
