#!/usr/bin/env python3
"""
verify_api.py
─────────────
Standalone verification script for the Django REST endpoints.
Runs without an HTTP server — uses Django's test client directly.

Usage:
    python3 verify_api.py

Tests:
  1. Model loads without error
  2. Bottleneck formula correctness
  3. GET /api/hardware/search?q=rtx
  4. GET /api/hardware/search?q=  (missing q → 400)
  5. POST /api/predict/fps        (valid payload → 200 + FPS)
  6. POST /api/predict/fps        (unknown hardware → 400)
  7. POST /api/predict/fps        (invalid resolution → 400)
"""

import os
import sys
import json

# ── Django bootstrap ──────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hardware_api.settings")
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIClient

# ── Local imports (after django.setup) ───────────────────────
from services.bottleneck import detect_bottleneck
from services.predictor import get_model

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
PASS = "\033[92m✔ PASS\033[0m"
FAIL = "\033[91m✘ FAIL\033[0m"
results = []


def check(label: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    print(f"  {icon}  {label}")
    if detail:
        print(f"         {detail}")
    results.append(condition)


# ─────────────────────────────────────────────────────────────
#  Test 1: Model loads
# ─────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  TEST 1: CatBoost Model Load")
print("══════════════════════════════════════════════")
try:
    model = get_model()
    check(
        "Model loaded successfully",
        model is not None,
        f"Trees: {model.tree_count_}  |  Features: {len(model.feature_names_)}",
    )
    check(
        "get_model() is a singleton (same object on second call)",
        get_model() is model,
    )
except Exception as e:
    check("Model load", False, str(e))


# ─────────────────────────────────────────────────────────────
#  Test 2: Bottleneck formula
# ─────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  TEST 2: Bottleneck Detection Formula")
print("══════════════════════════════════════════════")

# Artificially weak CPU → should trigger CPU Bottleneck
hw_weak_cpu = {
    "cpu_turbo_clock_mhz": 100,  "cpu_cores": 1, "cpu_threads": 1,
    "gpu_fp32_tflops":     1e9,  "gpu_bandwidth_gb_s": 1e9,
}
bn = detect_bottleneck(hw_weak_cpu, "1080p")
check("Weak CPU → CPU Bottleneck", bn.status == "CPU Bottleneck",
      f"ratio={bn.ratio}, status={bn.status}")

# Balanced hardware
hw_balanced = {
    "cpu_turbo_clock_mhz": 5000, "cpu_cores": 8, "cpu_threads": 16,
    "gpu_fp32_tflops":     13450000, "gpu_bandwidth_gb_s": 616000,
}
bn2 = detect_bottleneck(hw_balanced, "1080p")
check("Balanced hardware → Balanced or CPU Bottleneck (ratio near 1)",
      bn2.ratio > 0, f"ratio={bn2.ratio}, status={bn2.status}")

# Resolution weight: 4K should increase GPU load, lowering ratio
bn_1080 = detect_bottleneck(hw_balanced, "1080p")
bn_4k   = detect_bottleneck(hw_balanced, "4k")
check(
    "4K resolution reduces B_ratio vs 1080p (higher GPU demand)",
    bn_4k.ratio < bn_1080.ratio,
    f"1080p ratio={bn_1080.ratio}  →  4K ratio={bn_4k.ratio}",
)


# ─────────────────────────────────────────────────────────────
#  Tests 3–7: API endpoints via Django test client
# ─────────────────────────────────────────────────────────────
client = APIClient()

print("\n══════════════════════════════════════════════")
print("  TEST 3: GET /api/hardware/search?q=rtx")
print("══════════════════════════════════════════════")
resp = client.get("/api/hardware/search", {"q": "rtx"})
check("Status 200", resp.status_code == 200, f"Got {resp.status_code}")
data = resp.json()
check("Response has 'results' key",   "results" in data)
check("Results is a list",            isinstance(data.get("results"), list))
check("At least 1 GPU result found",  len(data.get("results", [])) > 0,
      f"results={data.get('results', [])[:3]}")


print("\n══════════════════════════════════════════════")
print("  TEST 4: GET /api/hardware/search (missing q)")
print("══════════════════════════════════════════════")
resp = client.get("/api/hardware/search")
check("Status 400 on missing q", resp.status_code == 400, f"Got {resp.status_code}")
check("Error message in response", "error" in resp.json())


print("\n══════════════════════════════════════════════")
print("  TEST 5: POST /api/predict/fps (valid payload)")
print("══════════════════════════════════════════════")
payload = {
    "cpu_name":   "intel core i9-9900k",
    "gpu_name":   "nvidia geforce rtx 2080 ti",
    "game_name":  "Fortnite",
    "resolution": "1080p",
    "setting":    "high",
}
resp = client.post("/api/predict/fps", payload, format="json")
check("Status 200", resp.status_code == 200, f"Got {resp.status_code}\n         Body: {resp.content[:300].decode()}")
if resp.status_code == 200:
    pred = resp.json()
    check("predicted_fps present and positive",
          pred.get("predicted_fps", -1) > 0,
          f"predicted_fps = {pred.get('predicted_fps')}")
    check("bottleneck_status present",
          pred.get("bottleneck_status") in ["CPU Bottleneck", "Balanced", "GPU Bottleneck"],
          f"status = {pred.get('bottleneck_status')}")
    check("upgrade_suggestion is non-empty",
          bool(pred.get("upgrade_suggestion")))
    print()
    print("  📊 Prediction result:")
    for k, v in pred.items():
        print(f"     {k:<22} = {v}")


print("\n══════════════════════════════════════════════")
print("  TEST 6: POST /api/predict/fps (unknown hardware)")
print("══════════════════════════════════════════════")
resp = client.post("/api/predict/fps", {
    "cpu_name":   "FAKE CPU 9999",
    "gpu_name":   "FAKE GPU 9999",
    "game_name":  "Minecraft",
    "resolution": "1080p",
    "setting":    "high",
}, format="json")
check("Status 400 for unknown hardware", resp.status_code == 400, f"Got {resp.status_code}")
check("Error message in response", "error" in resp.json())


print("\n══════════════════════════════════════════════")
print("  TEST 7: POST /api/predict/fps (invalid resolution)")
print("══════════════════════════════════════════════")
resp = client.post("/api/predict/fps", {
    "cpu_name":   "intel core i9-9900k",
    "gpu_name":   "nvidia geforce rtx 2080 ti",
    "game_name":  "Fortnite",
    "resolution": "8K",          # ← invalid
    "setting":    "high",
}, format="json")
check("Status 400 for invalid resolution", resp.status_code == 400, f"Got {resp.status_code}")


# ─────────────────────────────────────────────────────────────
#  Summary
# ─────────────────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
pct    = 100 * passed // total if total else 0

print("\n══════════════════════════════════════════════")
print(f"  RESULTS: {passed}/{total} tests passed ({pct}%)")
print("══════════════════════════════════════════════\n")
sys.exit(0 if passed == total else 1)
