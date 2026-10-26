import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")


def _setting(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


DATABASE_URL = _setting(
    "PRAMAAN_DATABASE_URL",
    f"sqlite:///{(BACKEND_DIR / 'pramaan.db').as_posix()}",
)
STORAGE_DIR = Path(
    _setting("PRAMAAN_STORAGE_DIR", str(BACKEND_DIR / "storage"))
).resolve()
MAX_UPLOAD_BYTES = int(_setting("PRAMAAN_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in _setting("PRAMAAN_FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
TOKEN_SECRET = _setting("PRAMAAN_TOKEN_SECRET", "local-mvp-secret-change-before-deployment")
TOKEN_TTL_SECONDS = int(_setting("PRAMAAN_TOKEN_TTL_SECONDS", str(8 * 60 * 60)))
_configured_tesseract = _setting("PRAMAAN_TESSERACT_CMD", "")
_windows_tesseract = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
TESSERACT_CMD = (
    _configured_tesseract
    or shutil.which("tesseract")
    or (str(_windows_tesseract) if _windows_tesseract.is_file() else "")
)
ADMIN_USERNAME = _setting("PRAMAAN_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = _setting(
    "PRAMAAN_ADMIN_PASSWORD_HASH",
    "pbkdf2_sha256$260000$gOzHY8UA9nhT6UL1LxM7wQ$FcGaotGefLdg4JMOl5GiHSAF4kXYqQesDNqYX-4aadc",
)
REVIEWER_USERNAME = _setting("PRAMAAN_REVIEWER_USERNAME", "reviewer")
REVIEWER_PASSWORD_HASH = _setting(
    "PRAMAAN_REVIEWER_PASSWORD_HASH",
    "pbkdf2_sha256$260000$ORPTdUUFPmq5N8wyIz1QKA$C37q2feXpvwZLdsect1s95blD00_3-0UdK4TzKz-54s",
)
RULES_PATH = Path(_setting("PRAMAAN_RULES_PATH", str(BACKEND_DIR / "app" / "rules" / "validation_rules.json")))
ISSUER_DATA_PATH = Path(
    _setting("PRAMAAN_ISSUER_DATA_PATH", str(BACKEND_DIR / "app" / "rules" / "synthetic_issuers.json"))
)

if MAX_UPLOAD_BYTES < 1:
    raise ValueError("PRAMAAN_MAX_UPLOAD_BYTES must be positive")
if TOKEN_TTL_SECONDS < 1:
    raise ValueError("PRAMAAN_TOKEN_TTL_SECONDS must be positive")
