# Stripe Billing System - Complete Integration

Full-featured Stripe billing integration for aimodels.cloud, including usage tracking, invoice generation, fraud detection, and rate limiting.

## Quick Start

1. **Setup Stripe Account**
   ```bash
   # See STRIPE_SETUP.md for detailed instructions
   ```

2. **Install Dependencies**
   ```bash
   cd backend
   poetry install
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env.local
   # Edit with your Stripe keys and database credentials
   ```

4. **Initialize Database**
   ```bash
   poetry run python setup_billing.py
   ```

5. **Start Server**
   ```bash
   poetry run uvicorn src.main:app --reload --port 8000
   ```

6. **View API Docs**
   Open http://localhost:8000/docs

## What's Included

### Core Services

| Service | Purpose | File |
|---------|---------|------|
| **StripeService** | Customer & subscription management | `src/services/stripe_service.py` |
| **BillingService** | Usage tracking & cost calculation | `src/services/billing_service.py` |
| **InvoiceService** | Invoice generation & email | `src/services/invoice_service.py` |
| **RateLimitService** | Tier-based rate limiting | `src/services/rate_limit_service.py` |
| **FraudDetectionService** | Anomaly detection & alerts | `src/services/fraud_detection_service.py` |
| **WebhookService** | Stripe event handling | `src/services/webhook_service.py` |

### Database Models

| Model | Purpose |
|-------|---------|
| `StripeCustomer` | Customer profiles with tier info |
| `UsageRecord` | Individual API request tracking |
| `BillingCycle` | Monthly billing periods |
| `Invoice` | Generated invoices |
| `PaymentMethod` | Saved payment methods |
| `FraudAlert` | Fraud detection alerts |
| `RateLimitConfig` | Tier-based rate limit configs |

### API Endpoints

**Customer Management**
- `POST /v1/billing/customers` - Create customer
- `GET /v1/billing/customers/{account_id}` - Get customer
- `POST /v1/billing/customers/{account_id}/tier` - Update tier

**Subscriptions**
- `POST /v1/billing/subscriptions` - Create subscription
- `DELETE /v1/billing/subscriptions/{account_id}` - Cancel

**Usage & Billing**
- `POST /v1/billing/usage/track` - Track usage
- `GET /v1/billing/usage/{account_id}` - Get monthly usage
- `GET /v1/billing/usage/{account_id}/limits` - Check limits
- `GET /v1/billing/usage/{account_id}/history` - Usage history

**Rate Limiting**
- `POST /v1/billing/rate-limit/check` - Check rate limit

**Invoicing**
- `POST /v1/billing/invoices` - Create invoice
- `POST /v1/billing/invoices/{invoice_id}/send` - Send email
- `GET /v1/billing/invoices/{account_id}` - List invoices
- `GET /v1/billing/invoices/{invoice_id}/detail` - Get invoice

**Payment Methods**
- `POST /v1/billing/payment-methods` - Add method
- `GET /v1/billing/payment-methods/{account_id}` - List methods
- `DELETE /v1/billing/payment-methods/{account_id}/{id}` - Remove method

**Fraud Detection**
- `GET /v1/billing/fraud/alerts/{account_id}` - Get alerts
- `GET /v1/billing/fraud/status/{account_id}` - Check status
- `POST /v1/billing/fraud/alerts/{alert_id}/resolve` - Resolve alert

**Dashboard**
- `GET /v1/billing/dashboard/{account_id}` - Full billing dashboard

**Webhooks**
- `POST /v1/billing/webhooks/stripe` - Stripe webhook receiver

## Pricing Model

### Costs per 1M tokens (with 2.5x markup):

| Model | Input | Output | Example (1K in + 500 out) |
|-------|-------|--------|--------------------------|
| GPT-4 | $40 | $120 | $0.25 |
| Claude 3 Opus | $15 | $75 | $0.11 |
| Together Llama | $1.60 | $1.60 | $0.004 |
| Local/Custom | $0 | $0 | $0 |

### Billing Tiers:

| Tier | Price | Token Limit | Requests | RPM | Features |
|------|-------|-----|---------|-----|----------|
| FREE | Free | 1M | 10K | 10 | Demo access |
| PRO | $29/mo | 100M | 1M | 100 | Production-ready |
| ENTERPRISE | Custom | Unlimited | Unlimited | Custom | Premium support |

## Usage Example

### 1. Create Customer

```python
from src.services.stripe_service import StripeService

stripe_service = StripeService()
customer = stripe_service.create_customer(
    db,
    account_id="acc_123",
    email="user@example.com",
    name="John Doe"
)
```

### 2. Track Usage

```python
from src.services.billing_service import BillingService

BillingService.record_usage(
    db,
    customer_id=customer.id,
    model_id="gpt-4",
    tokens_input=1000,
    tokens_output=500
)
```

### 3. Get Monthly Usage

```python
usage = BillingService.get_monthly_usage(db, customer.id)
print(f"Cost this month: ${usage['total_cost']:.2f}")
print(f"Requests: {usage['total_requests']}")
```

### 4. Create Invoice

```python
from src.services.invoice_service import InvoiceService
from src.services.billing_service import BillingService
from datetime import datetime
from dateutil.relativedelta import relativedelta

now = datetime.utcnow()
period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
period_end = (period_start + relativedelta(months=1)) - relativedelta(seconds=1)

cycle = BillingService.create_billing_cycle(db, customer.id, period_start, period_end)
invoice = InvoiceService.create_invoice(db, customer.id, cycle.id)
InvoiceService.send_invoice_email(db, invoice.id)
```

### 5. Check Fraud Status

```python
from src.services.fraud_detection_service import FraudDetectionService

status = FraudDetectionService.check_account_status(db, customer.id)
if status["status"] == "risky":
    # Take action - suspend account, alert admin, etc.
    pass
```

## Fraud Detection

### Detection Methods

1. **Usage Spike** - Current cost > 3x weekly average
2. **Rapid Requests** - 100+ requests in 5 minutes
3. **Unusual Pattern** - Today's requests > 5x daily average

### Response Actions

- **MEDIUM severity** - Add caution flag, monitor
- **HIGH severity** - Block requests, notify user
- **Multiple HIGH** - Suspend account

Example:

```python
should_block, reason = FraudDetectionService.should_block_request(db, customer_id)
if should_block:
    raise HTTPException(status_code=429, detail=reason)
```

## Rate Limiting

### Implementation in Middleware

```python
from src.services.rate_limit_service import RateLimitService

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    customer_id = request.headers.get("X-Customer-ID")
    
    rate_limit_service = RateLimitService()
    result = rate_limit_service.check_rate_limit(
        db, customer_id, limit_type="requests_per_minute"
    )
    
    if not result["allowed"]:
        return JSONResponse(
            status_code=429,
            content={"error": result["reason"]}
        )
    
    return await call_next(request)
```

## Testing

### Run Tests

```bash
cd backend
poetry run pytest tests/test_billing.py -v
```

### Test Coverage

```bash
poetry run pytest tests/ --cov=src --cov-report=html
```

### Example Test

```python
def test_usage_tracking():
    customer = stripe_service.create_customer(db, "acc_1", "test@example.com", "Test")
    BillingService.record_usage(db, customer.id, "gpt-4", 1000, 500)
    usage = BillingService.get_monthly_usage(db, customer.id)
    assert usage["total_cost"] > 0
```

## Monitoring & Alerts

### Key Metrics

- **Daily Active Users** - `SELECT COUNT(DISTINCT account_id) FROM usage_records WHERE DATE(timestamp) = TODAY()`
- **Total Revenue** - `SELECT SUM(cost_usd) FROM usage_records WHERE EXTRACT(MONTH FROM timestamp) = CURRENT_MONTH`
- **Payment Success Rate** - `SELECT COUNT(*) FILTER (WHERE status='paid') / COUNT(*) FROM invoices`
- **Fraud Alert Rate** - `SELECT COUNT(*) FROM fraud_alerts WHERE is_resolved=FALSE`

### Setup Alerts

```bash
# Email alert on payment failure > 10%
SELECT COUNT(*) FILTER (WHERE status='failed') * 100.0 / COUNT(*)
FROM invoices
WHERE created_at > NOW() - INTERVAL '24 hours'
```

## Production Checklist

- [ ] Stripe Live keys configured
- [ ] PostgreSQL production database setup
- [ ] Redis production instance running
- [ ] SMTP credentials verified
- [ ] SSL/TLS enabled on all endpoints
- [ ] Webhook signing secret stored securely
- [ ] Database backups scheduled
- [ ] Error logging (Sentry) configured
- [ ] Monitoring dashboard setup
- [ ] Rate limit thresholds tuned
- [ ] Customer communication plan ready
- [ ] Support process documented
- [ ] Tax calculations verified (if applicable)

## File Structure

```
backend/
├── src/
│   ├── models/
│   │   └── billing.py              # Database models
│   ├── services/
│   │   ├── stripe_service.py       # Stripe integration
│   │   ├── billing_service.py      # Usage tracking & calculations
│   │   ├── invoice_service.py      # Invoicing & email
│   │   ├── rate_limit_service.py   # Rate limiting
│   │   ├── fraud_detection_service.py  # Fraud detection
│   │   └── webhook_service.py      # Webhook handling
│   └── routes/
│       └── billing.py              # API endpoints
├── tests/
│   └── test_billing.py             # Test suite
├── setup_billing.py                # Setup script
├── .env.example                    # Environment template
└── pyproject.toml                  # Dependencies

docs/
├── BILLING_INTEGRATION.md          # Complete API documentation
├── STRIPE_SETUP.md                 # Setup guide
└── BILLING_README.md               # This file
```

## Support & Documentation

- **API Docs** - http://localhost:8000/docs (when running)
- **Stripe Docs** - https://stripe.com/docs
- **Setup Guide** - See STRIPE_SETUP.md
- **Full Integration** - See BILLING_INTEGRATION.md
- **Database Schema** - See models in src/models/billing.py

## Key Implementation Details

### Usage Tracking

Every inference call should record usage:

```python
@app.post("/v1/infer")
async def infer(request: InferenceRequest, db: Session = Depends()):
    # ... run inference ...
    
    # Track usage
    BillingService.record_usage(
        db,
        customer_id,
        model_id,
        tokens_input,
        tokens_output
    )
```

### Monthly Billing

Should be run monthly (via cron or scheduled job):

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

def monthly_billing_job():
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0)
    period_end = (period_start + relativedelta(months=1)) - relativedelta(seconds=1)
    
    customers = db.query(StripeCustomer).filter_by(is_active=True).all()
    for customer in customers:
        cycle = BillingService.create_billing_cycle(
            db, customer.id, period_start, period_end
        )
        invoice = InvoiceService.create_invoice(db, customer.id, cycle.id)
        InvoiceService.send_invoice_email(db, invoice.id)
```

### Webhook Processing

All Stripe events are handled in `WebhookService`:

```python
stripe_event = stripe.Webhook.construct_event(
    payload, signature, webhook_secret
)
result = WebhookService.process_webhook(
    db, stripe_event["type"], stripe_event["data"]["object"]
)
```

## Performance Optimization

### Database Indexes

Key indexes for performance:

```sql
CREATE INDEX idx_usage_records_customer_month ON usage_records(customer_id, month);
CREATE INDEX idx_billing_cycles_customer_date ON billing_cycles(customer_id, period_start);
CREATE INDEX idx_fraud_alerts_customer_resolved ON fraud_alerts(customer_id, is_resolved);
```

### Caching

Rate limit counters cached in Redis:

```python
key = f"rate_limit:{customer_id}:{limit_type}"
current = self.redis_client.get(key)
self.redis_client.expire(key, 60)  # 60 second TTL
```

## Cost Analysis

### Monthly Infrastructure Cost
- PostgreSQL: ~$50
- Redis: ~$20
- Stripe processing: ~2.9% + $0.30 per transaction
- SMTP: ~$30 (SendGrid)
- **Total: ~$100 + transaction fees**

### Revenue Potential (Year 1)
- 100 Pro users @ $29 = $2,900/mo
- 10 Enterprise @ $500 = $5,000/mo
- 50% usage overages = $2,500/mo
- **Total: ~$10,400/mo = $125K/year**

## Next Steps

1. **Complete Stripe Setup** - Follow STRIPE_SETUP.md
2. **Integrate with Inference** - Add usage tracking to `/v1/infer`
3. **Setup Monitoring** - Configure alerts for fraud/payments
4. **Deploy to Production** - Use Docker + Kubernetes
5. **Customer Communication** - Update docs with pricing
6. **Tax Compliance** - Verify sales tax handling
7. **Support Process** - Define billing support workflow

## Contact & Support

For issues or questions:
1. Check documentation (BILLING_INTEGRATION.md, STRIPE_SETUP.md)
2. Review test cases (tests/test_billing.py)
3. Check Stripe dashboard for webhook logs
4. Review API server logs for errors

---

Built for aimodels.cloud - White-label AI inference platform
