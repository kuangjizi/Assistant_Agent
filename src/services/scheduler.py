# src/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import logging

class SchedulerService:
    def __init__(self, content_retriever, summarizer, email_service, db_manager):
        self.content_retriever = content_retriever
        self.summarizer = summarizer
        self.email_service = email_service
        self.db_manager = db_manager

        # Explicitly configure the scheduler to use threads
        executors = {
            'default': ThreadPoolExecutor(10) # 10 threads in the pool
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults
        )
        self.scheduler.configure(timezone='America/Los_Angeles')

    def start(self):
        """Start the scheduler"""
        self.scheduler.start()

        # Schedule daily content retrieval and summary
        self.scheduler.add_job(
            func=self.daily_content_update,
            trigger="cron",
            hour=8,  # 8 AM daily
            minute=0,
            id='daily_content_update',
            replace_existing=True
        )

        logging.info("Scheduler started successfully")

    async def daily_content_update(self):
        """Daily job to retrieve content and send summary"""
        try:
            logging.info("Starting daily content update...")

            # Get active URLs
            urls = [item['url'] for item in self.db_manager.get_active_urls()]

            if not urls:
                logging.warning("No active URLs to monitor")
                return

            # Retrieve new content
            new_content = await self.content_retriever.retrieve_content(urls)

            # Create summary
            summary_data = self.summarizer.create_daily_summary()

            # Send email if there's new content
            if summary_data['content_count'] > 0:
                await self.email_service.send_daily_summary(summary_data)
                logging.info(f"Daily summary sent: {summary_data['content_count']} new items")
            else:
                logging.info("No new content found today")

        except Exception as e:
            logging.error(f"Error in daily content update: {e}")

    def add_custom_job(self, func, trigger_config: dict, job_id: str):
        """Add custom scheduled job"""
        self.scheduler.add_job(
            func=func,
            trigger=trigger_config.get('trigger', 'cron'),
            **{k: v for k, v in trigger_config.items() if k != 'trigger'},
            id=job_id,
            replace_existing=True
        )

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
