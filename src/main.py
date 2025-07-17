# src/main.py
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent))

from utils.config_manager import get_config
from utils.logging_config import setup_logging
from data.database import DatabaseManager
from data.vector_store import VectorStoreManager
from agents.content_retriever import ContentRetriever
from agents.query_engine import QueryEngine
from agents.summarizer import Summarizer
from services.scheduler import SchedulerService
from services.email_service import EmailService

class AIAssistantApp:
    def __init__(self):
        self.config = get_config(config_path="config/config.yaml")
        setup_logging(self.config.get('system.log_level'))
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.db_manager = None
        self.vector_store = None
        self.content_retriever = None
        self.query_engine = None
        self.summarizer = None
        self.scheduler = None
        self.email_service = None

    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("Initializing AI Assistant Application...")

            # Database
            self.db_manager = DatabaseManager(self.config.database_url)
            self.logger.info("Database manager initialized")

            # Vector Store
            self.vector_store = VectorStoreManager(
                persist_directory=self.config.vector_store_config['path'],
                collection_name=self.config.vector_store_config['collection_name']
            )
            self.logger.info("Vector store initialized")

            # Email Service
            self.email_service = EmailService(self.config.email_config)
            self.logger.info("Email service initialized")

            # Content Retriever
            self.content_retriever = ContentRetriever(
                vector_store=self.vector_store,
                db_manager=self.db_manager,
                # config=self.config
            )
            self.logger.info("Content retriever initialized")

            # Query Engine
            self.query_engine = QueryEngine(
                vector_store=self.vector_store,
                model_config=self.config.google_model_config
            )
            self.logger.info("Query engine initialized")

            # Summarizer
            self.summarizer = Summarizer(
                db_manager=self.db_manager,
                model_config=self.config.google_model_config
            )
            self.logger.info("Summarizer initialized")

            # Scheduler
            self.scheduler = SchedulerService(
                content_retriever=self.content_retriever,
                summarizer=self.summarizer,
                email_service=self.email_service,
                db_manager=self.db_manager
            )
            self.logger.info("Scheduler initialized")

            self.logger.info("All components initialized successfully!")

        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            raise

    async def start_services(self):
        """Start background services"""
        try:
            self.logger.info("Starting background services...")

            # Start scheduler
            self.scheduler.start()
            self.logger.info("Scheduler started")

            # Run initial content update
            await self.run_initial_setup()

            self.logger.info("All services started successfully!")

        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            raise

    async def run_initial_setup(self):
        """Run initial content retrieval"""
        try:
            self.logger.info("Running initial content retrieval...")

            urls = self.db_manager.get_active_urls()
            if urls:
                url_list = [url_info['url'] for url_info in urls]
                await self.content_retriever.retrieve_content(url_list)
                self.logger.info(f"Initial content retrieval completed for {len(url_list)} URLs")
            else:
                self.logger.warning("No URLs configured for monitoring")

        except Exception as e:
            self.logger.error(f"Initial setup failed: {e}")

    def stop_services(self):
        """Stop all services"""
        if self.scheduler:
            self.scheduler.stop()
        self.logger.info("Services stopped")

async def main():
    """Main application entry point"""
    app = AIAssistantApp()

    try:
        await app.initialize()
        await app.start_services()

        # Keep the application running
        print("AI Assistant is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        print("\nShutting down...")
        app.stop_services()
    except Exception as e:
        logging.error(f"Application error: {e}")
        app.stop_services()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
