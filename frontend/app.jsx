// VertebraAI – Pantalla principal
// Conectada al backend FastAPI: POST /api/vertebraai/xrays
// Pipeline ganador notebook 06: VertebraPrompt-Net + BoxRefiner + MedSAM

const { useState, useEffect, useRef, useCallback } = React;

// ───────────────────────── Configuración del backend ─────────────────────────
// `??` no `||`: cuando estamos detrás de CloudFront, config.js setea
// BACKEND_URL = "" para usar rutas relativas same-origin. Con `||` el string
// vacío sería falsy y caeríamos al fallback localhost.
const BACKEND_URL = window.BACKEND_URL ?? 'http://localhost:8000';
const API_BASE = `${BACKEND_URL}/api/vertebraai`;

// ───────────────────────── Iconos (Material-style outline) ─────────────────────────
const Icon = ({ name, size = 24, ...props }) => {
  const paths = {
    upload: 'M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z',
    image: 'M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5z',
    download: 'M19 9h-4V3H9v6H5l7 7zM5 18v2h14v-2z',
    close: 'M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
    play: 'M8 5v14l11-7z',
    refresh: 'M17.65 6.35A7.958 7.958 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08a6 6 0 1 1-5.65-8c1.66 0 3.14.69 4.22 1.78L13 11h7V4z',
    zoom_in: 'M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19zM5 9.5A4.5 4.5 0 1 1 9.5 14 4.5 4.5 0 0 1 5 9.5M12 10h-2v2H9v-2H7V9h2V7h1v2h2z',
    zoom_out: 'M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19zM5 9.5A4.5 4.5 0 1 1 9.5 14 4.5 4.5 0 0 1 5 9.5M7 9h5v1H7z',
    fit: 'M3 5v4h2V5h4V3H5c-1.1 0-2 .9-2 2m2 10H3v4c0 1.1.9 2 2 2h4v-2H5zm14 4h-4v2h4c1.1 0 2-.9 2-2v-4h-2zm0-16h-4v2h4v4h2V5c0-1.1-.9-2-2-2',
    sun: 'M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5M2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1m18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1M11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1m0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1M5.99 4.58a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41zm12.37 12.37a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0a.996.996 0 0 0 0-1.41zm1.06-10.96a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0zM7.05 18.36a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0z',
    moon: 'M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.389 5.389 0 0 1-4.4 2.26 5.403 5.403 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1',
    bolt: 'M7 21h2l4-9V3h-1L7 12zm10-9-4 9h-1l3-7-3-3z',
    check: 'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
    info: 'M11 7h2v2h-2zm0 4h2v6h-2zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8',
    spine: 'M12 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4M9 7v2h6V7zm-1 4v2h8v-2zm-1 4v2h10v-2zm-1 4v2h12v-2z',
    layers: 'm12 16 7-4-2-1-5 3-5-3-2 1zm0-4 7-4-7-4-7 4zm0 8 7-4-2-1-5 3-5-3-2 1z',
    tune: 'M3 17v2h6v-2zM3 5v2h10V5zm10 16v-2h8v-2h-8v-2h-2v6zM7 9v2H3v2h4v2h2V9zm14 4v-2H11v2zm-6-4h2V7h4V5h-4V3h-2z',
    error: 'M11 15h2v2h-2zm0-8h2v6h-2zm.99-5C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2M12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8',
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d={paths[name] || ''} />
    </svg>
  );
};

// ───────────────────────── App Bar ─────────────────────────
function AppBar({ onReset, onToggleTheme, theme, modelVersion }) {
  return (
    <header className="appbar">
      <div className="appbar-left">
        <div className="logo-mark" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24">
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#80D8FF" />
                <stop offset="100%" stopColor="#4FC3F7" />
              </linearGradient>
            </defs>
            <circle cx="12" cy="12" r="11" fill="none" stroke="url(#logoGrad)" strokeWidth="1.5" opacity="0.4" />
            <path d="M12 3 a2 2 0 1 1 0 .01 M9 8 h6 M8 12 h8 M9 16 h6 M10 20 h4" stroke="url(#logoGrad)" strokeWidth="2" strokeLinecap="round" fill="none" />
          </svg>
        </div>
        <div className="appbar-titles">
          <h1>VertebraAI</h1>
          <span className="appbar-subtitle">{modelVersion || 'Segmentación de columna'}</span>
        </div>
      </div>

      <div className="appbar-right">
        <span className="status-pill">
          <span className="status-dot" /> {modelVersion ? 'Modelo conectado' : 'Conectando…'}
        </span>
        <button className="icon-btn" onClick={onToggleTheme} title="Cambiar tema">
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} />
        </button>
        <button className="icon-btn" onClick={onReset} title="Nueva sesión">
          <Icon name="refresh" size={20} />
        </button>
      </div>
    </header>
  );
}

// ───────────────────────── Drag & Drop ─────────────────────────
function UploadZone({ onUpload }) {
  const [drag, setDrag] = useState(false);
  const fileInput = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    onUpload(file);
  };

  return (
    <div className="upload-shell">
      <div
        className={`upload-zone ${drag ? 'drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => fileInput.current?.click()}
      >
        <input
          ref={fileInput}
          type="file"
          accept="image/png,image/jpeg"
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />

        <div className="upload-glow" aria-hidden="true">
          <div className="ring r1" />
          <div className="ring r2" />
          <div className="ring r3" />
          <div className="upload-icon">
            <Icon name="upload" size={44} />
          </div>
        </div>

        <h2>Arrastra una radiografía de columna</h2>
        <p>o haz clic para seleccionar un archivo</p>

        <button className="btn-tonal" onClick={(e) => { e.stopPropagation(); fileInput.current?.click(); }}>
          <Icon name="image" size={18} /> Seleccionar archivo
        </button>

        <ul className="upload-meta">
          <li>Formato: <b>PNG / JPEG</b></li>
          <li>Resolución mínima: <b>32 × 32 px</b></li>
          <li>Vista: <b>AP</b></li>
        </ul>
      </div>

      <div className="upload-side">
        <div className="info-card">
          <div className="info-card-header">
            <Icon name="bolt" size={18} />
            <span>Sobre el modelo</span>
          </div>
          <p>
            Pipeline 3-stage: <b>VertebraPrompt-Net + BoxRefiner + MedSAM ViT-B</b>.
            Detecta y segmenta hasta 22 vértebras (C3–L5) en radiografías AP.
          </p>
          <div className="kpi-row">
            <div><span>Dice estricto</span><b>0.553</b></div>
            <div><span>Dice flexible</span><b>0.768</b></div>
            <div><span>IoU estricto</span><b>0.479</b></div>
          </div>
        </div>

        <div className="info-card subtle">
          <div className="info-card-header">
            <Icon name="info" size={18} />
            <span>Uso clínico</span>
          </div>
          <p>
            Esta herramienta es un <b>apoyo diagnóstico</b>. Toda decisión
            clínica debe ser revisada por un radiólogo o especialista
            cualificado.
          </p>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────── Pantalla de procesamiento ─────────────────────────
// Estos pasos deben coincidir exactamente con los que el backend agrega a
// `processing.steps` en services/app/core/use_cases/analyze_image.py.
// Si cambian allá, cambiarlos también acá (no hay streaming: la animación es
// una estimación de UX mientras se espera la respuesta).
const PROCESS_STEPS = [
  'Decodificación de imagen',
  'Letterbox 1024×1024 + normalización por percentiles',
  'VertebraPrompt-Net (512×512): heatmap + wh + offset',
  'DP anatómico → cajas T1–L5 con plantilla mediana',
  'BoxRefiner: corrección local de cajas (192×192)',
  'MedSAM box_only por caja → máscaras binarias',
  'Composición y reverse-letterbox al espacio original',
  'Cálculo métricas por vértebra',
  'Generación máscara coloreada',
];

function ProcessingScreen({ filename, fileUrl }) {
  // Avance suave de UI mientras se espera la respuesta del backend
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  // Dimensiones naturales de la imagen para alinear el frame con el resultado.
  const [imgDims, setImgDims] = useState(null);

  useEffect(() => {
    // El backend puede tardar varios segundos. Mostramos avance estimado.
    const interval = setInterval(() => {
      setProgress((p) => {
        // Curva asintótica: avanza rápido al inicio y desacelera cerca del 90%
        const next = p + (90 - p) * 0.05;
        setStep(Math.min(PROCESS_STEPS.length - 1, Math.floor((next / 100) * PROCESS_STEPS.length)));
        return next;
      });
    }, 200);
    return () => clearInterval(interval);
  }, []);

  // Aspect ratio dinámico = dims reales de la imagen subida; así el frame de
  // procesamiento ocupa exactamente el mismo lugar que el .comparator del
  // resultado y no hay "salto" visual al transicionar.
  const aspectRatio = imgDims ? `${imgDims.w} / ${imgDims.h}` : undefined;

  return (
    <div className="processing">
      <div className="processing-stage">
        <div className="processing-stage-frame">
          <div className="scan-frame" style={aspectRatio ? { aspectRatio } : undefined}>
            <div className="scan-svg">
              {fileUrl
                ? <img
                    src={fileUrl}
                    alt="Radiografía"
                    onLoad={(e) => setImgDims({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                : null
              }
            </div>
            <div className="scan-line" />
            <div className="scan-grid" />
            <div className="scan-corners">
              <span /><span /><span /><span />
            </div>
          </div>
        </div>

        <div className="processing-info">
          <span className="proc-tag">
            <span className="pulse-dot" /> ANÁLISIS EN CURSO
          </span>
          <h2>Procesando radiografía</h2>
          <p className="filename">
            <Icon name="image" size={14} /> {filename}
          </p>

          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
            <div className="progress-shine" style={{ left: `${progress}%` }} />
          </div>
          <div className="progress-meta">
            <span>{Math.round(progress)}%</span>
            <span className="mono">{PROCESS_STEPS[step]}…</span>
          </div>

          <ul className="step-list">
            {PROCESS_STEPS.map((s, i) => (
              <li key={s} className={i < step ? 'done' : i === step ? 'active' : ''}>
                <span className="step-bullet">
                  {i < step ? <Icon name="check" size={12} /> : i === step ? <span className="spinner" /> : <span className="dot" />}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────── Pantalla de error ─────────────────────────
function ErrorScreen({ error, onRetry }) {
  return (
    <div className="processing">
      <div className="processing-stage" style={{ flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 24 }}>
        <div style={{ color: '#ff5252' }}>
          <Icon name="error" size={64} />
        </div>
        <h2 style={{ margin: 0 }}>Error en el análisis</h2>
        <p className="filename" style={{ maxWidth: 480 }}>{error}</p>
        <button className="btn-tonal" onClick={onRetry}>
          <Icon name="refresh" size={18} /> Intentar de nuevo
        </button>
      </div>
    </div>
  );
}

// ───────────────────────── Vista de resultados ─────────────────────────
function ResultView({ result, fileUrl, filename, onNew }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [hoveredId, setHoveredId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  const handleWheel = (e) => {
    e.preventDefault();
    const dz = e.deltaY < 0 ? 0.12 : -0.12;
    setZoom((z) => Math.max(0.5, Math.min(4, z + dz)));
  };

  const onMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('.slider-handle')) return;
    setIsPanning(true);
    panStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  };
  const onMouseMove = (e) => {
    if (!isPanning) return;
    setPan({
      x: panStart.current.panX + (e.clientX - panStart.current.x),
      y: panStart.current.panY + (e.clientY - panStart.current.y),
    });
  };
  const onMouseUp = () => setIsPanning(false);
  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  // Slider handle drag
  const sliderRef = useRef(null);
  const draggingSlider = useRef(false);
  const onSliderDown = (e) => {
    e.stopPropagation();
    draggingSlider.current = true;
  };
  useEffect(() => {
    const move = (e) => {
      if (!draggingSlider.current || !sliderRef.current) return;
      const rect = sliderRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSliderPos(Math.max(0, Math.min(100, pct)));
    };
    const up = () => { draggingSlider.current = false; };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
  }, []);

  // Datos REALES del backend
  const { metrics, vertebrae, mask, processing, study_id, timestamp } = result;
  const maskUrl = `data:image/png;base64,${mask.data}`;

  // Mapeo región → color (alineado con backend _REGION_COLORS)
  const regionColors = {
    cervical: '#4285F4',
    thoracic: '#34A853',
    lumbar:   '#EA4335',
  };

  // Etiquetas de regiones para mostrar (sin C1/C2 — backend solo C3-C7)
  const regionInfo = [
    { key: 'cervical', label: 'Cervical', range: 'C3 – C7' },
    { key: 'thoracic', label: 'Torácica', range: 'T1 – T12' },
    { key: 'lumbar',   label: 'Lumbar',   range: 'L1 – L5' },
  ];

  // Vértebra activa para mostrar bounding box: hover gana sobre selección
  // (al pasar el mouse sobre otra chip preview esa, al salir vuelve a la
  // seleccionada con click). Solo se muestra si la vértebra fue detectada
  // y el backend devolvió bounding box.
  const activeId = hoveredId ?? selectedId;
  const activeVert = activeId
    ? vertebrae.find(v => v.id === activeId && v.detected && v.bounding_box)
    : null;
  const toggleSelected = (id) => setSelectedId(prev => (prev === id ? null : id));

  // Descarga de exports vía endpoint del backend
  const downloadExport = (format) => {
    const url = `${API_BASE}/xrays/${study_id}/exports/${format}`;
    window.open(url, '_blank');
  };

  // Formatear timestamp
  const formattedTime = (() => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  })();

  return (
    <div className="result-shell">
      {/* Toolbar */}
      <div className="result-toolbar">
        <div className="result-file">
          <Icon name="image" size={16} />
          <span className="mono">{filename}</span>
          <span className="chip success">
            <Icon name="check" size={12} /> Análisis completado
          </span>
        </div>

        <div className="result-tools">
          <div className="zoom-cluster">
            <button className="icon-btn" onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}>
              <Icon name="zoom_out" size={18} />
            </button>
            <span className="zoom-readout mono">{Math.round(zoom * 100)}%</span>
            <button className="icon-btn" onClick={() => setZoom((z) => Math.min(4, z + 0.2))}>
              <Icon name="zoom_in" size={18} />
            </button>
            <button className="icon-btn" onClick={resetView} title="Ajustar">
              <Icon name="fit" size={18} />
            </button>
          </div>
          <button className="btn-filled" onClick={() => downloadExport('overlay')} title="Descargar overlay">
            <Icon name="download" size={18} /> Exportar
          </button>
        </div>
      </div>

      <div className="result-body">
        {/* Stage central */}
        <div
          className="stage"
          onWheel={handleWheel}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
        >
          {/* Comparador slider con imagen REAL + máscara REAL.
              Aspect-ratio dinámico basado en las dimensiones de la máscara
              que devolvió el backend (mantiene proporciones de la radiografía). */}
          <div
            className="comparator"
            ref={sliderRef}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              aspectRatio: `${mask.dimensions.width} / ${mask.dimensions.height}`,
            }}
          >
            <div className="layer xray-layer">
              <img
                src={fileUrl}
                alt="Radiografía original"
                style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
              />
            </div>

            <div
              className="layer mask-layer"
              style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
            >
              <div className="mask-inner" style={{ position: 'relative', width: '100%', height: '100%' }}>
                <img
                  src={fileUrl}
                  alt=""
                  style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                />
                <img
                  src={maskUrl}
                  alt="Máscara segmentada"
                  style={{
                    position: 'absolute',
                    top: 0, left: 0, width: '100%', height: '100%',
                    objectFit: 'contain',
                    mixBlendMode: 'screen',
                    opacity: 0.75,
                    display: 'block',
                  }}
                />
              </div>
            </div>

            <div
              className="slider-handle"
              style={{ left: `${sliderPos}%` }}
              onMouseDown={onSliderDown}
            >
              <div className="slider-bar" />
              <div className="slider-knob">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5 4 12l4 7zm8 0v14l4-7z" />
                </svg>
              </div>
              <div className="slider-tag top">ORIGINAL</div>
              <div className="slider-tag bottom">SEGMENTADO</div>
            </div>

            {/* Bounding-box overlay de la vértebra activa (hover/click en chip).
                Las coords vienen en píxeles del espacio original (lo que
                devuelve el backend tras reverse-letterbox); el comparator
                tiene el aspect ratio idéntico, así que basta con
                porcentajes. */}
            {activeVert && (() => {
              const bb = activeVert.bounding_box;
              const W = mask.dimensions.width;
              const H = mask.dimensions.height;
              const leftPct = (bb.x_min / W) * 100;
              const topPct = (bb.y_min / H) * 100;
              const widthPct = ((bb.x_max - bb.x_min) / W) * 100;
              const heightPct = ((bb.y_max - bb.y_min) / H) * 100;
              // Si la caja está muy pegada al borde superior, mostrar el
              // tag dentro de la caja (top-left) en vez de arriba.
              const labelInside = topPct < 5;
              return (
                <div className="bbox-layer">
                  <div
                    className={`bbox-overlay ${labelInside ? 'tag-inside' : ''}`}
                    style={{
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: `${widthPct}%`,
                      height: `${heightPct}%`,
                      '--bbox-color': regionColors[activeVert.region],
                    }}
                  >
                    <span className="bbox-label">
                      {activeVert.label}
                      <span className="bbox-conf">
                        {(activeVert.confidence * 100).toFixed(0)}%
                      </span>
                    </span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* HUD esquinas — solo datos REALES del backend */}
          <div className="hud hud-tl mono">
            <div>STUDY · {formattedTime}</div>
            <div>ID · {study_id.slice(0, 8)}</div>
          </div>
          <div className="hud hud-tr mono">
            <div>{metrics.model_metrics.model_version}</div>
            <div>Conf {(metrics.confidence * 100).toFixed(1)}%</div>
          </div>
          <div className="hud hud-bl mono">
            <div>Dice {metrics.model_metrics.dice.toFixed(3)} · IoU {metrics.model_metrics.iou.toFixed(3)}</div>
            <div>{mask.dimensions.width} × {mask.dimensions.height} px</div>
          </div>
          <div className="hud hud-br mono">
            <div>{Math.round(zoom * 100)}% · ({pan.x}, {pan.y})</div>
            <div>{metrics.model_metrics.latency_ms.toFixed(0)} ms inferencia</div>
          </div>
        </div>

        {/* Panel lateral derecho */}
        <aside className="side-panel">
          <section className="panel-card">
            <header>
              <h3>Resultados</h3>
              <span className="chip mono">{(processing.total_time_ms / 1000).toFixed(2)}s</span>
            </header>
            <div className="big-stat">
              <div className="big-stat-value">
                {metrics.detected_count}
                <span>/{vertebrae.length}</span>
              </div>
              <div className="big-stat-label">Vértebras detectadas</div>
            </div>
            <div className="confidence">
              <div className="conf-row">
                <span>Confianza global</span>
                <b className="mono">{(metrics.confidence * 100).toFixed(1)}%</b>
              </div>
              <div className="conf-bar">
                <div className="conf-fill" style={{ width: `${metrics.confidence * 100}%` }} />
              </div>
            </div>
          </section>

          <section className="panel-card">
            <header><h3>Por región</h3></header>
            <ul className="region-list">
              {regionInfo.map((r) => {
                const data = metrics.by_region[r.key];
                if (!data) return null;
                return (
                  <li key={r.key}>
                    <span className="region-dot" style={{ background: regionColors[r.key] }} />
                    <div className="region-text">
                      <b>{r.label}</b>
                      <span className="mono">{r.range}</span>
                    </div>
                    <div className="region-stats">
                      <span className="mono">
                        <b>{data.detected_count}</b>/{data.expected_count}
                      </span>
                      <span className="mono dim">{(data.mean_confidence * 100).toFixed(1)}%</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="panel-card">
            <header><h3>Vértebras</h3></header>
            <div className="vert-grid">
              {vertebrae.map((v) => {
                const isHovered = hoveredId === v.id;
                const isSelected = selectedId === v.id;
                return (
                  <button
                    key={v.id}
                    className={[
                      'vert-chip',
                      v.region,
                      (isHovered || isSelected) ? 'on' : '',
                      isSelected ? 'selected' : '',
                      !v.detected ? 'missing' : '',
                    ].filter(Boolean).join(' ')}
                    onMouseEnter={() => setHoveredId(v.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => v.detected && v.bounding_box && toggleSelected(v.id)}
                    disabled={!v.detected || !v.bounding_box}
                    title={v.detected
                      ? `${v.label} · ${(v.confidence * 100).toFixed(1)}% · ${v.pixel_count} px${v.bounding_box ? ' · click para fijar' : ''}`
                      : `${v.label} · no detectada`
                    }
                  >{v.label}</button>
                );
              })}
            </div>
          </section>

          <section className="panel-card">
            <header><h3>Exportar</h3></header>
            <div className="export-buttons">
              <button className="btn-outline" onClick={() => downloadExport('png')}>
                <Icon name="download" size={16} /> Original
              </button>
              <button className="btn-outline" onClick={() => downloadExport('mask')}>
                <Icon name="download" size={16} /> Máscara
              </button>
              <button className="btn-outline" onClick={() => downloadExport('overlay')}>
                <Icon name="download" size={16} /> Overlay
              </button>
              <button className="btn-outline" onClick={() => downloadExport('report')}>
                <Icon name="download" size={16} /> Reporte
              </button>
            </div>
          </section>

          <button className="btn-tonal full" onClick={onNew}>
            <Icon name="refresh" size={18} /> Analizar otra radiografía
          </button>
        </aside>
      </div>
    </div>
  );
}

// ───────────────────────── App raíz ─────────────────────────
const TWEAK_DEFAULS = /*EDITMODE-BEGIN*/{
  "theme": "dark"
}/*EDITMODE-END*/;

function App() {
  const [phase, setPhase] = useState('upload');     // upload | processing | result | error
  const [filename, setFilename] = useState('');
  const [fileUrl, setFileUrl] = useState(null);     // URL local de la imagen subida
  const [result, setResult] = useState(null);       // Respuesta del backend
  const [error, setError] = useState(null);
  const [modelVersion, setModelVersion] = useState(null);
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULS);

  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
  }, [tweaks.theme]);

  // Health check inicial para mostrar versión del modelo
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setModelVersion(data.model_version); })
      .catch(() => {/* silencioso: el AppBar mostrará "Conectando…" */});
  }, []);

  const start = async (file) => {
    setFilename(file.name);
    const localUrl = URL.createObjectURL(file);
    setFileUrl(localUrl);
    setPhase('processing');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', 'medsam');

      const response = await fetch(`${API_BASE}/xrays`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let message = `HTTP ${response.status}`;
        try {
          const errBody = await response.json();
          message = errBody.detail || errBody.error || message;
        } catch {/* sin cuerpo JSON */}
        throw new Error(message);
      }

      const data = await response.json();
      setResult(data);
      setPhase('result');
    } catch (err) {
      console.error('Error en análisis:', err);
      setError(err.message || 'No se pudo conectar con el servicio');
      setPhase('error');
    }
  };

  const reset = () => {
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    setPhase('upload');
    setFilename('');
    setFileUrl(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="app">
      <AppBar
        onReset={reset}
        onToggleTheme={() => setTweak('theme', tweaks.theme === 'dark' ? 'light' : 'dark')}
        theme={tweaks.theme}
        modelVersion={modelVersion}
      />

      <main className="main">
        {phase === 'upload' && <UploadZone onUpload={start} />}
        {phase === 'processing' && <ProcessingScreen filename={filename} fileUrl={fileUrl} />}
        {phase === 'error' && <ErrorScreen error={error} onRetry={reset} />}
        {phase === 'result' && result && (
          <ResultView result={result} fileUrl={fileUrl} filename={filename} onNew={reset} />
        )}
      </main>

      <footer className="app-footer mono">
        <span>VertebraAI · Apoyo diagnóstico — no sustituye criterio clínico</span>
        <span>Pipeline: VertebraPrompt + BoxRefiner + MedSAM</span>
      </footer>

      <TweaksPanel title="Tweaks">
        <TweakSection title="Apariencia">
          <TweakRadio
            label="Tema"
            value={tweaks.theme}
            onChange={(v) => setTweak('theme', v)}
            options={[
              { value: 'dark', label: 'Oscuro' },
              { value: 'light', label: 'Claro' },
            ]}
          />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
