### Overall Architecture
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   Scheduler     │    │   Data Storage  │
│   (Streamlit)   │◄──►│   (APScheduler) │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Query Engine  │    │Content Retrieval│    │   Vector Store  │
│   (LangChain)   │◄──►│   (Scrapy)      │◄──►│   (ChromaDB)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Service   │    │   Email Service │    │   Config Mgmt   │
│   (OpenAI/Local)│    │   (SMTP)        │    │   (YAML/JSON)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘

### Components
Core Framework: LangChain

Excellent RAG (Retrieval-Augmented Generation) capabilities
Built-in document processing and vector store integration
Extensible agent framework
Strong community support

Web Scraping: Scrapy + BeautifulSoup

Scrapy: Robust, scalable web crawling framework
BeautifulSoup: Flexible HTML parsing for diverse content types
Better than Selenium for performance, more reliable than simple requests

Vector Database: ChromaDB

Lightweight, embeddable vector database
Easy integration with LangChain
Good performance for moderate scale
Alternative: Weaviate for larger scale

Scheduler: APScheduler

Python-native scheduling with cron-like capabilities
Persistent job storage
Better than celery for simpler use cases

Database: PostgreSQL

Reliable ACID compliance
JSON support for flexible schema
Full-text search capabilities
Web Interface: Streamlit

Rapid prototyping and deployment
Built-in components for chat interfaces
Easy integration with Python backend


### Project Structure
```
└── 📁Assistant_Agent
    └── 📁config
        ├── config.yaml
        ├── requirements.txt
    └── 📁evaluation
        ├── __init__.py
        ├── content_metrics.py
        ├── evaluation_runner.py
        ├── performance_testing.py
        ├── query_metrics.py
        ├── system_health.py
    └── 📁src
        └── 📁agents
            ├── __init__.py
            ├── content_retriever.py
            ├── query_engine.py
            ├── summarizer.py
        └── 📁data
            ├── __init__.py
            ├── database.py
            ├── vector_store.py
        └── 📁services
            ├── __init__.py
            ├── email_service.py
            ├── scheduler.py
            ├── web_scraper.py
        └── 📁utils
            ├── __init__.py
            ├── config_manager.py
            ├── logging_config.py
        ├── __init__.py
        ├── main.py
    └── 📁tests
        └── 📁unit
            ├── __init__.py
            ├── test_config_manager.py
            ├── test_database.py
        ├── __init__.py
        ├── conftest.py
    └── 📁web
        ├── __init__.py
        ├── streamlit_app.py
    ├── __init__.py
    ├── .env
    ├── .gitignore
    ├── docker-compose.yml
    ├── init.sql
    └── ReadMe.md
```
Here's how the chat memory currently works:

1.  **Session-Based Storage**:

    *   Chat history is stored in Streamlit's `session_state` (`st.session_state.messages`)
    *   This state persists only while the browser tab remains open
    *   If you refresh the page or close the browser, the chat history is lost
2.  **In-Memory Processing**:

    *   For each query, we pass the current session's chat history to the query engine
    *   The query engine uses this history to provide context-aware responses
    *   But this memory isn't persisted anywhere permanently
