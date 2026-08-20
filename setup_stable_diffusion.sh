#!/bin/bash
# Quick Setup für Stable Diffusion WebUI

set -e

echo "🎨 Stable Diffusion Setup für Liara"
echo "==================================="
echo ""

# 1. Prüfe System
echo "📊 Prüfe System-Anforderungen..."
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
CPU_CORES=$(nproc)

echo "CPU: $CPU_CORES Kerne"
echo "RAM: ${RAM_GB}GB"

if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU gefunden:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    USE_CPU=false
else
    echo "ℹ️  Keine unterstützte GPU - nutze CPU-Modus"
    echo "   (GT730 zu alt für Stable Diffusion)"
    echo "   Performance: 2-5 Minuten pro Bild (512x512)"
    USE_CPU=true
fi

# 2. Clone Repository
if [ ! -d "/opt/stable-diffusion-webui" ]; then
    echo ""
    echo "📥 Klone AUTOMATIC1111 Repository..."
    cd /opt
    sudo git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
    sudo chown -R $USER:$USER /opt/stable-diffusion-webui
else
    echo "✅ AUTOMATIC1111 bereits installiert"
fi

# 3. Download Modell
cd /opt/stable-diffusion-webui/models/Stable-diffusion/
if [ ! -f "v1-5-pruned-emaonly.safetensors" ]; then
    echo ""
    echo "📦 Lade Stable Diffusion 1.5 herunter (4GB)..."
    wget -q --show-progress https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
    echo "✅ Modell heruntergeladen"
else
    echo "✅ Modell bereits vorhanden"
fi

# 4. .env konfigurieren
echo ""
echo "⚙️  Konfiguriere Liara..."
cd /opt/liara/app
if ! grep -q "SD_WEBUI_URL" .env 2>/dev/null; then
    cat >> .env << 'EOF'

# Stable Diffusion (lokale Bild-Generierung)
SD_WEBUI_URL=http://localhost:7860
SD_OUTPUT_DIR=/opt/liara/app/generated_images
EOF
    echo "✅ .env aktualisiert"
else
    echo "✅ .env bereits konfiguriert"
fi

# 5. Output-Verzeichnis erstellen
mkdir -p /opt/liara/app/generated_images
echo "✅ Output-Verzeichnis erstellt"

# 6. Systemd Service (optional)
echo ""
read -p "Soll Stable Diffusion automatisch starten? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[JjYy]$ ]]; then
    sudo tee /etc/systemd/system/sd-webui.service > /dev/null << EOF
[Unit]
Description=Stable Diffusion WebUI
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/stable-diffusion-webui
ExecStart=/bin/bash /opt/stable-diffusion-webui/webui.sh --api --listen --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable sd-webui
    echo "✅ Systemd Service erstellt"
fi

# 7. Start WebUI
echo ""
echo "🚀 Starte Stable Diffusion WebUI..."
cd /opt/stable-diffusion-webui

# Erste Installation (download dependencies)
if [ ! -d "venv" ]; then
    echo "📦 Installiere Dependencies (kann 5-10 Minuten dauern)..."
    ./webui.sh --skip-torch-cuda-test --exit
fi

# Starte im Hintergrund
echo "🎨 Starte WebUI mit API..."
if [ "$USE_CPU" = true ]; then
    echo "⚙️  CPU-Modus aktiviert (langsamer, aber funktioniert ohne GPU)"
    nohup ./webui.sh --api --listen --port 7860 --skip-torch-cuda-test --no-half --precision full > /tmp/sd-webui.log 2>&1 &
else
    nohup ./webui.sh --api --listen --port 7860 > /tmp/sd-webui.log 2>&1 &
fi
WEBUI_PID=$!
echo "PID: $WEBUI_PID"

# Warte auf Start
echo "⏳ Warte auf WebUI-Start (kann 30-60 Sekunden dauern)..."
for i in {1..60}; do
    if curl -s http://localhost:7860/sdapi/v1/sd-models > /dev/null 2>&1; then
        echo "✅ WebUI läuft!"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# 8. Teste API
echo ""
echo "🧪 Teste API..."
if curl -s http://localhost:7860/sdapi/v1/sd-models | grep -q "v1-5"; then
    echo "✅ API funktioniert!"
    echo "✅ Modell geladen: Stable Diffusion 1.5"
else
    echo "⚠️  API-Test fehlgeschlagen"
    echo "Logs: tail -f /tmp/sd-webui.log"
fi

# 9. Restart Liara Backend
echo ""
read -p "Liara Backend neustarten? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[JjYy]$ ]]; then
    sudo systemctl restart liara
    echo "✅ Liara Backend neugestartet"
fi

# Zusammenfassung
echo ""
echo "🎉 Setup abgeschlossen!"
echo "===================="
echo ""
echo "📊 Status:"
echo "  WebUI: http://localhost:7860"
echo "  API: http://localhost:7860/docs"
echo "  Logs: tail -f /tmp/sd-webui.log"
echo ""
if [ "$USE_CPU" = true ]; then
    echo "⚠️  CPU-Modus Performance:"
    echo "  512x512: ~2-5 Minuten"
    echo "  Empfehlung: Niedrige Auflösung (512x512), weniger Steps (15)"
    echo ""
fi
echo "🎨 Test im Liara-Chat:"
echo '  "Kannst du mir ein Bild erstellen, ein futuristisches Raumschiff?"'
echo ""
echo "📚 Dokumentation:"
echo "  /opt/liara/docs/STABLE_DIFFUSION_SETUP.md"
echo "  /opt/liara/docs/IMAGE_GENERATION.md"
echo ""
echo "🔧 Weitere Modelle:"
echo "  https://civitai.com"
echo "  https://huggingface.co/models?pipeline_tag=text-to-image"
echo ""
