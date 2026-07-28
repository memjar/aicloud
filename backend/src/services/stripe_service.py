import os
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
import stripe
from sqlalchemy.orm import Session
from src.models.billing import (
    StripeCustomer, UsageRecord, BillingCycle, Invoice,
    PaymentMethod, BillingTier, RateLimitConfig
)


class StripeService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        stripe.api_key = self.api_key

    def create_customer(
        self,
        db: Session,
        account_id: str,
        email: str,
        name: str
    ) -> StripeCustomer:
        existing = db.query(StripeCustomer).filter_by(account_id=account_id).first()
        if existing:
            return existing

        stripe_customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"account_id": account_id}
        )

        customer = StripeCustomer(
            id=str(uuid.uuid4()),
            account_id=account_id,
            stripe_customer_id=stripe_customer.id,
            email=email,
            current_tier=BillingTier.FREE
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    def get_customer(self, db: Session, account_id: str) -> Optional[StripeCustomer]:
        return db.query(StripeCustomer).filter_by(account_id=account_id).first()

    def update_billing_tier(
        self,
        db: Session,
        account_id: str,
        tier: BillingTier
    ) -> StripeCustomer:
        customer = self.get_customer(db, account_id)
        if not customer:
            raise ValueError(f"Customer not found for account {account_id}")

        tier_config = db.query(RateLimitConfig).filter_by(tier=tier).first()
        if not tier_config:
            raise ValueError(f"No rate limit config for tier {tier}")

        customer.current_tier = tier
        customer.monthly_limit_tokens = tier_config.tokens_per_month
        customer.monthly_limit_requests = tier_config.requests_per_day * 30
        customer.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(customer)
        return customer

    def create_subscription(
        self,
        db: Session,
        account_id: str,
        tier: BillingTier,
        payment_method_id: str
    ) -> dict:
        customer = self.get_customer(db, account_id)
        if not customer:
            raise ValueError(f"Customer not found for account {account_id}")

        tier_prices = {
            BillingTier.FREE: None,
            BillingTier.PRO: os.getenv("STRIPE_PRICE_PRO"),
            BillingTier.ENTERPRISE: os.getenv("STRIPE_PRICE_ENTERPRISE")
        }

        price_id = tier_prices.get(tier)
        if not price_id:
            return {"error": f"No price configured for tier {tier}"}

        subscription = stripe.Subscription.create(
            customer=customer.stripe_customer_id,
            items=[{"price": price_id}],
            payment_settings={
                "save_default_payment_method": "off",
                "default_mandate": None
            },
            metadata={"account_id": account_id, "tier": tier.value}
        )

        customer.stripe_subscription_id = subscription.id
        customer.current_tier = tier
        customer.updated_at = datetime.utcnow()
        db.commit()

        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end
        }

    def cancel_subscription(
        self,
        db: Session,
        account_id: str
    ) -> dict:
        customer = self.get_customer(db, account_id)
        if not customer or not customer.stripe_subscription_id:
            raise ValueError(f"No subscription found for account {account_id}")

        stripe.Subscription.delete(customer.stripe_subscription_id)

        customer.stripe_subscription_id = None
        customer.current_tier = BillingTier.FREE
        customer.updated_at = datetime.utcnow()
        db.commit()

        return {"status": "cancelled"}

    def add_payment_method(
        self,
        db: Session,
        account_id: str,
        payment_method_id: str
    ) -> PaymentMethod:
        customer = self.get_customer(db, account_id)
        if not customer:
            raise ValueError(f"Customer not found for account {account_id}")

        existing = db.query(PaymentMethod).filter_by(
            customer_id=customer.id,
            stripe_payment_method_id=payment_method_id
        ).first()
        if existing:
            return existing

        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer.stripe_customer_id
        )

        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        card = pm.card

        payment_method = PaymentMethod(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            stripe_payment_method_id=payment_method_id,
            card_last4=card.last4,
            card_brand=card.brand.upper(),
            exp_month=card.exp_month,
            exp_year=card.exp_year
        )
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
        return payment_method

    def remove_payment_method(
        self,
        db: Session,
        account_id: str,
        payment_method_id: str
    ) -> dict:
        customer = self.get_customer(db, account_id)
        if not customer:
            raise ValueError(f"Customer not found for account {account_id}")

        stripe.PaymentMethod.detach(payment_method_id)

        db.query(PaymentMethod).filter_by(
            customer_id=customer.id,
            stripe_payment_method_id=payment_method_id
        ).delete()
        db.commit()

        return {"status": "removed"}

    def get_payment_methods(
        self,
        db: Session,
        account_id: str
    ) -> list[PaymentMethod]:
        customer = self.get_customer(db, account_id)
        if not customer:
            return []
        return db.query(PaymentMethod).filter_by(customer_id=customer.id).all()

    def sync_subscription_status(
        self,
        db: Session,
        account_id: str
    ) -> dict:
        customer = self.get_customer(db, account_id)
        if not customer or not customer.stripe_subscription_id:
            return {"status": "no_subscription"}

        subscription = stripe.Subscription.retrieve(customer.stripe_subscription_id)

        if subscription.status == "active":
            for item in subscription.items.data:
                tier_map = {
                    "price_pro": BillingTier.PRO,
                    "price_enterprise": BillingTier.ENTERPRISE
                }
                for attr, t in tier_map.items():
                    if os.getenv(f"STRIPE_PRICE_{t.value.upper()}") == item.price.id:
                        customer.current_tier = t
                        break

        return {
            "status": subscription.status,
            "current_period_end": subscription.current_period_end
        }
