# CPU-Modus Performance-Tipps für Stable Diffusion

## ⚡ GT730 / Keine GPU Support

Die GT730 wird von aktuellen PyTorch-Versionen nicht mehr unterstützt (Compute Capability 3.5, zu alt).

**Lösung**: CPU-Modus nutzen!

---

## 🚀 Performance-Optimierungen

### 1. Reduzierte Auflösung
```bash
# Statt 1024x1024:
width=512
height=512

# Oder Portrait:
width=384
height=512
```

### 2. Weniger Steps
```bash
# Standard GPU: 20-50 Steps
# CPU: 10-15 Steps (ausreichend!)

num_steps=15
```

### 3. Schnellerer Sampler
```bash
# Beste CPU-Performance:
sampler="Euler a"  # Schnell
sampler="LMS"      # Noch schneller

# Langsam (vermeiden):
sampler="DPM++ 2M Karras"
```

### 4. Kleineres Modell
```bash
# Statt SDXL (7GB):
# SD 1.5 (4GB) nutzen
```

---

## ⏱️ Erwartete Zeiten (CPU-Modus)

| Auflösung | Steps | CPU (8 Kerne) | CPU (16 Kerne) |
|-----------|-------|---------------|----------------|
| 512x512   | 10    | ~1-2 min      | ~45-60s        |
| 512x512   | 15    | ~2-3 min      | ~60-90s        |
| 512x768   | 15    | ~3-4 min      | ~90-120s       |
| 768x768   | 15    | ~4-6 min      | ~2-3 min       |

---

## 🔧 WebUI CPU-Start Flags

```bash
./webui.sh \
  --api \
  --listen \
  --skip-torch-cuda-test \  # Überspringe CUDA-Check
  --no-half \               # CPU braucht full precision
  --precision full \        # Explizit full precision
  --medvram                 # Weniger RAM nutzen (optional)
```

---

## 💡 Alternative: Externe GPU später

Wenn du irgendwann eine bessere GPU einbauen möchtest:

**Empfohlene Budget-GPUs für Stable Diffusion:**
- **RTX 3060** (12GB VRAM) - ~300€ gebraucht
- **RTX 3060 Ti** (8GB) - ~250€
- **RTX 4060** (8GB) - ~320€ neu

**Performance-Vergleich:**
- GT730: ❌ Nicht unterstützt
- CPU (16 Kerne): 🐌 2-5 Minuten
- RTX 3060: ⚡ 3-8 Sekunden
- RTX 4090: 🚀 1-2 Sekunden

---

## 📊 RAM-Anforderungen

| Modell | Minimum RAM | Empfohlen |
|--------|-------------|-----------|
| SD 1.5 | 8 GB        | 12 GB     |
| SDXL   | 16 GB       | 24 GB     |

**Dein System**: Sollte für SD 1.5 ausreichen!

---

## 🎯 Liara CPU-Konfiguration

Anpassungen in `image_generation.py`:

```python
# Defaults für CPU-Modus:
width: int = 512       # Statt 1024
height: int = 512      # Statt 1024
num_steps: int = 15    # Statt 20
sampler: str = "Euler a"  # Schnellster
```

User kann im Chat sagen:
```
"Erstell mir ein Bild, klein und schnell"
→ Liara nutzt 384x384, 10 Steps
```

---

## ✅ Vorteile CPU-Modus

- ✅ Funktioniert ohne GPU
- ✅ Keine Treiber-Probleme
- ✅ Stabiler (kein VRAM-OOM)
- ✅ Privacy-First (lokal)

**Nachteil**: Langsamer (aber für gelegentliche Nutzung OK!)

---

**Empfehlung**: 
CPU-Modus für jetzt, später eventuell RTX 3060 (12GB) holen wenn Bild-Generierung oft genutzt wird.
