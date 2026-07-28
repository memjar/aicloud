"""
Secure key logging and monitoring without exposing sensitive values.
Tracks key usage patterns for audit trails and rotation decisions.
"""

import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from enum import Enum
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


class KeyType(str, Enum):
    """Types of API keys being tracked."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    STRIPE = "stripe"
    DATABASE = "database"
    REDIS = "redis"
    JWT = "jwt"


class KeyEvent(str, Enum):
    """Events related to key usage and rotation."""
    LOADED = "loaded"
    USED = "used"
    FAILED = "failed"
    ROTATED = "rotated"
    EXPIRED = "expired"
    ACCESSED = "accessed"


@dataclass
class KeyUsageMetric:
    """Metric for key usage tracking."""
    key_type: str
    event: str
    timestamp: str
    key_hash: str
    status: str
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    user_id: Optional[str] = None


class KeyHasher:
    """Hashes keys for secure logging without exposing actual values."""

    @staticmethod
    def hash_key(key: str) -> str:
        """
        Generate a short hash of the key for identification.

        Args:
            key: The API key to hash

        Returns:
            SHA256 hash (first 16 chars) of the key
        """
        if not key:
            return "unknown"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    @staticmethod
    def mask_key(key: str, visible_chars: int = 4) -> str:
        """
        Create a masked version of the key for display.

        Args:
            key: The API key
            visible_chars: Number of characters to keep visible

        Returns:
            Masked key like "sk_live_****...****xxxx"
        """
        if not key or len(key) < visible_chars:
            return "***"

        prefix = key[:visible_chars] if visible_chars > 0 else ""
        suffix = key[-4:] if len(key) > 4 else ""
        masked = f"{prefix}{'*' * (len(key) - visible_chars - 4)}{suffix}"
        return masked


class KeyUsageLogger:
    """Logs key usage patterns without exposing sensitive data."""

    def __init__(self, environment: str = "development"):
        """
        Initialize key usage logger.

        Args:
            environment: Current environment (dev, staging, prod)
        """
        self.environment = environment
        self.usage_log: List[KeyUsageMetric] = []
        self.key_metadata: Dict[str, Dict[str, Any]] = {}

    def register_key(
        self,
        key_type: KeyType,
        key: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a key for monitoring.

        Args:
            key_type: Type of key
            key: The actual API key
            metadata: Additional metadata (provider, rotation_date, etc.)
        """
        key_hash = KeyHasher.hash_key(key)
        masked = KeyHasher.mask_key(key)

        self.key_metadata[key_type.value] = {
            'hash': key_hash,
            'masked': masked,
            'registered_at': datetime.utcnow().isoformat(),
            'last_used': None,
            'use_count': 0,
            'error_count': 0,
            'metadata': metadata or {},
        }

        logger.info(
            f"Registered key: type={key_type.value}, "
            f"hash={key_hash}, masked={masked}"
        )

    def log_key_event(
        self,
        key_type: KeyType,
        event: KeyEvent,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """
        Log a key usage event.

        Args:
            key_type: Type of key
            event: Event type (used, failed, etc.)
            status: Event status (success, failure, etc.)
            details: Additional event details
            user_id: User ID if applicable
            source: Source of the event (API endpoint, scheduled task, etc.)
        """
        if key_type.value not in self.key_metadata:
            logger.warning(f"Key type {key_type.value} not registered")
            return

        metadata = self.key_metadata[key_type.value]
        key_hash = metadata['hash']

        metric = KeyUsageMetric(
            key_type=key_type.value,
            event=event.value,
            timestamp=datetime.utcnow().isoformat(),
            key_hash=key_hash,
            status=status,
            details=details,
            source=source,
            user_id=user_id,
        )

        self.usage_log.append(metric)

        if event == KeyEvent.USED:
            metadata['last_used'] = datetime.utcnow().isoformat()
            metadata['use_count'] += 1
        elif event == KeyEvent.FAILED:
            metadata['error_count'] += 1

        log_message = (
            f"Key event: type={key_type.value}, event={event.value}, "
            f"status={status}, hash={key_hash}"
        )
        if source:
            log_message += f", source={source}"

        if status == "success":
            logger.debug(log_message)
        else:
            logger.warning(log_message)

    def get_key_status(self, key_type: KeyType) -> Optional[Dict[str, Any]]:
        """
        Get current status of a key.

        Args:
            key_type: Type of key

        Returns:
            Key metadata including usage stats
        """
        return self.key_metadata.get(key_type.value)

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get summary of key usage across all keys.

        Returns:
            Dictionary with usage statistics
        """
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.environment,
            'total_events': len(self.usage_log),
            'keys': {},
        }

        for key_type, metadata in self.key_metadata.items():
            summary['keys'][key_type] = {
                'hash': metadata['hash'],
                'masked': metadata['masked'],
                'registered_at': metadata['registered_at'],
                'last_used': metadata['last_used'],
                'use_count': metadata['use_count'],
                'error_count': metadata['error_count'],
                'health': 'healthy' if metadata['error_count'] == 0 else 'degraded',
            }

        return summary

    def get_recent_events(self, key_type: Optional[KeyType] = None, hours: int = 24) -> List[Dict]:
        """
        Get recent key events for audit trail.

        Args:
            key_type: Filter by key type (optional)
            hours: Look back this many hours

        Returns:
            List of recent events
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        events = []

        for metric in self.usage_log:
            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time < cutoff:
                continue

            if key_type and metric.key_type != key_type.value:
                continue

            events.append(asdict(metric))

        return events

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect suspicious key usage patterns.

        Returns:
            List of detected anomalies
        """
        anomalies = []

        for key_type, metadata in self.key_metadata.items():
            # Check for high error rate
            total_events = metadata['use_count'] + metadata['error_count']
            if total_events > 0:
                error_rate = metadata['error_count'] / total_events
                if error_rate > 0.1:
                    anomalies.append({
                        'type': 'high_error_rate',
                        'key_type': key_type,
                        'error_rate': error_rate,
                        'threshold': 0.1,
                    })

            # Check if key hasn't been used recently
            if metadata['last_used']:
                last_used = datetime.fromisoformat(metadata['last_used'])
                age = (datetime.utcnow() - last_used).days
                if age > 7:
                    anomalies.append({
                        'type': 'unused_key',
                        'key_type': key_type,
                        'days_unused': age,
                        'threshold_days': 7,
                    })

        return anomalies

    def export_audit_log(self, filepath: Optional[str] = None) -> str:
        """
        Export audit log in JSON format.

        Args:
            filepath: Optional file path to save log

        Returns:
            JSON string of audit log
        """
        audit_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.environment,
            'summary': self.get_usage_summary(),
            'recent_events': self.get_recent_events(hours=168),
            'anomalies': self.detect_anomalies(),
        }

        json_log = json.dumps(audit_data, indent=2, default=str)

        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(json_log)
                logger.info(f"Audit log exported to {filepath}")
            except Exception as e:
                logger.error(f"Failed to export audit log: {e}")

        return json_log


# Global key logger instance
_key_logger: Optional[KeyUsageLogger] = None


def get_key_logger(environment: str = "development") -> KeyUsageLogger:
    """
    Get or create the global key logger instance.

    Args:
        environment: Current environment

    Returns:
        KeyUsageLogger instance
    """
    global _key_logger
    if _key_logger is None:
        _key_logger = KeyUsageLogger(environment)
    return _key_logger
