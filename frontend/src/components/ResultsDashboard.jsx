import { useEffect, useRef } from 'react';

/* ── FPS Arc Gauge (canvas) ─────────────────────────────────── */
function FPSGauge({ fps, maxFps = 350 }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const ctx = c.getContext('2d');
    const W = c.width, H = c.height, cx = W / 2, cy = H * 0.56, r = W * 0.38;
    const ratio = Math.min(fps / maxFps, 1);
    const startA = Math.PI * 0.8, sweep = Math.PI * 1.4;
    const endA = startA + sweep * ratio;

    const color = fps >= 144 ? '#22c55e' : fps >= 60 ? '#f97316' : fps >= 30 ? '#eab308' : '#ef4444';

    ctx.clearRect(0, 0, W, H);

    // Track
    ctx.beginPath(); ctx.arc(cx, cy, r, startA, startA + sweep);
    ctx.strokeStyle = '#1a1a28'; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.stroke();

    // Fill arc
    if (ratio > 0) {
      const grad = ctx.createConicalGradient ? null : null;
      ctx.save();
      ctx.shadowColor = color; ctx.shadowBlur = 18;
      ctx.beginPath(); ctx.arc(cx, cy, r, startA, endA);
      ctx.strokeStyle = color; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.stroke();
      ctx.restore();
    }

    // Tick marks
    for (let i = 0; i <= 10; i++) {
      const a = startA + (sweep * i) / 10;
      const inner = r - 14, outer = r - 7;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * inner, cy + Math.sin(a) * inner);
      ctx.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer);
      ctx.strokeStyle = i === 0 || i === 10 ? '#4a4a6a' : '#252535';
      ctx.lineWidth = i % 5 === 0 ? 1.5 : 1; ctx.stroke();
    }

    // Center number
    ctx.fillStyle = '#f1f1f8';
    ctx.font = `700 ${W * 0.22}px 'Rajdhani', sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(Math.round(fps), cx, cy + 2);

    // Unit
    ctx.fillStyle = '#4a4a6a';
    ctx.font = `600 ${W * 0.08}px 'Inter', sans-serif`;
    ctx.fillText('FPS', cx, cy + W * 0.16);
  }, [fps, maxFps]);

  return <canvas ref={ref} width={180} height={140} className="fps-gauge-canvas" aria-label={`${Math.round(fps)} FPS`} />;
}

/* ── Bottleneck Track ───────────────────────────────────────── */
function BottleneckTrack({ ratio, status }) {
  // Map ratio to 0–100 position. Balanced = 50% (ratio=1.0)
  const pct = Math.max(0, Math.min(100, (ratio / 2) * 100));
  const color =
    status === 'CPU Bottleneck' ? 'var(--red)' :
    status === 'GPU Bottleneck' ? 'var(--yellow)' :
    'var(--green)';
  const fillLeft  = ratio < 1 ? `${pct}%`      : '50%';
  const fillWidth = `${Math.abs(pct - 50)}%`;

  return (
    <div className="bn-track-wrap">
      <div className="bn-track">
        <div className="bn-track-gradient" />
        <div className="bn-track-fill"
          style={{ left: fillLeft, width: fillWidth, background: color, opacity: .7 }} />
        <div className="bn-needle"
          style={{ left: `${pct}%`, borderColor: color, boxShadow: `0 0 8px ${color}` }} />
      </div>
      <div className="bn-track-labels">
        <span style={{ color: 'var(--red)' }}>CPU Limited</span>
        <span style={{ color: 'var(--green)' }}>Balanced</span>
        <span style={{ color: 'var(--yellow)' }}>GPU Limited</span>
      </div>
    </div>
  );
}

/* ── Main Dashboard ─────────────────────────────────────────── */
export default function ResultsDashboard({ result }) {
  const {
    predicted_fps, bottleneck_ratio, bottleneck_pct, bottleneck_status,
    upgrade_suggestion, cpu_name, gpu_name, game_name, resolution, setting,
  } = result;

  const fps = Math.round(predicted_fps);
  const grade =
    fps >= 144 ? { label: '144+ Excellent', cls: 'fps-grade--excellent' } :
    fps >= 60  ? { label: '60+ Playable',   cls: 'fps-grade--great' }     :
    fps >= 30  ? { label: '30+ Moderate',   cls: 'fps-grade--ok' }        :
               { label: 'Below 30 — Low',   cls: 'fps-grade--low' };

  const bnColor =
    bottleneck_status === 'CPU Bottleneck' ? 'var(--red)' :
    bottleneck_status === 'GPU Bottleneck' ? 'var(--yellow)' :
    'var(--green)';

  const bnIcon =
    bottleneck_status === 'CPU Bottleneck' ? '⚠' :
    bottleneck_status === 'GPU Bottleneck' ? '⚠' : '✓';

  return (
    <div className="dashboard">

      {/* Config breadcrumb */}
      <div className="dash-config-strip">
        <span className="config-tag config-tag--cpu">{cpu_name}</span>
        <span className="config-sep">+</span>
        <span className="config-tag config-tag--gpu">{gpu_name}</span>
        <span className="config-sep">·</span>
        <span className="config-tag">{game_name}</span>
        <span className="config-sep">·</span>
        <span className="config-tag">{resolution.toUpperCase()}</span>
        <span className="config-tag">{setting}</span>
      </div>

      {/* Top metrics row */}
      <div className="metrics-row">

        {/* FPS Hero */}
        <div className="fps-hero-card">
          <div className="fps-card-label">Predicted Output</div>
          <FPSGauge fps={predicted_fps} />
          <div className={`fps-grade ${grade.cls}`}>{grade.label}</div>
        </div>

        {/* Bottleneck % */}
        <div className="metric-card">
          <div className="metric-card-label">Bottleneck</div>
          <div className="metric-card-value" style={{ color: bnColor }}>{bottleneck_pct}%</div>
          <div className="metric-card-sub">off-balance from neutral</div>
          <div className="metric-card-bar">
            <div className="metric-card-bar-fill" style={{ width: `${Math.min(bottleneck_pct, 100)}%`, background: bnColor }} />
          </div>
        </div>

        {/* B-Ratio */}
        <div className="metric-card">
          <div className="metric-card-label">Balance Ratio</div>
          <div className="metric-card-value">{bottleneck_ratio.toFixed(3)}</div>
          <div className="metric-card-sub">ideal = 1.000</div>
          <div className="metric-card-bar">
            <div className="metric-card-bar-fill"
              style={{ width: `${Math.min(bottleneck_ratio * 50, 100)}%`, background: 'var(--purple)' }} />
          </div>
        </div>

        {/* Resolution */}
        <div className="metric-card">
          <div className="metric-card-label">Config</div>
          <div className="metric-card-value" style={{ fontSize: '1.2rem', fontFamily: 'JetBrains Mono, monospace' }}>
            {resolution.toUpperCase()}
          </div>
          <div className="metric-card-sub">{setting} quality preset</div>
          <div className="metric-card-bar" style={{ marginTop: 'auto' }}>
            <div className="metric-card-bar-fill"
              style={{
                width: resolution === '4k' ? '100%' : resolution === '1440p' ? '65%' : '35%',
                background: 'var(--orange)',
              }} />
          </div>
        </div>
      </div>

      {/* Bottleneck card */}
      <div className="bottleneck-card">
        <div className="bn-card-header">
          <span className="bn-card-title">Hardware Bottleneck Analysis</span>
          <span className="bn-status-pill"
            style={{ color: bnColor, borderColor: bnColor, background: `color-mix(in srgb, ${bnColor} 12%, transparent)` }}>
            {bottleneck_status}
          </span>
        </div>

        <BottleneckTrack ratio={bottleneck_ratio} status={bottleneck_status} />

        <div className="bn-suggestion" style={{ borderColor: `color-mix(in srgb, ${bnColor} 25%, var(--border-med))` }}>
          <div className="bn-suggestion-icon"
            style={{ background: `color-mix(in srgb, ${bnColor} 15%, transparent)`, color: bnColor }}>
            {bnIcon}
          </div>
          <div>
            <div className="bn-suggestion-title" style={{ color: bnColor }}>Upgrade Recommendation</div>
            <div className="bn-suggestion-body">{upgrade_suggestion}</div>
          </div>
        </div>
      </div>

      {/* Spec breakdown cards */}
      <div className="specs-row">
        {/* CPU specs */}
        <div className="spec-card">
          <div className="spec-card-header">
            <div className="spec-card-icon"
              style={{ background: 'var(--purple-glow)', color: 'var(--purple)', border: '1px solid var(--purple)' }}>
              ⚙
            </div>
            <span className="spec-card-title">CPU</span>
            <span className="spec-card-name">{cpu_name}</span>
          </div>
          <table className="spec-table">
            <tbody>
              <tr><td>Architecture</td><td>x86-64</td></tr>
              <tr><td>Role</td><td>Game logic · AI · Physics</td></tr>
              <tr><td>Bottleneck impact</td><td style={{ color: bottleneck_status === 'CPU Bottleneck' ? 'var(--red)' : 'var(--green)' }}>
                {bottleneck_status === 'CPU Bottleneck' ? '⚠ Limiting factor' : '✓ Not limiting'}
              </td></tr>
              <tr><td>B-Ratio contribution</td><td>{bottleneck_ratio.toFixed(3)} × W<sub>res</sub></td></tr>
            </tbody>
          </table>
        </div>

        {/* GPU specs */}
        <div className="spec-card">
          <div className="spec-card-header">
            <div className="spec-card-icon"
              style={{ background: 'var(--orange-glow)', color: 'var(--orange)', border: '1px solid var(--orange-dim)' }}>
              ▣
            </div>
            <span className="spec-card-title">GPU</span>
            <span className="spec-card-name">{gpu_name}</span>
          </div>
          <table className="spec-table">
            <tbody>
              <tr><td>Target</td><td>{resolution.toUpperCase()} · {setting} preset</td></tr>
              <tr><td>Resolution weight</td>
                <td>{resolution === '4k' ? '1.7' : resolution === '1440p' ? '1.3' : '1.0'}× load</td></tr>
              <tr><td>Bottleneck impact</td>
                <td style={{ color: bottleneck_status === 'GPU Bottleneck' ? 'var(--yellow)' : 'var(--green)' }}>
                  {bottleneck_status === 'GPU Bottleneck' ? '⚠ Limiting factor' : '✓ Not limiting'}
                </td></tr>
              <tr><td>Predicted FPS</td>
                <td style={{ color: 'var(--orange)', fontWeight: 700 }}>{fps} FPS</td></tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
