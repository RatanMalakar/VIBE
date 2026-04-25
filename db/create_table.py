from db_connection import get_connection

def create_table():
    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS news (
                
                )

    """)