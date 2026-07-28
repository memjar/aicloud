"""Tests for model routing and rate limiting."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core import (
    InferenceRequest,
    ModelConfig,
    ProviderType,
    RateLimitConfig,
)
from src.router import ModelRouter, RateLimitTracker


@pytest.fixture
def router():
    """Create model router."""
    return ModelRouter()


@pytest.fixture
def rate_limit_config():
    """Create rate limit config."""
    return RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        tokens_per_minute=10000,
        tokens_per_day=1000000,
        concurrent_requests=10,
    )


@pytest.fixture
def openai_config():
    """Create OpenAI model config."""
    return ModelConfig(
        id="gpt-4-test",
        name="GPT-4",
        provider=ProviderType.OPENAI,
        model_id="gpt-4",
        pricing_input=0.03,
        pricing_output=0.06,
    )


@pytest.fixture
def anthropic_config():
    """Create Anthropic model config."""
    return ModelConfig(
        id="claude-3-test",
        name="Claude 3",
        provider=ProviderType.ANTHROPIC,
        model_id="claude-3-opus-20240229",
        pricing_input=0.015,
        pricing_output=0.075,
    )


class TestModelRouter:
    """Tests for model router."""

    def test_register_model(self, router, openai_config):
        """Test model registration."""
        router.register_model(openai_config, use_mock=True)

        assert "gpt-4-test" in router.models
        assert router.models["gpt-4-test"] == openai_config

    def test_register_multiple_models(self, router, openai_config, anthropic_config):
        """Test registering multiple models."""
        router.register_model(openai_config, use_mock=True)
        router.register_model(anthropic_config, use_mock=True)

        assert len(router.models) == 2
        assert "gpt-4-test" in router.models
        assert "claude-3-test" in router.models

    def test_model_not_found(self, router):
        """Test inference with non-existent model."""
        request = InferenceRequest(
            model_id="nonexistent",
            messages=[{"role": "user", "content": "test"}],
        )

        with pytest.raises(ValueError, match="Model nonexistent not found"):
            import asyncio
            asyncio.run(router.infer(request, "test-key"))

    @pytest.mark.asyncio
    async def test_successful_inference(self, router, openai_config):
        """Test successful inference."""
        router.register_model(openai_config, use_mock=True)

        request = InferenceRequest(
            model_id="gpt-4-test",
            messages=[{"role": "user", "content": "test"}],
        )

        response = await router.infer(request, "test-key")

        assert response is not None
        assert response.model == "gpt-4-test"
        assert len(response.choices) > 0

    @pytest.mark.asyncio
    async def test_stats_tracking(self, router, openai_config):
        """Test statistics tracking."""
        router.register_model(openai_config, use_mock=True)

        request = InferenceRequest(
            model_id="gpt-4-test",
            messages=[{"role": "user", "content": "test message"}],
        )

        await router.infer(request, "test-key")

        stats = router.get_model_stats("gpt-4-test")
        assert stats["requests"] == 1
        assert stats["total_tokens"] > 0
        assert stats["avg_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_multiple_requests_stats(self, router, openai_config):
        """Test stats accumulation across requests."""
        router.register_model(openai_config, use_mock=True)

        request = InferenceRequest(
            model_id="gpt-4-test",
            messages=[{"role": "user", "content": "test"}],
        )

        for _ in range(3):
            await router.infer(request, "test-key")

        stats = router.get_model_stats("gpt-4-test")
        assert stats["requests"] == 3

    def test_fallback_chain(self, router, openai_config, anthropic_config):
        """Test fallback model chain."""
        router.register_model(openai_config, use_mock=True)
        router.register_model(anthropic_config, use_mock=True)

        router.set_fallback_chain("gpt-4-test", ["claude-3-test"])

        assert "gpt-4-test" in router.fallback_models
        assert "claude-3-test" in router.fallback_models["gpt-4-test"]

    @pytest.mark.asyncio
    async def test_health_check(self, router, openai_config):
        """Test health check."""
        router.register_model(openai_config, use_mock=True)

        health = await router.health_check()

        assert "gpt-4-test" in health
        assert health["gpt-4-test"] is True

    def test_get_all_stats(self, router, openai_config, anthropic_config):
        """Test getting all stats."""
        router.register_model(openai_config, use_mock=True)
        router.register_model(anthropic_config, use_mock=True)

        all_stats = router.get_all_stats()

        assert len(all_stats) >= 2
        assert "gpt-4-test" in all_stats
        assert "claude-3-test" in all_stats


class TestRateLimitTracker:
    """Tests for rate limit tracking."""

    def test_rate_limit_creation(self, rate_limit_config):
        """Test rate limiter creation."""
        tracker = RateLimitTracker("key-1", rate_limit_config)

        assert tracker.key_id == "key-1"
        assert tracker.requests_this_minute == 0
        assert tracker.concurrent_requests == 0

    def test_requests_per_minute_limit(self, rate_limit_config):
        """Test request per minute limit."""
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=100,
            tokens_per_minute=10000,
            tokens_per_day=1000000,
        )
        tracker = RateLimitTracker("key-1", config)

        # Should allow up to 5 requests
        for i in range(5):
            allowed, error = tracker.check_and_update(10, 10)
            assert allowed is True
            assert error is None

        # 6th request should be denied
        allowed, error = tracker.check_and_update(10, 10)
        assert allowed is False
        assert "requests per minute" in error

    def test_tokens_per_minute_limit(self):
        """Test tokens per minute limit."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            tokens_per_minute=100,
            tokens_per_day=1000000,
        )
        tracker = RateLimitTracker("key-1", config)

        # Should allow up to 100 tokens
        allowed, error = tracker.check_and_update(50, 50)
        assert allowed is True

        # Next request exceeds limit
        allowed, error = tracker.check_and_update(40, 20)
        assert allowed is False
        assert "tokens per minute" in error

    def test_concurrent_request_limit(self):
        """Test concurrent request limit."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            tokens_per_minute=10000,
            tokens_per_day=1000000,
            concurrent_requests=2,
        )
        tracker = RateLimitTracker("key-1", config)

        # Allow 2 concurrent
        allowed, _ = tracker.check_and_update(10, 10)
        assert allowed is True

        allowed, _ = tracker.check_and_update(10, 10)
        assert allowed is True

        # 3rd should fail
        allowed, error = tracker.check_and_update(10, 10)
        assert allowed is False
        assert "concurrent" in error

    def test_release_concurrent(self):
        """Test releasing concurrent request slot."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            tokens_per_minute=10000,
            tokens_per_day=1000000,
            concurrent_requests=1,
        )
        tracker = RateLimitTracker("key-1", config)

        # Use the slot
        allowed, _ = tracker.check_and_update(10, 10)
        assert allowed is True

        # Next should fail
        allowed, _ = tracker.check_and_update(10, 10)
        assert allowed is False

        # Release
        tracker.release_concurrent()

        # Now should succeed
        allowed, _ = tracker.check_and_update(10, 10)
        assert allowed is True

    def test_time_window_reset(self, rate_limit_config):
        """Test time window reset."""
        tracker = RateLimitTracker("key-1", rate_limit_config)

        # Use up requests
        for _ in range(60):
            tracker.check_and_update(1, 1)

        # Next should fail
        allowed, error = tracker.check_and_update(1, 1)
        assert allowed is False

        # Simulate time passing
        tracker.last_reset_minute = datetime.utcnow() - timedelta(seconds=61)

        # Should reset and allow
        tracker.reset_if_needed()
        allowed, _ = tracker.check_and_update(1, 1)
        assert allowed is True

    def test_tokens_per_day_limit(self):
        """Test tokens per day limit."""
        config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=100000,
            tokens_per_minute=1000000,
            tokens_per_day=100,
        )
        tracker = RateLimitTracker("key-1", config)

        # Use up daily limit
        allowed, _ = tracker.check_and_update(50, 50)
        assert allowed is True

        # Next should fail
        allowed, error = tracker.check_and_update(1, 1)
        assert allowed is False
        assert "tokens per day" in error

    def test_requests_per_hour_limit(self):
        """Test requests per hour limit."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=5,
            tokens_per_minute=100000,
            tokens_per_day=1000000,
        )
        tracker = RateLimitTracker("key-1", config)

        # Allow 5 requests per hour
        for _ in range(5):
            allowed, _ = tracker.check_and_update(1, 1)
            assert allowed is True

        # 6th should fail
        allowed, error = tracker.check_and_update(1, 1)
        assert allowed is False
        assert "requests per hour" in error


class TestModelRouterWithRateLimiting:
    """Integration tests for router with rate limiting."""

    def test_router_rate_limiting(self, router, openai_config, rate_limit_config):
        """Test rate limiting in router."""
        router.register_model(openai_config, use_mock=True)
        router.create_rate_limiter("key-1", rate_limit_config)

        limiter = router.rate_limiters["key-1"]
        assert limiter is not None
        assert limiter.key_id == "key-1"
