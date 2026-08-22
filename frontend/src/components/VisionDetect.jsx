import { useEffect, useMemo, useRef, useState } from 'react'
import './VisionDetect.css'

const backends = [
  { value: 'hailo', label: 'Hailo-8L' },
  { value: 'edgetpu', label: 'Edge TPU' },
  { value: 'cpu', label: 'CPU-Stub' },
]

// Mirrors what each backend actually has wired up server-side:
// hailo_vision_service.MODELS_CONFIG and edge01's server.py MODEL_PATHS.
const modelsByBackend = {
  hailo: [
    { value: 'yolov8n', label: 'YOLOv8n (schnell)' },
    { value: 'yolov8s', label: 'YOLOv8s (genauer)' },
    { value: 'yolov8s-pose', label: 'YOLOv8s-Pose' },
  ],
  edgetpu: [
    { value: 'ssd_mobiledet', label: 'SSD MobileDet (COCO, ~70ms)' },
    { value: 'ssd_mobilenet_v2', label: 'SSD MobileNet v2 (COCO, ~65ms)' },
    { value: 'efficientdet_lite0', label: 'EfficientDet-Lite0 (COCO, genauer, ~230ms)' },
    { value: 'yolov8n', label: 'YOLOv8n (nur CPU, ~2.3s - keine TPU-Beschleunigung möglich)' },
  ],
  cpu: [
    { value: 'stub', label: 'CPU-Stub (Platzhalter)' },
  ],
}

const defaultModel = 'yolov8n'

// Same pattern as AiExecTab.jsx: this page's plain fetch() never went
// through services/api.js's 401-refresh handling, and previously didn't
// even send an Authorization header at all, so every request failed with
// "Not authenticated" regardless of token state.
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('liara_refresh_token');
  if (!refreshToken) return false;

  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    if (!res.ok) return false;

    const data = await res.json();
    localStorage.setItem('liara_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('liara_refresh_token', data.refresh_token);
    }
    return true;
  } catch {
    return false;
  }
}

async function authFetch(url, options = {}) {
  const withAuth = () => ({
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
    }
  });

  let res = await fetch(url, withAuth());
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await fetch(url, withAuth());
    }
  }
  return res;
}

function VisionDetect() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [backend, setBackend] = useState('hailo')
  const [model, setModel] = useState(defaultModel)
  const [scoreThreshold, setScoreThreshold] = useState(0.25)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const imgRef = useRef(null)
  const [renderSize, setRenderSize] = useState({ width: 1, height: 1 })

  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const scale = useMemo(() => {
    if (!result?.image_size) return { x: 1, y: 1 }
    const { width: iw, height: ih } = result.image_size
    return {
      x: renderSize.width / Math.max(iw, 1),
      y: renderSize.height / Math.max(ih, 1),
    }
  }, [renderSize, result])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setResult(null)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Bitte eine Bilddatei auswählen.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)

    const form = new FormData()
    form.append('file', file)
    form.append('backend', backend)
    form.append('model', model || defaultModel)
    form.append('score_threshold', scoreThreshold)

    try {
      const resp = await authFetch('/api/vision/detect', {
        method: 'POST',
        body: form,
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `Request failed with ${resp.status}`)
      }
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setError(err.message || 'Fehler beim Upload')
    } finally {
      setLoading(false)
    }
  }

  const handleImageLoad = () => {
    const el = imgRef.current
    if (!el) return
    setRenderSize({ width: el.clientWidth, height: el.clientHeight })
  }

  return (
    <div className="vision-page">
      <div className="vision-card">
        <div className="vision-header">
          <div>
            <h2>Vision Detection</h2>
            <p>Objekterkennung mit wählbarem Backend (Hailo / Edge TPU / CPU-Stub).</p>
          </div>
          <span className="badge">Beta</span>
        </div>

        <form className="vision-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label className="form-label">Bild hochladen</label>
            <input type="file" accept="image/*" onChange={handleFileChange} />
          </div>
          <div className="form-grid">
            <div>
              <label className="form-label">Backend</label>
              <select
                value={backend}
                onChange={(e) => {
                  const newBackend = e.target.value
                  setBackend(newBackend)
                  setModel(modelsByBackend[newBackend][0].value)
                }}
              >
                {backends.map((b) => (
                  <option key={b.value} value={b.value}>{b.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Modell</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {modelsByBackend[backend].map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Score Threshold</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={scoreThreshold}
                onChange={(e) => setScoreThreshold(parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Analysiere...' : 'Analysieren'}
            </button>
            {error && <span className="error-text">{error}</span>}
          </div>
        </form>

        <div className="vision-body">
          <div className="vision-preview">
            {preview ? (
              <div className="vision-image-wrapper">
                <img ref={imgRef} src={preview} alt="Preview" onLoad={handleImageLoad} />
                {result?.boxes?.map((box, idx) => {
                  const left = box.x * scale.x
                  const top = box.y * scale.y
                  const width = box.width * scale.x
                  const height = box.height * scale.y
                  return (
                    <div
                      key={idx}
                      className="vision-box"
                      style={{ left, top, width, height }}
                    >
                      <div className="vision-box-label">
                        {box.label} ({(box.score * 100).toFixed(1)}%)
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="vision-placeholder">Kein Bild ausgewählt</div>
            )}
          </div>

          <div className="vision-meta">
            <h4>Ergebnis</h4>
            {!result && <p className="muted">Noch keine Auswertung.</p>}
            {result && (
              <div className="result-card">
                <div className="result-row">
                  <span>Backend</span>
                  <strong>{result.backend}</strong>
                </div>
                <div className="result-row">
                  <span>Modell</span>
                  <strong>{result.model}</strong>
                </div>
                <div className="result-row">
                  <span>Latency</span>
                  <strong>{result.latency_ms?.toFixed(1)} ms</strong>
                </div>
                <div className="result-row">
                  <span>Bildgröße</span>
                  <strong>{result.image_size?.width}×{result.image_size?.height}px</strong>
                </div>
                <div className="result-row">
                  <span>Detections</span>
                  <strong>{result.boxes?.length || 0}</strong>
                </div>
                <div className="box-list">
                  {result.boxes?.map((b, i) => (
                    <div key={i} className="box-item">
                      <div>{b.label}</div>
                      <div className="muted">{(b.score * 100).toFixed(1)}% · x={b.x}, y={b.y}, w={b.width}, h={b.height}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default VisionDetect
