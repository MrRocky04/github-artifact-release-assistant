"""Application configuration."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_SOURCE_BRANCH = "main"

# Absolute paths so the app behaves the same no matter where it is started from.
APP_DATA_DIR = BASE_DIR / ".artifact-assistant"
REPOSITORY_WORKSPACE = str(APP_DATA_DIR / "repositories")
UPLOAD_DIR = APP_DATA_DIR / "uploads"
QUESTIONS_FILE = BASE_DIR / "questions_config.json"

# Web UI
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

# Only this artifact type is accepted.
ALLOWED_EXTENSION = ".aar"
