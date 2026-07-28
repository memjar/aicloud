"""Load testing scripts for inference pipeline."""

import asyncio
import time
import json
import argparse
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from statistics import mean, stdev
from datetime import datetime

from src.core import (
    InferenceRequest,
    ModelConfig,
    ProviderType,
)
from src.router import ModelRouter
from src.adapters import MockAdapter


@dataclass
class LoadTestResult:
    """Result of a load test."""
    test_name: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    requests_per_second: float
    mean_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in asdict(self).items()
        }


class LoadTester:
    """Load testing utility."""

    def __init__(self, router: ModelRouter, num_workers: int = 5):
        self.router = router
        self.num_workers = num_workers
        self.latencies: List[float] = []
        self.errors: List[str] = []

    async def run_concurrent_requests(
        self,
        num_requests: int,
        model_id: str,
        messages: List[Dict[str, str]],
    ) -> LoadTestResult:
        """Run concurrent inference requests."""
        start_time = datetime.utcnow()
        start = time.time()

        tasks = []
        successful = 0
        failed = 0

        for i in range(num_requests):
            request = InferenceRequest(
                model_id=model_id,
                messages=messages,
                request_id=f"load-test-{i}",
            )

            task = self._run_request(request)
            tasks.append(task)

            if len(tasks) >= self.num_workers:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        failed += 1
                        self.errors.append(str(result))
                    elif result is not None:
                        successful += 1

                tasks = []

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    self.errors.append(str(result))
                elif result is not None:
                    successful += 1

        end = time.time()
        end_time = datetime.utcnow()
        duration = end - start

        return self._create_result(
            test_name=f"concurrent_{num_requests}",
            start_time=start_time,
            end_time=end_time,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_duration_seconds=duration,
        )

    async def run_sequential_requests(
        self,
        num_requests: int,
        model_id: str,
        messages: List[Dict[str, str]],
    ) -> LoadTestResult:
        """Run sequential inference requests."""
        start_time = datetime.utcnow()
        start = time.time()

        successful = 0
        failed = 0

        for i in range(num_requests):
            request = InferenceRequest(
                model_id=model_id,
                messages=messages,
                request_id=f"load-test-seq-{i}",
            )

            try:
                await self._run_request(request)
                successful += 1
            except Exception as e:
                failed += 1
                self.errors.append(str(e))

        end = time.time()
        end_time = datetime.utcnow()
        duration = end - start

        return self._create_result(
            test_name=f"sequential_{num_requests}",
            start_time=start_time,
            end_time=end_time,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_duration_seconds=duration,
        )

    async def _run_request(self, request: InferenceRequest) -> bool:
        """Run a single request and measure latency."""
        start = time.time()

        try:
            response = await self.router.infer(request, "test-key")
            latency = time.time() - start

            self.latencies.append(latency)
            return True

        except Exception as e:
            self.errors.append(str(e))
            return False

    def _create_result(
        self,
        test_name: str,
        start_time: datetime,
        end_time: datetime,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        total_duration_seconds: float,
    ) -> LoadTestResult:
        """Create load test result."""
        rps = total_requests / total_duration_seconds if total_duration_seconds > 0 else 0

        if self.latencies:
            latencies_ms = [l * 1000 for l in self.latencies]
            mean_latency = mean(latencies_ms)
            min_latency = min(latencies_ms)
            max_latency = max(latencies_ms)
            sorted_latencies = sorted(latencies_ms)
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        else:
            mean_latency = 0
            min_latency = 0
            max_latency = 0
            p95 = 0
            p99 = 0

        return LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_duration_seconds=total_duration_seconds,
            requests_per_second=rps,
            mean_latency_ms=mean_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            errors=self.errors,
        )

    def reset(self):
        """Reset state for next test."""
        self.latencies = []
        self.errors = []


async def run_load_tests(
    num_requests: int = 100,
    num_workers: int = 5,
    output_file: str = None,
) -> List[LoadTestResult]:
    """Run comprehensive load tests."""
    router = ModelRouter()

    config = ModelConfig(
        id="load-test-model",
        name="Load Test",
        provider=ProviderType.OPENAI,
        model_id="gpt-4",
        pricing_input=0.03,
        pricing_output=0.06,
    )

    router.register_model(config, use_mock=True)

    tester = LoadTester(router, num_workers)
    results: List[LoadTestResult] = []

    messages = [{"role": "user", "content": "Test message for load testing"}]

    print(f"Running load tests with {num_requests} requests...")
    print()

    # Test 1: Sequential
    print("Test 1: Sequential requests...")
    tester.reset()
    result = await tester.run_sequential_requests(
        num_requests // 2,
        "load-test-model",
        messages,
    )
    results.append(result)
    print(f"  Requests/sec: {result.requests_per_second:.2f}")
    print(f"  Mean latency: {result.mean_latency_ms:.2f}ms")
    print(f"  P99 latency: {result.p99_latency_ms:.2f}ms")
    print()

    # Test 2: Concurrent with 5 workers
    print("Test 2: Concurrent requests (5 workers)...")
    tester.reset()
    result = await tester.run_concurrent_requests(
        num_requests,
        "load-test-model",
        messages,
    )
    results.append(result)
    print(f"  Requests/sec: {result.requests_per_second:.2f}")
    print(f"  Mean latency: {result.mean_latency_ms:.2f}ms")
    print(f"  P99 latency: {result.p99_latency_ms:.2f}ms")
    print()

    # Test 3: Concurrent with 20 workers
    print("Test 3: Concurrent requests (20 workers)...")
    tester.num_workers = 20
    tester.reset()
    result = await tester.run_concurrent_requests(
        num_requests,
        "load-test-model",
        messages,
    )
    results.append(result)
    print(f"  Requests/sec: {result.requests_per_second:.2f}")
    print(f"  Mean latency: {result.mean_latency_ms:.2f}ms")
    print(f"  P99 latency: {result.p99_latency_ms:.2f}ms")
    print()

    if output_file:
        with open(output_file, "w") as f:
            json.dump(
                [r.to_dict() for r in results],
                f,
                indent=2,
            )
        print(f"Results saved to {output_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run load tests")
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent workers",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results",
    )

    args = parser.parse_args()

    results = asyncio.run(run_load_tests(
        num_requests=args.requests,
        num_workers=args.workers,
        output_file=args.output,
    ))

    print("Load testing complete!")
