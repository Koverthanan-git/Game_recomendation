import { useEffect, useRef } from 'react';

/**
 * FPSGauge — animated circular gauge for the FPS reading.
 * Draws on a canvas for a premium feel.
 */
function FPSGauge({ fps, maxFps = 300 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx    = canvas.getContext('2d');
    const w      = canvas.width;
    const h      = canvas.height;
    const cx     = w / 2;
    const cy     = h / 2;
    const r      = w * 0.42;
    const ratio  = Math.min(fps / maxFps, 1);
    const start  = Math.PI * 0.75;
    const end    = start + Math.PI * 1.5 * ratio;

    // Colour based on fps
    const color = fps >= 144
      ? '#10b981'
      : fps >= 60
      ? '#3b82f6'
      : fps >= 30
      ? '#f59e0b'
      : '#ef4444';

    ctx.clearRect(0, 0, w, h);

    // Track arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI * 0.75, Math.PI * 2.25);
    ctx.strokeStyle = '#1a2035';
    ctx.lineWidth   = 14;
    ctx.lineCap     = 'round';
    ctx.stroke();

    // Glow
    ctx.save();
    ctx.shadowColor = color;
    ctx.shadowBlur  = 24;

    // Value arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, start, end);
    ctx.strokeStyle = color;
    ctx.lineWidth   = 14;
    ctx.lineCap     = 'round';
    ctx.stroke();
    ctx.restore();

    // Center FPS number
    ctx.fillStyle = '#f1f5f9';
    ctx.font      = `bold ${w * 0.18}px 'Orbitron', sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(Math.round(fps), cx, cy - 8);

    // Unit label
    ctx.fillStyle = '#64748b';
    ctx.font      = `500 ${w * 0.08}px 'Inter', sans-serif`;
    ctx.fillText('FPS', cx, cy + w * 0.14);
  }, [fps, maxFps]);

  return (
    <canvas
      ref={canvasRef}
      width={220}
      height={220}
      className="fps-gauge"
      aria-label={`${Math.round(fps)} FPS`}
    />
  );
}

/* ── Bottleneck Bar ─────────────────────────────────────────── */
function BottleneckBar({ ratio, status }) {
  const pct = Math.min(ratio * 100, 200); // 100 = balanced point

  const color =
    status === 'CPU Bottleneck' ? '#ef4444' :
    status === 'GPU Bottleneck' ? '#f59e0b' :
    '#10b981';

  const label =
    status === 'CPU Bottleneck' ? '⬅ CPU Limited' :
    status === 'GPU Bottleneck' ? 'GPU Limited ➡' :
    '✓ Balanced';

  return (
    <div className="bn-bar-wrap">
      <div className="bn-bar-labels">
        <span style={{ color: '#ef4444' }}>CPU</span>
        <span className="bn-bar-status" style={{ color }}>
          {status}
        </span>
        <span style={{ color: '#f59e0b' }}>GPU</span>
      </div>
      <div className="bn-bar-track">
        <div
          className="bn-bar-center"
          aria-label="Balanced point"
        />
        <div
          className="bn-bar-fill"
          style={{
            left:    ratio < 1 ? `${(ratio / 2) * 100}%` : '50%',
            width:   `${Math.abs(ratio - 1) * 50}%`,
            background: color,
            boxShadow: `0 0 12px ${color}80`,
          }}
        />
        <div
          className="bn-bar-needle"
          style={{
            left: `${Math.min((ratio / 2) * 100, 100)}%`,
            borderColor: color,
            boxShadow: `0 0 8px ${color}`,
          }}
        />
      </div>
      <p className="bn-bar-legend">{label}</p>
    </div>
  );
}

/* ── Stat Pill ──────────────────────────────────────────────── */
function StatPill({ icon, label, value, sub }) {
  return (
    <div className="stat-pill">
      <span className="stat-icon">{icon}</span>
      <div>
        <p className="stat-label">{label}</p>
        <p className="stat-value">{value}</p>
        {sub && <p className="stat-sub">{sub}</p>}
      </div>
    </div>
  );
}

/* ── Main Dashboard ─────────────────────────────────────────── */
/**
 * ResultsDashboard
 * ────────────────
 * Props: result — full API response object from POST /api/predict/fps
 */
export default function ResultsDashboard({ result }) {
  const {
    predicted_fps,
    bottleneck_ratio,
    bottleneck_pct,
    bottleneck_status,
    upgrade_suggestion,
    cpu_name,
    gpu_name,
    game_name,
    resolution,
    setting,
  } = result;

  const fps = Math.round(predicted_fps);

  const fpsLabel =
    fps >= 144 ? { text: 'Excellent', cls: 'fps-label--green' } :
    fps >= 60  ? { text: 'Playable',  cls: 'fps-label--blue'  } :
    fps >= 30  ? { text: 'Moderate',  cls: 'fps-label--yellow' } :
               { text: 'Unplayable', cls: 'fps-label--red'    };

  const bnColor =
    bottleneck_status === 'CPU Bottleneck' ? '#ef4444' :
    bottleneck_status === 'GPU Bottleneck' ? '#f59e0b' :
    '#10b981';

  return (
    <section className="dashboard" aria-label="Prediction Results">

      {/* Header strip */}
      <div className="dash-header">
        <h2 className="dash-title">Performance Analysis</h2>
        <div className="dash-config">
          <span className="config-chip">{cpu_name}</span>
          <span className="config-sep">+</span>
          <span className="config-chip">{gpu_name}</span>
          <span className="config-sep">·</span>
          <span className="config-chip">{game_name}</span>
          <span className="config-sep">·</span>
          <span className="config-chip">{resolution} {setting}</span>
        </div>
      </div>

      {/* FPS + Bottleneck row */}
      <div className="dash-main">

        {/* Left — FPS gauge */}
        <div className="fps-panel">
          <FPSGauge fps={predicted_fps} maxFps={350} />
          <span className={`fps-label ${fpsLabel.cls}`}>{fpsLabel.text}</span>
        </div>

        {/* Right — Bottleneck + stats */}
        <div className="bn-panel">
          <div
            className="bn-status-badge"
            style={{ borderColor: bnColor, color: bnColor, background: `${bnColor}12` }}
          >
            {bottleneck_status === 'Balanced'       && '✓ '}
            {bottleneck_status === 'CPU Bottleneck' && '⚠ '}
            {bottleneck_status === 'GPU Bottleneck' && '⚠ '}
            {bottleneck_status}
          </div>

          <BottleneckBar ratio={bottleneck_ratio} status={bottleneck_status} />

          <div className="stats-row">
            <StatPill icon="📊" label="Bottleneck"  value={`${bottleneck_pct}%`} sub="off-balance" />
            <StatPill icon="⚙️"  label="B-Ratio"    value={bottleneck_ratio.toFixed(3)} sub="cpu/gpu×wRes" />
            <StatPill icon="🎮"  label="Resolution" value={resolution.toUpperCase()} />
          </div>
        </div>
      </div>

      {/* Upgrade Recommendation */}
      <div className="recommendation" style={{ borderColor: `${bnColor}44` }}>
        <div className="rec-icon" style={{ background: `${bnColor}20`, color: bnColor }}>
          {bottleneck_status === 'Balanced' ? '✓' : '↑'}
        </div>
        <div>
          <p className="rec-title" style={{ color: bnColor }}>Upgrade Recommendation</p>
          <p className="rec-text">{upgrade_suggestion}</p>
        </div>
      </div>

    </section>
  );
}
