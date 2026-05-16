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

// ───────────────────────── Tarjeta de modelo seleccionable ─────────────────────────
// Render de un ModelCard del catálogo /models. El click levanta `onClick` para
// que el padre actualice `selectedModelId`. Mostramos hasta 3 métricas para
// que el KPI row entre con cualquier modelo (medsam tiene 4, unet binario 2).
function ModelCard({ model, selected, onClick }) {
  const kpis = (model.metrics || []).slice(0, 3);
  return (
    <button
      type="button"
      className={`model-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      <div className="model-card-header">
        <Icon name="bolt" size={18} />
        <h3 className="model-card-title">{model.display_name}</h3>
        {selected && <Icon name="check" size={16} className="model-card-check" />}
      </div>
      {kpis.length > 0 && (
        <div className="kpi-row model-card-kpis">
          {kpis.map((m) => (
            <div key={m.name}>
              <span>{m.name.replace(/_/g, ' ')}</span>
              <b>{m.value.toFixed(3)}</b>
            </div>
          ))}
        </div>
      )}
    </button>
  );
}

// ───────────────────────── Drag & Drop ─────────────────────────
function UploadZone({ onUpload, models, selectedModelId, onSelectModel }) {
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
        <div className="model-cards">
          <div className="model-cards-header">
            <Icon name="bolt" size={18} />
            <span>Selecciona un modelo</span>
          </div>
          {(!models || models.length === 0) ? (
            <div className="info-card subtle"><p>Cargando modelos…</p></div>
          ) : (
            models.map((m) => (
              <ModelCard
                key={m.id}
                model={m}
                selected={m.id === selectedModelId}
                onClick={() => onSelectModel(m.id)}
              />
            ))
          )}
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
// La lista de pasos viene del catálogo /models (campo `processing_steps` del
// ModelCard). No es streaming: la animación es una estimación de UX mientras
// se espera la respuesta. Si el backend no provee pasos, fallback genérico.
function ProcessingScreen({ filename, fileUrl, steps }) {
  const stepList = (steps && steps.length > 0) ? steps : ['Procesando…'];
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
        setStep(Math.min(stepList.length - 1, Math.floor((next / 100) * stepList.length)));
        return next;
      });
    }, 200);
    return () => clearInterval(interval);
  }, [stepList.length]);

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
            <span className="mono">{stepList[step]}…</span>
          </div>

          <ul className="step-list">
            {stepList.map((s, i) => (
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
function ResultView({ result, fileUrl, filename, onNew, onCompare }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [hoveredId, setHoveredId] = useState(null);
  // Multi-select de vértebras: Set para que React detecte cambios al hacer
  // copy-on-write (mutar el mismo Set no dispara re-render).
  const [selectedIds, setSelectedIds] = useState(() => new Set());
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

  // Conjunto de vértebras a dibujar sobre la máscara: las seleccionadas con
  // click + la del hover (si no estaba ya). Solo se incluyen las detectadas
  // con bounding_box. El hover se marca aparte para darle styling más fuerte.
  const activeBoxes = (() => {
    const byId = new Map(vertebrae.map(v => [v.id, v]));
    const ids = new Set(selectedIds);
    if (hoveredId) ids.add(hoveredId);
    return Array.from(ids)
      .map(id => byId.get(id))
      .filter(v => v && v.detected && v.bounding_box)
      .map(v => ({ vert: v, isHovered: v.id === hoveredId }));
  })();

  const toggleSelected = (id) => setSelectedIds(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const clearSelection = () => setSelectedIds(new Set());
  const selectableCount = vertebrae.filter(v => v.detected && v.bounding_box).length;

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
          <button className="btn-tonal" onClick={onCompare} title="Comparar con otro modelo">
            <Icon name="layers" size={18} /> Comparar
          </button>
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

            {/* Bounding-box overlays. Multi-select: dibujamos UN bbox por
                cada vértebra seleccionada con su color de región. El hover
                añade un overlay con styling reforzado (clase .hovered).
                Las coords vienen en píxeles del espacio original tras
                reverse-letterbox; el comparator preserva aspect ratio, así
                que porcentajes bastan. */}
            {activeBoxes.length > 0 && (
              <div className="bbox-layer">
                {activeBoxes.map(({ vert, isHovered }) => {
                  const bb = vert.bounding_box;
                  const W = mask.dimensions.width;
                  const H = mask.dimensions.height;
                  const leftPct = (bb.x_min / W) * 100;
                  const topPct = (bb.y_min / H) * 100;
                  const widthPct = ((bb.x_max - bb.x_min) / W) * 100;
                  const heightPct = ((bb.y_max - bb.y_min) / H) * 100;
                  // Si el bbox queda cerca del borde derecho de la imagen,
                  // la etiqueta (que va a la derecha por defecto) se saldría
                  // del frame. Flippeamos a la izquierda en ese caso.
                  const rightPct = leftPct + widthPct;
                  const labelOnLeft = rightPct > 88;
                  return (
                    <div
                      key={vert.id}
                      className={[
                        'bbox-overlay',
                        labelOnLeft ? 'tag-left' : '',
                        isHovered ? 'hovered' : '',
                      ].filter(Boolean).join(' ')}
                      style={{
                        left: `${leftPct}%`,
                        top: `${topPct}%`,
                        width: `${widthPct}%`,
                        height: `${heightPct}%`,
                        '--bbox-color': regionColors[vert.region],
                      }}
                    >
                      <span className="bbox-label">
                        {vert.label}
                        <span className="bbox-conf">
                          {(vert.confidence * 100).toFixed(0)}%
                        </span>
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
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
            <header className="vert-panel-header">
              <h3>Vértebras</h3>
              <div className="vert-selection-meta">
                <span className="vert-selection-count">
                  {selectedIds.size}/{selectableCount} seleccionadas
                </span>
                <button
                  type="button"
                  className="vert-clear-btn"
                  onClick={clearSelection}
                  disabled={selectedIds.size === 0}
                  title="Quitar todas las vértebras seleccionadas"
                >
                  Limpiar
                </button>
              </div>
            </header>
            <div className="vert-grid">
              {vertebrae.map((v) => {
                const isHovered = hoveredId === v.id;
                const isSelected = selectedIds.has(v.id);
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
                      ? `${v.label} · ${(v.confidence * 100).toFixed(1)}% · ${v.pixel_count} px${v.bounding_box ? (isSelected ? ' · click para quitar' : ' · click para añadir') : ''}`
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

// ───────────────────────── Comparación: panel reutilizable ─────────────────────────
// Render compacto de un análisis: título (display_name del modelo), métricas
// resumidas y la radiografía con su máscara superpuesta (overlay fijo).
function ComparePane({ title, metrics, fileUrl, maskBase64 }) {
  const maskUrl = `data:image/png;base64,${maskBase64}`;
  return (
    <div className="compare-pane">
      <div className="compare-pane-title">
        <h3>{title}</h3>
        <span className="mono">
          Dice {metrics.dice.toFixed(3)} · IoU {metrics.iou.toFixed(3)} · {metrics.latency_ms.toFixed(0)} ms
        </span>
      </div>
      {/* El canvas toma el alto disponible vía flex; las imágenes usan
          object-fit: contain para que la radiografía completa se vea
          dentro del viewport sin scroll, preservando aspect ratio. */}
      <div className="compare-canvas">
        <img className="compare-xray" src={fileUrl} alt="Radiografía original" />
        <img className="compare-mask" src={maskUrl} alt="Máscara del modelo" />
      </div>
    </div>
  );
}

// ───────────────────────── Modal selector de modelo (comparación) ─────────────────────────
// Lista las opciones disponibles (ya filtradas) reusando ModelCard. ESC cierra.
function ModelPickerModal({ models, onPick, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <header className="modal-header">
          <h2>Comparar contra…</h2>
          <button className="icon-btn" onClick={onClose} title="Cerrar (Esc)">
            <Icon name="close" size={20} />
          </button>
        </header>
        {models.length === 0 ? (
          <p className="modal-empty">No hay otros modelos disponibles para comparar.</p>
        ) : (
          <div className="modal-model-list">
            {models.map((m) => (
              <ModelCard key={m.id} model={m} selected={false} onClick={() => onPick(m.id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ───────────────────────── Pantalla 3: comparación de modelos ─────────────────────────
function CompareView({
  result,
  fileUrl,
  filename,
  models,
  selectedModelId,
  compareModelId,
  compareResult,
  compareLoading,
  compareError,
  onPickCompare,
  onBack,
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const availableModels = models.filter((m) => m.id !== selectedModelId);
  const primaryModel = models.find((m) => m.id === selectedModelId);
  const compareModel = compareModelId ? models.find((m) => m.id === compareModelId) : null;

  return (
    <div className="compare-shell">
      <div className="compare-toolbar">
        <button className="btn-tonal" onClick={onBack}>
          <Icon name="refresh" size={16} /> Volver al resultado
        </button>
        <div className="compare-file">
          <Icon name="image" size={16} />
          <span className="mono">{filename}</span>
        </div>
      </div>

      <div className="compare-body">
        <ComparePane
          title={primaryModel?.display_name || 'Modelo A'}
          metrics={result.metrics.model_metrics}
          fileUrl={fileUrl}
          maskBase64={result.mask.data}
        />

        {!compareModelId ? (
          <button
            type="button"
            className="compare-empty"
            onClick={() => setPickerOpen(true)}
            disabled={availableModels.length === 0}
            title={availableModels.length === 0
              ? 'No hay otros modelos publicados'
              : 'Elegir modelo para comparar'}
          >
            <span className="compare-empty-plus">+</span>
            <span className="compare-empty-label">Comparar con otro modelo</span>
          </button>
        ) : compareLoading ? (
          <div className="compare-pane compare-status">
            <div className="spinner" />
            <p>Ejecutando {compareModel?.display_name || 'modelo'}…</p>
          </div>
        ) : compareError ? (
          <div className="compare-pane compare-status compare-status-error">
            <Icon name="error" size={32} />
            <p>{compareError}</p>
            <button className="btn-tonal" onClick={() => setPickerOpen(true)}>
              Reintentar con otro modelo
            </button>
          </div>
        ) : compareResult ? (
          <ComparePane
            title={compareModel?.display_name || 'Modelo B'}
            metrics={compareResult.metrics.model_metrics}
            fileUrl={fileUrl}
            maskBase64={compareResult.mask.data}
          />
        ) : null}
      </div>

      {pickerOpen && (
        <ModelPickerModal
          models={availableModels}
          onPick={(id) => { setPickerOpen(false); onPickCompare(id); }}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}

// ───────────────────────── App raíz ─────────────────────────
const TWEAK_DEFAULS = /*EDITMODE-BEGIN*/{
  "theme": "dark"
}/*EDITMODE-END*/;

function App() {
  const [phase, setPhase] = useState('upload');     // upload | processing | result | error | compare
  const [filename, setFilename] = useState('');
  const [fileUrl, setFileUrl] = useState(null);     // URL local de la imagen subida
  // Guardamos también el File blob original para poder re-submitirlo a /xrays
  // cuando el usuario quiera correr la comparación con otro modelo.
  const [originalFile, setOriginalFile] = useState(null);
  const [result, setResult] = useState(null);       // Respuesta del backend
  const [error, setError] = useState(null);
  const [modelVersion, setModelVersion] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('medsam');
  // Estado de comparación contra un segundo modelo (pantalla 3).
  const [compareModelId, setCompareModelId] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState(null);
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

  // Catálogo de modelos para las tarjetas seleccionables de la pantalla de upload.
  // Si el backend no expone 'medsam' caemos al primer modelo del catálogo.
  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data?.items) return;
        setModels(data.items);
        const hasMedsam = data.items.some((m) => m.id === 'medsam');
        if (!hasMedsam && data.items.length > 0) {
          setSelectedModelId(data.items[0].id);
        }
      })
      .catch(() => {/* silencioso: UploadZone mostrará "Cargando modelos…" */});
  }, []);

  const start = async (file) => {
    setFilename(file.name);
    setOriginalFile(file);
    const localUrl = URL.createObjectURL(file);
    setFileUrl(localUrl);
    setPhase('processing');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', selectedModelId);

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
    setOriginalFile(null);
    setResult(null);
    setError(null);
    setCompareModelId(null);
    setCompareResult(null);
    setCompareError(null);
    setCompareLoading(false);
  };

  // Comparación con un segundo modelo: re-submit del MISMO file al endpoint
  // /xrays con otro `model`. Vive como estado independiente para no pisar el
  // resultado del primer análisis (que sigue visible en la pantalla 3).
  const runComparison = async (modelId) => {
    if (!originalFile) return;
    setCompareModelId(modelId);
    setCompareLoading(true);
    setCompareError(null);
    setCompareResult(null);
    try {
      const formData = new FormData();
      formData.append('file', originalFile);
      formData.append('model', modelId);
      const response = await fetch(`${API_BASE}/xrays`, { method: 'POST', body: formData });
      if (!response.ok) {
        let message = `HTTP ${response.status}`;
        try {
          const errBody = await response.json();
          message = errBody.detail || errBody.error || message;
        } catch {/* sin cuerpo JSON */}
        throw new Error(message);
      }
      setCompareResult(await response.json());
    } catch (err) {
      console.error('Error en comparación:', err);
      setCompareError(err.message || 'No se pudo ejecutar la comparación');
    } finally {
      setCompareLoading(false);
    }
  };

  const enterCompare = () => {
    setCompareResult(null);
    setCompareModelId(null);
    setCompareError(null);
    setCompareLoading(false);
    setPhase('compare');
  };
  const exitCompare = () => setPhase('result');

  return (
    <div className="app">
      <AppBar
        onReset={reset}
        onToggleTheme={() => setTweak('theme', tweaks.theme === 'dark' ? 'light' : 'dark')}
        theme={tweaks.theme}
        modelVersion={modelVersion}
      />

      <main className="main">
        {phase === 'upload' && (
          <UploadZone
            onUpload={start}
            models={models}
            selectedModelId={selectedModelId}
            onSelectModel={setSelectedModelId}
          />
        )}
        {phase === 'processing' && (
          <ProcessingScreen
            filename={filename}
            fileUrl={fileUrl}
            steps={models.find((m) => m.id === selectedModelId)?.processing_steps || []}
          />
        )}
        {phase === 'error' && <ErrorScreen error={error} onRetry={reset} />}
        {phase === 'result' && result && (
          <ResultView
            result={result}
            fileUrl={fileUrl}
            filename={filename}
            onNew={reset}
            onCompare={enterCompare}
          />
        )}
        {phase === 'compare' && result && (
          <CompareView
            result={result}
            fileUrl={fileUrl}
            filename={filename}
            models={models}
            selectedModelId={selectedModelId}
            compareModelId={compareModelId}
            compareResult={compareResult}
            compareLoading={compareLoading}
            compareError={compareError}
            onPickCompare={runComparison}
            onBack={exitCompare}
          />
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
