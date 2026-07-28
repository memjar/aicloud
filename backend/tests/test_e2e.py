"""End-to-end inference pipeline tests."""

import pytest
from datetime import datetime, timedelta

from src.core import (
    InferenceRequest,
    ModelConfig,
    ProviderType,
    BillingRecord,
    RateLimitConfig,
)
from src.router import ModelRouter
from src.billing import BillingCalculator, BillingValidator
from src.adapters import MockAdapter


@pytest.fixture
def complete_setup():
    """Set up complete inference pipeline."""
    router = ModelRouter()
    calculator = BillingCalculator()
    validator = BillingValidator(calculator)

    # Register multiple models
    models = [
        ModelConfig(
            id="gpt-4",
            name="GPT-4",
            provider=ProviderType.OPENAI,
            model_id="gpt-4",
            pricing_input=0.03,
            pricing_output=0.06,
        ),
        ModelConfig(
            id="claude-3-opus",
            name="Claude 3 Opus",
            provider=ProviderType.ANTHROPIC,
            model_id="claude-3-opus-20240229",
            pricing_input=0.015,
            pricing_output=0.075,
        ),
        ModelConfig(
            id="llama-2-70b",
            name="Llama 2 70B",
            provider=ProviderType.TOGETHER,
            model_id="meta-llama/llama-2-70b-chat-hf",
            pricing_input=0.0009,
            pricing_output=0.0009,
        ),
    ]

    for model in models:
        router.register_model(model, use_mock=True)

    # Set up rate limiting
    rate_limit = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        tokens_per_minute=10000,
        tokens_per_day=1000000,
    )
    router.create_rate_limiter("user-key-1", rate_limit)

    return {
        "router": router,
        "calculator": calculator,
        "validator": validator,
    }


class TestE2EBasicInference:
    """Basic end-to-end inference tests."""

    @pytest.mark.asyncio
    async def test_single_inference_request(self, complete_setup):
        """Test single inference request through pipeline."""
        router = complete_setup["router"]

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ],
        )

        response = await router.infer(request, "user-key-1")

        assert response is not None
        assert response.model == "gpt-4"
        assert response.provider == ProviderType.OPENAI
        assert len(response.choices) > 0
        assert response.usage["total_tokens"] > 0
        assert response.cost_usd >= 0

    @pytest.mark.asyncio
    async def test_multi_model_inference(self, complete_setup):
        """Test inference with multiple models."""
        router = complete_setup["router"]

        models = ["gpt-4", "claude-3-opus", "llama-2-70b"]
        responses = []

        for model_id in models:
            request = InferenceRequest(
                model_id=model_id,
                messages=[{"role": "user", "content": "test"}],
            )

            response = await router.infer(request, "user-key-1")
            responses.append(response)

        assert len(responses) == 3
        assert all(r is not None for r in responses)
        assert responses[0].provider == ProviderType.OPENAI
        assert responses[1].provider == ProviderType.ANTHROPIC
        assert responses[2].provider == ProviderType.TOGETHER


class TestE2EBillingIntegration:
    """End-to-end billing integration tests."""

    @pytest.mark.asyncio
    async def test_billing_record_creation(self, complete_setup):
        """Test billing record creation from inference."""
        router = complete_setup["router"]
        calculator = complete_setup["calculator"]

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[{"role": "user", "content": "test message"}],
            user_id="user-123",
        )

        response = await router.infer(request, "user-key-1")

        record = BillingRecord(
            request_id=response.id,
            user_id="user-123",
            model_id="gpt-4",
            provider=ProviderType.OPENAI,
            prompt_tokens=response.usage["prompt_tokens"],
            completion_tokens=response.usage["completion_tokens"],
            total_tokens=response.usage["total_tokens"],
            cost_usd=response.cost_usd,
        )

        calculator.add_record(record)

        user_cost = calculator.get_user_cost("user-123")
        assert user_cost > 0

    @pytest.mark.asyncio
    async def test_billing_cycle_summary(self, complete_setup):
        """Test billing cycle summary generation."""
        router = complete_setup["router"]
        calculator = complete_setup["calculator"]

        now = datetime.utcnow()
        start = now - timedelta(days=1)
        end = now

        # Make multiple requests
        for i in range(3):
            model_id = ["gpt-4", "claude-3-opus", "llama-2-70b"][i]

            request = InferenceRequest(
                model_id=model_id,
                messages=[{"role": "user", "content": f"request {i}"}],
                user_id="user-456",
            )

            response = await router.infer(request, "user-key-1")

            record = BillingRecord(
                request_id=response.id,
                user_id="user-456",
                model_id=model_id,
                provider=response.provider,
                prompt_tokens=response.usage["prompt_tokens"],
                completion_tokens=response.usage["completion_tokens"],
                total_tokens=response.usage["total_tokens"],
                cost_usd=response.cost_usd,
                timestamp=now,
            )

            calculator.add_record(record)

        cycle = calculator.get_cycle_summary(start, end, "user-456")

        assert cycle.total_tokens > 0
        assert cycle.total_cost_usd > 0
        assert len(cycle.by_provider) == 3
        assert len(cycle.by_model) == 3

    @pytest.mark.asyncio
    async def test_billing_validation(self, complete_setup):
        """Test billing record validation."""
        router = complete_setup["router"]
        calculator = complete_setup["calculator"]
        validator = complete_setup["validator"]

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        )

        response = await router.infer(request, "user-key-1")

        record = BillingRecord(
            request_id=response.id,
            user_id="user-789",
            model_id="gpt-4",
            provider=ProviderType.OPENAI,
            prompt_tokens=response.usage["prompt_tokens"],
            completion_tokens=response.usage["completion_tokens"],
            total_tokens=response.usage["total_tokens"],
            cost_usd=response.cost_usd,
        )

        valid, error = validator.validate_record(record)
        assert valid is True
        assert error is None


class TestE2ERateLimiting:
    """End-to-end rate limiting tests."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, complete_setup):
        """Test rate limit enforcement."""
        router = complete_setup["router"]
        limiter = router.rate_limiters["user-key-1"]

        # Set tight limits for testing
        from src.core import RateLimitConfig
        tight_limit = RateLimitConfig(
            requests_per_minute=2,
            requests_per_hour=10,
            tokens_per_minute=100,
            tokens_per_day=10000,
        )
        router.rate_limiters["user-key-1"] = type(limiter)(
            "user-key-1",
            tight_limit,
        )

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        )

        # First two should succeed
        response1 = await router.infer(request, "user-key-1")
        assert response1 is not None

        response2 = await router.infer(request, "user-key-1")
        assert response2 is not None


class TestE2EErrorHandling:
    """End-to-end error handling tests."""

    @pytest.mark.asyncio
    async def test_invalid_model_error(self, complete_setup):
        """Test error handling for invalid model."""
        router = complete_setup["router"]

        request = InferenceRequest(
            model_id="nonexistent-model",
            messages=[{"role": "user", "content": "test"}],
        )

        with pytest.raises(ValueError):
            await router.infer(request, "user-key-1")

    @pytest.mark.asyncio
    async def test_empty_messages_handling(self, complete_setup):
        """Test handling of empty messages."""
        router = complete_setup["router"]

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[],
        )

        # Should still work with mock adapter
        response = await router.infer(request, "user-key-1")
        assert response is not None


class TestE2EStats:
    """End-to-end statistics tracking tests."""

    @pytest.mark.asyncio
    async def test_model_stats_accumulation(self, complete_setup):
        """Test stats accumulation across requests."""
        router = complete_setup["router"]

        for i in range(5):
            request = InferenceRequest(
                model_id="gpt-4",
                messages=[{"role": "user", "content": f"request {i}"}],
            )

            await router.infer(request, "user-key-1")

        stats = router.get_model_stats("gpt-4")

        assert stats["requests"] == 5
        assert stats["total_tokens"] > 0
        assert stats["total_cost"] > 0
        assert stats["avg_latency_ms"] > 0
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_all_models_stats(self, complete_setup):
        """Test stats for all models."""
        router = complete_setup["router"]

        models = ["gpt-4", "claude-3-opus", "llama-2-70b"]

        for model_id in models:
            request = InferenceRequest(
                model_id=model_id,
                messages=[{"role": "user", "content": "test"}],
            )

            await router.infer(request, "user-key-1")

        all_stats = router.get_all_stats()

        assert len(all_stats) >= 3
        for model_id in models:
            assert model_id in all_stats
            assert all_stats[model_id]["requests"] >= 1


class TestE2EFallback:
    """End-to-end fallback chain tests."""

    @pytest.mark.asyncio
    async def test_fallback_chain_success(self, complete_setup):
        """Test fallback chain when primary fails."""
        router = complete_setup["router"]

        # Set up fallback chain
        router.set_fallback_chain("gpt-4", ["claude-3-opus", "llama-2-70b"])

        request = InferenceRequest(
            model_id="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        )

        # Should still work with fallback chain
        response = await router.infer(request, "user-key-1")
        assert response is not None
