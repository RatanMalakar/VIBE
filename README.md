# VIBE — Company News Intelligence Dashboard

> Real-time news scraping · NLP sentiment analysis · Category classification · Premium dark UI

![VIBE Screenshot](frontend/index.html)

---

## Features

- **Live news scraping** from Google News RSS for any company
- **NLP pipeline** (zero model downloads):
  - Enhanced sentiment analysis with negation detection
  - 6-category classifier (AI/Tech, Finance, Legal, Products, M&A, People)
  - Company relevance filter to remove false positives (e.g. Marlboro city vs brand)
- **Correct article links** — fixed critical RSS `<guid>` extraction bug
- **Sorted by latest** publication date
- **Real timestamps** — `scraped_at` + `Published` stored per article
- **Premium dark UI** — glassmorphism cards, sentiment badges, category chips, refresh button
- **Production-ready Flask API** — proper error handling, CORS, input sanitization, health endpoint

---

## Project Structure

```
VIBE/
├── app.py               # Root launcher — run this
├── backend/
│   ├── app.py           # Flask REST API (full version)
│   └── config.py        # Centralized path & env config
├── scraper/
│   ├── scraper.py       # News scraper (RSS + NLP pipeline)
│   └── nlp_utils.py     # Sentiment, category, relevance NLP
├── frontend/
│   └── index.html       # Premium dark dashboard UI
├── data/                # Excel output files (auto-created)
├── db/
│   ├── db_connection.py # PostgreSQL connection (optional)
│   └── create_table.py  # DB schema
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/RatanMalakar/VIBE.git
cd VIBE

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the frontend UI |
| `/articles?company=tesla` | GET | Returns cached articles (auto-scrapes if no cache) |
| `/refresh?company=tesla` | GET | Fetches fresh news + returns updated articles |
| `/health` | GET | Health check for deployment platforms |

### Example Response — `/articles?company=tesla`
```json
{
  "company": "tesla",
  "count": 10,
  "articles": [
    {
      "Title": "Tesla reports record Q1 deliveries",
      "Source": "Reuters",
      "Category": "Finance / Markets",
      "Sentiment": "Positive",
      "Link": "https://news.google.com/...",
      "Published": "2026-04-25 08:00:00 UTC",
      "Scraped_At": "2026-04-25T09:15:00+00:00"
    }
  ]
}
```

---

## Deployment

### Backend — Render (Free Tier)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
5. Add environment variables from `.env.example` if using DB

### Frontend — Vercel / Netlify (Static)

If deploying frontend separately:
1. Update the `fetch()` URLs in `frontend/index.html` to point to your Render backend URL
2. Deploy `frontend/` folder to Vercel or Netlify

### Environment Variables

Copy `.env.example` → `.env` and fill in values:

```env
DB_HOST=localhost
DB_NAME=vibe_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_PORT=5432
MAX_ARTICLES=15
```

---

## Bugs Fixed

| Bug | Fix |
|-----|-----|
| `item.link.text` returning wrong URLs | Use `<guid>` tag for correct article links |
| 500 crash on unknown company | Try/except + auto-scrape on cache miss |
| No `scraped_at` timestamp | Added UTC ISO timestamp to every article |
| Articles not sorted by date | `sort_values('Published_dt', ascending=False)` |
| Field mismatch (title vs Title) | Consistent capitalized column names |
| `os.geten()` typo in DB module | Fixed to `os.getenv()` |
| Empty `CREATE TABLE` schema | Complete schema with indexes |
| No refresh button in UI | Added with loading state |
| No error handling in frontend | Error toast + empty state |
| Company disambiguation (Marlboro) | Fuzzy relevance filter via `difflib` |
