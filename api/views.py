"""
api/views.py
────────────
REST API views:

  GET  /api/hardware/all
       Returns all distinct CPU and GPU names for client-side preloading.
       One-time fetch; frontend filters locally (country-selector pattern).

  GET  /api/hardware/search?q=<query>
       Autocomplete CPU/GPU name search from PostgreSQL (fallback).

  POST /api/predict/fps
       Predicts FPS for a CPU+GPU+Game+Resolution+Setting combination
       using the CatBoost model, and returns bottleneck analysis.
"""

import logging

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from api.serializers import FPSPredictRequestSerializer
from api.db import search_hardware, get_hardware_row, get_game_genres, get_all_hardware
from services.predictor import predict_fps
from services.bottleneck import detect_bottleneck

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  GET /api/hardware/all  — full list for client-side filtering
# ══════════════════════════════════════════════════════

class HardwareAllView(APIView):
    """
    Returns ALL distinct CPU and GPU names in one shot.
    The frontend loads this once on startup and filters locally
    as the user types — instant, zero-lag country-selector UX.

    Response
    --------
    200 OK:
    {
        "cpus": ["amd athlon 200ge", "amd ryzen 5 1600x", ...],
        "gpus": ["amd radeon pro vega 64", "nvidia geforce gtx 1050", ...],
        "cpu_count": 142,
        "gpu_count": 87
    }
    """

    # In-memory cache so the DB is only hit once per server process
    _cache: dict | None = None

    def get(self, request: Request) -> Response:
        if HardwareAllView._cache is None:
            try:
                data = get_all_hardware()
                HardwareAllView._cache = {
                    "cpus":      data["cpus"],
                    "gpus":      data["gpus"],
                    "cpu_count": len(data["cpus"]),
                    "gpu_count": len(data["gpus"]),
                }
                log.info(
                    "HardwareAllView: cached %d CPUs + %d GPUs",
                    len(data["cpus"]), len(data["gpus"]),
                )
            except Exception as exc:
                log.error("HardwareAllView DB error: %s", exc)
                return Response(
                    {"error": "Could not load hardware list from database."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(HardwareAllView._cache)


# ══════════════════════════════════════════════════════
#  GET /api/hardware/search?q=<query>  — fallback search
# ══════════════════════════════════════════════════════

class HardwareSearchView(APIView):
    """
    Autocomplete endpoint for CPU and GPU name lookups.

    Query Parameters
    ----------------
    q : str  (required) — search term (min 2 chars recommended)

    Response
    --------
    200 OK:
    {
        "query": "rtx 2080",
        "results": [
            {"type": "gpu", "name": "nvidia geforce rtx 2080"},
            {"type": "gpu", "name": "nvidia geforce rtx 2080 ti"},
            ...
        ]
    }

    400 Bad Request: if 'q' is missing or empty.
    """

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"error": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(query) < 2:
            return Response(
                {"error": "Query must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            results = search_hardware(query, limit=15)
        except Exception as exc:
            log.error("Hardware search DB error: %s", exc)
            return Response(
                {"error": "Database error during search."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"query": query, "count": len(results), "results": results})


# ══════════════════════════════════════════════════════
#  POST /api/predict/fps
# ══════════════════════════════════════════════════════

class FPSPredictView(APIView):
    """
    FPS prediction endpoint.

    Request Body (JSON)
    -------------------
    {
        "cpu_name":   "intel core i9-9900k",
        "gpu_name":   "nvidia geforce rtx 2080 ti",
        "game_name":  "Fortnite",
        "resolution": "1080p",
        "setting":    "ultra"
    }

    Response
    --------
    200 OK:
    {
        "cpu_name":           "intel core i9-9900k",
        "gpu_name":           "nvidia geforce rtx 2080 ti",
        "game_name":          "Fortnite",
        "resolution":         "1080p",
        "setting":            "ultra",
        "predicted_fps":      182.4,
        "bottleneck_ratio":   0.91,
        "bottleneck_pct":     9.0,
        "bottleneck_status":  "Balanced",
        "upgrade_suggestion": "Your CPU and GPU are well-matched ..."
    }

    Errors
    ------
    400 — validation failure or hardware combo not found in DB
    503 — model load failure
    500 — inference error
    """

    def post(self, request: Request) -> Response:
        # 1. Validate request payload
        serializer = FPSPredictRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data       = serializer.validated_data
        cpu_name   = data["cpu_name"].lower().strip()
        gpu_name   = data["gpu_name"].lower().strip()
        game_name  = data["game_name"].strip()
        resolution = data["resolution"]
        setting    = data["setting"]

        # 2. Look up hardware specs from PostgreSQL
        hw_row = get_hardware_row(cpu_name, gpu_name)
        if hw_row is None:
            return Response(
                {
                    "error": (
                        f"Hardware combination not found in database: "
                        f"CPU='{cpu_name}' + GPU='{gpu_name}'. "
                        f"Use GET /api/hardware/search?q=<name> to find valid names."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Fetch game genre metadata (for the model's igdb_genres feature)
        igdb_genres = get_game_genres(game_name)
        hw_row["igdb_genres"] = igdb_genres

        # 4. Run CatBoost inference
        try:
            predicted_fps = predict_fps(
                hardware_row=hw_row,
                game_name=game_name,
                resolution=resolution,
                setting=setting,
            )
        except FileNotFoundError as exc:
            log.error("Model file missing: %s", exc)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            log.exception("CatBoost inference error")
            return Response(
                {"error": f"Prediction failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 5. Bottleneck analysis
        bn = detect_bottleneck(hw_row, resolution)

        log.info(
            "Prediction | CPU=%s GPU=%s Game=%s Res=%s Setting=%s → %.1f FPS [%s]",
            cpu_name, gpu_name, game_name, resolution, setting,
            predicted_fps, bn.status,
        )

        return Response({
            "cpu_name":           cpu_name,
            "gpu_name":           gpu_name,
            "game_name":          game_name,
            "resolution":         resolution,
            "setting":            setting,
            "predicted_fps":      predicted_fps,
            "bottleneck_ratio":   bn.ratio,
            "bottleneck_pct":     bn.percentage,
            "bottleneck_status":  bn.status,
            "upgrade_suggestion": bn.suggestion,
        })
