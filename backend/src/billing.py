"""Billing and cost calculation logic."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from core import BillingRecord, ProviderType


# Provider pricing (per 1K tokens)
PROVIDER_PRICING = {
    ProviderType.OPENAI: {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    },
    ProviderType.ANTHROPIC: {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    },
    ProviderType.TOGETHER: {
        "meta-llama/llama-2-70b": {"input": 0.0009, "output": 0.0009},
        "meta-llama/llama-2-13b": {"input": 0.000225, "output": 0.0003},
    },
}


@dataclass
class BillingCycle:
    """Billing cycle summary."""
    start_date: datetime
    end_date: datetime
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    by_provider: Dict[str, Dict] = None
    by_model: Dict[str, Dict] = None

    def __post_init__(self):
        if self.by_provider is None:
            self.by_provider = {}
        if self.by_model is None:
            self.by_model = {}


class BillingCalculator:
    """Calculate costs based on token usage."""

    def __init__(self):
        self.pricing = PROVIDER_PRICING
        self.billing_records: List[BillingRecord] = []

    def get_provider_pricing(
        self,
        provider: ProviderType,
        model: str,
    ) -> Optional[Dict[str, float]]:
        """Get pricing for a provider/model combination."""
        provider_models = self.pricing.get(provider, {})
        return provider_models.get(model)

    def calculate_cost(
        self,
        provider: ProviderType,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Optional[float]:
        """Calculate cost for a request."""
        pricing = self.get_provider_pricing(provider, model)
        if not pricing:
            return None

        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def add_record(self, record: BillingRecord):
        """Add a billing record."""
        self.billing_records.append(record)

    def get_cycle_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
    ) -> BillingCycle:
        """Get billing cycle summary."""
        cycle = BillingCycle(start_date, end_date)

        for record in self.billing_records:
            if record.timestamp < start_date or record.timestamp > end_date:
                continue

            if user_id and record.user_id != user_id:
                continue

            cycle.total_tokens += record.total_tokens
            cycle.total_cost_usd += record.cost_usd

            provider_name = record.provider.value
            if provider_name not in cycle.by_provider:
                cycle.by_provider[provider_name] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                }

            cycle.by_provider[provider_name]["tokens"] += record.total_tokens
            cycle.by_provider[provider_name]["cost"] += record.cost_usd
            cycle.by_provider[provider_name]["requests"] += 1

            if record.model_id not in cycle.by_model:
                cycle.by_model[record.model_id] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                }

            cycle.by_model[record.model_id]["tokens"] += record.total_tokens
            cycle.by_model[record.model_id]["cost"] += record.cost_usd
            cycle.by_model[record.model_id]["requests"] += 1

        return cycle

    def get_user_cost(self, user_id: str) -> float:
        """Get total cost for a user."""
        return sum(
            r.cost_usd
            for r in self.billing_records
            if r.user_id == user_id
        )

    def get_model_cost(self, model_id: str) -> float:
        """Get total cost for a model."""
        return sum(
            r.cost_usd
            for r in self.billing_records
            if r.model_id == model_id
        )

    def estimate_cost(
        self,
        provider: ProviderType,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate cost for potential request."""
        cost = self.calculate_cost(
            provider,
            model,
            prompt_tokens,
            completion_tokens,
        )
        return cost if cost is not None else 0.0


class TokenCounter:
    """Count tokens in text (simplified approximation)."""

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count using word count approximation."""
        # Rough approximation: 1 token ~= 4 characters or 0.75 words
        words = len(text.split())
        return max(1, int(words / 0.75))

    @staticmethod
    def count_message_tokens(messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages."""
        total = 0
        for msg in messages:
            # Add tokens for role and content
            total += TokenCounter.count_tokens(msg.get("role", ""))
            total += TokenCounter.count_tokens(msg.get("content", ""))
            total += 4  # Overhead per message
        return total


class BillingValidator:
    """Validate billing calculations."""

    def __init__(self, calculator: BillingCalculator):
        self.calculator = calculator

    def validate_record(self, record: BillingRecord) -> tuple[bool, Optional[str]]:
        """Validate a billing record."""
        if record.total_tokens != record.prompt_tokens + record.completion_tokens:
            return False, "Total tokens mismatch"

        if record.cost_usd < 0:
            return False, "Cost cannot be negative"

        expected_cost = self.calculator.calculate_cost(
            record.provider,
            record.model_id,
            record.prompt_tokens,
            record.completion_tokens,
        )

        if expected_cost is None:
            return False, f"Unknown pricing for {record.provider}/{record.model_id}"

        # Allow 0.01% tolerance for rounding
        tolerance = expected_cost * 0.0001
        if abs(record.cost_usd - expected_cost) > tolerance:
            return (
                False,
                f"Cost mismatch: expected {expected_cost}, got {record.cost_usd}",
            )

        return True, None

    def validate_cycle(self, cycle: BillingCycle) -> tuple[bool, Optional[str]]:
        """Validate a billing cycle."""
        if cycle.total_cost_usd < 0:
            return False, "Total cost cannot be negative"

        provider_total = sum(p["cost"] for p in cycle.by_provider.values())
        model_total = sum(m["cost"] for m in cycle.by_model.values())

        if abs(cycle.total_cost_usd - provider_total) > 0.01:
            return False, "Provider cost sum mismatch"

        if abs(cycle.total_cost_usd - model_total) > 0.01:
            return False, "Model cost sum mismatch"

        token_total = sum(p["tokens"] for p in cycle.by_provider.values())
        if cycle.total_tokens != token_total:
            return False, "Token count mismatch"

        return True, None
