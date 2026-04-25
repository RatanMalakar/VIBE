"""
config.py — Centralized path & environment configuration for VIBE backend.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from /backend)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# ── Directory Paths ──────────────────────────────────────────
DATA_DIR = _ROOT / "data"
FRONTEND_DIR = _ROOT / "frontend"
LOG_FILE = _ROOT / "app.log"
SCRAPER_DIR = _ROOT / "scraper"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Database (optional, future use) ─────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "vibe_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

# ── App Settings ─────────────────────────────────────────────
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", 15))
ALLOWED_COMPANY_RE = r"^[a-zA-Z0-9 \-\.&]{1,60}$"  # Whitelist for safety
