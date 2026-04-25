"""
create_table.py — Creates the VIBE news table in PostgreSQL
"""

from db_connection import get_connection

def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id          SERIAL PRIMARY KEY,
            company     VARCHAR(100) NOT NULL,
            title       TEXT NOT NULL,
            source      VARCHAR(200),
            category    VARCHAR(100),
            sentiment   VARCHAR(50),
            link        TEXT,
            published   TIMESTAMPTZ,
            scraped_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_news_company ON news(company);
        CREATE INDEX IF NOT EXISTS idx_news_scraped ON news(scraped_at DESC);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Table created successfully.")

if __name__ == "__main__":
    create_table()