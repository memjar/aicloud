"""Core types and interfaces for the inference pipeline."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class ProviderType(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    LOCAL = "local"


class ModelStatus(Enum):
    """Model deployment status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


@dataclass
class ModelConfig:
    """Model configuration."""
    id: str
    name: str
    provider: ProviderType
    model_id: str
    status: ModelStatus = ModelStatus.ACTIVE
    pricing_input: float = 0.0  # Cost per 1K input tokens
    pricing_output: float = 0.0  # Cost per 1K output tokens
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    timeout_seconds: int = 60
    max_retries: int = 3
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class InferenceRequest:
    """Inference request structure."""
    model_id: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class InferenceResponse:
    """Inference response structure."""
    id: str
    model: str
    object: str = "text_completion"
    created: datetime = None
    choices: List[Dict[str, Any]] = None
    usage: Dict[str, int] = None
    provider: ProviderType = None
    latency_ms: float = 0.0
    provider_response_time_ms: float = 0.0
    cost_usd: float = 0.0

    def __post_init__(self):
        if self.created is None:
            self.created = datetime.utcnow()
        if self.choices is None:
            self.choices = []
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


@dataclass
class ErrorResponse:
    """Error response structure."""
    error: str
    error_code: str
    message: str
    timestamp: datetime = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class BillingRecord:
    """Billing record for tracking costs."""
    request_id: str
    user_id: str
    model_id: str
    provider: ProviderType
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int
    requests_per_hour: int
    tokens_per_minute: int
    tokens_per_day: int
    concurrent_requests: int = 10
