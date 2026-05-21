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
    clock: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2M12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8m.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
    logout: 'M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z',
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d={paths[name] || ''} />
    </svg>
  );
};

// ───────────────────────── Login screen ─────────────────────────
function LoginView({ onLogin }) {
  // step: 'login' | 'forgot-request' | 'forgot-confirm'
  const [step, setStep] = React.useState('login');
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [otpCode, setOtpCode] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [info, setInfo] = React.useState(null);

  function resetToLogin() {
    setStep('login');
    setError(null);
    setInfo(null);
    setOtpCode('');
    setNewPassword('');
  }

  async function handleLogin(e) {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true); setError(null);
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
    } finally { setLoading(false); }
  }

  async function handleForgotRequest(e) {
    e.preventDefault();
    if (!username) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'No se pudo enviar el código');
      }
      setInfo('Código OTP enviado al correo registrado. Revisa tu bandeja.');
      setStep('forgot-confirm');
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }

  async function handleForgotConfirm(e) {
    e.preventDefault();
    if (!otpCode || !newPassword) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/confirm-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, otp_code: otpCode, new_password: newPassword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Código incorrecto o expirado');
      }
      setInfo('Contraseña actualizada. Ya puedes iniciar sesión.');
      resetToLogin();
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }

  return (
    <div className="login-view">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-logo">VertebraAI</span>
          <p className="login-subtitle">Sistema de segmentación de columna vertebral</p>
        </div>

        {/* ── Paso 1: login ── */}
        {step === 'login' && (
          <form className="login-form" onSubmit={handleLogin}>
            <div className="login-field-group">
              <label className="login-label" htmlFor="login-username">Usuario</label>
              <input id="login-username" className="login-field" type="text"
                autoComplete="username" placeholder="usuario o correo"
                value={username} onChange={e => setUsername(e.target.value)}
                disabled={loading} required />
            </div>
            <div className="login-field-group">
              <label className="login-label" htmlFor="login-password">Contraseña</label>
              <input id="login-password" className="login-field" type="password"
                autoComplete="current-password" placeholder="••••••••"
                value={password} onChange={e => setPassword(e.target.value)}
                disabled={loading} required />
            </div>
            {info && <p className="login-info">{info}</p>}
            {error && <p className="login-error">{error}</p>}
            <button className="btn-filled login-submit" type="submit"
              disabled={loading || !username || !password}>
              {loading ? <span className="login-spinner" /> : 'Ingresar'}
            </button>
            <button type="button" className="login-forgot-link"
              onClick={() => { setError(null); setInfo(null); setStep('forgot-request'); }}>
              ¿Olvidaste tu contraseña?
            </button>
          </form>
        )}

        {/* ── Paso 2: solicitar OTP ── */}
        {step === 'forgot-request' && (
          <form className="login-form" onSubmit={handleForgotRequest}>
            <p className="login-step-title">Recuperar contraseña</p>
            <p className="login-step-desc">Ingresa tu usuario y te enviaremos un código OTP al correo registrado.</p>
            <div className="login-field-group">
              <label className="login-label" htmlFor="forgot-username">Usuario</label>
              <input id="forgot-username" className="login-field" type="text"
                autoComplete="username" placeholder="usuario o correo"
                value={username} onChange={e => setUsername(e.target.value)}
                disabled={loading} required />
            </div>
            {error && <p className="login-error">{error}</p>}
            <button className="btn-filled login-submit" type="submit"
              disabled={loading || !username}>
              {loading ? <span className="login-spinner" /> : 'Enviar código OTP'}
            </button>
            <button type="button" className="login-forgot-link" onClick={resetToLogin}>
              ← Volver al inicio de sesión
            </button>
          </form>
        )}

        {/* ── Paso 3: confirmar OTP + nueva contraseña ── */}
        {step === 'forgot-confirm' && (
          <form className="login-form" onSubmit={handleForgotConfirm}>
            <p className="login-step-title">Establecer nueva contraseña</p>
            {info && <p className="login-info">{info}</p>}
            <div className="login-field-group">
              <label className="login-label" htmlFor="otp-code">Código OTP</label>
              <input id="otp-code" className="login-field" type="text"
                inputMode="numeric" maxLength={6} placeholder="123456"
                value={otpCode} onChange={e => setOtpCode(e.target.value.replace(/\D/g, ''))}
                disabled={loading} required />
            </div>
            <div className="login-field-group">
              <label className="login-label" htmlFor="new-password">Nueva contraseña</label>
              <input id="new-password" className="login-field" type="password"
                autoComplete="new-password" placeholder="••••••••"
                value={newPassword} onChange={e => setNewPassword(e.target.value)}
                disabled={loading} required />
            </div>
            {error && <p className="login-error">{error}</p>}
            <button className="btn-filled login-submit" type="submit"
              disabled={loading || !otpCode || !newPassword}>
              {loading ? <span className="login-spinner" /> : 'Confirmar nueva contraseña'}
            </button>
            <button type="button" className="login-forgot-link"
              onClick={() => setStep('forgot-request')}>
              ← Reenviar código
            </button>
          </form>
        )}

        <p className="login-footer">Apoyo diagnóstico — Uso exclusivo de personal autorizado</p>
      </div>
    </div>
  );
}

// ───────────────────────── App Bar ─────────────────────────
function AppBar({ onReset, onToggleTheme, theme, selectedModelName, canReanalyze, onPickModel, phase, onLogout, authToken }) {
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
          <span className="appbar-subtitle">{selectedModelName || 'Segmentación de columna'}</span>
        </div>
      </div>

      <div className="appbar-right">
        {phase !== 'compare' && (
          <button
            type="button"
            className="status-pill appbar-model-btn"
            onClick={canReanalyze ? onPickModel : undefined}
            disabled={!canReanalyze}
            title={canReanalyze ? "Cambiar modelo y re-analizar" : "Modelo conectado"}
          >
            <span className="status-dot" />
            {canReanalyze && selectedModelName ? selectedModelName : (selectedModelName ? 'Modelo conectado' : 'Conectando…')}
          </button>
        )}
        <button className="icon-btn" onClick={onToggleTheme} title="Cambiar tema">
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} />
        </button>
        <button className="icon-btn" onClick={onReset} title="Nueva sesión">
          <Icon name="refresh" size={20} />
        </button>
        {authToken && (
          <button className="icon-btn appbar-logout-btn" onClick={onLogout} title="Cerrar sesión">
            <Icon name="logout" size={20} />
          </button>
        )}
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
function ResultView({ result, fileUrl, filename, onNew, onCompare, authToken }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [hoveredId, setHoveredId] = useState(null);
  // Multi-select de vértebras: Set para que React detecte cambios al hacer
  // copy-on-write (mutar el mismo Set no dispara re-render).
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const [actionsOpen, setActionsOpen] = useState(false);
  const actionsRef = useRef(null);

  useEffect(() => {
    if (!actionsOpen) return;
    const close = (e) => {
      if (actionsRef.current && !actionsRef.current.contains(e.target)) {
        setActionsOpen(false);
      }
    };
    const escape = (e) => { if (e.key === 'Escape') setActionsOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', escape);
    };
  }, [actionsOpen]);

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

  // Descarga de exports vía endpoint del backend con auth header
  const downloadExport = async (format) => {
    const url = `${API_BASE}/xrays/${study_id}/exports/${format}`;
    try {
      const res = await fetch(url, {
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `${study_id}_${format}`;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch {}
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
          <div className="actions-menu" ref={actionsRef}>
            <button
              className="btn-filled"
              onClick={() => setActionsOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={actionsOpen}
              title="Acciones"
            >
              <Icon name="download" size={18} /> Acciones
              <span className="caret" aria-hidden="true">▾</span>
            </button>
            {actionsOpen && (
              <div className="actions-dropdown" role="menu">
                <div className="actions-section-title">Exportar</div>
                <button role="menuitem" onClick={() => { downloadExport('png'); setActionsOpen(false); }}>
                  <Icon name="download" size={16} /> Original
                </button>
                <button role="menuitem" onClick={() => { downloadExport('mask'); setActionsOpen(false); }}>
                  <Icon name="download" size={16} /> Máscara
                </button>
                <button role="menuitem" onClick={() => { downloadExport('overlay'); setActionsOpen(false); }}>
                  <Icon name="download" size={16} /> Overlay
                </button>
                <button role="menuitem" onClick={() => { downloadExport('report'); setActionsOpen(false); }}>
                  <Icon name="download" size={16} /> Reporte
                </button>
                <div className="actions-divider" />
                <button role="menuitem" onClick={() => { setActionsOpen(false); onNew(); }}>
                  <Icon name="refresh" size={16} /> Analizar otra radiografía
                </button>
              </div>
            )}
          </div>
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
              // -50%/-50% mantiene el centrado heredado del CSS (top:50% left:50%);
              // el pan se aplica en el frame del elemento y el scale se hace
              // respecto al transform-origin: center.
              transform: `translate(-50%, -50%) translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
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

        </aside>
      </div>
    </div>
  );
}

// ───────────────────────── Comparación: panel reutilizable ─────────────────────────
// Render compacto de un análisis: título + métricas como barras de progreso
// (Dice/IoU usan los mismos estilos conf-bar/conf-fill que la "Confianza
// global" de la pantalla de resultados) + radiografía con máscara superpuesta.
// Los slots no primarios reciben `onChange` para abrir el picker que reemplaza
// el modelo del slot.
const COMPARE_REGION_COLORS = {
  cervical: '#4285F4',
  thoracic: '#34A853',
  lumbar:   '#EA4335',
};
const COMPARE_REGION_INFO = [
  { key: 'cervical', label: 'Cervical', range: 'C3–C7' },
  { key: 'thoracic', label: 'Torácica', range: 'T1–T12' },
  { key: 'lumbar',   label: 'Lumbar',   range: 'L1–L5' },
];

function ComparePane({ title, metrics, fileUrl, maskBase64, primary, onChange, onError, error, fullResult, showDetail }) {
  if (error) {
    return (
      <div className="compare-pane compare-status compare-status-error">
        <Icon name="error" size={32} />
        <p>{error}</p>
        {onError && (
          <button className="btn-tonal" onClick={onError}>
            Reintentar con otro modelo
          </button>
        )}
      </div>
    );
  }
  const maskUrl = `data:image/png;base64,${maskBase64}`;
  return (
    <div className={`compare-pane${showDetail ? ' compare-pane--detail' : ''}`}>
      <div className="compare-pane-header">
        <h3>{title}</h3>
        {!primary && onChange && (
          <button
            type="button"
            className="compare-change-btn"
            onClick={onChange}
            title="Cambiar modelo"
          >
            <Icon name="tune" size={14} />
            <span>Cambiar</span>
            <span className="caret" aria-hidden="true">▾</span>
          </button>
        )}
      </div>

      {/* En modo normal las métricas van arriba; en detalle desaparecen (se muestran abajo) */}
      {!showDetail && (
        <div className="compare-metrics">
          <div className="metric-row">
            <div className="conf-row">
              <span>Dice</span>
              <b className="mono">{metrics.dice.toFixed(3)}</b>
            </div>
            <div className="conf-bar">
              <div className="conf-fill" style={{ width: `${Math.max(0, Math.min(1, metrics.dice)) * 100}%` }} />
            </div>
          </div>
          <div className="metric-row">
            <div className="conf-row">
              <span>IoU</span>
              <b className="mono">{metrics.iou.toFixed(3)}</b>
            </div>
            <div className="conf-bar">
              <div className="conf-fill" style={{ width: `${Math.max(0, Math.min(1, metrics.iou)) * 100}%` }} />
            </div>
          </div>
          <div className="metric-row metric-row-latency">
            <div className="conf-row">
              <span><Icon name="clock" size={12} /> Tiempo de ejecución</span>
              <b className="mono">{metrics.latency_ms.toFixed(0)} ms</b>
            </div>
          </div>
        </div>
      )}

      <div className={`compare-canvas${showDetail ? ' compare-canvas--compact' : ''}`}>
        <img className="compare-xray" src={fileUrl} alt="Radiografía original" />
        <img className="compare-mask" src={maskUrl} alt="Máscara del modelo" />
      </div>

      {showDetail && fullResult && (
        <div className="compare-detail">
          <div className="compare-detail-section">Resultados</div>
          <div className="compare-detail-row">
            <span>Vértebras detectadas</span>
            <b className="mono">{fullResult.metrics.detected_count}/{fullResult.vertebrae?.length ?? '?'}</b>
          </div>
          <div className="compare-detail-row">
            <span>Confianza global</span>
            <b className="mono">{(fullResult.metrics.confidence * 100).toFixed(1)}%</b>
          </div>
          <div className="compare-detail-divider" />
          <div className="compare-detail-section">Por región</div>
          {COMPARE_REGION_INFO.map((r) => {
            const data = fullResult.metrics.by_region?.[r.key];
            if (!data) return null;
            return (
              <div key={r.key} className="compare-detail-region">
                <span className="compare-detail-region-name">
                  <span className="compare-detail-dot" style={{ background: COMPARE_REGION_COLORS[r.key] }} />
                  {r.label} <span className="compare-detail-range">{r.range}</span>
                </span>
                <span className="mono">
                  {data.detected_count}/{data.expected_count}
                  <span className="compare-detail-conf"> · {(data.mean_confidence * 100).toFixed(1)}%</span>
                </span>
              </div>
            );
          })}
          <div className="compare-detail-divider" />
          <div className="compare-detail-section">Métricas del modelo</div>
          <div className="compare-detail-row">
            <span>Dice</span>
            <b className="mono">{metrics.dice.toFixed(3)}</b>
          </div>
          <div className="compare-detail-bar">
            <div className="compare-detail-bar-fill" style={{ width: `${Math.max(0, Math.min(1, metrics.dice)) * 100}%` }} />
          </div>
          <div className="compare-detail-row">
            <span>IoU</span>
            <b className="mono">{metrics.iou.toFixed(3)}</b>
          </div>
          <div className="compare-detail-bar">
            <div className="compare-detail-bar-fill" style={{ width: `${Math.max(0, Math.min(1, metrics.iou)) * 100}%` }} />
          </div>
          <div className="compare-detail-row">
            <span><Icon name="clock" size={12} /> Tiempo de ejecución</span>
            <b className="mono">{metrics.latency_ms.toFixed(0)} ms</b>
          </div>
        </div>
      )}
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
// Soporta hasta 2 slots de comparación (3 paneles totales: primario + 2). Cada
// slot tiene su botón "cambiar modelo" que abre el picker. El picker excluye
// todos los modelos ya visibles (primario + otros slots) para evitar duplicados.
function CompareView({
  result,
  fileUrl,
  filename,
  models,
  selectedModelId,
  compareSlots,
  onAddSlot,
  onChangeSlot,
  onBack,
}) {
  // pickerState: null | { mode: 'add' } | { mode: 'change', slotIdx }
  const [pickerState, setPickerState] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  const primaryModel = models.find((m) => m.id === selectedModelId);
  const usedIds = new Set([selectedModelId, ...compareSlots.map((s) => s.modelId)]);
  // Excluye el primario y todos los slots; en modo 'change' también excluye el
  // modelo actual del slot (sería un no-op).
  const pickerModels = (() => {
    if (!pickerState) return [];
    if (pickerState.mode === 'add') {
      return models.filter((m) => !usedIds.has(m.id));
    }
    return models.filter((m) => !usedIds.has(m.id));
  })();

  const canAddMore = compareSlots.length < 2 && models.some((m) => !usedIds.has(m.id));
  const paneCount = 1 + compareSlots.length + (canAddMore ? 1 : 0);

  return (
    <div className="compare-shell">
      <div className="compare-toolbar">
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button className="btn-tonal" onClick={onBack}>
            <Icon name="refresh" size={16} /> Volver al resultado
          </button>
          <button
            className={`btn-tonal${showDetail ? ' btn-tonal--active' : ''}`}
            onClick={() => setShowDetail((v) => !v)}
            title={showDetail ? 'Ocultar métricas detalladas' : 'Ver métricas detalladas por modelo'}
          >
            <Icon name="info" size={16} /> {showDetail ? 'Ocultar detalle' : 'Ver detalle'}
          </button>
        </div>
        <div className="compare-file">
          <Icon name="image" size={16} />
          <span className="mono">{filename}</span>
        </div>
      </div>

      <div
        className="compare-body"
        style={{ gridTemplateColumns: `repeat(${paneCount}, minmax(0, 1fr))` }}
      >
        <ComparePane
          primary
          title={primaryModel?.display_name || 'Modelo A'}
          metrics={result.metrics.model_metrics}
          fileUrl={fileUrl}
          maskBase64={result.mask.data}
          fullResult={result}
          showDetail={showDetail}
        />

        {compareSlots.map((slot, idx) => {
          const slotModel = models.find((m) => m.id === slot.modelId);
          const openChange = () => setPickerState({ mode: 'change', slotIdx: idx });
          if (slot.error) {
            return (
              <ComparePane
                key={`slot-${idx}`}
                error={slot.error}
                onError={openChange}
              />
            );
          }
          if (!slot.result) {
            // Placeholder mínimo mientras corre el reanalyzing overlay; no se
            // ve normalmente porque el overlay cubre todo, pero quedaría algo
            // visible si el overlay se cerrase antes de tiempo.
            return (
              <div key={`slot-${idx}`} className="compare-pane compare-status">
                <div className="spinner" />
                <p>Ejecutando {slotModel?.display_name || 'modelo'}…</p>
              </div>
            );
          }
          return (
            <ComparePane
              key={`slot-${idx}`}
              title={slotModel?.display_name || `Modelo ${idx + 2}`}
              metrics={slot.result.metrics.model_metrics}
              fileUrl={fileUrl}
              maskBase64={slot.result.mask.data}
              onChange={openChange}
              fullResult={slot.result}
              showDetail={showDetail}
            />
          );
        })}

        {canAddMore && (
          <button
            type="button"
            className="compare-empty"
            onClick={() => setPickerState({ mode: 'add' })}
            title="Elegir modelo para comparar"
          >
            <span className="compare-empty-plus">+</span>
            <span className="compare-empty-label">Seleccionar otro modelo<br/>para comparar</span>
          </button>
        )}
      </div>

      {pickerState && (
        <ModelPickerModal
          models={pickerModels}
          onPick={(id) => {
            if (pickerState.mode === 'add') onAddSlot(id);
            else onChangeSlot(pickerState.slotIdx, id);
            setPickerState(null);
          }}
          onClose={() => setPickerState(null)}
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
  const [phase, setPhase] = useState(() =>
    localStorage.getItem('vertebraai-token') ? 'upload' : 'login'
  );
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('vertebraai-token'));
  const [authUser, setAuthUser] = useState(null);
  const [filename, setFilename] = useState('');
  const [fileUrl, setFileUrl] = useState(null);     // URL local de la imagen subida
  // Guardamos también el File blob original para poder re-submitirlo a /xrays
  // cuando el usuario quiera correr la comparación con otro modelo.
  const [originalFile, setOriginalFile] = useState(null);
  const [result, setResult] = useState(null);       // Respuesta del backend
  const [error, setError] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('medsam');
  // Comparación: hasta 2 slots (pantalla 3 muestra 3 paneles totales con el
  // primario). Cada slot: { modelId, result?, error? }.
  const [compareSlots, setCompareSlots] = useState([]);
  // Picker del appbar + estado de re-análisis con overlay fullscreen.
  const [pickerOpen, setPickerOpen] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(null); // null | { modelId }
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULS);

  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
  }, [tweaks.theme]);

  // Validate stored token on mount; authToken is already initialised from localStorage
  useEffect(() => {
    if (!authToken) { setPhase('login'); return; }
    fetch(`${API_BASE}/auth/me`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    }).then(r => {
      if (r.ok) return r.json();
      throw new Error('invalid');
    }).then(user => {
      setAuthUser(user);
    }).catch(() => {
      localStorage.removeItem('vertebraai-token');
      setAuthToken(null);
      setPhase('login');
    });
  }, []);

  async function handleLogin(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Credenciales inválidas');
    }
    const data = await res.json();
    localStorage.setItem('vertebraai-token', data.token);
    setAuthToken(data.token);
    setAuthUser(data.user);
    setPhase('upload');
  }

  function handleLogout() {
    localStorage.removeItem('vertebraai-token');
    setAuthToken(null);
    setAuthUser(null);
    setPhase('login');
  }

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

  const start = async (file, modelIdOverride) => {
    const modelToUse = modelIdOverride || selectedModelId;
    setFilename(file.name);
    setOriginalFile(file);
    const localUrl = URL.createObjectURL(file);
    setFileUrl(localUrl);
    setPhase('processing');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', modelToUse);

      const response = await fetch(`${API_BASE}/xrays`, {
        method: 'POST',
        body: formData,
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}),
        },
      });
      if (!response.ok) {
        let message = `HTTP ${response.status}`;
        try { const errBody = await response.json(); message = errBody.detail || errBody.error || message; } catch {}
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
    setCompareSlots([]);
  };

  // POST /xrays con el archivo cargado y el modelo dado. Helper compartido
  // por todas las acciones que disparan inferencia desde la pantalla de
  // resultados o comparación (no por el flujo de upload inicial).
  const _runAnalysisFor = async (modelId) => {
    const formData = new FormData();
    formData.append('file', originalFile);
    formData.append('model', modelId);
    const response = await fetch(`${API_BASE}/xrays`, {
      method: 'POST',
      body: formData,
      headers: {
        ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}),
      },
    });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try { const errBody = await response.json(); message = errBody.detail || errBody.error || message; } catch {}
      throw new Error(message);
    }
    return response.json();
  };

  // Re-análisis (pantalla 2): reemplaza el resultado actual con otro modelo.
  const reanalyzeWith = async (modelId) => {
    if (!originalFile || modelId === selectedModelId) {
      setPickerOpen(false);
      return;
    }
    setPickerOpen(false);
    setReanalyzing({ modelId });
    try {
      const data = await _runAnalysisFor(modelId);
      setResult(data);
      setSelectedModelId(modelId);
      setCompareSlots([]);
    } catch (err) {
      console.error('Error en re-análisis:', err);
      setError(err.message || 'No se pudo ejecutar el re-análisis');
      setPhase('error');
    } finally {
      setReanalyzing(null);
    }
  };

  // Comparación: añade un slot ejecutando el modelo elegido. Muestra el
  // overlay fullscreen igual que el re-análisis (pantalla 2).
  const addCompareSlot = async (modelId) => {
    if (!originalFile) return;
    setReanalyzing({ modelId });
    try {
      const data = await _runAnalysisFor(modelId);
      setCompareSlots((prev) => [...prev, { modelId, result: data, error: null }]);
    } catch (err) {
      console.error('Error agregando comparación:', err);
      setCompareSlots((prev) => [...prev, { modelId, result: null, error: err.message || 'Error de comparación' }]);
    } finally {
      setReanalyzing(null);
    }
  };

  // Comparación: reemplaza el modelo de un slot existente. Mismo overlay.
  const changeCompareSlot = async (slotIdx, newModelId) => {
    if (!originalFile) return;
    setReanalyzing({ modelId: newModelId });
    try {
      const data = await _runAnalysisFor(newModelId);
      setCompareSlots((prev) => prev.map((s, i) => i === slotIdx ? { modelId: newModelId, result: data, error: null } : s));
    } catch (err) {
      console.error('Error cambiando modelo del slot:', err);
      setCompareSlots((prev) => prev.map((s, i) => i === slotIdx ? { modelId: newModelId, result: null, error: err.message || 'Error de comparación' } : s));
    } finally {
      setReanalyzing(null);
    }
  };

  const enterCompare = () => {
    setCompareSlots([]);
    setPhase('compare');
  };
  const exitCompare = () => setPhase('result');

  // Derivados para el AppBar: el título usa el display_name del modelo activo.
  const selectedModel = models.find((m) => m.id === selectedModelId);
  const selectedModelName = selectedModel?.display_name || null;
  const canReanalyze = phase === 'result' && !!originalFile;

  if (phase === 'login') {
    return <LoginView onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <AppBar
        onReset={reset}
        onToggleTheme={() => setTweak('theme', tweaks.theme === 'dark' ? 'light' : 'dark')}
        theme={tweaks.theme}
        selectedModelName={selectedModelName}
        canReanalyze={canReanalyze}
        onPickModel={() => setPickerOpen(true)}
        phase={phase}
        onLogout={handleLogout}
        authToken={authToken}
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
            authToken={authToken}
          />
        )}
        {phase === 'compare' && result && (
          <CompareView
            result={result}
            fileUrl={fileUrl}
            filename={filename}
            models={models}
            selectedModelId={selectedModelId}
            compareSlots={compareSlots}
            onAddSlot={addCompareSlot}
            onChangeSlot={changeCompareSlot}
            onBack={exitCompare}
          />
        )}
      </main>

      {pickerOpen && (
        <ModelPickerModal
          models={models.filter((m) => m.id !== selectedModelId)}
          onPick={(id) => reanalyzeWith(id)}
          onClose={() => setPickerOpen(false)}
        />
      )}
      {reanalyzing && (
        <div className="reanalyze-overlay">
          <ProcessingScreen
            filename={filename}
            fileUrl={fileUrl}
            steps={models.find((m) => m.id === reanalyzing.modelId)?.processing_steps || []}
          />
        </div>
      )}

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
