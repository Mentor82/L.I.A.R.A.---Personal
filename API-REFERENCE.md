# 🌙 Liara API Reference

**Base URL**: `http://localhost:8100`

---

## System & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API Status & Version |
| `/info` | GET | System Information (CPU, Memory, Uptime) |
| `/dashboard/info` | GET | Dashboard Metrics |
| `/liara/status` | GET | Liara Status |
| `/liara/health` | GET | Liara Health Check |
| `/liara/about` | GET | About Liara |
| `/liara/persona` | GET | Persona Definition & Version |

---

## Chat & Messages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/message` | POST | Send Chat Message |
| `/chat/stream` | POST | Stream Chat Response |
| `/chat/models` | GET | List Available Models |
| `/chat/models/summary` | GET | Model Summary |
| `/chat/model/select` | POST | Select Active Model |
| `/chat/status` | GET | Chat Status |

---

## Sessions & Memory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat-sessions/` | GET | List Sessions |
| `/chat-sessions/` | POST | Create Session |
| `/chat-sessions/{id}` | GET | Get Session |
| `/chat-sessions/{id}` | PUT | Update Session |
| `/chat-sessions/{id}` | DELETE | Delete Session |
| `/memory/` | GET | List Memories |
| `/memory/` | POST | Create Memory |
| `/memory/{id}` | GET | Get Memory |
| `/memory/{id}` | PUT | Update Memory |
| `/memory/{id}` | DELETE | Delete Memory |

---

## Mood & Sentiment

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mood/status` | GET | Current Mood Status |
| `/mood/update` | POST | Update Mood |
| `/mood/detect` | POST | Auto-Detect Mood |
| `/mood/modifiers` | GET | Available Mood Modifiers |
| `/mood/reset` | POST | Reset Mood |
| `/mood/states` | GET | Mood State History |
| `/sentiment/analyze` | POST | Analyze Sentiment |

---

## Tasks, Calendar & Notes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks` | GET | List Tasks |
| `/tasks` | POST | Create Task |
| `/tasks/{id}` | GET | Get Task |
| `/tasks/{id}` | PUT | Update Task |
| `/tasks/{id}` | DELETE | Delete Task |
| `/tasks/{id}/complete` | POST | Mark Complete |
| `/tasks/daily` | GET | Daily Tasks |
| `/tasks/weekly` | GET | Weekly Tasks |
| `/calendar` | GET | List Calendar Events |
| `/calendar` | POST | Create Event |
| `/calendar/{id}` | DELETE | Delete Event |
| `/notes` | GET | List Notes |
| `/notes` | POST | Create Note |
| `/notes/{id}` | PUT | Update Note |
| `/notes/{id}` | DELETE | Delete Note |

---

## AI Validation & Code Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate/health` | GET | Multi-Backend Health Status |
| `/validate/models` | GET | Available Models |
| `/validate/generate` | POST | Generate Text |
| `/validate/python` | POST | Validate Python Code |
| `/validate/javascript` | POST | Validate JavaScript |
| `/validate/typescript` | POST | Validate TypeScript |
| `/validate/java` | POST | Validate Java |
| `/validate/cpp` | POST | Validate C++ |
| `/validate/rust` | POST | Validate Rust |
| `/validate/go` | POST | Validate Go |
| `/validate/ruby` | POST | Validate Ruby |
| `/validate/php` | POST | Validate PHP |
| `/validate/sql` | POST | Validate SQL |
| `/validate/bash` | POST | Validate Bash |
| `/validate/json` | POST | Validate JSON |
| `/validate/yaml` | POST | Validate YAML |
| `/validate/html` | POST | Validate HTML |
| `/validate/css` | POST | Validate CSS |

---

## Backend Services

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gpu` | GET | GPU Metrics |
| `/ollama/models` | GET | Ollama Models |
| `/ollama/model/{name}` | GET | Model Details |
| `/hailo/health` | GET | Hailo-8L NPU Status |
| `/hailo/device` | GET | Hailo Device Information |
| `/hailo/models` | GET | List HEF Models |
| `/hailo/infer` | POST | Run Inference on Model |
| `/hailo/metrics` | GET | Prometheus Metrics |
| `/hailo/power` | GET | Power Consumption Profile |
| **HAILO VISION** | | **Optimized Computer Vision on NPU** |
| `/hailo/vision/models` | GET | List Vision Models |
| `/hailo/vision/detect` | POST | Object Detection (YOLOv8) |
| `/hailo/vision/pose` | POST | Human Pose Estimation |
| `/hailo/vision/faces` | POST | Face Detection & Landmarks |
| `/hailo/vision/segment` | POST | Instance Segmentation |
| `/vision/analyze` | POST | Image Analysis (LLaVA/Ollama) |

---

## Admin Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/services` | GET | System Services |
| `/admin/services/{name}/start` | POST | Start Service |
| `/admin/services/{name}/stop` | POST | Stop Service |
| `/admin/terminal` | WebSocket | Terminal PTY |
| `/admin/logs` | GET | System Logs |
| `/admin/config` | GET | System Config |

---

## Authentication & Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Login |
| `/auth/logout` | POST | Logout |
| `/auth/verify` | GET | Verify Token |
| `/users` | GET | List Users (Admin) |
| `/users/{id}` | GET | Get User |
| `/users/{id}` | PUT | Update User |
| `/profile` | GET | Current User Profile |
| `/profile` | PUT | Update Profile |

---

## Privacy & Location

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/privacy/consent` | GET | Privacy Consent Status |
| `/privacy/consent` | POST | Update Consent |
| `/location/detect` | GET | Detect Location |
| `/location/set` | POST | Set Manual Location |
| `/web-safety/check` | POST | Web Safety Check |

---

## Multi-Backend Validation Architecture

### Primary: liara-core (192.168.178.60:11434)
- **Status**: ✅ HEALTHY
- **Timeout**: 120s inference, 10s health check
- **Models**: phi:2.7b, llama3.1:8b, mistral:7b

### Fallback: liara (192.168.178.50:11434)
- **Status**: ✅ HEALTHY
- **Timeout**: 120s inference, 10s health check
- **Models**: 10 models available

### Request Format

**Text Generation:**
```json
{
  "model": "phi:2.7b",
  "prompt": "Your prompt here",
  "max_tokens": 100
}
```

**Code Validation:**
```json
{
  "code": "your code here"
}
```

---

## Hailo Vision API (Hailo-8L NPU on RPi5)

**Architecture**: All vision requests are proxied to **RPi5 (192.168.178.15:5000)** where the Hailo-8L NPU provides hardware-accelerated inference.

### Vision Model Availability

| Model | Type | Status | Input Size | Latency |
|-------|------|--------|-----------|----------|
| yolov8n | Detection | ✅ Ready | 640×640 | 45-65ms |
| yolov8s | Detection | ✅ Ready | 640×640 | 65-85ms |
| yolov8s_pose | Pose | ✅ Ready | 640×640 | 85-110ms |
| yolov5n_seg | Segmentation | ✅ Ready | 640×640 | 120-160ms |
| yolov5s_seg | Segmentation | ✅ Ready | 640×640 | 160-210ms |
| yolov11n | Detection | ✅ Ready | 640×640 | 50-70ms |
| yolov10n | Detection | ✅ Ready | 640×640 | 50-70ms |

**Location**: `/home/mirko/hailo_models/` on RPi5 | **Format**: HEF | **Source**: AWS S3

---

### 1. List Available Models

```bash
GET /hailo/vision/models
```

**Response**:
```json
{
  "count": 7,
  "models": ["yolov8n", "yolov8s", "yolov8s_pose", "yolov5n_seg", "yolov5s_seg", "yolov11n", "yolov10n"],
  "rpi5_status": "healthy",
  "source": "hailo-rpi5"
}
```

---

### 2. Object Detection

```bash
POST /hailo/vision/detect
Content-Type: multipart/form-data

file: <image (JPG/PNG/WEBP, max 10MB)>
model: yolov8n (optional)
confidence: 0.5 (optional, 0-1)
```

**Example**:
```bash
curl -X POST http://localhost:8100/hailo/vision/detect \
  -F "file=@image.jpg" \
  -F "model=yolov8s" \
  -F "confidence=0.5"
```

**Response**:
```json
{
  "model": "yolov8s",
  "confidence_threshold": 0.5,
  "status": "completed",
  "output": "[YOLO detection results]",
  "latency_ms": 72.5,
  "timestamp": "2026-01-03T23:12:10.123456",
  "rpi5_status": "healthy",
  "source": "hailo-rpi5"
}
```

**Supported**: 80 COCO classes (person, car, dog, cat, etc.)

---

### 3. Human Pose Estimation

```bash
POST /hailo/vision/pose
Content-Type: multipart/form-data

file: <image (JPG/PNG/WEBP, max 10MB)>
model: yolov8s_pose (optional)
```

**Example**:
```bash
curl -X POST http://localhost:8100/hailo/vision/pose \
  -F "file=@image.jpg"
```

**Response**:
```json
{
  "model": "yolov8s_pose",
  "status": "completed",
  "output": "[17-keypoint pose in COCO format]",
  "latency_ms": 98.3,
  "timestamp": "2026-01-03T23:12:10.123456",
  "rpi5_status": "healthy",
  "source": "hailo-rpi5"
}
```

**17 Keypoints**: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles

---

### 4. Face Detection

```bash
POST /hailo/vision/faces
Content-Type: multipart/form-data

file: <image (JPG/PNG/WEBP, max 10MB)>
model: yolov8s (optional)
confidence: 0.6 (optional)
```

**Example**:
```bash
curl -X POST http://localhost:8100/hailo/vision/faces \
  -F "file=@image.jpg" \
  -F "confidence=0.6"
```

---

### 5. Instance Segmentation

```bash
POST /hailo/vision/segment
Content-Type: multipart/form-data

file: <image (JPG/PNG/WEBP, max 10MB)>
model: yolov5n_seg (optional)
```

**Example**:
```bash
curl -X POST http://localhost:8100/hailo/vision/segment \
  -F "file=@image.jpg"
```

**Returns**: Instance masks with class labels

---

### Error Handling & Troubleshooting

| Status | Scenario | Fix |
|--------|----------|-----|
| 200 | Success | Inference completed ✅ |
| 400 | Invalid file | Use JPG/PNG/WEBP |
| 413 | File too large | Max 10MB per image |
| 503 | RPi5 offline | `ping 192.168.178.15` |
| 504 | Timeout | Model inference >30s |
| 500 | Inference error | Check model/image compatibility |

**Check RPi5**: `curl http://localhost:8100/hailo/vision/models | jq .rpi5_status`

**Restart RPi5 API**: `ssh mirko@192.168.178.15 "sudo systemctl restart hailo-api"`

---

**Last Updated**: Jan 3, 2026
**Liara Version**: 1.2.0
