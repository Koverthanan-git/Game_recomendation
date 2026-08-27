"""
hardware_api Django project — settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-hardware-rec-engine-dev-key-change-in-prod")

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "hardware_api.urls"

WSGI_APPLICATION = "hardware_api.wsgi.application"

# PostgreSQL — credentials from .env
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     os.getenv("DB_NAME", "postgres"),
        "USER":     os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST":     os.getenv("DB_HOST", "localhost"),
        "PORT":     os.getenv("DB_PORT", "5432"),
    }
}

# CatBoost model path
CATBOOST_MODEL_PATH = str(BASE_DIR / "catboost_fps_model.cbm")

# DRF
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES":     ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES":        ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],   # no auth needed for this API
    "DEFAULT_PERMISSION_CLASSES":     [],   # no permissions required
}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
