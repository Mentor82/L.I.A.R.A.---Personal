# Lokale Stable Diffusion Integration für Liara

## 🎨 Privacy-First Bild-Generierung

Liara nutzt **AUTOMATIC1111 Stable Diffusion WebUI** für lokale Bild-Generierung.

**Alle Daten bleiben auf deinem Server** - keine Cloud-APIs, keine Tracking, 100% privat!

---

## ⚡ Features

- **Privacy-First**: Alle Daten lokal, keine Cloud
- **Kostenlos**: Keine API-Gebühren
- **Unbegrenzt**: Generiere so viele Bilder wie du willst
- **Anpassbar**: Wähle eigene Modelle (Realistic, Anime, Artistic)
- **Schnell**: 3-15 Sekunden (mit GPU)

---

## 🔧 Setup

Siehe: [`/opt/liara/docs/STABLE_DIFFUSION_SETUP.md`](/opt/liara/docs/STABLE_DIFFUSION_SETUP.md)

**Kurzversion:**
1. AUTOMATIC1111 installieren
2. Modell herunterladen (SD 1.5 oder SDXL)
3. WebUI mit `--api` starten
4. Liara Backend neustarten

---

## 💻 Vorteile gegenüber Cloud-APIs

| Feature | Lokal (Liara) | Cloud (Replicate) |
|---------|---------------|-------------------|
| **Kosten** | $0 (nur Strom) | $0.002-$0.005/Bild |
| **Privacy** | ✅ 100% lokal | ❌ Daten in Cloud |
| **Tracking** | ✅ Kein Tracking | ❌ API-Logs |
| **Limite** | ✅ Unbegrenzt | ❌ Rate Limits |
| **DSGVO** | ✅ Konform | ⚠️ US-Server |
| **Anpassung** | ✅ Eigene Modelle | ❌ Feste Modelle |

---

## 🚀 Verwendung

### Im Chat

User fragt einfach:

```
"Kannst du mir ein Bild erstellen, eine mechanische Einheit aus Gold und Juwelen?"
```

Liara erkennt automatisch:
- Keywords: "bild", "erstell", "generier", "mal", "zeichne"
- Optimiert Prompt
- Generiert Bild
- Zeigt Bild im Chat (Markdown)

### API Direct

```bash
curl -X POST http://localhost:8100/chat/generate-image \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "prompt": "A mechanical gold unit with jewels and magic",
    "width": 512,
    "height": 512,
    "num_steps": 20
  }'
```

Response:

```json
{
  "success": true,
  "image_path": "/opt/liara/app/generated_images/liara_20251206_190630.png",
  "image_url": "/api/images/liara_20251206_190630.png",
  "image_base64": "data:image/png;base64,iVBORw0KG...",
  "prompt": "A mechanical gold unit...",
  "model": "Stable Diffusion (local)",
  "generation_time": 3.2
}
```

---

## 🎯 Prompt-Optimierung

Liara optimiert automatisch basierend auf Keywords:

| User-Wunsch | Automatische Tags |
|-------------|-------------------|
| "Foto von..." | `photorealistic, studio lighting` |
| "Fantasy Szene..." | `artstation, concept art, elegant` |
| "Mechanisches..." | `industrial design, intricate mechanisms` |
| Default | `highly detailed, professional, 8k uhd, sharp focus` |

---

## 🔒 Fallback-Modus

**Wenn SD WebUI nicht läuft:**

```
🤖 Liara: "Ich würde dir sehr gerne ein Bild erstellen! 🎨 
Allerdings ist meine lokale Stable Diffusion derzeit nicht gestartet. 
Mein Administrator kann sie mit `./webui.sh --api --listen` starten. 
Dann kann ich wunderschöne Bilder für dich erstellen - komplett privat! 🔒"
```

---

## 📊 Technische Details

### Backend

**File**: `services/image_generation.py`
- API-Endpoint: `http://localhost:7860/sdapi/v1/txt2img`
- Output: Base64 + lokale Datei
- Timeout: 180 Sekunden
- Format: PNG

**Endpoint**: `POST /chat/generate-image`
- Auth: Required (JWT)
- Default: 512x512, 20 Steps

### Frontend

**Markdown-Integration**: Base64-Images direkt im Chat
```markdown
![Generiertes Bild](data:image/png;base64,...)
```

**CSS** (`MarkdownMessage.css`):
- Rounded Corners: 12px
- Purple Border: `rgba(139, 92, 246, 0.3)`
- Hover-Effekt: `scale(1.02)` + Shadow
- Cursor: Pointer (klickbar)

---

## 🐛 Troubleshooting

### "SD WebUI nicht erreichbar"

**Ursache**: Stable Diffusion WebUI läuft nicht

**Lösung**:
```bash
cd /opt/stable-diffusion-webui
./webui.sh --api --listen
```

**Prüfe Status:**
```bash
curl http://localhost:7860/sdapi/v1/sd-models
```

### Out of Memory (GPU)

**Ursache**: GPU-VRAM zu klein

**Lösung**:
```bash
./webui.sh --api --listen --medvram
# Oder:
./webui.sh --api --listen --lowvram
```

### Bilder zu langsam

**Optimierungen:**
- xFormers installieren: `./webui.sh --reinstall-xformers`
- Schnellere Sampler: Euler a, LMS
- Weniger Steps: 15 statt 20

---

## 📈 Monitoring

### Backend Logs

```bash
sudo journalctl -u liara -f | grep -i "image"
```

### Request-Beispiel

```python
# services/image_generation.py
async def generate_image(prompt: str):
    # POST zu Replicate API
    # Polling bis "succeeded"
    # Return image_url
```

## 🔮 Roadmap

- [x] Lokale Stable Diffusion (AUTOMATIC1111)
- [ ] Bild-Variationen generieren
- [ ] Inpainting (Bild-Editierung)
- [ ] ControlNet (Pose, Depth)
- [ ] Style-Presets (Anime, Realistic, Artistic)
- [ ] Bild-Galerie im Frontend
- [ ] Batch-Generierung (mehrere Bilder)
- [ ] LoRA Support

---

## ✅ Changelog

**v2.8.0** (6. Dezember 2025)
- ✅ Lokale Stable Diffusion Integration
- ✅ AUTOMATIC1111 WebUI Support
- ✅ Privacy-First (keine Cloud-APIs)
- ✅ Base64-Rendering im Chat
- ✅ Prompt-Optimierung
- ✅ Timeout-Fix (60s → 120s)
- ✅ Intent-Erkennung für Bild-Anfragen

---

## 📝 Beispiele

### Overdrive's Original-Anfrage (jetzt funktioniert!)

**User**: "Kannst du mir ein Bild erstellen, eine Mechanischer Einheit aus Gold und Juwelen, mit Magie..."

**Liara** (VORHER): 
```
Error: Read timed out (60s)
```

**Liara** (JETZT):
```
🎨 Hier ist dein Bild! Ich habe es mit meiner lokalen Stable Diffusion erstellt.

![Generiertes Bild](data:image/png;base64,...)

✨ Generiert in 3.2 Sekunden - komplett privat auf diesem Server! 🔒
```
✨ Generiert mit SDXL Lightning in 3.2 Sekunden.
```

### Weitere Beispiele

```
"Mal mir einen Sonnenuntergang am Meer"
→ Photorealistic, Studio Lighting

"Zeig mir eine Fantasy-Stadt"
→ Artstation, Concept Art, Elegant

"Erstell ein futuristisches Raumschiff"
→ Industrial Design, Intricate Mechanisms
```

---

## 🎓 Für Entwickler

### Dependencies

```python
# requirements.txt (bereits vorhanden)
httpx>=0.28.0  # Für Replicate API
```

### Eigene Prompts

```python
from services.image_generation import get_image_generation_service

service = get_image_generation_service()

result = await service.generate_image(
    prompt="Dein Custom Prompt",
    width=768,
    height=1024,  # Portrait
    num_steps=8,  # Mehr Steps = bessere Qualität
    guidance_scale=0.0
)

if result["success"]:
    print(result["image_url"])
```

---
## 🙏 Credits

- **AUTOMATIC1111**: Stable Diffusion WebUI
- **Stability AI**: Stable Diffusion Models
- **FastAPI**: Backend Framework
- **React Markdown**: Frontend Rendering

---

**Status**: ✅ Privacy-First Implementierung
**Kosten**: $0 (nur Strom)
**Version**: 2.8.0
**Datum**: 6. Dezember 2025
**Datum**: 6. Dezember 2025
