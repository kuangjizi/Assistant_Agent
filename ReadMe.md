## AI Assistant Agent

This project create an AI Assistant that uses Retrieval-Augmented Generation (RAG) to provide intelligent responses based on content it continuously monitors and retrieves from the specified websites. It's designed as a knowledge management and question-answering system with automated content retrieval, summarization, and email notifications.

### Key Features
------------

1.  **Blog-Aware Content Retrieval**: Specialized handling for blog sites, detecting index pages and extracting individual posts.

2. **Automated Summaries**: Generates daily and topic-specific summaries without user intervention.

3.  **Multi-Source Answers**: Combines information from the vector database with web search results.

4.  **Conversational Memory**: Maintains context across chat interactions within a session.

5.  **Admin Dashboard**: Provides system statistics and maintenance functions.


###  Core Functionality
------------------

1.  **Web Content Monitoring**: Automatically retrieves content from configured URLs, processes it, and stores it for later retrieval.

2.  **Intelligent Question Answering**: Uses RAG (Retrieval-Augmented Generation) to answer questions based on retrieved content, combining knowledge from its vector database with web search results.

3.  **Content Summarization**: Generates daily summaries and topic-specific summaries of newly retrieved content.

4.  **Email Notifications**: Sends automated email alerts, daily summaries, and topic summaries.

5.  **Chat Interface**: Provides a conversational interface with memory capabilities to maintain context across interactions.

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

### Frontend

*   **Web Interface (Streamlit)**: Provides a user-friendly interface for interacting with the system, including chat, summaries, and admin functions.

### Backend

*   **Query Engine**: Processes user questions using RAG techniques to provide accurate answers with source citations.
*   **Content Retriever**: Fetches and processes content from monitored URLs, including specialized handling for blog sites.
*   **Summarizer**: Creates daily and topic-based summaries of retrieved content.
*   **Scheduler**: Manages periodic tasks like content retrieval and summary generation.

### Data Storage

*   **PostgreSQL Database**: Stores URL configurations, content records, and query logs.
*   **Vector Store (ChromaDB)**: Stores vector embeddings of content for semantic search.

### Services

*   **Email Service**: Handles email notifications and summaries.
*   **Web Scraper**: Advanced web content extraction with specialized handling for different site types.

Technical Stack
---------------

*   **LangChain**: Core framework for RAG capabilities and LLM integration
*   **ChromaDB**: Vector database for semantic search
*   **PostgreSQL**: Relational database for structured data
*   **Streamlit**: Web interface framework
*   **APScheduler**: Task scheduling
*   **BeautifulSoup & Requests**: Web content extraction
*   **Google Generative AI**: LLM provider for text generation and embeddings



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
