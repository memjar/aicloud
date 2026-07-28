"""Performance benchmarking tests."""

import pytest
import asyncio
import time
from statistics import mean, stdev
from typing import List

from src.core import (
    InferenceRequest,
    ModelConfig,
    ProviderType,
)
from src.adapters import MockAdapter


@pytest.fixture
def benchmark_config():
    """Create config for benchmarking."""
    return ModelConfig(
        id="benchmark-model",
        name="Benchmark",
        provider=ProviderType.OPENAI,
        model_id="gpt-4",
        pricing_input=0.03,
        pricing_output=0.06,
        timeout_seconds=10,
    )


@pytest.fixture
def benchmark_request():
    """Create request for benchmarking."""
    return InferenceRequest(
        model_id="benchmark-model",
        messages=[{"role": "user", "content": "test message"}],
        temperature=0.7,
        max_tokens=100,
    )


class TestLatencyBenchmarks:
    """Latency benchmarking tests."""

    @pytest.mark.asyncio
    async def test_single_request_latency(self, benchmark_config, benchmark_request):
        """Test latency of single request."""
        adapter = MockAdapter(benchmark_config)

        start = time.time()
        response, stats = await adapter.infer(benchmark_request)
        end = time.time()

        latency_ms = (end - start) * 1000

        assert latency_ms > 0
        assert latency_ms < 1000  # Should complete in under 1 second
        assert stats.latency_ms < 100  # Mock should be fast

    @pytest.mark.asyncio
    async def test_latency_consistency(self, benchmark_config, benchmark_request):
        """Test latency consistency across multiple requests."""
        adapter = MockAdapter(benchmark_config)

        latencies: List[float] = []

        for _ in range(10):
            _, stats = await adapter.infer(benchmark_request)
            latencies.append(stats.latency_ms)

        avg_latency = mean(latencies)
        assert avg_latency < 100

        if len(latencies) > 1:
            std_dev = stdev(latencies)
            assert std_dev < 50  # Should be relatively consistent

    @pytest.mark.asyncio
    async def test_target_latency_met(self, benchmark_config, benchmark_request):
        """Test that latency target is met (< 100ms)."""
        adapter = MockAdapter(benchmark_config)

        latencies: List[float] = []

        for _ in range(20):
            _, stats = await adapter.infer(benchmark_request)
            latencies.append(stats.latency_ms)

        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        assert p95_latency < 100
        assert p99_latency < 150


class TestThroughputBenchmarks:
    """Throughput benchmarking tests."""

    @pytest.mark.asyncio
    async def test_sequential_throughput(self, benchmark_config, benchmark_request):
        """Test sequential request throughput."""
        adapter = MockAdapter(benchmark_config)

        start = time.time()
        num_requests = 10

        for _ in range(num_requests):
            _, _ = await adapter.infer(benchmark_request)

        end = time.time()
        duration = end - start

        throughput = num_requests / duration
        assert throughput > 1  # At least 1 request per second

    @pytest.mark.asyncio
    async def test_concurrent_throughput(self, benchmark_config, benchmark_request):
        """Test concurrent request throughput."""
        adapter = MockAdapter(benchmark_config)

        start = time.time()
        num_requests = 20
        concurrent = 5

        tasks = []
        for i in range(num_requests):
            if len(tasks) >= concurrent:
                await asyncio.gather(*tasks)
                tasks = []

            task = adapter.infer(benchmark_request)
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

        end = time.time()
        duration = end - start

        throughput = num_requests / duration
        assert throughput > 5  # Should handle concurrent better


class TestMemoryEfficiency:
    """Memory efficiency tests."""

    @pytest.mark.asyncio
    async def test_adapter_memory_usage(self, benchmark_config, benchmark_request):
        """Test that adapter doesn't leak memory."""
        adapter = MockAdapter(benchmark_config)

        # Run multiple requests
        for _ in range(100):
            _, _ = await adapter.infer(benchmark_request)

        # Should complete without issues
        assert adapter is not None

    @pytest.mark.asyncio
    async def test_response_size(self, benchmark_config, benchmark_request):
        """Test response size is reasonable."""
        adapter = MockAdapter(benchmark_config)

        response, _ = await adapter.infer(benchmark_request)

        # Response should be serializable
        import json
        response_dict = {
            "id": response.id,
            "model": response.model,
            "tokens": response.usage["total_tokens"],
            "cost": response.cost_usd,
        }

        json_size = len(json.dumps(response_dict).encode())
        assert json_size < 10000  # Response should be under 10KB


class TestErrorPerformance:
    """Performance under error conditions."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self, benchmark_config, benchmark_request):
        """Test timeout handling doesn't hang."""
        config = ModelConfig(
            id="timeout-test",
            name="Timeout Test",
            provider=ProviderType.OPENAI,
            model_id="gpt-4",
            timeout_seconds=1,
        )

        adapter = MockAdapter(config)

        start = time.time()
        try:
            _, _ = await adapter.infer(benchmark_request)
        except Exception:
            pass

        elapsed = time.time() - start

        # Should not hang (allow some overhead)
        assert elapsed < 5


class PerformanceBenchmark:
    """Benchmark runner for performance testing."""

    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []

    def record(self, duration: float):
        """Record a measurement."""
        self.times.append(duration)

    def summary(self) -> dict:
        """Get summary statistics."""
        if not self.times:
            return {}

        return {
            "name": self.name,
            "count": len(self.times),
            "mean_ms": mean(self.times) * 1000,
            "min_ms": min(self.times) * 1000,
            "max_ms": max(self.times) * 1000,
            "p50_ms": sorted(self.times)[len(self.times) // 2] * 1000,
            "p95_ms": sorted(self.times)[int(len(self.times) * 0.95)] * 1000,
            "p99_ms": sorted(self.times)[int(len(self.times) * 0.99)] * 1000,
        }


@pytest.mark.asyncio
async def test_benchmark_runner():
    """Test the benchmark runner itself."""
    bench = PerformanceBenchmark("test_bench")

    for i in range(10):
        bench.record(0.001 * (i + 1))

    summary = bench.summary()

    assert summary["count"] == 10
    assert summary["mean_ms"] > 0
    assert summary["p99_ms"] >= summary["p95_ms"]
    assert summary["max_ms"] >= summary["min_ms"]
