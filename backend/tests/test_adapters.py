"""Tests for model provider adapters."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.core import (
    InferenceRequest,
    InferenceResponse,
    ModelConfig,
    ProviderType,
)
from src.adapters import (
    OpenAIAdapter,
    AnthropicAdapter,
    TogetherAIAdapter,
    MockAdapter,
    create_adapter,
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
        max_tokens=2048,
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
        max_tokens=2048,
    )


@pytest.fixture
def together_config():
    """Create Together.ai model config."""
    return ModelConfig(
        id="llama-2-test",
        name="Llama 2 70B",
        provider=ProviderType.TOGETHER,
        model_id="meta-llama/llama-2-70b-chat-hf",
        pricing_input=0.0009,
        pricing_output=0.0009,
        max_tokens=2048,
    )


@pytest.fixture
def test_request():
    """Create test inference request."""
    return InferenceRequest(
        model_id="test-model",
        messages=[
            {"role": "user", "content": "What is 2+2?"},
        ],
        temperature=0.7,
        max_tokens=100,
    )


class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    @pytest.mark.asyncio
    async def test_successful_inference(self, openai_config, test_request):
        """Test successful inference with OpenAI."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")

        mock_response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {"content": "4"},
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            response, stats = await adapter.infer(test_request)

            assert response.model == openai_config.id
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 5
            assert response.provider == ProviderType.OPENAI
            assert stats.success is True
            assert stats.input_tokens == 10
            assert stats.output_tokens == 5

            # Check cost calculation
            expected_cost = (10 / 1000) * 0.03 + (5 / 1000) * 0.06
            assert abs(stats.cost_usd - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_cost_calculation(self, openai_config, test_request):
        """Test cost calculation for OpenAI."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")

        cost = adapter.calculate_cost(100, 50)
        expected = (100 / 1000) * 0.03 + (50 / 1000) * 0.06
        assert abs(cost - expected) < 0.0001

    @pytest.mark.asyncio
    async def test_http_error_handling(self, openai_config, test_request):
        """Test HTTP error handling."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_post.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                await adapter.infer(test_request)

    @pytest.mark.asyncio
    async def test_adapter_cleanup(self, openai_config):
        """Test adapter cleanup."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")
        await adapter.close()
        # Verify no errors on close


class TestAnthropicAdapter:
    """Tests for Anthropic adapter."""

    @pytest.mark.asyncio
    async def test_successful_inference(self, anthropic_config, test_request):
        """Test successful inference with Anthropic."""
        adapter = AnthropicAdapter(anthropic_config, "test-api-key")

        mock_response = {
            "id": "msg-123",
            "content": [{"text": "4"}],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
            },
        }

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            response, stats = await adapter.infer(test_request)

            assert response.model == anthropic_config.id
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 5
            assert response.provider == ProviderType.ANTHROPIC
            assert stats.success is True

            # Check cost calculation (different from OpenAI)
            expected_cost = (10 / 1000) * 0.015 + (5 / 1000) * 0.075
            assert abs(stats.cost_usd - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_max_tokens_default(self, anthropic_config, test_request):
        """Test default max_tokens handling."""
        anthropic_config.max_tokens = None
        adapter = AnthropicAdapter(anthropic_config, "test-api-key")

        mock_response = {
            "id": "msg-123",
            "content": [{"text": "4"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            response, stats = await adapter.infer(test_request)
            assert response is not None


class TestTogetherAIAdapter:
    """Tests for Together.ai adapter."""

    @pytest.mark.asyncio
    async def test_successful_inference(self, together_config, test_request):
        """Test successful inference with Together.ai."""
        adapter = TogetherAIAdapter(together_config, "test-api-key")

        mock_response = {
            "id": "together-123",
            "choices": [{"message": {"content": "4"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            response, stats = await adapter.infer(test_request)

            assert response.provider == ProviderType.TOGETHER
            assert stats.input_tokens == 10
            assert stats.output_tokens == 5

            # Check cost calculation
            expected_cost = (10 / 1000) * 0.0009 + (5 / 1000) * 0.0009
            assert abs(stats.cost_usd - expected_cost) < 0.0001


class TestMockAdapter:
    """Tests for mock adapter."""

    @pytest.mark.asyncio
    async def test_mock_inference(self):
        """Test mock adapter inference."""
        config = ModelConfig(
            id="mock-test",
            name="Mock",
            provider=ProviderType.OPENAI,
            model_id="mock",
            pricing_input=0.001,
            pricing_output=0.001,
        )

        adapter = MockAdapter(config)

        request = InferenceRequest(
            model_id="mock-test",
            messages=[{"role": "user", "content": "test"}],
        )

        response, stats = await adapter.infer(request)

        assert response.model == "mock-test"
        assert stats.success is True
        assert response.latency_ms > 0
        assert len(response.choices) > 0

    @pytest.mark.asyncio
    async def test_mock_consistency(self):
        """Test mock adapter consistency."""
        config = ModelConfig(
            id="mock-test",
            name="Mock",
            provider=ProviderType.OPENAI,
            model_id="mock",
            pricing_input=0.01,
            pricing_output=0.01,
        )

        adapter = MockAdapter(config)

        request = InferenceRequest(
            model_id="mock-test",
            messages=[{"role": "user", "content": "hello world"}],
        )

        response1, stats1 = await adapter.infer(request)
        response2, stats2 = await adapter.infer(request)

        # Both should succeed
        assert response1 is not None
        assert response2 is not None


class TestAdapterFactory:
    """Tests for adapter factory."""

    def test_create_openai_adapter(self, openai_config):
        """Test creating OpenAI adapter."""
        adapter = create_adapter(openai_config, "test-key")
        assert isinstance(adapter, OpenAIAdapter)

    def test_create_anthropic_adapter(self, anthropic_config):
        """Test creating Anthropic adapter."""
        adapter = create_adapter(anthropic_config, "test-key")
        assert isinstance(adapter, AnthropicAdapter)

    def test_create_together_adapter(self, together_config):
        """Test creating Together adapter."""
        adapter = create_adapter(together_config, "test-key")
        assert isinstance(adapter, TogetherAIAdapter)

    def test_unsupported_provider(self):
        """Test unsupported provider."""
        config = ModelConfig(
            id="test",
            name="Test",
            provider=ProviderType.LOCAL,
            model_id="test",
        )

        with pytest.raises(ValueError, match="Unsupported provider"):
            create_adapter(config, "test-key")


class TestAdapterLatency:
    """Tests for adapter latency tracking."""

    @pytest.mark.asyncio
    async def test_latency_measurement(self, openai_config, test_request):
        """Test latency measurement."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")

        mock_response = {
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "4"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            response, stats = await adapter.infer(test_request)

            assert stats.latency_ms > 0
            assert response.latency_ms == stats.latency_ms
            assert response.provider_response_time_ms > 0


class TestAdapterRetries:
    """Tests for adapter retry logic."""

    @pytest.mark.asyncio
    async def test_error_on_retry_exhaustion(self, openai_config, test_request):
        """Test error when retries exhausted."""
        adapter = OpenAIAdapter(openai_config, "test-api-key")

        with patch.object(
            adapter.http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_post.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await adapter.infer(test_request)
