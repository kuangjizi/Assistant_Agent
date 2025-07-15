# tests/unit/test_database.py
import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import psycopg2
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from data.database import DatabaseManager

class TestDatabaseManager:

    @pytest.fixture
    def sqlite_db_manager(self, temp_dir):
        """Create a database manager with SQLite for testing"""
        db_path = f"sqlite:///{temp_dir}/test.db"

        # Create SQLite database with test schema
        conn = sqlite3.connect(f"{temp_dir}/test.db")
        cursor = conn.cursor()

        # Create test tables
        cursor.execute("""
            CREATE TABLE monitored_urls (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                tags TEXT,
                check_frequency INTEGER DEFAULT 24
            )
        """)

        cursor.execute("""
            CREATE TABLE content_records (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                content_hash TEXT,
                content TEXT,
                retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                word_count INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE query_logs (
                id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT,
                sources TEXT,
                confidence TEXT,
                response_time REAL,
                user_feedback INTEGER,
                session_id TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        # Mock the PostgreSQL-specific parts
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            db_manager = DatabaseManager(db_path)
            db_manager.connection_string = f"sqlite:///{temp_dir}/test.db"

            yield db_manager

    def test_add_url(self, sqlite_db_manager):
        """Test adding URLs to monitor"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            result = sqlite_db_manager.add_url(
                'https://example.com/test',
                'test_user',
                ['tech', 'news']
            )

            assert result == True
            mock_cursor.execute.assert_called()

    def test_get_active_urls(self, sqlite_db_manager):
        """Test getting active URLs"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {'url': 'https://example.com', 'tags': ['tech'], 'check_frequency': 24},
                {'url': 'https://test.com', 'tags': ['news'], 'check_frequency': 12}
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            urls = sqlite_db_manager.get_active_urls()

            assert len(urls) == 2
            assert urls[0]['url'] == 'https://example.com'
            assert urls[1]['url'] == 'https://test.com'

    def test_is_content_new(self, sqlite_db_manager):
        """Test checking if content is new"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            # Test new content (no existing hash)
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            is_new = sqlite_db_manager.is_content_new('https://example.com', 'hash123')
            assert is_new == True

            # Test existing content with different hash
            mock_cursor.fetchone.return_value = ('different_hash',)
            is_new = sqlite_db_manager.is_content_new('https://example.com', 'hash123')
            assert is_new == True

            # Test existing content with same hash
            mock_cursor.fetchone.return_value = ('hash123',)
            is_new = sqlite_db_manager.is_content_new('https://example.com', 'hash123')
            assert is_new == False

    def test_update_content_record(self, sqlite_db_manager):
        """Test updating content records"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            sqlite_db_manager.update_content_record(
                'https://example.com',
                'hash123',
                'Test Title',
                'Test content here'
            )

            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()

    def test_get_content_since(self, sqlite_db_manager):
        """Test getting content since a date"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    'url': 'https://example.com',
                    'title': 'Test Article',
                    'content': 'Test content',
                    'retrieved_at': datetime.now(),
                    'tags': ['tech']
                }
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            since_date = datetime.now() - timedelta(days=1)
            content = sqlite_db_manager.get_content_since(since_date)

            assert len(content) == 1
            assert content[0]['title'] == 'Test Article'

    def test_log_query(self, sqlite_db_manager):
        """Test logging queries"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            sqlite_db_manager.log_query(
                'What is AI?',
                'AI is artificial intelligence.',
                [{'url': 'https://example.com', 'title': 'AI Article'}],
                'High',
                1.5
            )

            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()

    def test_connection_error_handling(self):
        """Test handling of database connection errors"""
        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("Connection failed")):
            with pytest.raises(psycopg2.OperationalError):
                DatabaseManager("postgresql://invalid:connection@localhost/db")

    def test_query_error_handling(self, sqlite_db_manager):
        """Test handling of query errors"""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database error")

            # Should return empty list on error
            urls = sqlite_db_manager.get_active_urls()
            assert urls == []
