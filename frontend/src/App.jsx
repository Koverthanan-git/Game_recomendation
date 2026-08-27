import { useState } from 'react';
import ConfigForm from './components/ConfigForm';
import ResultsDashboard from './components/ResultsDashboard';
import { predictFPS } from './api';
import './App.css';

export default function App() {
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  async function handlePredict(config) {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await predictFPS(config);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Prediction failed. Is the Django server running on :8000?');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-layout">

      {/* ══ LEFT SIDEBAR ══════════════════════════════════════════ */}
      <aside className="sidebar">

        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-mark">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <polygon points="11,1 21,6 21,16 11,21 1,16 1,6" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <text x="11" y="15" textAnchor="middle" fontSize="10" fontWeight="700" fill="currentColor" fontFamily="sans-serif">F</text>
            </svg>
          </div>
          <div>
            <div className="logo-name">FPS Oracle</div>
            <div className="logo-sub">Hardware Performance Engine</div>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* Section label */}
        <div className="sidebar-section-label">
          <span className="section-dot" />
          Rig Configuration
        </div>

        {/* Config form fills the rest of the sidebar */}
        <div className="sidebar-form-wrap">
          <ConfigForm onSubmit={handlePredict} loading={loading} />
        </div>

        {/* Sidebar footer */}
        <div className="sidebar-footer">
          <span>v1.0 · CatBoost · 2,996 trees</span>
        </div>
      </aside>

      {/* ══ MAIN CONTENT ═════════════════════════════════════════ */}
      <main className="main-panel">

        {/* Top bar */}
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-title">Performance Dashboard</span>
            <span className="topbar-pipe">|</span>
            <span className="topbar-sub">AI-powered FPS prediction & bottleneck analysis</span>
          </div>
          <div className="topbar-right">
            <div className={`status-dot ${loading ? 'status-dot--busy' : result ? 'status-dot--ok' : 'status-dot--idle'}`} />
            <span className="status-text">
              {loading ? 'Running inference…' : result ? 'Prediction ready' : 'Awaiting input'}
            </span>
          </div>
        </header>

        {/* Content area */}
        <div className="content-area">

          {/* Empty state */}
          {!result && !loading && !error && (
            <div className="empty-panel">
              <div className="empty-grid">
                {/* Placeholder metric cards */}
                {['FPS', 'Bottleneck', 'B-Ratio', 'Resolution'].map((label) => (
                  <div key={label} className="empty-card">
                    <span className="empty-card-label">{label}</span>
                    <div className="empty-card-value">—</div>
                  </div>
                ))}
              </div>
              <div className="empty-cta">
                <div className="empty-icon">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="22" stroke="var(--border-hi)" strokeWidth="1.5" strokeDasharray="4 3"/>
                    <path d="M24 14v10l6 6" stroke="var(--orange)" strokeWidth="2" strokeLinecap="round"/>
                    <circle cx="24" cy="24" r="3" fill="var(--orange)"/>
                  </svg>
                </div>
                <p className="empty-headline">Configure your rig on the left</p>
                <p className="empty-body">Select your CPU, GPU, game, resolution and quality preset,<br/>then click <strong style={{color:'var(--orange)'}}>Predict FPS</strong> to run the AI model.</p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="error-panel">
              <div className="error-icon">!</div>
              <div>
                <p className="error-title">Prediction Error</p>
                <p className="error-body">{error}</p>
              </div>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="loading-panel">
              <div className="loading-rings">
                <div className="ring ring-1" />
                <div className="ring ring-2" />
                <div className="ring ring-3" />
                <div className="ring-core">
                  <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
                    <polygon points="11,1 21,6 21,16 11,21 1,16 1,6" fill="none" stroke="var(--orange)" strokeWidth="1.5"/>
                  </svg>
                </div>
              </div>
              <p className="loading-text">Running inference across 2,996 decision trees</p>
              <p className="loading-sub">CatBoostRegressor · PostgreSQL · IGDB enrichment</p>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <ResultsDashboard result={result} />
          )}

        </div>
      </main>
    </div>
  );
}
