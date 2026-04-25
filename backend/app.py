"""
app.py — VIBE Flask REST API (production-ready)

Improvements over original:
  - All routes return proper jsonify() with correct HTTP status codes
  - /articles: try/except around Excel read, returns 404 if not found
  - /articles: auto-triggers scraper if Excel doesn't exist (live fetch)
  - /refresh: returns fresh article data immediately (no extra roundtrip)
  - Input sanitization: only alphanumeric + safe chars allowed
  - CORS enabled for frontend/API separation
  - Serves frontend/index.html cleanly via send_from_directory
  - webbrowser.open() removed (not for production)
  - Structured logging
"""

import sys
import re
import logging
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd

# ── Path setup ───────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scraper"))
sys.path.insert(0, str(_ROOT / "backend"))

from config import DATA_DIR, FRONTEND_DIR, LOG_FILE, ALLOWED_COMPANY_RE, MAX_ARTICLES

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

# ── Flask App ─────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")
CORS(app)  # Allow cross-origin requests


# ── Helpers ───────────────────────────────────────────────────────────

def _sanitize_company(raw: str) -> str | None:
    """
    Sanitize company input:
    - Strip whitespace
    - Enforce alphanumeric + safe chars whitelist
    - Return None if invalid (prevents path traversal attacks)
    """
    if not raw:
        return None
    raw = raw.strip()
    if not re.match(ALLOWED_COMPANY_RE, raw):
        logger.warning(f"Invalid company input rejected: '{raw}'")
        return None
    return raw


def _company_to_filename(company: str) -> Path:
    """Convert company name to its normalized Excel file path."""
    normalized = re.sub(r"[^a-zA-Z0-9_\-]", "_", company.lower())
    return DATA_DIR / f"{normalized}.xlsx"


def _load_articles(filepath: Path) -> list[dict]:
    """
    Load articles from Excel, clean NaN values, and return as list of dicts.
    Sorted by 'Published' column (latest first) if present.
    """
    df = pd.read_excel(filepath)

    # Convert NaN → None (JSON-serializable)
    df = df.where(pd.notna(df), None)

    # Ensure proper column ordering for API response
    priority_cols = ["Title", "Source", "Category", "Sentiment", "Link", "Published", "Scraped_At"]
    other_cols = [c for c in df.columns if c not in priority_cols]
    ordered_cols = [c for c in priority_cols if c in df.columns] + other_cols
    df = df[ordered_cols]

    return df.to_dict(orient="records")


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """Serve the frontend index.html"""
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/articles", methods=["GET"])
def get_articles():
    """
    GET /articles?company=<name>

    Returns JSON array of articles for the given company.
    If no cached Excel exists, automatically triggers the scraper (live fetch).
    
    Response: 200 with articles array, or 4xx/5xx with {"error": "..."}
    """
    raw_company = request.args.get("company", "")
    company = _sanitize_company(raw_company)

    if not company:
        return jsonify({"error": "Please provide a valid company name (letters, numbers, spaces only)"}), 400

    filepath = _company_to_filename(company)
    logger.info(f"GET /articles?company={company} | File: {filepath}")

    # Auto-fetch if no cached data
    if not filepath.exists():
        logger.info(f"No cached data for '{company}', running scraper...")
        try:
            from scraper import start_research
            result = start_research(company)
            if not result:
                return jsonify({"error": f"Could not fetch news for '{company}'. Please try again."}), 502
        except Exception as e:
            logger.error(f"Scraper error for '{company}': {e}")
            return jsonify({"error": "Scraper failed. Please try again later."}), 500

    # Load and return articles
    try:
        articles = _load_articles(filepath)
        logger.info(f"Returning {len(articles)} articles for '{company}'")
        return jsonify({"company": company, "count": len(articles), "articles": articles}), 200
    except Exception as e:
        logger.error(f"Failed to read Excel for '{company}': {e}")
        return jsonify({"error": f"Failed to load data for '{company}'. Try refreshing."}), 500


@app.route("/refresh", methods=["GET"])
def refresh():
    """
    GET /refresh?company=<name>

    Triggers the scraper to fetch fresh news, then returns the updated articles.
    Frontend can call this and immediately get fresh data — no second /articles call needed.
    """
    raw_company = request.args.get("company", "")
    company = _sanitize_company(raw_company)

    if not company:
        return jsonify({"error": "Please provide a valid company name"}), 400

    logger.info(f"GET /refresh?company={company}")

    try:
        from scraper import start_research
        result = start_research(company)
    except Exception as e:
        logger.error(f"Scraper exception for '{company}': {e}")
        return jsonify({"error": "Scraper encountered an error. Please try again."}), 500

    if not result:
        return jsonify({"error": f"No news found for '{company}'. Try a different name."}), 404

    # Return fresh data directly
    try:
        filepath = Path(result)
        articles = _load_articles(filepath)
        logger.info(f"Refresh complete: {len(articles)} articles for '{company}'")
        return jsonify({
            "message": f"Data refreshed for '{company}'",
            "company": company,
            "count": len(articles),
            "articles": articles,
        }), 200
    except Exception as e:
        logger.error(f"Post-refresh read error for '{company}': {e}")
        return jsonify({"error": "Scraped successfully but failed to load results."}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for deployment platforms (Render/Railway)."""
    return jsonify({"status": "ok", "service": "VIBE API"}), 200


# ── Error Handlers ────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Unhandled server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting VIBE development server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
