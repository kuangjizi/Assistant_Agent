# src/evaluation/evaluation_runner.py
import schedule
import time
from datetime import datetime, timedelta

class EvaluationRunner:
    def __init__(self, db_manager, query_engine, content_retriever):
        self.db_manager = db_manager
        self.query_engine = query_engine
        self.content_retriever = content_retriever

        # Initialize evaluation components
        self.content_metrics = ContentRetrievalMetrics(db_manager)
        self.query_metrics = QueryPerformanceMetrics(db_manager)
        self.health_monitor = SystemHealthMonitor(db_manager)
        self.performance_tester = PerformanceTester(query_engine)

    def run_daily_evaluation(self):
        """Run comprehensive daily evaluation"""

        evaluation_results = {
            "date": datetime.now().isoformat(),
            "content_retrieval": self.content_metrics.calculate_retrieval_success_rate(timedelta(days=1)),
            "content_freshness": self.content_metrics.calculate_content_freshness(),
            "query_performance": self.query_metrics.calculate_response_metrics(timedelta(days=1)),
            "user_satisfaction": self.query_metrics.calculate_user_satisfaction(timedelta(days=1)),
            "system_health": self.health_monitor.generate_health_report()
        }

        # Store evaluation results
        self.db_manager.store_evaluation_results(evaluation_results)

        # Check for alerts
        self._check_performance_alerts(evaluation_results)

        return evaluation_results

    def run_weekly_performance_test(self):
        """Run weekly performance testing"""

        # Standard test queries
        test_queries = [
            "What are the latest developments in AI?",
            "Summarize recent technology trends",
            "What are the key market updates?",
            "Explain the recent policy changes"
        ]

        # Run load test
        load_test_results = asyncio.run(
            self.performance_tester.load_test_queries(test_queries, concurrent_users=5)
        )

        # Store results
        self.db_manager.store_performance_test_results(load_test_results)

        return load_test_results

    def _check_performance_alerts(self, results: dict):
        """Check for performance issues and send alerts"""

        alerts = []

        # Check success rates
        if results["content_retrieval"]["success_rate"] < 0.8:
            alerts.append("Content retrieval success rate below 80%")

        if results["query_performance"]["high_confidence_rate"] < 0.6:
            alerts.append("Query confidence rate below 60%")

        # Check response times
        if results["query_performance"]["avg_response_time"] > 5.0:
            alerts.append("Average query response time above 5 seconds")

        # Check system health
        if results["system_health"]["system_metrics"]["cpu_usage_percent"] > 80:
            alerts.append("High CPU usage detected")

        if results["system_health"]["system_metrics"]["memory_usage_percent"] > 85:
            alerts.append("High memory usage detected")

        # Send alerts if any issues found
        if alerts:
            self._send_performance_alerts(alerts)

    def _send_performance_alerts(self, alerts: list):
        """Send performance alerts to administrators"""
        # This would integrate with your alerting system
        # For now, just log the alerts
        for alert in alerts:
            logging.warning(f"PERFORMANCE ALERT: {alert}")

    def start_scheduled_evaluation(self):
        """Start scheduled evaluation jobs"""

        # Daily evaluation at 9 AM
        schedule.every().day.at("09:00").do(self.run_daily_evaluation)

        # Weekly performance test on Sundays at 2 AM
        schedule.every().sunday.at("02:00").do(self.run_weekly_performance_test)

        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
