import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.models.billing import (
    UsageRecord, BillingCycle, StripeCustomer, Invoice, BillingTier
)


MODEL_COSTS_PER_1M_TOKENS = {
    "gpt-4": {"input": Decimal("40"), "output": Decimal("120")},
    "claude-3-opus": {"input": Decimal("15"), "output": Decimal("75")},
    "together-llama": {"input": Decimal("1.60"), "output": Decimal("1.60")},
    "local": {"input": Decimal("0"), "output": Decimal("0")},
}

MARKUP_MULTIPLIER = Decimal("2.5")  # 2-3x provider cost


class BillingService:
    @staticmethod
    def record_usage(
        db: Session,
        customer_id: str,
        model_id: str,
        tokens_input: int,
        tokens_output: int
    ) -> UsageRecord:
        cost = BillingService._calculate_cost(model_id, tokens_input, tokens_output)
        month = datetime.utcnow().strftime("%Y-%m")

        usage = UsageRecord(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            model_id=model_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            requests_count=1,
            cost_usd=cost,
            month=month
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return usage

    @staticmethod
    def _calculate_cost(
        model_id: str,
        tokens_input: int,
        tokens_output: int
    ) -> Decimal:
        base_model = model_id.split("-")[0].lower()
        costs = MODEL_COSTS_PER_1M_TOKENS.get(base_model, MODEL_COSTS_PER_1M_TOKENS["local"])

        input_cost = (Decimal(tokens_input) / Decimal("1_000_000")) * costs["input"]
        output_cost = (Decimal(tokens_output) / Decimal("1_000_000")) * costs["output"]
        total_cost = (input_cost + output_cost) * MARKUP_MULTIPLIER

        return total_cost.quantize(Decimal("0.00000001"))

    @staticmethod
    def get_monthly_usage(
        db: Session,
        customer_id: str,
        month: Optional[str] = None
    ) -> dict:
        if not month:
            month = datetime.utcnow().strftime("%Y-%m")

        usage = db.query(UsageRecord).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.month == month
            )
        ).all()

        total_tokens_in = sum(u.tokens_input for u in usage)
        total_tokens_out = sum(u.tokens_output for u in usage)
        total_cost = sum(u.cost_usd for u in usage)
        total_requests = len(usage)

        return {
            "month": month,
            "tokens_input": total_tokens_in,
            "tokens_output": total_tokens_out,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "usage_by_model": BillingService._group_by_model(usage)
        }

    @staticmethod
    def _group_by_model(usage_records: list[UsageRecord]) -> dict:
        grouped = {}
        for record in usage_records:
            if record.model_id not in grouped:
                grouped[record.model_id] = {
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "cost": Decimal("0"),
                    "requests": 0
                }
            grouped[record.model_id]["tokens_input"] += record.tokens_input
            grouped[record.model_id]["tokens_output"] += record.tokens_output
            grouped[record.model_id]["cost"] += record.cost_usd
            grouped[record.model_id]["requests"] += record.requests_count

        for model in grouped:
            grouped[model]["cost"] = float(grouped[model]["cost"])
        return grouped

    @staticmethod
    def create_billing_cycle(
        db: Session,
        customer_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> BillingCycle:
        existing = db.query(BillingCycle).filter(
            and_(
                BillingCycle.customer_id == customer_id,
                BillingCycle.period_start == period_start,
                BillingCycle.period_end == period_end
            )
        ).first()
        if existing:
            return existing

        month = period_start.strftime("%Y-%m")
        usage = db.query(UsageRecord).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.month == month
            )
        ).all()

        total_tokens_in = sum(u.tokens_input for u in usage)
        total_tokens_out = sum(u.tokens_output for u in usage)
        subtotal = sum(u.cost_usd for u in usage)
        total_requests = len(usage)

        billing_cycle = BillingCycle(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
            total_tokens_input=total_tokens_in,
            total_tokens_output=total_tokens_out,
            total_requests=total_requests,
            subtotal_usd=subtotal,
            tax_usd=Decimal("0"),
            total_usd=subtotal
        )
        db.add(billing_cycle)
        db.commit()
        db.refresh(billing_cycle)
        return billing_cycle

    @staticmethod
    def get_current_month_cost(db: Session, customer_id: str) -> Decimal:
        month = datetime.utcnow().strftime("%Y-%m")
        total = db.query(func.sum(UsageRecord.cost_usd)).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.month == month
            )
        ).scalar()
        return total or Decimal("0")

    @staticmethod
    def check_usage_limits(
        db: Session,
        customer_id: str
    ) -> dict:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            return {"error": "Customer not found"}

        month = datetime.utcnow().strftime("%Y-%m")
        usage = db.query(UsageRecord).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.month == month
            )
        ).all()

        total_tokens = sum(u.tokens_input + u.tokens_output for u in usage)
        total_requests = len(usage)

        return {
            "tokens_used": total_tokens,
            "tokens_limit": customer.monthly_limit_tokens,
            "tokens_remaining": max(0, customer.monthly_limit_tokens - total_tokens),
            "tokens_exceeded": total_tokens > customer.monthly_limit_tokens,
            "requests_used": total_requests,
            "requests_limit": customer.monthly_limit_requests,
            "requests_remaining": max(0, customer.monthly_limit_requests - total_requests),
            "requests_exceeded": total_requests > customer.monthly_limit_requests,
        }

    @staticmethod
    def apply_discount(
        db: Session,
        billing_cycle_id: str,
        discount_amount: Decimal,
        reason: str
    ) -> BillingCycle:
        cycle = db.query(BillingCycle).filter_by(id=billing_cycle_id).first()
        if not cycle:
            raise ValueError(f"Billing cycle {billing_cycle_id} not found")

        cycle.discount_usd = discount_amount
        cycle.total_usd = cycle.subtotal_usd - discount_amount + cycle.tax_usd
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def calculate_tax(subtotal: Decimal, tax_rate: Decimal = Decimal("0.1")) -> Decimal:
        return (subtotal * tax_rate).quantize(Decimal("0.01"))

    @staticmethod
    def get_usage_history(
        db: Session,
        customer_id: str,
        months: int = 12
    ) -> list[dict]:
        end_date = datetime.utcnow()
        start_date = end_date - relativedelta(months=months)

        cycles = db.query(BillingCycle).filter(
            and_(
                BillingCycle.customer_id == customer_id,
                BillingCycle.period_start >= start_date,
                BillingCycle.period_end <= end_date
            )
        ).order_by(BillingCycle.period_start.desc()).all()

        return [
            {
                "period_start": c.period_start.isoformat(),
                "period_end": c.period_end.isoformat(),
                "tokens_input": c.total_tokens_input,
                "tokens_output": c.total_tokens_output,
                "requests": c.total_requests,
                "cost": float(c.total_usd)
            }
            for c in cycles
        ]
