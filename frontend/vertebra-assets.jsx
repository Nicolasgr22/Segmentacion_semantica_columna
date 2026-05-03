// Placeholder SVG assets para radiografía y máscara de segmentación
// Diseñados para evocar una columna lateral sin recrear UI propietaria

const VERTEBRAE = [
  // y, height, width-factor, region, label
  { id: 'C1', y: 60,  h: 22, w: 0.55, region: 'cervical', label: 'C1' },
  { id: 'C2', y: 84,  h: 22, w: 0.58, region: 'cervical', label: 'C2' },
  { id: 'C3', y: 108, h: 22, w: 0.60, region: 'cervical', label: 'C3' },
  { id: 'C4', y: 132, h: 22, w: 0.62, region: 'cervical', label: 'C4' },
  { id: 'C5', y: 156, h: 22, w: 0.64, region: 'cervical', label: 'C5' },
  { id: 'C6', y: 180, h: 22, w: 0.66, region: 'cervical', label: 'C6' },
  { id: 'C7', y: 204, h: 24, w: 0.68, region: 'cervical', label: 'C7' },
  { id: 'T1', y: 230, h: 26, w: 0.74, region: 'thoracic', label: 'T1' },
  { id: 'T2', y: 258, h: 26, w: 0.78, region: 'thoracic', label: 'T2' },
  { id: 'T3', y: 286, h: 28, w: 0.82, region: 'thoracic', label: 'T3' },
  { id: 'T4', y: 316, h: 28, w: 0.84, region: 'thoracic', label: 'T4' },
  { id: 'T5', y: 346, h: 30, w: 0.86, region: 'thoracic', label: 'T5' },
  { id: 'T6', y: 378, h: 30, w: 0.88, region: 'thoracic', label: 'T6' },
  { id: 'T7', y: 410, h: 32, w: 0.90, region: 'thoracic', label: 'T7' },
  { id: 'T8', y: 444, h: 32, w: 0.92, region: 'thoracic', label: 'T8' },
  { id: 'T9', y: 478, h: 34, w: 0.94, region: 'thoracic', label: 'T9' },
  { id: 'T10', y: 514, h: 34, w: 0.96, region: 'thoracic', label: 'T10' },
  { id: 'T11', y: 550, h: 36, w: 0.98, region: 'thoracic', label: 'T11' },
  { id: 'T12', y: 588, h: 38, w: 1.00, region: 'thoracic', label: 'T12' },
  { id: 'L1', y: 628, h: 42, w: 1.05, region: 'lumbar', label: 'L1' },
  { id: 'L2', y: 672, h: 44, w: 1.08, region: 'lumbar', label: 'L2' },
  { id: 'L3', y: 718, h: 46, w: 1.10, region: 'lumbar', label: 'L3' },
  { id: 'L4', y: 766, h: 46, w: 1.10, region: 'lumbar', label: 'L4' },
  { id: 'L5', y: 814, h: 48, w: 1.10, region: 'lumbar', label: 'L5' },
];

// Centro horizontal de la columna (curvatura natural)
function spineCenterX(y) {
  // Cervical curva ligeramente hacia adelante, torácica hacia atrás, lumbar hacia adelante
  const cx = 200;
  if (y < 220) return cx + Math.sin((y - 60) / 50) * 8;
  if (y < 580) return cx - 14 + Math.sin((y - 220) / 80) * 4;
  return cx + 6 + Math.sin((y - 580) / 60) * 6;
}

// Radiografía base: tonos grises azulados sobre fondo oscuro
function XrayImage({ noiseOpacity = 0.4 }) {
  return (
    <svg
      viewBox="0 0 400 900"
      preserveAspectRatio="xMidYMid meet"
      style={{ width: '100%', height: '100%', display: 'block' }}
    >
      <defs>
        <radialGradient id="xrayBg" cx="50%" cy="45%" r="65%">
          <stop offset="0%" stopColor="#1a2942" />
          <stop offset="60%" stopColor="#0c1626" />
          <stop offset="100%" stopColor="#050a14" />
        </radialGradient>
        <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#1a2942" stopOpacity="0" />
          <stop offset="20%" stopColor="#2c4566" stopOpacity="0.4" />
          <stop offset="50%" stopColor="#3d5e8a" stopOpacity="0.6" />
          <stop offset="80%" stopColor="#2c4566" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#1a2942" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="boneGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#9bb5d6" stopOpacity="0.5" />
          <stop offset="50%" stopColor="#dde7f5" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#9bb5d6" stopOpacity="0.5" />
        </linearGradient>
        <filter id="xrayBlur">
          <feGaussianBlur stdDeviation="0.6" />
        </filter>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" />
          <feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.6  0 0 0 0 0.8  0 0 0 0.15 0" />
        </filter>
      </defs>

      {/* Fondo */}
      <rect width="400" height="900" fill="url(#xrayBg)" />

      {/* Silueta del cuerpo */}
      <ellipse cx="200" cy="450" rx="180" ry="430" fill="url(#bodyGrad)" />

      {/* Costillas (torácicas) */}
      <g opacity="0.35" stroke="#a8c4e8" strokeWidth="1.5" fill="none" filter="url(#xrayBlur)">
        {Array.from({ length: 11 }).map((_, i) => {
          const yy = 240 + i * 32;
          const cx = spineCenterX(yy);
          return (
            <g key={i}>
              <path d={`M ${cx} ${yy} Q ${cx - 90} ${yy + 20} ${cx - 150} ${yy + 50}`} />
              <path d={`M ${cx} ${yy} Q ${cx + 90} ${yy + 20} ${cx + 150} ${yy + 50}`} />
            </g>
          );
        })}
      </g>

      {/* Cráneo base */}
      <ellipse cx="200" cy="40" rx="60" ry="48" fill="#dde7f5" opacity="0.55" filter="url(#xrayBlur)" />

      {/* Vértebras (huesos visibles) */}
      <g filter="url(#xrayBlur)">
        {VERTEBRAE.map((v) => {
          const cx = spineCenterX(v.y + v.h / 2);
          const w = 38 * v.w;
          return (
            <g key={v.id}>
              {/* Cuerpo vertebral */}
              <rect
                x={cx - w / 2}
                y={v.y}
                width={w}
                height={v.h - 4}
                rx={4}
                fill="url(#boneGrad)"
                opacity={0.92}
              />
              {/* Disco intervertebral más oscuro */}
              <rect
                x={cx - w / 2 + 3}
                y={v.y + v.h - 4}
                width={w - 6}
                height={3}
                fill="#0c1626"
                opacity={0.5}
              />
              {/* Apófisis posterior */}
              <ellipse
                cx={cx + w / 2 + 6}
                cy={v.y + v.h / 2}
                rx={6}
                ry={v.h / 3}
                fill="#9bb5d6"
                opacity={0.5}
              />
            </g>
          );
        })}
      </g>

      {/* Pelvis insinuada */}
      <path
        d="M 130 870 Q 200 850 270 870 L 280 900 L 120 900 Z"
        fill="#dde7f5"
        opacity="0.4"
        filter="url(#xrayBlur)"
      />

      {/* Grano */}
      <rect width="400" height="900" filter="url(#grain)" opacity={noiseOpacity} />
    </svg>
  );
}

// Máscara de segmentación con colores por región
function SegmentationMask({
  showLabels = true,
  hoveredId = null,
  onHover = () => {},
  colorMode = 'region', // 'region' | 'gradient' | 'unique' | 'mono'
}) {
  const regionColors = {
    cervical: '#4FC3F7',
    thoracic: '#80D8FF',
    lumbar: '#00E5A0',
  };

  const colorFor = (v, idx) => {
    if (colorMode === 'mono') return '#4FC3F7';
    if (colorMode === 'region') return regionColors[v.region];
    if (colorMode === 'gradient') {
      // Cyan claro arriba → verde abajo
      const t = idx / (VERTEBRAE.length - 1);
      const hueStart = 200; // azul cyan
      const hueEnd = 160;   // verde-cyan
      const hue = hueStart + (hueEnd - hueStart) * t;
      return `oklch(0.78 0.16 ${hue})`;
    }
    // unique
    const hue = (idx * 360) / VERTEBRAE.length;
    return `oklch(0.78 0.14 ${hue + 180})`;
  };

  return (
    <svg
      viewBox="0 0 400 900"
      preserveAspectRatio="xMidYMid meet"
      style={{ width: '100%', height: '100%', display: 'block' }}
    >
      <defs>
        <filter id="maskGlow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Fondo translúcido para legibilidad de la máscara sin la radiografía */}
      <rect width="400" height="900" fill="#050a14" opacity="0.4" />

      {VERTEBRAE.map((v, i) => {
        const cx = spineCenterX(v.y + v.h / 2);
        const w = 38 * v.w;
        const color = colorFor(v, i);
        const isHovered = hoveredId === v.id;
        return (
          <g
            key={v.id}
            onMouseEnter={() => onHover(v.id)}
            onMouseLeave={() => onHover(null)}
            style={{ cursor: 'pointer', transition: 'opacity 120ms' }}
            opacity={hoveredId && !isHovered ? 0.55 : 1}
          >
            {/* Cuerpo vertebral segmentado */}
            <rect
              x={cx - w / 2}
              y={v.y}
              width={w}
              height={v.h - 4}
              rx={5}
              fill={color}
              fillOpacity={isHovered ? 0.85 : 0.7}
              stroke={color}
              strokeWidth={isHovered ? 2 : 1}
              filter={isHovered ? 'url(#maskGlow)' : undefined}
            />
            {/* Apófisis */}
            <ellipse
              cx={cx + w / 2 + 6}
              cy={v.y + v.h / 2}
              rx={6}
              ry={v.h / 3}
              fill={color}
              fillOpacity={isHovered ? 0.85 : 0.65}
            />
            {/* Etiqueta */}
            {showLabels && (
              <g>
                <line
                  x1={cx + w / 2 + 14}
                  y1={v.y + v.h / 2}
                  x2={cx + w / 2 + 30}
                  y2={v.y + v.h / 2}
                  stroke={color}
                  strokeWidth={0.8}
                  opacity={0.6}
                />
                <text
                  x={cx + w / 2 + 34}
                  y={v.y + v.h / 2 + 3}
                  fontSize="10"
                  fontFamily="'Roboto Mono', monospace"
                  fill={color}
                  fillOpacity={isHovered ? 1 : 0.85}
                  fontWeight={isHovered ? 700 : 500}
                >
                  {v.label}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}

window.VERTEBRAE = VERTEBRAE;
window.spineCenterX = spineCenterX;
window.XrayImage = XrayImage;
window.SegmentationMask = SegmentationMask;
