# Lokale Stable Diffusion Setup für Liara

## 🎨 Privacy-First Bild-Generierung

Liara nutzt **AUTOMATIC1111 Stable Diffusion WebUI** für lokale Bild-Generierung.

**Alle Daten bleiben auf deinem Server** - keine Cloud-APIs!

---

## 📦 Installation

### 1. AUTOMATIC1111 WebUI installieren

```bash
cd /opt
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
cd stable-diffusion-webui
```

### 2. Stable Diffusion Modell herunterladen

**Option A: Stable Diffusion 1.5** (schnell, 4GB)
```bash
cd models/Stable-diffusion/
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
```

**Option B: Stable Diffusion XL** (besser, 7GB)
```bash
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

### 3. WebUI mit API starten

```bash
cd /opt/stable-diffusion-webui
./webui.sh --api --listen --port 7860
```

**Flags:**
- `--api`: Aktiviert REST API für Liara
- `--listen`: Akzeptiert externe Verbindungen
- `--port 7860`: Standard-Port (anpassbar)

---

## ⚙️ Liara Konfiguration

### .env anpassen

```bash
# /opt/liara/app/.env
SD_WEBUI_URL=http://localhost:7860
SD_OUTPUT_DIR=/opt/liara/app/generated_images
```

### Backend neustarten

```bash
sudo systemctl restart liara
```

---

## 🚀 Verwendung

### Im Chat

User: "Kannst du mir ein Bild erstellen, ein futuristisches Raumschiff?"

Liara generiert lokal und zeigt Bild im Chat!

---

## 🔧 Systemd Service (Auto-Start)

Damit Stable Diffusion automatisch startet:

```bash
sudo nano /etc/systemd/system/sd-webui.service
```

```ini
[Unit]
Description=Stable Diffusion WebUI
After=network.target

[Service]
Type=simple
User=mirko
WorkingDirectory=/opt/stable-diffusion-webui
ExecStart=/bin/bash /opt/stable-diffusion-webui/webui.sh --api --listen --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable sd-webui
sudo systemctl start sd-webui
```

---

## 💻 Hardware-Anforderungen

| Komponente | Minimum | Empfohlen |
|------------|---------|-----------|
| **GPU** | NVIDIA GTX 1060 (6GB) | RTX 3060 (12GB) |
| **RAM** | 8 GB | 16 GB |
| **Speicher** | 10 GB | 20 GB (für mehrere Modelle) |
| **VRAM** | 4 GB | 8 GB+ |

**Ohne GPU**: CPU-Modus möglich, aber langsam (2-5 Minuten pro Bild)

---

## 🎯 Optimierungen

### xFormers (schneller)

```bash
cd /opt/stable-diffusion-webui
./webui.sh --reinstall-xformers
./webui.sh --api --listen --xformers
```

### Low VRAM Mode (bei wenig GPU-RAM)

```bash
./webui.sh --api --listen --medvram
# Oder für sehr wenig VRAM:
./webui.sh --api --listen --lowvram
```

### Schnellere Sampler

In Liara's Config:
- **Euler a**: Schnell, gute Qualität
- **DPM++ 2M Karras**: Beste Qualität
- **LMS**: Sehr schnell

---

## 🔍 Troubleshooting

### "SD WebUI nicht erreichbar"

**Prüfe ob Service läuft:**
```bash
curl http://localhost:7860/sdapi/v1/sd-models
```

**Erwartete Antwort:**
```json
[
  {
    "title": "v1-5-pruned-emaonly",
    "model_name": "v1-5-pruned-emaonly",
    ...
  }
]
```

### Port-Konflikt

```bash
sudo lsof -i :7860
# Prozess killen:
sudo kill -9 <PID>
```

### Out of Memory (OOM)

```bash
# Reduziere Bildgröße
# In Liara Chat-Endpoint: width=512, height=512 statt 1024
```

---

## 📊 Performance

| Modell | Auflösung | Steps | Zeit (RTX 3060) | Qualität |
|--------|-----------|-------|-----------------|----------|
| SD 1.5 | 512x512 | 20 | ~3s | ⭐⭐⭐ |
| SD 1.5 | 768x768 | 30 | ~8s | ⭐⭐⭐⭐ |
| SDXL | 1024x1024 | 20 | ~15s | ⭐⭐⭐⭐⭐ |

---

## 🎨 Modell-Empfehlungen

### Realistische Bilder
- **Realistic Vision**: https://civitai.com/models/4201
- **DreamShaper**: https://civitai.com/models/4384

### Anime/Cartoon
- **Anything V5**: https://civitai.com/models/9409
- **Counterfeit**: https://civitai.com/models/4468

### Artistic
- **Dreamlike Photoreal**: https://civitai.com/models/1274
- **Protogen**: https://civitai.com/models/3627

Modelle nach `/opt/stable-diffusion-webui/models/Stable-diffusion/` kopieren.

---

## 🔐 Sicherheit

**Privacy-Vorteile gegenüber Cloud-APIs:**
- ✅ Keine Daten verlassen den Server
- ✅ Keine API-Keys/Tracking
- ✅ Keine Kosten pro Bild
- ✅ Unbegrenzte Generierungen
- ✅ Volle Kontrolle über Modelle
- ✅ DSGVO-konform

---

## 📚 Weiterführende Links

- **AUTOMATIC1111 Wiki**: https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki
- **Civitai Models**: https://civitai.com
- **Hugging Face**: https://huggingface.co/models?pipeline_tag=text-to-image
- **r/StableDiffusion**: https://reddit.com/r/StableDiffusion

---

## ✅ Checklist

- [ ] AUTOMATIC1111 installiert
- [ ] Modell heruntergeladen (SD 1.5 oder SDXL)
- [ ] WebUI mit `--api --listen` gestartet
- [ ] `SD_WEBUI_URL` in `.env` gesetzt
- [ ] Liara Backend neugestartet
- [ ] Test-Bild generiert
- [ ] Optional: Systemd Service eingerichtet

---

**Status**: Privacy-First ✅
**Kosten**: $0 (nur Strom)
**Datum**: 6. Dezember 2025
