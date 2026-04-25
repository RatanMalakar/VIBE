"""
db_connection.py — PostgreSQL connection (optional, future use)
Fix: os.geten → os.getenv (was a typo causing NameError)
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "vibe_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),   # Fixed: was os.geten (typo)
        port=os.getenv("DB_PORT", "5432")
    )