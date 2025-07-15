# src/evaluation/system_health.py
import psutil
import time
from datetime import datetime, timedelta
from src.evaluation.content_metrics import ContentRetrievalMetrics
from src.evaluation.query_metrics import QueryPerformanceMetrics

class SystemHealthMonitor:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.start_time = time.time()

    def get_system_metrics(self) -> dict:
        """Get current system performance metrics"""
        return {
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "uptime_hours": (time.time() - self.start_time) / 3600,
            "timestamp": datetime.now().isoformat()
        }

    def check_database_health(self) -> dict:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            # Simple connectivity test
            self.db_manager.get_active_urls()
            connection_time = time.time() - start_time

            # Check table sizes
            table_stats = self.db_manager.get_table_statistics()

            return {
                "status": "healthy",
                "connection_time_ms": connection_time * 1000,
                "table_statistics": table_stats,
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    def generate_health_report(self) -> dict:
        """Generate comprehensive health report"""
        return {
            "system_metrics": self.get_system_metrics(),
            "database_health": self.check_database_health(),
            "content_metrics": ContentRetrievalMetrics(self.db_manager).calculate_retrieval_success_rate(timedelta(days=1)),
            "query_metrics": QueryPerformanceMetrics(self.db_manager).calculate_response_metrics(timedelta(days=1))
        }
