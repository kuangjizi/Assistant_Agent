
from datetime import datetime, timedelta

class ContentRetrievalMetrics:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    class ContentRetrievalMetrics:
        def __init__(self, db_manager):
            self.db_manager = db_manager

        def calculate_retrieval_success_rate(self, time_period: timedelta) -> dict:
            """Calculate success rate of content retrieval"""
            since_date = datetime.now() - time_period

            # Get retrieval attempts and successes
            attempts = self.db_manager.get_retrieval_attempts(since_date)
            successes = self.db_manager.get_successful_retrievals(since_date)

            success_rate = len(successes) / len(attempts) if attempts else 0

            return {
                "success_rate": success_rate,
                "total_attempts": len(attempts),
                "successful_retrievals": len(successes),
                "failed_retrievals": len(attempts) - len(successes),
                "period": str(time_period)
            }

    def calculate_content_freshness(self) -> dict:
        """Measure how fresh the content is"""
        urls = self.db_manager.get_active_urls()
        freshness_scores = []

        for url_info in urls:
            last_update = self.db_manager.get_last_content_update(url_info['url'])
            if last_update:
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                freshness_score = max(0, 1 - (hours_since_update / 24))  # Decay over 24 hours
                freshness_scores.append(freshness_score)

        avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0

        return {
            "average_freshness": avg_freshness,
            "monitored_urls": len(urls),
            "urls_with_recent_updates": len([s for s in freshness_scores if s > 0.5])
        }
