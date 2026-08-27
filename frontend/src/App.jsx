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
      setError(err.message || 'Prediction failed. Is the Django server running?');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">

      {/* ── Hero Header ───────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">⚡</span>
            <span className="logo-text">
              <span className="logo-brand">FPS</span>
              <span className="logo-sub">Oracle</span>
            </span>
          </div>
          <p className="header-tagline">
            AI-powered gaming performance prediction &amp; hardware bottleneck analysis
          </p>
        </div>
        <div className="header-glow" aria-hidden />
      </header>

      <main className="app-main">

        {/* ── Config Panel ──────────────────────────────────────── */}
        <section className="panel config-panel">
          <div className="panel-header">
            <h1 className="panel-title">
              <span className="panel-title-icon">🖥️</span>
              Configure Your Rig
            </h1>
            <p className="panel-subtitle">
              Type your CPU and GPU names to search the database, then select your game and target settings.
            </p>
          </div>
          <ConfigForm onSubmit={handlePredict} loading={loading} />
        </section>

        {/* ── Error ─────────────────────────────────────────────── */}
        {error && (
          <div className="error-banner" role="alert">
            <span className="error-icon">⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────── */}
        {loading && (
          <div className="loading-panel" aria-live="polite">
            <div className="loading-orbs">
              <span /><span /><span />
            </div>
            <p>Running inference across 2,996 decision trees…</p>
          </div>
        )}

        {result && !loading && (
          <section className="panel results-panel">
            <ResultsDashboard result={result} />
          </section>
        )}

        {/* ── Empty state ───────────────────────────────────────── */}
        {!result && !loading && !error && (
          <div className="empty-state">
            <div className="empty-icon">🎮</div>
            <p className="empty-title">Ready to Predict</p>
            <p className="empty-sub">
              Select your CPU, GPU, and game above, then hit <strong>Predict FPS</strong>.
            </p>
          </div>
        )}

      </main>

      <footer className="app-footer">
        <p>Hardware Recommendation Engine · Semester 5 Deep Learning Project</p>
      </footer>
    </div>
  );
}
