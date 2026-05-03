// VertebraAI – Pantalla principal
// Material Design 3 dark mode, paleta tech-medical (azules eléctricos rayos X)

const { useState, useEffect, useRef, useCallback } = React;

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
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d={paths[name] || ''} />
    </svg>
  );
};

// ───────────────────────── App Bar ─────────────────────────
function AppBar({ onReset, onToggleTheme, theme }) {
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
          <span className="appbar-subtitle">Segmentación de columna · v2.4</span>
        </div>
      </div>

      <nav className="appbar-nav">
        <a className="active" href="#">Análisis</a>
        <a href="#">Historial</a>
        <a href="#">Modelo</a>
        <a href="#">Ayuda</a>
      </nav>

      <div className="appbar-right">
        <span className="status-pill">
          <span className="status-dot" /> Modelo activo
        </span>
        <button className="icon-btn" onClick={onToggleTheme} title="Cambiar tema">
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} />
        </button>
        <button className="icon-btn" onClick={onReset} title="Nueva sesión">
          <Icon name="refresh" size={20} />
        </button>
        <div className="avatar">DR</div>
      </div>
    </header>
  );
}

// ───────────────────────── Drag & Drop ─────────────────────────
function UploadZone({ onUpload }) {
  const [drag, setDrag] = useState(false);
  const fileInput = useRef(null);

  const handleFile = (file) => {
    // En este prototipo, cualquier archivo "pasa" — disparamos el flujo demo
    onUpload(file ? file.name : 'columna_lateral_001.png');
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
          accept="image/png"
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
          <li>Formato: <b>PNG</b></li>
          <li>Resolución mínima: <b>512 × 512 px</b></li>
          <li>Vista: <b>Lateral / AP</b></li>
        </ul>
      </div>

      <div className="upload-side">
        <div className="info-card">
          <div className="info-card-header">
            <Icon name="bolt" size={18} />
            <span>Sobre el modelo</span>
          </div>
          <p>
            Red neuronal U-Net 3D entrenada sobre <b>14.382 estudios</b> anotados
            por radiólogos certificados. Detecta y segmenta vértebras
            cervicales, torácicas y lumbares.
          </p>
          <div className="kpi-row">
            <div><span>Dice</span><b>0.943</b></div>
            <div><span>IoU</span><b>0.892</b></div>
            <div><span>Latencia</span><b>~3.2 s</b></div>
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
const PROCESS_STEPS = [
  'Decodificando PNG',
  'Normalizando intensidad',
  'Localizando columna vertebral',
  'Segmentando vértebras',
  'Etiquetando regiones',
  'Calculando métricas',
];

function ProcessingScreen({ filename, onDone }) {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const totalMs = 4200;
    const interval = setInterval(() => {
      setProgress((p) => {
        const next = p + 100 / (totalMs / 60);
        if (next >= 100) {
          clearInterval(interval);
          setTimeout(onDone, 250);
          return 100;
        }
        setStep(Math.min(PROCESS_STEPS.length - 1, Math.floor((next / 100) * PROCESS_STEPS.length)));
        return next;
      });
    }, 60);
    return () => clearInterval(interval);
  }, [onDone]);

  return (
    <div className="processing">
      <div className="processing-stage">
        <div className="scan-frame">
          <div className="scan-svg">
            <XrayImage noiseOpacity={0.5} />
          </div>
          <div className="scan-line" />
          <div className="scan-grid" />
          <div className="scan-corners">
            <span /><span /><span /><span />
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

// ───────────────────────── Vista de resultados ─────────────────────────
function ResultView({ filename, onNew }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [hoveredId, setHoveredId] = useState(null);
  const [showLabels, setShowLabels] = useState(true);
  const [colorMode, setColorMode] = useState('region');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const stageRef = useRef(null);

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

  // Métricas de demo
  const metrics = {
    detected: 24,
    expected: 24,
    confidence: 0.946,
    cervical: { count: 7, conf: 0.962 },
    thoracic: { count: 12, conf: 0.948 },
    lumbar: { count: 5, conf: 0.921 },
    processingMs: 3210,
  };

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
          <div className="seg-control">
            <label>Color</label>
            <div className="seg-buttons">
              {[
                { v: 'region', label: 'Región' },
                { v: 'gradient', label: 'Gradiente' },
                { v: 'unique', label: 'Único' },
                { v: 'mono', label: 'Mono' },
              ].map((o) => (
                <button
                  key={o.v}
                  className={colorMode === o.v ? 'active' : ''}
                  onClick={() => setColorMode(o.v)}
                >{o.label}</button>
              ))}
            </div>
          </div>
          <button
            className={`tool-btn ${showLabels ? 'on' : ''}`}
            onClick={() => setShowLabels((s) => !s)}
            title="Etiquetas"
          >
            <Icon name="layers" size={18} /> Etiquetas
          </button>
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
          <button className="btn-filled" title="Descargar">
            <Icon name="download" size={18} /> Exportar
          </button>
        </div>
      </div>

      <div className="result-body">
        {/* Stage central */}
        <div
          className="stage"
          ref={stageRef}
          onWheel={handleWheel}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
        >
          {/* Reglas */}
          <div className="ruler ruler-top">
            {Array.from({ length: 21 }).map((_, i) => (
              <span key={i} className={i % 5 === 0 ? 'major' : ''} />
            ))}
          </div>
          <div className="ruler ruler-left">
            {Array.from({ length: 31 }).map((_, i) => (
              <span key={i} className={i % 5 === 0 ? 'major' : ''} />
            ))}
          </div>

          {/* Comparador slider */}
          <div
            className="comparator"
            ref={sliderRef}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            }}
          >
            <div className="layer xray-layer">
              <XrayImage noiseOpacity={0.35} />
            </div>

            <div
              className="layer mask-layer"
              style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
            >
              <div className="mask-inner">
                <XrayImage noiseOpacity={0.25} />
                <div className="mask-overlay">
                  <SegmentationMask
                    showLabels={showLabels}
                    hoveredId={hoveredId}
                    onHover={setHoveredId}
                    colorMode={colorMode}
                  />
                </div>
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
          </div>

          {/* HUD esquinas */}
          <div className="hud hud-tl mono">
            <div>STUDY · 2026-04-28 14:32</div>
            <div>VIEW · LATERAL</div>
          </div>
          <div className="hud hud-tr mono">
            <div>U-Net 3D · v2.4.1</div>
            <div>Conf {Math.round(metrics.confidence * 1000) / 10}%</div>
          </div>
          <div className="hud hud-bl mono">
            <div>kVp 75 · mA 320</div>
            <div>1024 × 2304 px</div>
          </div>
          <div className="hud hud-br mono">
            <div>{Math.round(zoom * 100)}% · ({pan.x}, {pan.y})</div>
            <div>RGBA · 16-bit</div>
          </div>
        </div>

        {/* Panel lateral derecho */}
        <aside className="side-panel">
          <section className="panel-card">
            <header>
              <h3>Resultados</h3>
              <span className="chip mono">{(metrics.processingMs / 1000).toFixed(2)}s</span>
            </header>
            <div className="big-stat">
              <div className="big-stat-value">
                {metrics.detected}<span>/{metrics.expected}</span>
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
              {[
                { key: 'cervical', label: 'Cervical', range: 'C1 – C7', dot: '#4FC3F7', ...metrics.cervical },
                { key: 'thoracic', label: 'Torácica', range: 'T1 – T12', dot: '#80D8FF', ...metrics.thoracic },
                { key: 'lumbar',   label: 'Lumbar',   range: 'L1 – L5',  dot: '#00E5A0', ...metrics.lumbar },
              ].map((r) => (
                <li key={r.key}>
                  <span className="region-dot" style={{ background: r.dot }} />
                  <div className="region-text">
                    <b>{r.label}</b>
                    <span className="mono">{r.range}</span>
                  </div>
                  <div className="region-stats">
                    <span className="mono"><b>{r.count}</b> v.</span>
                    <span className="mono dim">{(r.conf * 100).toFixed(1)}%</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel-card">
            <header><h3>Vértebras</h3></header>
            <div className="vert-grid">
              {VERTEBRAE.map((v) => (
                <button
                  key={v.id}
                  className={`vert-chip ${v.region} ${hoveredId === v.id ? 'on' : ''}`}
                  onMouseEnter={() => setHoveredId(v.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >{v.label}</button>
              ))}
            </div>
          </section>

          <section className="panel-card">
            <header><h3>Exportar</h3></header>
            <div className="export-buttons">
              <button className="btn-outline"><Icon name="download" size={16} /> PNG</button>
              <button className="btn-outline"><Icon name="download" size={16} /> Máscara</button>
              <button className="btn-outline"><Icon name="download" size={16} /> Overlay</button>
              <button className="btn-outline"><Icon name="download" size={16} /> Reporte</button>
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
  const [phase, setPhase] = useState('upload'); // upload | processing | result
  const [filename, setFilename] = useState('');
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULS);

  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
  }, [tweaks.theme]);

  const start = (name) => {
    setFilename(name);
    setPhase('processing');
  };
  const reset = () => {
    setPhase('upload');
    setFilename('');
  };

  return (
    <div className="app">
      <AppBar
        onReset={reset}
        onToggleTheme={() => setTweak('theme', tweaks.theme === 'dark' ? 'light' : 'dark')}
        theme={tweaks.theme}
      />

      <main className="main">
        {phase === 'upload' && <UploadZone onUpload={start} />}
        {phase === 'processing' && (
          <ProcessingScreen filename={filename} onDone={() => setPhase('result')} />
        )}
        {phase === 'result' && <ResultView filename={filename} onNew={reset} />}
      </main>

      <footer className="app-footer mono">
        <span>VertebraAI · Apoyo diagnóstico — no sustituye criterio clínico</span>
        <span>HIPAA · ISO 13485</span>
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
