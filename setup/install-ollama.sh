#!/bin/bash
set -e

echo "🚀 Ollama Installation für Liara"
echo "================================"
echo ""

# Prüfe ob root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen: sudo bash install-ollama.sh"
    exit 1
fi

echo "✓ Root-Rechte bestätigt"
echo ""

# 1. Download und installiere Ollama
echo "📦 Installiere Ollama..."
if curl -fsSL https://ollama.com/install.sh | sh; then
    echo "✓ Ollama installiert"
else
    echo "❌ Installation fehlgeschlagen"
    exit 1
fi
echo ""

# 2. Warte bis Ollama Service läuft
echo "⏳ Warte auf Ollama Service..."
sleep 3
if systemctl is-active --quiet ollama; then
    echo "✓ Ollama Service läuft"
else
    echo "⚠️  Service noch nicht aktiv, starte manuell..."
    systemctl start ollama 2>/dev/null || /usr/local/bin/ollama serve &
    sleep 3
fi
echo ""

# 3. Modelle laden
echo "📚 Lade Ollama-Modelle..."
echo "   Dies kann einige Minuten dauern..."
echo ""

echo "⬇️  Lade llama3.2:1b (700MB - schnell)..."
/usr/local/bin/ollama pull llama3.2:1b
echo ""

echo "⬇️  Lade llama3.2:3b (2GB - standard)..."
/usr/local/bin/ollama pull llama3.2:3b
echo ""

echo "⬇️  Lade mistral:7b (4GB - premium)..."
/usr/local/bin/ollama pull mistral:7b
echo ""

echo "⬇️  Lade llama3.1:8b (4.7GB - beste Qualität)..."
/usr/local/bin/ollama pull llama3.1:8b
echo ""

# Zeige installierte Modelle
echo "✅ Installation abgeschlossen!"
echo ""
echo "📋 Installierte Modelle:"
/usr/local/bin/ollama list
echo ""

echo "🎉 Ollama ist bereit!"
echo ""
echo "Teste mit:"
echo "  ollama run llama3.2:3b"
echo ""
echo "Service-Befehle:"
echo "  systemctl status ollama"
echo "  systemctl restart ollama"
echo "  journalctl -u ollama -f"
