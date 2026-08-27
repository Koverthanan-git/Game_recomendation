"""
services/predictor.py
─────────────────────
Loads the CatBoost FPS regression model ONCE at module import time.
All subsequent calls reuse the in-memory model (zero reload overhead).

Expected feature order matches clean_training_data.csv (26 features, target=fps):
  Categorical: cpu_name, gpu_name, gpu_architecture, gpu_memory_type,
               game_name, igdb_genres, resolution, setting
  Numerical  : cpu_cores, cpu_threads, cpu_base_clock_mhz,
               cpu_turbo_clock_mhz, cpu_tdp_watts, cpu_process_nm,
               cpu_cache_l3_kb, gpu_vram_gb, gpu_base_clock_mhz,
               gpu_boost_clock_mhz, gpu_memory_bus_bits, gpu_bandwidth_gb_s,
               gpu_shading_units, gpu_tmus, gpu_rops, gpu_fp32_tflops,
               gpu_process_nm, gpu_transistors_m
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from django.conf import settings

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  Feature schema — must match training column order exactly
# ─────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    # Numeric features
    "cpu_cores",
    "cpu_threads",
    "cpu_base_clock_mhz",
    "cpu_turbo_clock_mhz",
    "cpu_tdp_watts",
    "cpu_process_nm",
    "cpu_cache_l3_kb",
    "gpu_tmus",
    "gpu_rops",
    "gpu_fp32_tflops",
    "gpu_process_nm",
    "gpu_transistors_m",
    # Categorical features
    "cpu_name",
    "gpu_name",
    "gpu_architecture",
    "game_name",
    "igdb_genres",
    "resolution",
    "setting",
]

CATEGORICAL_FEATURES = [
    "cpu_name",
    "gpu_name",
    "gpu_architecture",
    "game_name",
    "igdb_genres",
    "resolution",
    "setting",
]

# ─────────────────────────────────────────────────────────────
#  Singleton model loader
# ─────────────────────────────────────────────────────────────
_model: CatBoostRegressor | None = None


def get_model() -> CatBoostRegressor:
    """Return the cached CatBoost model, loading it once on first call."""
    global _model
    if _model is None:
        model_path = Path(settings.CATBOOST_MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"CatBoost model not found at: {model_path}\n"
                f"Please place catboost_fps_model.cbm in the project root."
            )
        log.info("Loading CatBoost model from %s …", model_path)
        _model = CatBoostRegressor()
        _model.load_model(str(model_path))
        log.info(
            "Model loaded — %d trees, features: %s",
            _model.tree_count_,
            _model.feature_names_,
        )
    return _model


def predict_fps(hardware_row: dict, game_name: str, resolution: str, setting: str) -> float:
    """
    Run CatBoost inference and return predicted FPS.

    Parameters
    ----------
    hardware_row : dict
        Row from hardware_specs table (keys match FEATURE_NAMES).
    game_name    : str  — readable game name (e.g. 'Call Of Duty Ww2')
    resolution   : str  — '1080p' | '1440p' | '4k'
    setting      : str  — 'low' | 'med' | 'high' | 'ultra' | 'max'

    Returns
    -------
    float  — predicted FPS, clamped to [0, 999]
    """
    model = get_model()

    # Build single-row DataFrame matching model's exact 19-feature order
    row = {
        # ── Numeric ──────────────────────────────────────────
        "cpu_cores":           hardware_row.get("cpu_cores"),
        "cpu_threads":         hardware_row.get("cpu_threads"),
        "cpu_base_clock_mhz":  hardware_row.get("cpu_base_clock_mhz"),
        "cpu_turbo_clock_mhz": hardware_row.get("cpu_turbo_clock_mhz"),
        "cpu_tdp_watts":       hardware_row.get("cpu_tdp_watts"),
        "cpu_process_nm":      hardware_row.get("cpu_process_nm"),
        "cpu_cache_l3_kb":     hardware_row.get("cpu_cache_l3_kb"),
        "gpu_tmus":            hardware_row.get("gpu_tmus"),
        "gpu_rops":            hardware_row.get("gpu_rops"),
        "gpu_fp32_tflops":     hardware_row.get("gpu_fp32_tflops"),
        "gpu_process_nm":      hardware_row.get("gpu_process_nm"),
        "gpu_transistors_m":   hardware_row.get("gpu_transistors_m"),
        # ── Categorical ───────────────────────────────────────
        "cpu_name":            hardware_row.get("cpu_name", ""),
        "gpu_name":            hardware_row.get("gpu_name", ""),
        "gpu_architecture":    hardware_row.get("gpu_architecture", ""),
        "game_name":           game_name,
        "igdb_genres":         hardware_row.get("igdb_genres", ""),
        "resolution":          resolution.lower(),
        "setting":             setting.lower(),
    }

    df = pd.DataFrame([row], columns=FEATURE_NAMES)

    # Fill None in categorical columns with empty string (CatBoost requirement)
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].fillna("").astype(str)

    # Fill None in numeric columns with 0
    num_cols = [c for c in FEATURE_NAMES if c not in CATEGORICAL_FEATURES]
    df[num_cols] = df[num_cols].fillna(0).astype(float)

    cat_indices = [FEATURE_NAMES.index(c) for c in CATEGORICAL_FEATURES]
    raw = model.predict(df)
    fps = float(np.squeeze(raw))
    return round(max(0.0, min(fps, 999.0)), 2)
