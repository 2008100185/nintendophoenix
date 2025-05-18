import os
import psycopg2
from urllib.parse import urlparse

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL no está definida")

    result = urlparse(db_url)
    return psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode="require"
    )

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP
                )
            ''')
            conn.commit()
    add_missing_column()

def add_missing_column():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='articles' AND column_name='published_at'
                        ) THEN
                            ALTER TABLE articles ADD COLUMN published_at TIMESTAMP;
                        END IF;
                    END;
                    $$;
                """)
                conn.commit()
    except Exception as e:
        print(f"Error al verificar o crear columna: {e}")

def save_article(url, published_at=None):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO articles (url, published_at) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING',
                    (url, published_at)
                )
                conn.commit()
    except Exception as e:
        print(f"Error al guardar artículo: {e}")

def is_article_saved(url):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
                return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error al comprobar artículo: {e}")
        return False

def delete_old_articles(days=30):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM articles WHERE created_at < NOW() - INTERVAL %s', (f'{days} days',))
            conn.commit()

def get_all_articles():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT url FROM articles')
            return [row[0] for row in cursor.fetchall()]

def get_articles_not_in_channel(existing_urls, max_age_hours=3):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT url FROM articles
                WHERE url NOT IN %s AND published_at >= NOW() - INTERVAL %s
            ''', (tuple(existing_urls), f'{max_age_hours} hours'))
            return [row[0] for row in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
    add_missing_column()
