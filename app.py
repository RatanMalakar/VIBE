"""
app.py — VIBE root launcher.
Run from the project root with:  python app.py

This file is the single entry-point. It sets up sys.path so that
backend/ and scraper/ modules resolve correctly, then starts Flask.
"""

import sys
import re
import logging
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd

# ── Absolute root of the project ────────────────────────────────────
ROOT = Path(__file__).resolve().parent

# Add backend + scraper to path so imports work regardless of CWD
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scraper"))

# ── Paths ────────────────────────────────────────────────────────────
DATA_DIR     = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"
LOG_FILE     = ROOT / "app.log"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_COMPANY_RE = r"^[a-zA-Z0-9 \-\.&]{1,60}$"

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Flask ────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── Helpers ──────────────────────────────────────────────────────────

def _sanitize(raw: str):
    if not raw:
        return None
    raw = raw.strip()
    return raw if re.match(ALLOWED_COMPANY_RE, raw) else None


def _filepath(company: str) -> Path:
    name = re.sub(r"[^a-zA-Z0-9_\-]", "_", company.lower())
    return DATA_DIR / f"{name}.xlsx"


def _load(path: Path) -> list:
    df = pd.read_excel(path)
    df = df.where(pd.notna(df), None)
    priority = ["Title", "Source", "Category", "Sentiment", "Link", "Published", "Scraped_At"]
    cols = [c for c in priority if c in df.columns] + [c for c in df.columns if c not in priority]
    return df[cols].to_dict(orient="records")


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/articles")
def get_articles():
    company = _sanitize(request.args.get("company", ""))
    if not company:
        return jsonify({"error": "Provide a valid company name"}), 400

    path = _filepath(company)
    logger.info(f"GET /articles?company={company}")

    if not path.exists():
        logger.info(f"No cache for '{company}', running scraper…")
        try:
            from scraper import start_research
            result = start_research(company)
            if not result:
                return jsonify({"error": f"No news found for '{company}'."}), 404
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            return jsonify({"error": "Scraper failed. Please try again."}), 500

    try:
        articles = _load(path)
        return jsonify({"company": company, "count": len(articles), "articles": articles}), 200
    except Exception as e:
        logger.error(f"Excel read error for '{company}': {e}")
        return jsonify({"error": "Failed to load cached data. Try refreshing."}), 500


@app.route("/refresh")
def refresh():
    company = _sanitize(request.args.get("company", ""))
    if not company:
        return jsonify({"error": "Provide a valid company name"}), 400

    logger.info(f"GET /refresh?company={company}")
    try:
        from scraper import start_research
        result = start_research(company)
    except Exception as e:
        logger.error(f"Scraper exception: {e}")
        return jsonify({"error": "Scraper encountered an error."}), 500

    if not result:
        return jsonify({"error": f"No news found for '{company}'."}), 404

    try:
        articles = _load(Path(result))
        return jsonify({"message": f"Refreshed '{company}'", "company": company,
                        "count": len(articles), "articles": articles}), 200
    except Exception as e:
        logger.error(f"Post-refresh read error: {e}")
        return jsonify({"error": "Scraped OK but failed to read results."}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nVIBE is running -> http://127.0.0.1:5000\n")
    app.run(debug=True, host="127.0.0.1", port=5000)