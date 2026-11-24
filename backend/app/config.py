import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # the backend/ folder
load_dotenv(BASE_DIR / ".env")


def _path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    DATABASE_PATH = _path(os.getenv("DATABASE_PATH"), BASE_DIR / "instance" / "resaleiq.db")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_PATH.as_posix()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = str(_path(os.getenv("UPLOAD_FOLDER"), BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # whole request
    MAX_IMAGE_BYTES = 8 * 1024 * 1024  # each photo
    MAX_IMAGES = 6

    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "168"))

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@resaleiq.local").strip().lower()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    AI_ESTIMATES_PER_HOUR = int(os.getenv("AI_ESTIMATES_PER_HOUR", "30"))

    # Without an email service the reset link is returned by the API in development
    # so the "forgot password" flow can be demonstrated. Never enable in production.
    EXPOSE_RESET_LINK = _bool("EXPOSE_RESET_LINK", APP_ENV != "production")
