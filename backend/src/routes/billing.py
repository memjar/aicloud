from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime

from src.models.billing import BillingTier, StripeCustomer
from src.services.stripe_service import StripeService
from src.services.billing_service import BillingService
from src.services.invoice_service import InvoiceService
from src.services.rate_limit_service import RateLimitService
from src.services.fraud_detection_service import FraudDetectionService
from src.services.webhook_service import WebhookService

router = APIRouter(prefix="/v1/billing", tags=["billing"])

stripe_service = StripeService()
rate_limit_service = RateLimitService()


@router.post("/customers")
async def create_customer(
    account_id: str,
    email: str,
    name: str,
    db: Session = Depends()
):
    customer = stripe_service.create_customer(db, account_id, email, name)
    return {
        "customer_id": customer.id,
        "stripe_customer_id": customer.stripe_customer_id,
        "tier": customer.current_tier.value,
        "created_at": customer.created_at.isoformat()
    }


@router.get("/customers/{account_id}")
async def get_customer(
    account_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "id": customer.id,
        "account_id": customer.account_id,
        "email": customer.email,
        "tier": customer.current_tier.value,
        "monthly_limit_tokens": customer.monthly_limit_tokens,
        "monthly_limit_requests": customer.monthly_limit_requests,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat()
    }


@router.post("/customers/{account_id}/tier")
async def update_tier(
    account_id: str,
    tier: BillingTier,
    db: Session = Depends()
):
    customer = stripe_service.update_billing_tier(db, account_id, tier)
    return {
        "account_id": customer.account_id,
        "tier": customer.current_tier.value,
        "monthly_limit_tokens": customer.monthly_limit_tokens
    }


@router.post("/subscriptions")
async def create_subscription(
    account_id: str,
    tier: BillingTier,
    payment_method_id: str,
    db: Session = Depends()
):
    result = stripe_service.create_subscription(db, account_id, tier, payment_method_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/subscriptions/{account_id}")
async def cancel_subscription(
    account_id: str,
    db: Session = Depends()
):
    result = stripe_service.cancel_subscription(db, account_id)
    return result


@router.post("/usage/track")
async def track_usage(
    account_id: str,
    model_id: str,
    tokens_input: int,
    tokens_output: int,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    should_block, reason = FraudDetectionService.should_block_request(db, customer.id)
    if should_block:
        raise HTTPException(status_code=429, detail=reason)

    usage = BillingService.record_usage(
        db,
        customer.id,
        model_id,
        tokens_input,
        tokens_output
    )

    return {
        "usage_id": usage.id,
        "cost_usd": float(usage.cost_usd),
        "timestamp": usage.timestamp.isoformat()
    }


@router.get("/usage/{account_id}")
async def get_usage(
    account_id: str,
    month: Optional[str] = None,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    usage_data = BillingService.get_monthly_usage(db, customer.id, month)
    return usage_data


@router.get("/usage/{account_id}/limits")
async def check_usage_limits(
    account_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    limits = BillingService.check_usage_limits(db, customer.id)
    return limits


@router.get("/usage/{account_id}/history")
async def get_usage_history(
    account_id: str,
    months: int = 12,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    history = BillingService.get_usage_history(db, customer.id, months)
    return {"history": history}


@router.post("/rate-limit/check")
async def check_rate_limit(
    account_id: str,
    limit_type: str = "requests_per_minute",
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = rate_limit_service.check_rate_limit(db, customer.id, limit_type)

    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result["reason"])

    return result


@router.post("/invoices")
async def create_invoice(
    account_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from dateutil.relativedelta import relativedelta
    period_end = (period_start + relativedelta(months=1)) - relativedelta(seconds=1)

    billing_cycle = BillingService.create_billing_cycle(
        db,
        customer.id,
        period_start,
        period_end
    )

    invoice = InvoiceService.create_invoice(db, customer.id, billing_cycle.id)

    return {
        "invoice_id": invoice.id,
        "stripe_invoice_id": invoice.stripe_invoice_id,
        "amount": float(invoice.amount_usd),
        "status": invoice.status,
        "pdf_url": invoice.pdf_url
    }


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    recipient_email: Optional[str] = None,
    db: Session = Depends()
):
    result = InvoiceService.send_invoice_email(db, invoice_id, recipient_email)
    return result


@router.get("/invoices/{account_id}")
async def list_invoices(
    account_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = InvoiceService.list_invoices(db, customer.id, limit, offset)
    return result


@router.get("/invoices/{invoice_id}/detail")
async def get_invoice(
    invoice_id: str,
    db: Session = Depends()
):
    invoice = InvoiceService.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "id": invoice.id,
        "stripe_id": invoice.stripe_invoice_id,
        "amount": float(invoice.amount_usd),
        "status": invoice.status,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "due_at": invoice.due_at.isoformat() if invoice.due_at else None,
        "pdf_url": invoice.pdf_url
    }


@router.post("/payment-methods")
async def add_payment_method(
    account_id: str,
    payment_method_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    method = stripe_service.add_payment_method(db, account_id, payment_method_id)
    return {
        "id": method.id,
        "card_last4": method.card_last4,
        "card_brand": method.card_brand,
        "exp_month": method.exp_month,
        "exp_year": method.exp_year
    }


@router.get("/payment-methods/{account_id}")
async def list_payment_methods(
    account_id: str,
    db: Session = Depends()
):
    methods = stripe_service.get_payment_methods(db, account_id)
    return {
        "methods": [
            {
                "id": m.id,
                "card_last4": m.card_last4,
                "card_brand": m.card_brand,
                "exp_month": m.exp_month,
                "exp_year": m.exp_year
            }
            for m in methods
        ]
    }


@router.delete("/payment-methods/{account_id}/{payment_method_id}")
async def remove_payment_method(
    account_id: str,
    payment_method_id: str,
    db: Session = Depends()
):
    result = stripe_service.remove_payment_method(db, account_id, payment_method_id)
    return result


@router.get("/fraud/alerts/{account_id}")
async def get_fraud_alerts(
    account_id: str,
    unresolved_only: bool = True,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    alerts = FraudDetectionService.get_fraud_alerts(db, customer.id, unresolved_only)
    return {"alerts": alerts}


@router.get("/fraud/status/{account_id}")
async def get_fraud_status(
    account_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    status = FraudDetectionService.check_account_status(db, customer.id)
    return status


@router.post("/fraud/alerts/{alert_id}/resolve")
async def resolve_fraud_alert(
    alert_id: str,
    resolution_notes: str = "",
    db: Session = Depends()
):
    success = FraudDetectionService.resolve_fraud_alert(db, alert_id, resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "resolved"}


@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends()
):
    body = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    event = WebhookService.construct_event(body, stripe_signature)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid signature")

    result = WebhookService.process_webhook(db, event["type"], event.get("data", {}).get("object", {}))

    if not result["success"]:
        return {"status": "received", "warning": result.get("error")}

    return {"status": "received"}


@router.get("/dashboard/{account_id}")
async def get_billing_dashboard(
    account_id: str,
    db: Session = Depends()
):
    customer = stripe_service.get_customer(db, account_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    current_month_usage = BillingService.get_monthly_usage(db, customer.id)
    current_month_cost = BillingService.get_current_month_cost(db, customer.id)
    limits = BillingService.check_usage_limits(db, customer.id)
    fraud_status = FraudDetectionService.check_account_status(db, customer.id)

    return {
        "customer": {
            "id": customer.id,
            "email": customer.email,
            "tier": customer.current_tier.value,
            "is_active": customer.is_active
        },
        "usage": {
            "tokens_input": current_month_usage["tokens_input"],
            "tokens_output": current_month_usage["tokens_output"],
            "total_requests": current_month_usage["total_requests"],
            "cost_usd": float(current_month_cost)
        },
        "limits": limits,
        "fraud": fraud_status
    }
