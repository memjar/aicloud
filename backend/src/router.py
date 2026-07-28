"""Model routing logic for handling inference requests."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from core import (
    InferenceRequest,
    InferenceResponse,
    ModelConfig,
    ProviderType,
    RateLimitConfig,
)
from adapters import BaseAdapter, create_adapter, MockAdapter


@dataclass
class RateLimitTracker:
    """Track rate limits for an API key."""
    key_id: str
    config: RateLimitConfig
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    tokens_this_minute: int = 0
    tokens_this_day: int = 0
    concurrent_requests: int = 0
    last_reset_minute: datetime = field(default_factory=datetime.utcnow)
    last_reset_hour: datetime = field(default_factory=datetime.utcnow)
    last_reset_day: datetime = field(default_factory=datetime.utcnow)

    def reset_if_needed(self):
        """Reset counters based on time windows."""
        now = datetime.utcnow()

        if (now - self.last_reset_minute).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.last_reset_minute = now

        if (now - self.last_reset_hour).total_seconds() >= 3600:
            self.requests_this_hour = 0
            self.last_reset_hour = now

        if (now - self.last_reset_day).total_seconds() >= 86400:
            self.tokens_this_day = 0
            self.last_reset_day = now

    def check_and_update(
        self,
        request_tokens: int,
        response_tokens: int,
    ) -> tuple[bool, Optional[str]]:
        """Check if request exceeds limits and update counters."""
        self.reset_if_needed()

        total_tokens = request_tokens + response_tokens

        if self.requests_this_minute >= self.config.requests_per_minute:
            return False, "Rate limit: requests per minute exceeded"

        if self.requests_this_hour >= self.config.requests_per_hour:
            return False, "Rate limit: requests per hour exceeded"

        if self.tokens_this_minute + total_tokens > self.config.tokens_per_minute:
            return False, "Rate limit: tokens per minute exceeded"

        if self.tokens_this_day + total_tokens > self.config.tokens_per_day:
            return False, "Rate limit: tokens per day exceeded"

        if self.concurrent_requests >= self.config.concurrent_requests:
            return False, "Rate limit: concurrent requests exceeded"

        self.requests_this_minute += 1
        self.requests_this_hour += 1
        self.tokens_this_minute += total_tokens
        self.tokens_this_day += total_tokens
        self.concurrent_requests += 1

        return True, None

    def release_concurrent(self):
        """Release a concurrent request slot."""
        if self.concurrent_requests > 0:
            self.concurrent_requests -= 1


class ModelRouter:
    """Routes inference requests to appropriate models and providers."""

    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.adapters: Dict[str, BaseAdapter] = {}
        self.rate_limiters: Dict[str, RateLimitTracker] = {}
        self.fallback_models: Dict[str, List[str]] = {}
        self.model_stats: Dict[str, Dict] = {}

    def register_model(
        self,
        config: ModelConfig,
        api_key: Optional[str] = None,
        use_mock: bool = False,
    ):
        """Register a model and its adapter."""
        self.models[config.id] = config
        self.model_stats[config.id] = {
            "requests": 0,
            "errors": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency_ms": 0.0,
        }

        if use_mock:
            self.adapters[config.id] = MockAdapter(config)
        elif api_key:
            self.adapters[config.id] = create_adapter(config, api_key)

    def set_fallback_chain(self, primary_model: str, fallbacks: List[str]):
        """Set fallback models for resilience."""
        self.fallback_models[primary_model] = fallbacks

    def create_rate_limiter(
        self,
        key_id: str,
        config: RateLimitConfig,
    ):
        """Create a rate limiter for an API key."""
        self.rate_limiters[key_id] = RateLimitTracker(key_id, config)

    async def infer(
        self,
        request: InferenceRequest,
        api_key: str,
        use_fallback: bool = True,
    ) -> InferenceResponse:
        """Route and execute an inference request."""
        model = self.models.get(request.model_id)
        if not model:
            raise ValueError(f"Model {request.model_id} not found")

        adapter = self.adapters.get(request.model_id)
        if not adapter:
            raise ValueError(f"No adapter for model {request.model_id}")

        try:
            response, stats = await adapter.infer(request)

            self.model_stats[request.model_id]["requests"] += 1
            self.model_stats[request.model_id]["total_tokens"] += stats.input_tokens + stats.output_tokens
            self.model_stats[request.model_id]["total_cost"] += stats.cost_usd

            avg_latency = self.model_stats[request.model_id]["avg_latency_ms"]
            total_requests = self.model_stats[request.model_id]["requests"]
            self.model_stats[request.model_id]["avg_latency_ms"] = (
                (avg_latency * (total_requests - 1) + stats.latency_ms) / total_requests
            )

            return response

        except Exception as e:
            self.model_stats[request.model_id]["errors"] += 1

            if use_fallback and request.model_id in self.fallback_models:
                for fallback_model in self.fallback_models[request.model_id]:
                    try:
                        request.model_id = fallback_model
                        return await self.infer(request, api_key, use_fallback=False)
                    except Exception:
                        continue

            raise

    def get_model_stats(self, model_id: str) -> Dict:
        """Get statistics for a model."""
        return self.model_stats.get(model_id, {})

    def get_all_stats(self) -> Dict:
        """Get statistics for all models."""
        return self.model_stats

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all adapters."""
        health = {}
        for model_id, adapter in self.adapters.items():
            try:
                request = InferenceRequest(
                    model_id=model_id,
                    messages=[{"role": "user", "content": "test"}],
                )
                response, _ = await adapter.infer(request)
                health[model_id] = True
            except Exception:
                health[model_id] = False
        return health
