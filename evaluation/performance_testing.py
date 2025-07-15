# src/evaluation/performance_testing.py
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

class PerformanceTester:
    def __init__(self, query_engine):
        self.query_engine = query_engine

    async def load_test_queries(self, test_queries: list, concurrent_users: int = 10) -> dict:
        """Perform load testing on query engine"""

        async def single_query_test(query: str) -> dict:
            start_time = time.time()
            try:
                result = await self.query_engine.answer_query(query)
                response_time = time.time() - start_time
                return {
                    "query": query,
                    "success": True,
                    "response_time": response_time,
                    "confidence": result.get("confidence", "Unknown")
                }
            except Exception as e:
                response_time = time.time() - start_time
                return {
                    "query": query,
                    "success": False,
                    "response_time": response_time,
                    "error": str(e)
                }

        # Create tasks for concurrent execution
        tasks = []
        for _ in range(concurrent_users):
            for query in test_queries:
                tasks.append(single_query_test(query))

        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        successful_queries = [r for r in results if r["success"]]
        failed_queries = [r for r in results if not r["success"]]

        response_times = [r["response_time"] for r in successful_queries]

        return {
            "total_queries": len(results),
            "successful_queries": len(successful_queries),
            "failed_queries": len(failed_queries),
            "success_rate": len(successful_queries) / len(results),
            "total_test_time": total_time,
            "queries_per_second": len(results) / total_time,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "median_response_time": statistics.median(response_times) if response_times else 0,
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
            "concurrent_users": concurrent_users
        }

    def stress_test_content_retrieval(self, urls: list, duration_minutes: int = 10) -> dict:
        """Stress test content retrieval system"""

        def retrieve_content_batch():
            start_time = time.time()
            try:
                # This would call your content retriever
                # For demo, we'll simulate
                time.sleep(random.uniform(1, 3))  # Simulate network delay
                return {
                    "success": True,
                    "response_time": time.time() - start_time,
                    "items_retrieved": random.randint(1, 5)
                }
            except Exception as e:
                return {
                    "success": False,
                    "response_time": time.time() - start_time,
                    "error": str(e)
                }

        results = []
        end_time = time.time() + (duration_minutes * 60)

        with ThreadPoolExecutor(max_workers=5) as executor:
            while time.time() < end_time:
                future = executor.submit(retrieve_content_batch)
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e),
                        "response_time": 30
                    })

                time.sleep(1)  # Wait between batches

        successful_retrievals = [r for r in results if r["success"]]

        return {
            "duration_minutes": duration_minutes,
            "total_attempts": len(results),
            "successful_attempts": len(successful_retrievals),
            "success_rate": len(successful_retrievals) / len(results),
            "avg_response_time": statistics.mean([r["response_time"] for r in successful_retrievals]),
            "total_items_retrieved": sum(r.get("items_retrieved", 0) for r in successful_retrievals)
        }
