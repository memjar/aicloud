from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Numeric, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class BillingTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"

    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"), unique=True, index=True)
    stripe_customer_id = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    current_tier = Column(SQLEnum(BillingTier), default=BillingTier.FREE)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    monthly_limit_tokens = Column(Integer, default=1_000_000)
    monthly_limit_requests = Column(Integer, default=10_000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usage = relationship("UsageRecord", back_populates="customer")
    billing_cycles = relationship("BillingCycle", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    payment_methods = relationship("PaymentMethod", back_populates="customer")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("stripe_customers.id"), index=True)
    model_id = Column(String, index=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    requests_count = Column(Integer, default=1)
    cost_usd = Column(Numeric(19, 8), default=Decimal("0"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    month = Column(String, index=True)  # YYYY-MM format

    customer = relationship("StripeCustomer", back_populates="usage")


class BillingCycle(Base):
    __tablename__ = "billing_cycles"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("stripe_customers.id"), index=True)
    period_start = Column(DateTime, index=True)
    period_end = Column(DateTime, index=True)
    total_tokens_input = Column(Integer, default=0)
    total_tokens_output = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    subtotal_usd = Column(Numeric(19, 8), default=Decimal("0"))
    discount_usd = Column(Numeric(19, 8), default=Decimal("0"))
    tax_usd = Column(Numeric(19, 8), default=Decimal("0"))
    total_usd = Column(Numeric(19, 8), default=Decimal("0"))
    status = Column(String, default="open")  # open, charged, refunded
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("StripeCustomer", back_populates="billing_cycles")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("stripe_customers.id"), index=True)
    stripe_invoice_id = Column(String, unique=True, index=True)
    billing_cycle_id = Column(String, ForeignKey("billing_cycles.id"))
    amount_usd = Column(Numeric(19, 8))
    tax_usd = Column(Numeric(19, 8), default=Decimal("0"))
    status = Column(String, default="draft")  # draft, sent, paid, failed, refunded
    issued_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    pdf_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("StripeCustomer", back_populates="invoices")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("stripe_customers.id"), index=True)
    stripe_payment_method_id = Column(String, unique=True)
    card_last4 = Column(String)
    card_brand = Column(String)
    exp_month = Column(Integer)
    exp_year = Column(Integer)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("StripeCustomer", back_populates="payment_methods")


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("stripe_customers.id"), index=True)
    alert_type = Column(String)  # usage_spike, rapid_requests, unusual_pattern
    severity = Column(String)  # low, medium, high
    message = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RateLimitConfig(Base):
    __tablename__ = "rate_limit_configs"

    id = Column(String, primary_key=True)
    tier = Column(SQLEnum(BillingTier), unique=True)
    requests_per_minute = Column(Integer)
    requests_per_day = Column(Integer)
    tokens_per_month = Column(Integer)
    concurrent_requests = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
