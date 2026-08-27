from django.urls import path
from api.views import HardwareSearchView, FPSPredictView, HardwareAllView

urlpatterns = [
    # GET /api/hardware/all   — full preload list for client-side filtering
    path("hardware/all",    HardwareAllView.as_view(),    name="hardware-all"),

    # GET /api/hardware/search?q=<query>  — fallback DB search
    path("hardware/search", HardwareSearchView.as_view(), name="hardware-search"),

    # POST /api/predict/fps
    path("predict/fps",     FPSPredictView.as_view(),     name="predict-fps"),
]
