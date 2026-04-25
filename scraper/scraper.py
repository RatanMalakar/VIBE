"""
scraper.py — VIBE News Scraper (production-ready)

Fixes applied:
  - Correct Google News RSS link extraction (guid tag, not link sibling)
  - scraped_at timestamp stored in UTC ISO format on every article
  - Articles sorted latest pub_date first
  - Company relevance filter (NLP disambiguation)
  - Enhanced sentiment + category classification
  - Output saved to /data directory
  - Removed unused psycopg2 import
  - Proper structured logging
"""

import sys
import re
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── Path setup: allow running from any directory ────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scraper"))
sys.path.insert(0, str(_ROOT / "backend"))

from nlp_utils import analyze_sentiment, classify_category, is_relevant

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(_ROOT / "app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

DATA_DIR = _ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_ARTICLES = 15
REQUEST_TIMEOUT = 10  # seconds


def _extract_real_link(item) -> str:
    """
    Extract the actual article URL from a Google News RSS <item>.

    Google News RSS structure:
      - <guid> contains the real Google News article URL
      - <link> is a TEXT NODE between tags, not a child element — 
        accessing item.link.text gives the NEXT item's title (bug!)
    
    We use <guid isPermaLink="false"> as the canonical link since it 
    consistently points to the correct article redirect page.
    """
    # Try guid first (most reliable)
    guid = item.find("guid")
    if guid and guid.text.startswith("http"):
        return guid.text.strip()

    # Fallback: navigate siblings to find the raw link text node
    # The <link> tag in RSS 2.0 is a text node between </title> and <guid>
    try:
        link_node = item.find("link")
        if link_node:
            # If it has text and looks like a URL
            if link_node.text and link_node.text.startswith("http"):
                return link_node.text.strip()
            # Some parsers capture it as next sibling
            sibling = link_node.next_sibling
            if sibling and str(sibling).strip().startswith("http"):
                return str(sibling).strip()
    except Exception:
        pass

    return ""


def _parse_pub_date(raw_date: str) -> datetime:
    """
    Parse RFC 2822 date strings from RSS into timezone-aware datetime.
    Falls back to current UTC time if parsing fails.
    """
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d %b %Y %H:%M:%S %z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw_date.strip(), fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: '{raw_date}', using current time")
    return datetime.now(timezone.utc)


def start_research(company: str) -> str | None:
    """
    Main scraping pipeline for a given company name.

    Steps:
      1. Fetch Google News RSS feed
      2. Parse up to MAX_ARTICLES items
      3. Filter irrelevant articles via NLP relevance check
      4. Enrich with sentiment + category labels
      5. Sort by publication date (latest first)
      6. Save to data/{company_normalized}.xlsx
    
    Returns: path to saved Excel file, or None on failure.
    """
    company = company.strip()
    company_normalized = re.sub(r"[^a-zA-Z0-9_\-]", "_", company.lower())
    output_path = DATA_DIR / f"{company_normalized}.xlsx"

    logger.info(f"Research started for: '{company}'")

    # ── 1. Fetch RSS Feed ────────────────────────────────────────
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(company)}&hl=en-IN&gl=IN&ceid=IN:en"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f"RSS fetch successful ({response.status_code}) for '{company}'")
    except requests.RequestException as e:
        logger.error(f"Network error fetching news for '{company}': {e}")
        return None

    # ── 2. Parse RSS XML ────────────────────────────────────────
    try:
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
    except Exception as e:
        logger.error(f"XML parse error for '{company}': {e}")
        return None

    if not items:
        logger.warning(f"No RSS items found for '{company}'")
        return None

    logger.info(f"Found {len(items)} raw articles for '{company}'")

    # ── 3. Process Articles ─────────────────────────────────────
    scraped_at = datetime.now(timezone.utc).isoformat()  # Single timestamp for batch
    news_data = []

    for item in items[:MAX_ARTICLES]:
        try:
            title = item.title.text.strip() if item.title else ""
            description = item.description.text.strip() if item.description else ""
            source = item.source.text.strip() if item.source else "Unknown Source"
            raw_date = item.pubDate.text.strip() if item.pubDate else ""
            link = _extract_real_link(item)

            if not title or not link:
                logger.debug(f"Skipping item with missing title or link")
                continue

            # ── Relevance Filter (company disambiguation) ────────
            if not is_relevant(company, title, description):
                logger.info(f"[FILTERED] Not relevant to '{company}': {title[:70]}")
                continue

            # ── Parse and validate date ──────────────────────────
            pub_date_dt = _parse_pub_date(raw_date)

            # ── NLP Enrichment ───────────────────────────────────
            combined_text = f"{title} {description}"
            sentiment = analyze_sentiment(combined_text)
            category = classify_category(combined_text)

            news_data.append({
                "Company": company,
                "Title": title,
                "Source": source,
                "Category": category,
                "Sentiment": sentiment,
                "Link": link,
                "Published": pub_date_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "Published_dt": pub_date_dt,   # temp column for sorting
                "Scraped_At": scraped_at,
            })

        except Exception as e:
            logger.warning(f"Error processing item: {e}")
            continue

    if not news_data:
        logger.warning(f"No relevant articles found for '{company}' after filtering")
        return None

    # ── 4. Sort by latest publication date first ─────────────────
    df = pd.DataFrame(news_data)
    df.sort_values("Published_dt", ascending=False, inplace=True)
    df.drop(columns=["Published_dt"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ── 5. Save to Excel ─────────────────────────────────────────
    try:
        df.to_excel(output_path, index=False)
        logger.info(f"Saved {len(df)} articles to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save Excel for '{company}': {e}")
        return None

    return str(output_path)


if __name__ == "__main__":
    # Allow CLI usage: python scraper.py <company_name>
    import sys
    company_arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Tesla"
    result = start_research(company_arg)
    print(f"Result: {result}")
