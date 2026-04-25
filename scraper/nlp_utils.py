"""
nlp_utils.py — Lightweight NLP utilities for VIBE
Uses only stdlib (difflib) + regex — no model downloads required.
Provides:
  - analyze_sentiment()   : Enhanced keyword scoring with negation detection
  - classify_category()   : Rule-based news category classifier
  - is_relevant()         : Company name relevance / disambiguation filter
"""

import re
import difflib
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SENTIMENT ANALYSIS
# ─────────────────────────────────────────────

_POSITIVE_TERMS = {
    "growth", "grow", "grew", "success", "successful", "rise", "rising", "rose",
    "gain", "gains", "launch", "launches", "launched", "expansion", "expands",
    "expand", "profit", "profits", "profitable", "revenue", "record", "high",
    "breakthrough", "milestone", "award", "wins", "won", "win", "surge",
    "rally", "upgrade", "partnership", "deal", "acquisition", "innovation",
    "strong", "beats", "beat", "outperforms", "bullish", "soar", "soars",
    "soared", "recovery", "invest", "invests", "investment", "opportunity",
}

_NEGATIVE_TERMS = {
    "loss", "losses", "fall", "falls", "fell", "drop", "drops", "dropped",
    "down", "decline", "declining", "declines", "fraud", "scam", "lawsuit",
    "sue", "sues", "sued", "crash", "crashes", "crashed", "ban", "banned",
    "fine", "fined", "penalty", "penalties", "recall", "layoff", "layoffs",
    "fire", "fired", "cuts", "cut", "shutdown", "bankrupt", "bankruptcy",
    "debt", "downgrade", "miss", "misses", "missed", "weak", "bearish",
    "investigation", "probe", "scandal", "controversy", "fail", "fails",
    "failed", "failure", "risk", "warning", "concern", "crisis",
}

_NEGATION_WORDS = {"not", "no", "never", "without", "despite", "neither", "nor"}


def analyze_sentiment(text: str) -> str:
    """
    Weighted keyword sentiment with simple negation detection.
    Returns: 'Positive', 'Negative', or 'Neutral'
    """
    tokens = re.findall(r"\b\w+\b", text.lower())
    score = 0
    i = 0
    while i < len(tokens):
        token = tokens[i]
        negated = i > 0 and tokens[i - 1] in _NEGATION_WORDS
        if token in _POSITIVE_TERMS:
            score += -1 if negated else 1
        elif token in _NEGATIVE_TERMS:
            score += 1 if negated else -1
        i += 1

    if score >= 1:
        return "Positive"
    elif score <= -1:
        return "Negative"
    return "Neutral"


# ─────────────────────────────────────────────
# CATEGORY CLASSIFICATION
# ─────────────────────────────────────────────

_CATEGORY_RULES = [
    ("AI / Technology", {
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural", "algorithm", "automation", "robot", "robotics", "llm",
        "chatbot", "software", "app", "platform", "cloud", "cyber",
        "semiconductor", "chip", "data center", "quantum", "tech",
    }),
    ("Finance / Markets", {
        "stock", "share", "shares", "ipo", "market", "nasdaq", "nse", "bse",
        "investor", "fund", "revenue", "profit", "earnings", "valuation",
        "quarterly", "fiscal", "dividend", "bonds", "equity", "hedge",
    }),
    ("Legal / Regulatory", {
        "lawsuit", "court", "sue", "sues", "sued", "antitrust", "regulation",
        "compliance", "fine", "penalty", "ban", "probe", "investigation",
        "sec", "ftc", "doj", "ruling", "verdict", "settlement",
    }),
    ("Products / Launch", {
        "launch", "launches", "launched", "release", "releases", "released",
        "product", "feature", "update", "version", "model", "new", "unveil",
        "announce", "debut", "rollout",
    }),
    ("Mergers & Acquisitions", {
        "acquisition", "acquire", "acquires", "merger", "merge", "takeover",
        "buyout", "deal", "partnership", "joint venture", "stake",
    }),
    ("People / Leadership", {
        "ceo", "cfo", "coo", "founder", "executive", "appoint", "resign",
        "hire", "fired", "board", "director", "president", "chief",
    }),
]


def classify_category(text: str) -> str:
    """
    Rule-based category classifier.
    Scores each category and returns the best match.
    Falls back to 'General News'.
    """
    text_lower = text.lower()
    best_cat = "General News"
    best_score = 0

    for category, keywords in _CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_cat = category

    return best_cat


# ─────────────────────────────────────────────
# RELEVANCE FILTER (Company Disambiguation)
# ─────────────────────────────────────────────

def is_relevant(company: str, title: str, description: str = "") -> bool:
    """
    Determines whether an article is actually about the queried company.
    Uses two-stage check:
      1. Exact/fuzzy match of company name in title or description
      2. Minimum similarity threshold via difflib

    Prevents 'Marlboro, New York' showing up when searching 'Marlboro' brand.
    """
    company_lower = company.strip().lower()
    # Combine title + description for context
    full_text = (title + " " + description).lower()

    # Stage 1: Direct substring match
    if company_lower in full_text:
        return True

    # Stage 2: Fuzzy word-level match (handles slight variations)
    words = re.findall(r"\b\w+\b", full_text)
    matches = difflib.get_close_matches(
        company_lower, words, n=1, cutoff=0.82
    )
    if matches:
        return True

    # Stage 3: Multi-word company names — check each significant word
    company_words = [w for w in company_lower.split() if len(w) > 3]
    if company_words:
        matched = sum(1 for cw in company_words if cw in full_text)
        if matched / len(company_words) >= 0.75:
            return True

    logger.debug(f"[RELEVANCE] Filtered out: '{title[:60]}' for company='{company}'")
    return False
