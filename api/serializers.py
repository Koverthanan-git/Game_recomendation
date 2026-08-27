"""
api/serializers.py
──────────────────
DRF serializers for request validation and response formatting.
"""

from rest_framework import serializers


# ── Request Serializers ───────────────────────────────────────

class FPSPredictRequestSerializer(serializers.Serializer):
    """
    Validates the POST /api/predict/fps payload.
    All fields are required.
    """
    cpu_name   = serializers.CharField(max_length=200)
    gpu_name   = serializers.CharField(max_length=200)
    game_name  = serializers.CharField(max_length=200)
    resolution = serializers.ChoiceField(
        choices=["1080p", "1440p", "4k", "4K"],
        help_text="Screen resolution: 1080p | 1440p | 4k",
    )
    setting = serializers.ChoiceField(
        choices=["low", "med", "medium", "high", "ultra", "max"],
        help_text="Graphics quality setting",
    )

    def validate_resolution(self, value):
        return value.lower()

    def validate_setting(self, value):
        # Normalize 'medium' → 'med'
        return "med" if value == "medium" else value.lower()


# ── Response Serializers ──────────────────────────────────────

class HardwareSearchItemSerializer(serializers.Serializer):
    type = serializers.CharField()   # 'cpu' or 'gpu'
    name = serializers.CharField()


class FPSPredictResponseSerializer(serializers.Serializer):
    cpu_name           = serializers.CharField()
    gpu_name           = serializers.CharField()
    game_name          = serializers.CharField()
    resolution         = serializers.CharField()
    setting            = serializers.CharField()
    predicted_fps      = serializers.FloatField()
    bottleneck_ratio   = serializers.FloatField()
    bottleneck_pct     = serializers.FloatField()
    bottleneck_status  = serializers.CharField()
    upgrade_suggestion = serializers.CharField()
