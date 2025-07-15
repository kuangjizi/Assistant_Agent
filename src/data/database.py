# src/data/database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging
import json

class DatabaseManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # URLs table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS monitored_urls (
                        id SERIAL PRIMARY KEY,
                        url TEXT UNIQUE NOT NULL,
                        added_by TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        tags TEXT[],
                        check_frequency INTEGER DEFAULT 24
                    )
                """)

                # Content table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS content_records (
                        id SERIAL PRIMARY KEY,
                        url TEXT NOT NULL,
                        title TEXT,
                        content_hash TEXT,
                        content TEXT,
                        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB,
                        FOREIGN KEY (url) REFERENCES monitored_urls(url)
                    )
                """)

                # Query logs
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS query_logs (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT,
                        sources JSONB,
                        confidence TEXT,
                        response_time FLOAT,
                        user_feedback INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()

    def add_url(self, url: str, added_by: str = "", tags: list = []) -> bool:
        """Add new URL to monitor"""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO monitored_urls (url, added_by, tags)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (url) DO UPDATE SET
                        is_active = TRUE,
                        tags = EXCLUDED.tags
                    """, (url, added_by, tags or []))
                    conn.commit()
                    return True
        except Exception as e:
            logging.error(f"Error adding URL {url}: {e}")
            return False

    def get_active_urls(self) -> list:
        """Get all active URLs to monitor"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT url, tags, check_frequency
                    FROM monitored_urls
                    WHERE is_active = TRUE
                """)
                return cur.fetchall()

    def is_content_new(self, url: str, content_hash: str) -> bool:
        """Check if content is new based on hash"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT content_hash FROM content_records
                    WHERE url = %s
                    ORDER BY retrieved_at DESC
                    LIMIT 1
                """, (url,))

                result = cur.fetchone()
                return result is None or result[0] != str(content_hash)

    def update_content_record(self, url: str, content_hash: str, title: str, content: str):
        """Update content record"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO content_records (url, title, content_hash, content)
                    VALUES (%s, %s, %s, %s)
                """, (url, title, str(content_hash), content))
                conn.commit()

    def get_content_since(self, since_date: datetime, topic_filter: str = "") -> list:
        """Get content since specified date"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT cr.url, cr.title, cr.content, cr.retrieved_at, mu.tags
                    FROM content_records cr
                    JOIN monitored_urls mu ON cr.url = mu.url
                    WHERE cr.retrieved_at >= %s
                """
                params = [since_date]

                if topic_filter:
                    query += " AND (cr.content ILIKE %s OR %s = ANY(mu.tags))"
                    params.extend([f"%{topic_filter}%", topic_filter])

                query += " ORDER BY cr.retrieved_at DESC"

                cur.execute(query, params)
                return cur.fetchall()

    def log_query(self, question: str, answer: str, sources: list, confidence: str, response_time: float):
        """Log query for performance analysis"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO query_logs (question, answer, sources, confidence, response_time)
                    VALUES (%s, %s, %s, %s, %s)
                """, (question, answer, json.dumps(sources), confidence, response_time))
                conn.commit()
