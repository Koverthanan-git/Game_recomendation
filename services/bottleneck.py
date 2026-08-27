"""
services/bottleneck.py
──────────────────────
Implements the CPU/GPU bottleneck detection formula:

    B_ratio = P_cpu / (P_gpu × W_res)

where:
  P_cpu  — CPU compute proxy = cpu_turbo_clock_mhz × cpu_cores × cpu_threads
  P_gpu  — GPU compute proxy = gpu_fp32_tflops × gpu_bandwidth_gb_s
  W_res  — resolution weight:
              1080p → 1.0
              1440p → 1.3
              4k    → 1.7

Thresholds:
  B_ratio < 0.75   → CPU Bottleneck  (CPU can't keep up with GPU)
  0.75 ≤ B < 1.25  → Balanced        (well-matched hardware)
  B_ratio ≥ 1.25   → GPU Bottleneck  (GPU is the limiting factor)
"""

from dataclasses import dataclass

# Resolution weight lookup
RESOLUTION_WEIGHTS: dict[str, float] = {
    "1080p": 1.0,
    "1440p": 1.3,
    "4k":    1.7,
    "4K":    1.7,
}

# Bottleneck status labels
STATUS_CPU_BOTTLENECK = "CPU Bottleneck"
STATUS_BALANCED       = "Balanced"
STATUS_GPU_BOTTLENECK = "GPU Bottleneck"

# Upgrade suggestions per status
UPGRADE_SUGGESTIONS: dict[str, str] = {
    STATUS_CPU_BOTTLENECK: (
        "Your CPU is limiting GPU performance. "
        "Consider upgrading to a CPU with more cores and higher clock speed."
    ),
    STATUS_BALANCED: (
        "Your CPU and GPU are well-matched. "
        "No immediate upgrade needed — both components are utilized efficiently."
    ),
    STATUS_GPU_BOTTLENECK: (
        "Your GPU is the performance bottleneck. "
        "Upgrading to a higher-tier GPU will increase FPS at this resolution."
    ),
}


@dataclass
class BottleneckResult:
    ratio:       float   # raw B_ratio value
    percentage:  float   # |1 - B_ratio| expressed as a percentage (0–100)
    status:      str     # one of the STATUS_* constants
    suggestion:  str     # human-readable upgrade suggestion


def _cpu_performance(hw: dict) -> float:
    """
    CPU compute proxy (log-normalized).
    Uses log(turbo_clock × cores × threads) to avoid overflow.
    """
    import math
    clock   = float(hw.get("cpu_turbo_clock_mhz") or hw.get("cpu_base_clock_mhz") or 1.0)
    cores   = float(hw.get("cpu_cores")   or 1)
    threads = float(hw.get("cpu_threads") or 1)
    raw = clock * cores * threads
    return math.log1p(raw)   # log(1 + x) — always positive, never overflows


def _gpu_performance(hw: dict) -> float:
    """
    GPU compute proxy (log-normalized).
    Uses log(fp32_tflops × bandwidth) for scale parity with CPU proxy.
    """
    import math
    fp32      = float(hw.get("gpu_fp32_tflops")    or 1.0)
    bandwidth = float(hw.get("gpu_bandwidth_gb_s") or 1.0)
    raw = fp32 * bandwidth
    return math.log1p(raw)


def detect_bottleneck(hardware_row: dict, resolution: str) -> BottleneckResult:
    """
    Evaluate CPU/GPU bottleneck for a given hardware combination and resolution.

    Parameters
    ----------
    hardware_row : dict
        Row from hardware_specs table with cpu_* and gpu_* fields.
    resolution   : str
        One of '1080p', '1440p', '4k'.

    Returns
    -------
    BottleneckResult dataclass with ratio, percentage, status, suggestion.
    """
    w_res = RESOLUTION_WEIGHTS.get(resolution.lower(), RESOLUTION_WEIGHTS.get(resolution, 1.0))

    p_cpu = _cpu_performance(hardware_row)
    p_gpu = _gpu_performance(hardware_row)

    # Guard against division by zero
    denominator = p_gpu * w_res
    if denominator == 0:
        ratio = 1.0
    else:
        ratio = p_cpu / denominator

    # Classify
    if ratio < 0.75:
        status = STATUS_CPU_BOTTLENECK
    elif ratio <= 1.25:
        status = STATUS_BALANCED
    else:
        status = STATUS_GPU_BOTTLENECK

    # Bottleneck percentage: how far from perfect balance (ratio = 1.0)
    percentage = round(abs(1.0 - ratio) * 100, 1)
    # Cap at 100%
    percentage = min(percentage, 100.0)

    return BottleneckResult(
        ratio      = round(ratio, 4),
        percentage = percentage,
        status     = status,
        suggestion = UPGRADE_SUGGESTIONS[status],
    )
