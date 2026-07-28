"""Provider adapters for multiple LLM services."""

import asyncio
import time
import random
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx

from core import (
    InferenceRequest,
    InferenceResponse,
    ErrorResponse,
    ModelConfig,
    ProviderType,
    BillingRecord,
)


@dataclass
class AdapterStats:
    """Statistics for an adapter call."""
    provider: ProviderType
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    success: bool
    error: Optional[str] = None


class BaseAdapter(ABC):
    """Base class for model provider adapters."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=config.timeout_seconds)

    @abstractmethod
    async def infer(
        self,
        request: InferenceRequest,
    ) -> tuple[InferenceResponse, AdapterStats]:
        """Run inference on the model."""
        pass

    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost based on token usage."""
        input_cost = (prompt_tokens / 1000) * self.config.pricing_input
        output_cost = (completion_tokens / 1000) * self.config.pricing_output
        return input_cost + output_cost

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI API."""

    def __init__(self, config: ModelConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.api_base = "https://api.openai.com/v1"

    async def infer(
        self,
        request: InferenceRequest,
    ) -> tuple[InferenceResponse, AdapterStats]:
        """Call OpenAI API."""
        start_time = time.time()

        payload = {
            "model": self.config.model_id,
            "messages": request.messages,
            "temperature": request.temperature or self.config.temperature,
            "max_tokens": request.max_tokens or self.config.max_tokens,
        }

        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            payload["stop"] = request.stop

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http_client.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            inference_response = InferenceResponse(
                id=data.get("id", ""),
                model=self.config.id,
                choices=data.get("choices", []),
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                provider=ProviderType.OPENAI,
                latency_ms=latency_ms,
                provider_response_time_ms=latency_ms,
                cost_usd=cost,
            )

            stats = AdapterStats(
                provider=ProviderType.OPENAI,
                model=self.config.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
            )

            return inference_response, stats

        except httpx.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000
            stats = AdapterStats(
                provider=ProviderType.OPENAI,
                model=self.config.id,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                success=False,
                error=str(e),
            )
            raise


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Claude API."""

    def __init__(self, config: ModelConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.api_base = "https://api.anthropic.com/v1"

    async def infer(
        self,
        request: InferenceRequest,
    ) -> tuple[InferenceResponse, AdapterStats]:
        """Call Anthropic API."""
        start_time = time.time()

        payload = {
            "model": self.config.model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens or self.config.max_tokens or 1024,
            "temperature": request.temperature or self.config.temperature,
        }

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http_client.post(
                f"{self.api_base}/messages",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            inference_response = InferenceResponse(
                id=data.get("id", ""),
                model=self.config.id,
                choices=[{"message": {"content": data.get("content", [{}])[0].get("text", "")}}],
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                provider=ProviderType.ANTHROPIC,
                latency_ms=latency_ms,
                provider_response_time_ms=latency_ms,
                cost_usd=cost,
            )

            stats = AdapterStats(
                provider=ProviderType.ANTHROPIC,
                model=self.config.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
            )

            return inference_response, stats

        except httpx.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000
            stats = AdapterStats(
                provider=ProviderType.ANTHROPIC,
                model=self.config.id,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                success=False,
                error=str(e),
            )
            raise


class TogetherAIAdapter(BaseAdapter):
    """Adapter for Together.ai API."""

    def __init__(self, config: ModelConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.api_base = "https://api.together.xyz/v1"

    async def infer(
        self,
        request: InferenceRequest,
    ) -> tuple[InferenceResponse, AdapterStats]:
        """Call Together.ai API."""
        start_time = time.time()

        payload = {
            "model": self.config.model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": request.temperature or self.config.temperature,
        }

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http_client.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            inference_response = InferenceResponse(
                id=data.get("id", ""),
                model=self.config.id,
                choices=data.get("choices", []),
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                provider=ProviderType.TOGETHER,
                latency_ms=latency_ms,
                provider_response_time_ms=latency_ms,
                cost_usd=cost,
            )

            stats = AdapterStats(
                provider=ProviderType.TOGETHER,
                model=self.config.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
            )

            return inference_response, stats

        except httpx.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000
            stats = AdapterStats(
                provider=ProviderType.TOGETHER,
                model=self.config.id,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                success=False,
                error=str(e),
            )
            raise


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    async def infer(
        self,
        request: InferenceRequest,
    ) -> tuple[InferenceResponse, AdapterStats]:
        """Return mock response."""
        latency_ms = random.uniform(10, 100)
        prompt_tokens = sum(len(msg.get("content", "").split()) for msg in request.messages)
        completion_tokens = random.randint(10, 100)
        cost = self.calculate_cost(prompt_tokens, completion_tokens)

        inference_response = InferenceResponse(
            id=f"mock-{request.request_id}",
            model=self.config.id,
            choices=[{"message": {"content": "This is a mock response."}}],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            provider=self.config.provider,
            latency_ms=latency_ms,
            provider_response_time_ms=latency_ms,
            cost_usd=cost,
        )

        stats = AdapterStats(
            provider=self.config.provider,
            model=self.config.id,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            success=True,
        )

        return inference_response, stats


def create_adapter(
    config: ModelConfig,
    api_key: str,
) -> BaseAdapter:
    """Factory function to create adapters."""
    if config.provider == ProviderType.OPENAI:
        return OpenAIAdapter(config, api_key)
    elif config.provider == ProviderType.ANTHROPIC:
        return AnthropicAdapter(config, api_key)
    elif config.provider == ProviderType.TOGETHER:
        return TogetherAIAdapter(config, api_key)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
