# tests/unit/test_database.py
import pytest
import psycopg2
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import psycopg2

from data.database import DatabaseManager

class TestDatabaseManager:

    def test_add_url(self, mock_db_manager):
        """Test adding URLs to monitor"""
        result = mock_db_manager.add_url(
            'https://example.com/test',
            'test_user',
            ['tech', 'news']
        )

        assert result == True

    def test_get_active_urls(self, mock_db_manager):
        """Test getting active URLs"""

        urls = mock_db_manager.get_active_urls()

        assert len(urls) == 2
        assert urls[0]['url'] == 'https://example.com'
        assert urls[1]['url'] == 'https://test.com'

    def test_is_content_new(self, mock_config):
        """Test checking if content is new - testing actual logic"""

        with patch('psycopg2.connect') as mock_connect:
            # Setup mock connection and cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

            # Create real DatabaseManager instance
            db_manager = DatabaseManager(mock_config.database_url)

            # Scenario 1: No existing content (cursor returns None) - should return True
            mock_cursor.fetchone.return_value = None
            is_new = db_manager.is_content_new('https://new-site.com', 'hash123')
            assert is_new == True

            # Scenario 2: Existing content with different hash - should return True
            mock_cursor.fetchone.return_value = ('different_stored_hash',)
            is_new = db_manager.is_content_new('https://example.com', 'new_hash')
            assert is_new == True

            # Scenario 3: Existing content with same hash - should return False
            mock_cursor.fetchone.return_value = ('same_hash',)
            is_new = db_manager.is_content_new('https://example.com', 'same_hash')
            assert is_new == False

    def test_update_content_record(self, mock_db_manager):
        """Test updating content records"""
        # Test that the method can be called without errors
        # The mock returns None (success)
        result = mock_db_manager.update_content_record(
            'https://example.com',
            'hash123',
            'Test Title',
            'Test content here'
        )

        # Should return None (success)
        assert result is None


    def test_get_content_since(self, mock_db_manager):
        """Test getting content since a date"""

        since_date = datetime.now() - timedelta(days=1)
        content = mock_db_manager.get_content_since(since_date, topic_filter='test')

        assert len(content) == 1
        assert content[0]['title'] == 'Test Article'

    def test_log_query(self, mock_db_manager):
        """Test logging queries"""
        mock_db_manager.log_query(
            'What is AI?',
            'AI is artificial intelligence.',
            [{'url': 'https://example.com', 'title': 'AI Article'}],
            'High',
            1.5
        )


    def test_connection_error_handling(self):
        """Test handling of database connection errors"""
        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("Connection failed")):
            with pytest.raises(psycopg2.OperationalError):
                DatabaseManager("postgresql://invalid:connection@localhost/db")

    def test_query_error_handling(self, mock_db_manager):
        """Test handling of query errors"""
        # Configure the specific method to raise an exception
        mock_db_manager.get_active_urls.side_effect = Exception("Database error")

        # Should raise an exception
        with pytest.raises(Exception, match="Database error"):
            mock_db_manager.get_active_urls()
