import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.billing import (
    Base, StripeCustomer, UsageRecord, BillingCycle, Invoice, BillingTier
)
from src.services.stripe_service import StripeService
from src.services.billing_service import BillingService
from src.services.rate_limit_service import RateLimitService
from src.services.fraud_detection_service import FraudDetectionService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    yield db
    db.close()


@pytest.fixture
def stripe_service():
    return StripeService(api_key="sk_test_fake")


class TestStripeService:
    def test_create_customer(self, test_db, stripe_service):
        customer = stripe_service.create_customer(
            test_db,
            account_id="acc_test_1",
            email="test@example.com",
            name="Test User"
        )

        assert customer.account_id == "acc_test_1"
        assert customer.email == "test@example.com"
        assert customer.current_tier == BillingTier.FREE

    def test_get_customer(self, test_db, stripe_service):
        customer = stripe_service.create_customer(
            test_db,
            account_id="acc_test_1",
            email="test@example.com",
            name="Test User"
        )

        retrieved = stripe_service.get_customer(test_db, "acc_test_1")
        assert retrieved.id == customer.id


class TestBillingService:
    def test_record_usage(self, test_db, stripe_service):
        customer = stripe_service.create_customer(
            test_db,
            account_id="acc_test_1",
            email="test@example.com",
            name="Test User"
        )

        usage = BillingService.record_usage(
            test_db,
            customer.id,
            "gpt-4",
            tokens_input=1000,
            tokens_output=500
        )

        assert usage.customer_id == customer.id
        assert usage.tokens_input == 1000
        assert usage.tokens_output == 500
        assert usage.cost_usd > 0

    def test_calculate_cost(self):
        cost = BillingService._calculate_cost(
            "gpt-4",
            tokens_input=1000,
            tokens_output=500
        )

        assert cost > 0
        assert isinstance(cost, Decimal)


class TestFraudDetectionService:
    def test_check_account_status(self, test_db, stripe_service):
        customer = stripe_service.create_customer(
            test_db,
            account_id="acc_test_1",
            email="test@example.com",
            name="Test User"
        )

        status = FraudDetectionService.check_account_status(test_db, customer.id)

        assert "status" in status
        assert "alerts" in status
        assert status["status"] in ["normal", "caution", "risky"]
