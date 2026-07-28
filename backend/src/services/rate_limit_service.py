import os
from datetime import datetime, timedelta
from typing import Optional
import redis
from sqlalchemy.orm import Session
from src.models.billing import StripeCustomer, RateLimitConfig, BillingTier


class RateLimitService:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    def get_rate_limit_config(
        self,
        db: Session,
        tier: BillingTier
    ) -> Optional[RateLimitConfig]:
        return db.query(RateLimitConfig).filter_by(tier=tier).first()

    def initialize_tier_configs(self, db: Session):
        tiers_config = {
            BillingTier.FREE: {
                "requests_per_minute": 10,
                "requests_per_day": 100,
                "tokens_per_month": 1_000_000,
                "concurrent_requests": 5
            },
            BillingTier.PRO: {
                "requests_per_minute": 100,
                "requests_per_day": 10_000,
                "tokens_per_month": 100_000_000,
                "concurrent_requests": 50
            },
            BillingTier.ENTERPRISE: {
                "requests_per_minute": 1000,
                "requests_per_day": 1_000_000,
                "tokens_per_month": 10_000_000_000,
                "concurrent_requests": 500
            }
        }

        for tier, config in tiers_config.items():
            existing = db.query(RateLimitConfig).filter_by(tier=tier).first()
            if not existing:
                rate_config = RateLimitConfig(
                    id=f"rate-{tier.value}",
                    tier=tier,
                    **config
                )
                db.add(rate_config)

        db.commit()

    def check_rate_limit(
        self,
        db: Session,
        customer_id: str,
        limit_type: str = "requests_per_minute"
    ) -> dict:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            return {"allowed": False, "reason": "customer_not_found"}

        config = self.get_rate_limit_config(db, customer.current_tier)
        if not config:
            return {"allowed": False, "reason": "tier_config_not_found"}

        limit = getattr(config, limit_type)
        key = f"rate_limit:{customer_id}:{limit_type}"

        current = int(self.redis_client.get(key) or 0)

        if current >= limit:
            ttl = self.redis_client.ttl(key)
            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "limit": limit,
                "current": current,
                "reset_in_seconds": ttl if ttl > 0 else 60
            }

        self.redis_client.incr(key)

        if limit_type == "requests_per_minute":
            self.redis_client.expire(key, 60)
        elif limit_type == "requests_per_day":
            self.redis_client.expire(key, 86400)

        return {
            "allowed": True,
            "limit": limit,
            "current": current + 1,
            "remaining": limit - (current + 1)
        }

    def check_monthly_token_limit(
        self,
        db: Session,
        customer_id: str,
        tokens_to_use: int
    ) -> dict:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            return {"allowed": False, "reason": "customer_not_found"}

        from src.services.billing_service import BillingService
        current_month_usage = BillingService.get_monthly_usage(db, customer_id)

        current_tokens = current_month_usage["tokens_input"] + current_month_usage["tokens_output"]
        limit = customer.monthly_limit_tokens

        if current_tokens + tokens_to_use > limit:
            return {
                "allowed": False,
                "reason": "monthly_limit_exceeded",
                "limit": limit,
                "used": current_tokens,
                "remaining": max(0, limit - current_tokens)
            }

        return {
            "allowed": True,
            "limit": limit,
            "used": current_tokens,
            "remaining": limit - (current_tokens + tokens_to_use)
        }

    def track_request(
        self,
        customer_id: str,
        endpoint: str,
        status_code: int,
        response_time_ms: int
    ):
        key = f"request_log:{customer_id}:{endpoint}"
        timestamp = datetime.utcnow().isoformat()

        log_entry = f"{timestamp}|{status_code}|{response_time_ms}"
        self.redis_client.lpush(key, log_entry)
        self.redis_client.expire(key, 86400)

    def get_request_metrics(
        self,
        customer_id: str,
        endpoint: Optional[str] = None,
        hours: int = 24
    ) -> dict:
        if endpoint:
            key = f"request_log:{customer_id}:{endpoint}"
            logs = self.redis_client.lrange(key, 0, -1)
        else:
            pattern = f"request_log:{customer_id}:*"
            keys = self.redis_client.keys(pattern)
            logs = []
            for k in keys:
                logs.extend(self.redis_client.lrange(k, 0, -1))

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        successful = 0
        failed = 0
        total_time = 0
        count = 0

        for log in logs:
            parts = log.split("|")
            if len(parts) >= 3:
                timestamp = datetime.fromisoformat(parts[0])
                status = int(parts[1])
                response_time = int(parts[2])

                if timestamp >= cutoff_time:
                    if 200 <= status < 300:
                        successful += 1
                    else:
                        failed += 1
                    total_time += response_time
                    count += 1

        return {
            "successful_requests": successful,
            "failed_requests": failed,
            "total_requests": successful + failed,
            "avg_response_time_ms": total_time // count if count > 0 else 0,
            "error_rate": (failed / (successful + failed) * 100) if (successful + failed) > 0 else 0
        }

    def reset_daily_limit(self, customer_id: str):
        key = f"rate_limit:{customer_id}:requests_per_day"
        self.redis_client.delete(key)

    def reset_minute_limit(self, customer_id: str):
        key = f"rate_limit:{customer_id}:requests_per_minute"
        self.redis_client.delete(key)
