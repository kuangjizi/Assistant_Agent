from datetime import datetime, timedelta


class QueryPerformanceMetrics:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def calculate_response_metrics(self, time_period: timedelta) -> dict:
        """Calculate query response performance"""
        since_date = datetime.now() - time_period
        query_logs = self.db_manager.get_query_logs(since_date)

        if not query_logs:
            return {"error": "No query logs found for the period"}

        response_times = [log['response_time'] for log in query_logs]
        confidence_distribution = {}

        for log in query_logs:
            conf = log['confidence']
            confidence_distribution[conf] = confidence_distribution.get(conf, 0) + 1

        return {
            "total_queries": len(query_logs),
            "avg_response_time": sum(response_times) / len(response_times),
            "median_response_time": sorted(response_times)[len(response_times)//2],
            "max_response_time": max(response_times),
            "confidence_distribution": confidence_distribution,
            "high_confidence_rate": confidence_distribution.get('High', 0) / len(query_logs)
        }

    def calculate_user_satisfaction(self, time_period: timedelta) -> dict:
        """Calculate user satisfaction metrics"""
        since_date = datetime.now() - time_period
        feedback_logs = self.db_manager.get_user_feedback(since_date)

        if not feedback_logs:
            return {"error": "No feedback data available"}

        positive_feedback = len([f for f in feedback_logs if f['rating'] >= 4])
        total_feedback = len(feedback_logs)

        return {
            "satisfaction_rate": positive_feedback / total_feedback,
            "total_feedback": total_feedback,
            "average_rating": sum(f['rating'] for f in feedback_logs) / total_feedback,
            "feedback_response_rate": total_feedback / self.db_manager.get_total_queries(since_date)
        }
