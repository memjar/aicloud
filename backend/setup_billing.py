#!/usr/bin/env python
"""
Setup script for Stripe billing integration.

Usage:
  python setup_billing.py
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from src.models.billing import (
    Base, RateLimitConfig, BillingTier
)
from src.services.rate_limit_service import RateLimitService


def setup_database():
    """Create all tables in the database."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    engine = create_engine(database_url)

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")

    return engine


def initialize_rate_limits(engine):
    """Initialize rate limit configurations for each tier."""
    Session = sessionmaker(bind=engine)
    db = Session()

    print("\nInitializing rate limit tiers...")

    rate_limit_service = RateLimitService()
    rate_limit_service.initialize_tier_configs(db)

    tiers = db.query(RateLimitConfig).all()
    for tier in tiers:
        print(f"✓ {tier.tier.value:12} - "
              f"{tier.requests_per_minute:4} req/min, "
              f"{tier.tokens_per_month:,} tokens/month")

    db.close()


def verify_stripe_config():
    """Verify Stripe configuration is present."""
    print("\nVerifying Stripe configuration...")

    required_keys = [
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_PRO",
        "STRIPE_PRICE_ENTERPRISE"
    ]

    missing = []
    for key in required_keys:
        if not os.getenv(key):
            missing.append(key)
        else:
            value = os.getenv(key)
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"✓ {key}: {masked}")

    if missing:
        print(f"\n⚠ Warning: Missing configuration for: {', '.join(missing)}")
        print("  These are required for production. Set them in .env or environment variables.")

    return len(missing) == 0


def verify_email_config():
    """Verify email configuration is present."""
    print("\nVerifying email configuration...")

    required_keys = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "FROM_EMAIL"
    ]

    missing = []
    for key in required_keys:
        if not os.getenv(key):
            missing.append(key)
        else:
            print(f"✓ {key}")

    if missing:
        print(f"\n⚠ Warning: Missing email configuration: {', '.join(missing)}")
        print("  Invoice emails will not be sent. Set these in .env to enable.")

    return len(missing) == 0


def verify_database():
    """Test database connection."""
    print("\nVerifying database connection...")

    database_url = os.getenv("DATABASE_URL", "sqlite:///./test.db")

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"✓ Database connected: {database_url.split('@')[-1]}")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def verify_redis():
    """Test Redis connection."""
    print("\nVerifying Redis connection...")

    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url)
        r.ping()
        print(f"✓ Redis connected: {redis_url}")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Rate limiting will not work. Install Redis or set REDIS_URL.")
        return False


def main():
    print("=" * 70)
    print("  Stripe Billing Integration Setup")
    print("=" * 70)

    # Verify environment
    if not os.getenv("DATABASE_URL"):
        print("\nℹ No DATABASE_URL set. Using SQLite for testing.")

    # Setup database
    try:
        engine = setup_database()
    except Exception as e:
        print(f"\n✗ Failed to setup database: {e}")
        return False

    # Initialize rate limits
    try:
        initialize_rate_limits(engine)
    except Exception as e:
        print(f"\n✗ Failed to initialize rate limits: {e}")
        return False

    # Verify configurations
    print("\n" + "=" * 70)
    print("  Configuration Verification")
    print("=" * 70)

    stripe_ok = verify_stripe_config()
    email_ok = verify_email_config()
    db_ok = verify_database()
    redis_ok = verify_redis()

    print("\n" + "=" * 70)
    print("  Setup Summary")
    print("=" * 70)

    checks = [
        ("Database", db_ok),
        ("Redis", redis_ok),
        ("Stripe", stripe_ok),
        ("Email", email_ok),
    ]

    for name, ok in checks:
        status = "✓ OK" if ok else "⚠ Warning"
        print(f"{status:12} {name}")

    print("\n" + "=" * 70)
    print("  Next Steps")
    print("=" * 70)
    print("""
1. Verify all configurations are set in .env
2. Create a Stripe test account at https://stripe.com
3. Get API keys from Stripe Dashboard → Settings → API Keys
4. Configure webhook endpoint in Stripe Dashboard → Webhooks
5. Start the API server:
   poetry run uvicorn src.main:app --reload --port 8000
6. Test the billing endpoints:
   curl http://localhost:8000/v1/billing/customers
7. View API docs at http://localhost:8000/docs
""")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
