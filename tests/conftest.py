# tests/conftest.py
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import yaml
from datetime import datetime, timedelta

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.config_manager import ConfigManager
from data.database import DatabaseManager
from data.vector_store import VectorStoreManager
from services.email_service import EmailService
from services.web_scraper import WebScraper

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def test_config_data():
    """Sample configuration data for tests"""
    return {
        'app': {
            'name': 'Test AI Assistant',
            'version': '1.0.0',
            'debug': True
        },
        'database': {
            'url': 'sqlite:///:memory:',
            'pool_size': 5
        },
        'openai': {
            'api_key': 'test-api-key',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.2
        },
        'email': {
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'test-password',
            'recipients': ['recipient@example.com']
        },
        'vector_store': {
            'path': './test_vector_store',
            'collection_name': 'test_docs'
        },
        'scraping': {
            'user_agent': 'Test-Agent/1.0',
            'request_delay': 0.1,
            'timeout': 10
        }
    }

@pytest.fixture
def test_config_file(temp_dir, test_config_data):
    """Create a test configuration file"""
    config_path = Path(temp_dir) / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(test_config_data, f)
    return str(config_path)

@pytest.fixture
def mock_config(test_config_data):
    """Mock configuration manager"""
    config = Mock(spec=ConfigManager)
    config.config_data = test_config_data
    config.get.side_effect = lambda key, default=None: _get_nested_value(test_config_data, key, default)
    config.get_section.side_effect = lambda section: test_config_data.get(section, {})
    config.database_url = test_config_data['database']['url']
    config.openai_api_key = test_config_data['openai']['api_key']
    config.email_config = test_config_data['email']
    config.vector_store_config = test_config_data['vector_store']
    config.scraping_config = test_config_data['scraping']
    return config

def _get_nested_value(data, key_path, default=None):
    """Helper function to get nested dictionary values"""
    keys = key_path.split('.')
    value = data
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    db_manager = Mock(spec=DatabaseManager)
    db_manager.get_active_urls.return_value = [
        {'url': 'https://example.com', 'tags': ['news'], 'check_frequency': 24},
        {'url': 'https://test.com', 'tags': ['tech'], 'check_frequency': 12}
    ]
    db_manager.add_url.return_value = True
    db_manager.update_content_record.return_value = None
    db_manager.get_content_since.return_value = [
        {
            'url': 'https://example.com/article1',
            'title': 'Test Article',
            'content': 'Test content',
            'retrieved_at': datetime.now(),
            'tags': ['news']
        }
    ]
    db_manager.log_query.return_value = None
    return db_manager

# @pytest.fixture
# def mock_vector_store():
#     """Mock vector store manager"""
#     vector_store = Mock(spec=VectorStoreManager)
#     vector_store.add_documents.return_value = ['doc1', 'doc2']
#     vector_store.add_texts.return_value = ['text1', 'text2']
#     vector_store.similarity_search.return_value = []
#     return vector_store

# @pytest.fixture
# def sample_html_content():
#     """Sample HTML content for testing"""
#     return """
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <title>Test Article</title>
#         <meta name="description" content="This is a test article">
#         <meta name="author" content="Test Author">
#     </head>
#     <body>
#         <header>
#             <nav>Navigation</nav>
#         </header>
#         <main>
#             <article>
#                 <h1>Test Article Title</h1>
#                 <p>This is the main content of the test article.</p>
#                 <p>It contains multiple paragraphs with useful information.</p>
#             </article>
#         </main>
#         <footer>Footer content</footer>
#         <script>console.log('test');</script>
#     </body>
#     </html>
#     """

# @pytest.fixture
# def sample_rss_content():
#     """Sample RSS content for testing"""
#     return """<?xml version="1.0" encoding="UTF-8"?>
#     <rss version="2.0">
#         <channel>
#             <title>Test RSS Feed</title>
#             <description>A test RSS feed</description>
#             <link>https://example.com</link>
#             <item>
#                 <title>Test Article 1</title>
#                 <description>Description of test article 1</description>
#                 <link>https://example.com/article1</link>
#                 <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
#             </item>
#             <item>
#                 <title>Test Article 2</title>
#                 <description>Description of test article 2</description>
#                 <link>https://example.com/article2</link>
#                 <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
#             </item>
#         </channel>
#     </rss>
#     """

# @pytest.fixture
# def sample_content_data():
#     """Sample content data for testing"""
#     return [
#         {
#             'url': 'https://example.com/article1',
#             'title': 'Test Article 1',
#             'content': 'This is the content of test article 1. It contains important information about testing.',
#             'timestamp': datetime.now(),
#             'metadata': {'author': 'Test Author', 'category': 'tech'}
#         },
#         {
#             'url': 'https://example.com/article2',
#             'title': 'Test Article 2',
#             'content': 'This is the content of test article 2. It discusses advanced testing techniques.',
#             'timestamp': datetime.now() - timedelta(hours=1),
#             'metadata': {'author': 'Another Author', 'category': 'development'}
#         }
#     ]
