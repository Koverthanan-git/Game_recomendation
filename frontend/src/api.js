/**
 * api.js — thin wrapper around the Django REST endpoints.
 * All calls go through Vite's /api proxy → Django :8000
 */

const BASE = '/api';

/**
 * GET /api/hardware/all
 * Returns { cpus: [...], gpus: [...] } — full preload list.
 * The frontend caches this and filters locally (instant country-selector UX).
 */
export async function fetchAllHardware() {
  const res = await fetch(`${BASE}/hardware/all`);
  if (!res.ok) throw new Error('Failed to load hardware list');
  return res.json(); // { cpus: [...], gpus: [...], cpu_count, gpu_count }
}

/**
 * GET /api/hardware/search?q=<query>
 * Fallback DB search (used only if the preload fails).
 */
export async function searchHardware(query) {
  if (!query || query.trim().length < 2) return [];
  const res = await fetch(`${BASE}/hardware/search?q=${encodeURIComponent(query.trim())}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results ?? [];
}

/** POST /api/predict/fps */
export async function predictFPS({ cpuName, gpuName, gameName, resolution, setting }) {
  const res = await fetch(`${BASE}/predict/fps`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cpu_name:   cpuName,
      gpu_name:   gpuName,
      game_name:  gameName,
      resolution,
      setting,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? 'Prediction failed');
  return data;
}
