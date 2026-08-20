# 🖼️ Vision API - Bildanalyse mit LLaVA

## Status: ✅ Implementiert (v3.0.1)

**Datum**: 6. Dezember 2025  
**Modell**: Ollama LLaVA 7B (lokal, privacy-first)

---

## Features

✅ **Bild-Upload & Analyse**
- Multimodale Bildverarbeitung mit LLaVA
- Unterstützte Formate: JPG, PNG, WEBP
- Max. Dateigröße: 10 MB
- Base64-Encoding für API-Transport

✅ **Fähigkeiten**
- Bildbeschreibung (auf Deutsch)
- Objekt-Erkennung
- Szenen-Analyse
- Text-Extraktion (OCR)
- Fragen zu Bildern beantworten
- Kontext-basierte Konversation

✅ **API-Endpoints**
- `POST /vision/analyze` - Einzelbild analysieren
- `POST /vision/chat` - Chat mit Bild-Kontext
- `GET /vision/models` - Verfügbare Vision-Modelle
- `GET /vision/status` - Service-Status

---

## Architektur

```
Frontend (React)
    ↓ [File Upload]
Vision Router (/api/routers/vision.py)
    ↓ [Base64 Encoding]
Vision Service (/services/vision_service.py)
    ↓ [Ollama API Call]
LLaVA 7B (localhost:11434)
    ↓ [Multimodal Analysis]
Response (JSON)
```

**Ablauf:**
1. User lädt Bild hoch (Frontend)
2. Backend validiert Format & Größe
3. Konvertierung zu Base64
4. LLaVA-Analyse mit Custom-Prompt
5. Rückgabe der Beschreibung

---

## API-Usage

### 1. Bild analysieren

```bash
curl -X POST http://localhost:8100/vision/analyze \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/path/to/image.jpg" \
  -F "prompt=Was siehst du auf diesem Bild?"
```

**Response:**
```json
{
  "description": "Auf dem Bild sehe ich einen gelben Kreis in der Mitte eines roten Rechtecks vor blauem Hintergrund.",
  "model_used": "llava:7b",
  "processing_time_ms": 3421,
  "image_size": {
    "bytes": 29809,
    "mb": 0.03
  },
  "timestamp": "2025-12-06T00:10:15.123Z"
}
```

### 2. Chat mit Bild

```bash
curl -X POST http://localhost:8100/vision/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@screenshot.png" \
  -F "message=Erkläre mir, was auf diesem Screenshot zu sehen ist"
```

**Response:**
```json
{
  "response": "Auf dem Screenshot ist eine Webanwendung mit...",
  "model_used": "llava:7b",
  "has_image": true,
  "image_format": "image/png"
}
```

### 3. Verfügbare Modelle

```bash
curl http://localhost:8100/vision/models \
  -H "Authorization: Bearer <TOKEN>"
```

**Response:**
```json
{
  "available_models": ["llava:7b", "llava:13b"],
  "default_model": "llava:7b",
  "recommended": {
    "fast": "llava:7b",
    "quality": "llava:13b",
    "premium": "llava:34b"
  }
}
```

### 4. Service-Status

```bash
curl http://localhost:8100/vision/status
```

**Response:**
```json
{
  "vision_available": true,
  "model": "llava:7b",
  "capabilities": [
    "Bildbeschreibung",
    "Objekt-Erkennung",
    "Szenen-Analyse",
    "Text-Extraktion (OCR)",
    "Fragen zu Bildern beantworten"
  ]
}
```

---

## Installation

### LLaVA Modell installieren

```bash
# 7B (schnell, ~4.7 GB)
ollama pull llava:7b

# 13B (bessere Qualität, ~8 GB)
ollama pull llava:13b

# 34B (beste Qualität, ~20 GB)
ollama pull llava:34b
```

### Backend aktivieren

Vision-Router ist bereits integriert:
```python
# main.py
from api.routers.vision import router as vision_router
app.include_router(vision_router)
```

---

## Python Client

```python
import requests
import base64

def analyze_image(image_path: str, prompt: str, token: str):
    """Analysiere Bild mit Liara Vision API"""
    
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'prompt': prompt}
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.post(
            'http://localhost:8100/vision/analyze',
            files=files,
            data=data,
            headers=headers
        )
        
    return response.json()

# Usage
result = analyze_image(
    image_path='/tmp/screenshot.png',
    prompt='Beschreibe dieses Bild detailliert',
    token='YOUR_AUTH_TOKEN'
)

print(result['description'])
```

---

## Sicherheit

✅ **Privacy-First**
- Alle Bilder bleiben lokal
- Kein Upload zu externen Services
- LLaVA läuft on-premise

✅ **Validierung**
- Dateityp-Check (nur Bilder)
- Größenlimit: 10 MB
- User-Authentifizierung erforderlich

✅ **Performance**
- Base64-Encoding im Memory
- Keine Disk-Speicherung
- Asynchrone Verarbeitung

---

## Limitierungen

⚠️ **Aktuelle Beschränkungen:**
- **Max. Bildgröße**: 10 MB
- **Timeout**: 60 Sekunden
- **Modell**: LLaVA 7B (single-image only)
- **Sprache**: Beste Ergebnisse auf Englisch, Deutsch funktioniert gut
- **Batch-Processing**: Nicht unterstützt (einzelne Bilder)

---

## Nächste Schritte (v3.1)

### Frontend-Integration
- [ ] Bild-Upload UI im Chat
- [ ] Drag & Drop Support
- [ ] Bildvorschau vor Upload
- [ ] Progress Bar bei Analyse
- [ ] Inline-Anzeige der Ergebnisse

### Feature-Erweiterungen
- [ ] Multi-Image Support (mehrere Bilder gleichzeitig)
- [ ] Bild-History (letzte analysierten Bilder)
- [ ] Context-Memory (Chat mit Bezug auf vorherige Bilder)
- [ ] OCR-Optimierung (Text-Extraktion verbessern)

### Performance
- [ ] Image-Compression vor Upload
- [ ] Thumbnail-Generation
- [ ] Caching häufiger Analysen
- [ ] GPU-Beschleunigung für LLaVA

---

## Testing

```bash
# Test-Bild erstellen
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (800, 600), color='skyblue')
draw = ImageDraw.Draw(img)
draw.rectangle([100, 100, 700, 500], outline='red', width=10)
draw.ellipse([250, 200, 550, 400], fill='yellow', outline='orange', width=5)
img.save('/tmp/test_image.jpg', 'JPEG', quality=95)
print('✅ Test-Bild erstellt')
"

# Vision-Status prüfen
curl http://localhost:8100/vision/status | jq

# Test-Analyse (mit Token)
curl -X POST http://localhost:8100/vision/analyze \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -F "file=@/tmp/test_image.jpg" \
  -F "prompt=Beschreibe die Formen und Farben auf diesem Bild" \
  | jq
```

---

## Modell-Performance

| Modell | Größe | RAM | Geschwindigkeit | Qualität |
|--------|-------|-----|-----------------|----------|
| llava:7b | 4.7 GB | 8 GB | ~3-5s | Gut |
| llava:13b | 8 GB | 16 GB | ~5-8s | Sehr gut |
| llava:34b | 20 GB | 32 GB | ~10-15s | Exzellent |

**Empfehlung**: `llava:7b` für Alltag, `llava:13b` für höhere Qualität

---

## Troubleshooting

**Problem**: "LLaVA nicht verfügbar"
```bash
# Prüfe Ollama
systemctl status ollama
ollama list

# Installiere LLaVA
ollama pull llava:7b
```

**Problem**: "Worker exiting with code 3"
```bash
# Prüfe Logs
tail -50 /var/log/liara/error.log

# Backend neu starten
sudo systemctl restart liara-backend
```

**Problem**: "Bild zu groß"
- Komprimiere Bild vor Upload
- Max. 10 MB supported
- Reduziere Auflösung mit ImageMagick:
  ```bash
  convert input.jpg -resize 2000x2000\> -quality 85 output.jpg
  ```

---

## Changelog

### v3.0.1 (2025-12-06)
- ✅ Vision-API implementiert
- ✅ LLaVA 7B integriert
- ✅ Base64-Upload Support
- ✅ Multimodale Analyse
- ✅ Deutsche Beschreibungen
