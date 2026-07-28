# Stripe Billing Integration - aimodels.cloud

Complete Stripe billing system for tracking usage, calculating charges, managing customers, and processing payments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│  POST /v1/billing/* routes (FastAPI)                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                  Service Layer                          │
├──────────────────────────────────────────────────────────┤
│ • StripeService (customer & subscription management)    │
│ • BillingService (usage tracking & calculations)       │
│ • InvoiceService (invoice generation & email)          │
│ • RateLimitService (tier-based rate limiting)          │
│ • FraudDetectionService (anomaly detection)            │
│ • WebhookService (Stripe event handling)               │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│              Database Models (PostgreSQL)               │
├──────────────────────────────────────────────────────────┤
│ • StripeCustomer (customer profiles)                    │
│ • UsageRecord (usage tracking per request)             │
│ • BillingCycle (monthly billing periods)               │
│ • Invoice (generated invoices)                          │
│ • PaymentMethod (saved payment methods)                │
│ • FraudAlert (fraud detection alerts)                  │
│ • RateLimitConfig (tier configurations)                │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│              External Services                          │
├──────────────────────────────────────────────────────────┤
│ • Stripe API (payments & subscriptions)                 │
│ • SMTP (invoice email delivery)                         │
│ • Redis (rate limiting & caching)                       │
└──────────────────────────────────────────────────────────┘
```

## Database Schema

### stripe_customers
Primary customer management table.

```sql
CREATE TABLE stripe_customers (
  id VARCHAR PRIMARY KEY,
  account_id VARCHAR UNIQUE NOT NULL,
  stripe_customer_id VARCHAR UNIQUE,
  email VARCHAR NOT NULL,
  current_tier ENUM('free', 'pro', 'enterprise'),
  stripe_subscription_id VARCHAR,
  monthly_limit_tokens INTEGER,
  monthly_limit_requests INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### usage_records
Individual API request tracking for billing.

```sql
CREATE TABLE usage_records (
  id VARCHAR PRIMARY KEY,
  customer_id VARCHAR REFERENCES stripe_customers(id),
  model_id VARCHAR NOT NULL,
  tokens_input INTEGER,
  tokens_output INTEGER,
  requests_count INTEGER DEFAULT 1,
  cost_usd DECIMAL(19, 8),
  timestamp TIMESTAMP,
  month VARCHAR -- YYYY-MM for aggregation
);
```

### billing_cycles
Monthly billing cycles with aggregated usage.

```sql
CREATE TABLE billing_cycles (
  id VARCHAR PRIMARY KEY,
  customer_id VARCHAR REFERENCES stripe_customers(id),
  period_start TIMESTAMP,
  period_end TIMESTAMP,
  total_tokens_input INTEGER,
  total_tokens_output INTEGER,
  total_requests INTEGER,
  subtotal_usd DECIMAL(19, 8),
  discount_usd DECIMAL(19, 8),
  tax_usd DECIMAL(19, 8),
  total_usd DECIMAL(19, 8),
  status VARCHAR DEFAULT 'open',
  created_at TIMESTAMP
);
```

### invoices
Generated invoices sent to customers.

```sql
CREATE TABLE invoices (
  id VARCHAR PRIMARY KEY,
  customer_id VARCHAR REFERENCES stripe_customers(id),
  stripe_invoice_id VARCHAR UNIQUE,
  billing_cycle_id VARCHAR REFERENCES billing_cycles(id),
  amount_usd DECIMAL(19, 8),
  tax_usd DECIMAL(19, 8),
  status VARCHAR DEFAULT 'draft',
  issued_at TIMESTAMP,
  due_at TIMESTAMP,
  paid_at TIMESTAMP,
  pdf_url VARCHAR,
  created_at TIMESTAMP
);
```

### payment_methods
Saved customer payment methods.

```sql
CREATE TABLE payment_methods (
  id VARCHAR PRIMARY KEY,
  customer_id VARCHAR REFERENCES stripe_customers(id),
  stripe_payment_method_id VARCHAR UNIQUE,
  card_last4 VARCHAR,
  card_brand VARCHAR,
  exp_month INTEGER,
  exp_year INTEGER,
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP
);
```

### fraud_alerts
Detected fraud/anomaly alerts.

```sql
CREATE TABLE fraud_alerts (
  id VARCHAR PRIMARY KEY,
  customer_id VARCHAR REFERENCES stripe_customers(id),
  alert_type VARCHAR,
  severity VARCHAR,
  message TEXT,
  detected_at TIMESTAMP,
  is_resolved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP
);
```

### rate_limit_configs
Rate limiting configuration per tier.

```sql
CREATE TABLE rate_limit_configs (
  id VARCHAR PRIMARY KEY,
  tier ENUM UNIQUE,
  requests_per_minute INTEGER,
  requests_per_day INTEGER,
  tokens_per_month INTEGER,
  concurrent_requests INTEGER,
  created_at TIMESTAMP
);
```

## Pricing Model

### Model Costs (per 1M tokens)

| Model | Input | Output |
|-------|-------|--------|
| GPT-4 | $40 | $120 |
| Claude 3 Opus | $15 | $75 |
| Together Llama | $1.60 | $1.60 |
| Local/Custom | $0 | $0 |

### Markup: 2.5x (provider cost × 2.5)

**Example: GPT-4 inference**
- 1000 input tokens + 500 output tokens
- Cost: (1000/1M × $40 + 500/1M × $120) × 2.5
- Cost: ($0.04 + $0.06) × 2.5 = **$0.25**

### Billing Tiers

| Tier | Monthly Cost | Token Limit | Request Limit | RPM | Features |
|------|----------|------|------|-------|----------|
| FREE | Free | 1M | 10K | 10 | Public models, trial access |
| PRO | $29 | 100M | 1M | 100 | Production-ready, custom rate limits |
| ENTERPRISE | Custom | Unlimited | Unlimited | Custom | Dedicated support, SLA |

## API Endpoints

### Customer Management

**Create Customer**
```
POST /v1/billing/customers
{
  "account_id": "acc_123",
  "email": "user@example.com",
  "name": "John Doe"
}
```

Response:
```json
{
  "customer_id": "cust_xyz",
  "stripe_customer_id": "cus_123",
  "tier": "free",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Get Customer**
```
GET /v1/billing/customers/{account_id}
```

**Update Tier**
```
POST /v1/billing/customers/{account_id}/tier
{
  "tier": "pro"
}
```

### Subscriptions

**Create Subscription**
```
POST /v1/billing/subscriptions
{
  "account_id": "acc_123",
  "tier": "pro",
  "payment_method_id": "pm_123"
}
```

**Cancel Subscription**
```
DELETE /v1/billing/subscriptions/{account_id}
```

### Usage Tracking

**Track Usage (called after each inference)**
```
POST /v1/billing/usage/track
{
  "account_id": "acc_123",
  "model_id": "gpt-4",
  "tokens_input": 100,
  "tokens_output": 50
}
```

Response:
```json
{
  "usage_id": "usage_abc",
  "cost_usd": 0.25,
  "timestamp": "2024-01-15T10:00:00Z"
}
```

**Get Monthly Usage**
```
GET /v1/billing/usage/{account_id}?month=2024-01
```

Response:
```json
{
  "month": "2024-01",
  "tokens_input": 5000000,
  "tokens_output": 2500000,
  "total_cost": 125.50,
  "total_requests": 5000,
  "usage_by_model": {
    "gpt-4": {
      "tokens_input": 3000000,
      "tokens_output": 1500000,
      "cost": 75.00,
      "requests": 3000
    }
  }
}
```

**Check Usage Limits**
```
GET /v1/billing/usage/{account_id}/limits
```

Response:
```json
{
  "tokens_used": 7500000,
  "tokens_limit": 100000000,
  "tokens_remaining": 92500000,
  "tokens_exceeded": false,
  "requests_used": 5000,
  "requests_limit": 1000000,
  "requests_remaining": 995000,
  "requests_exceeded": false
}
```

### Rate Limiting

**Check Rate Limit**
```
POST /v1/billing/rate-limit/check
{
  "account_id": "acc_123",
  "limit_type": "requests_per_minute"  # or requests_per_day
}
```

Response (if allowed):
```json
{
  "allowed": true,
  "limit": 100,
  "current": 45,
  "remaining": 55
}
```

### Invoicing

**Create Invoice**
```
POST /v1/billing/invoices
{
  "account_id": "acc_123"
}
```

**Send Invoice Email**
```
POST /v1/billing/invoices/{invoice_id}/send
{
  "recipient_email": "user@example.com"
}
```

**List Invoices**
```
GET /v1/billing/invoices/{account_id}?limit=50&offset=0
```

**Get Invoice Details**
```
GET /v1/billing/invoices/{invoice_id}/detail
```

### Payment Methods

**Add Payment Method**
```
POST /v1/billing/payment-methods
{
  "account_id": "acc_123",
  "payment_method_id": "pm_123"
}
```

**List Payment Methods**
```
GET /v1/billing/payment-methods/{account_id}
```

**Remove Payment Method**
```
DELETE /v1/billing/payment-methods/{account_id}/{payment_method_id}
```

### Fraud Detection

**Get Fraud Alerts**
```
GET /v1/billing/fraud/alerts/{account_id}?unresolved_only=true
```

**Check Account Status**
```
GET /v1/billing/fraud/status/{account_id}
```

Response:
```json
{
  "status": "normal|caution|risky",
  "alerts": [
    {
      "type": "usage_spike",
      "severity": "high",
      "message": "Usage spike detected: $500 vs avg $100"
    }
  ],
  "current_month_cost": 500.00
}
```

**Resolve Alert**
```
POST /v1/billing/fraud/alerts/{alert_id}/resolve
{
  "resolution_notes": "Legitimate spike due to campaign"
}
```

### Dashboard

**Get Billing Dashboard**
```
GET /v1/billing/dashboard/{account_id}
```

Response:
```json
{
  "customer": {
    "id": "cust_xyz",
    "email": "user@example.com",
    "tier": "pro",
    "is_active": true
  },
  "usage": {
    "tokens_input": 5000000,
    "tokens_output": 2500000,
    "total_requests": 5000,
    "cost_usd": 125.50
  },
  "limits": {
    "tokens_used": 7500000,
    "tokens_limit": 100000000,
    "tokens_remaining": 92500000
  },
  "fraud": {
    "status": "normal",
    "alerts": []
  }
}
```

### Webhooks

**Stripe Webhook Handler**
```
POST /v1/billing/webhooks/stripe
Headers: stripe-signature: <signature>
```

Handles:
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `charge.refunded`

## Implementation Guide

### 1. Environment Setup

Create `.env.local`:
```
STRIPE_API_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_ENTERPRISE=price_yyy

DATABASE_URL=postgresql://user:password@localhost/aimodels
REDIS_URL=redis://localhost:6379

SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxx
FROM_EMAIL=noreply@aimodels.cloud
```

### 2. Database Migrations

```bash
poetry run alembic init alembic
poetry run alembic revision --autogenerate -m "Add billing tables"
poetry run alembic upgrade head
```

### 3. Initialize Rate Limit Tiers

```python
from src.services.rate_limit_service import RateLimitService
from sqlalchemy.orm import Session

db = Session()
RateLimitService().initialize_tier_configs(db)
```

### 4. Register Routes

In `backend/src/main.py`:
```python
from src.routes.billing import router as billing_router

app.include_router(billing_router)
```

### 5. Usage Tracking Middleware

Add to inference endpoint:
```python
from src.services.billing_service import BillingService

# After inference completes
BillingService.record_usage(
    db,
    customer.id,
    model_id,
    tokens_input,
    tokens_output
)
```

### 6. Setup Stripe Webhooks

In Stripe Dashboard:
1. Go to Settings → Webhooks
2. Add endpoint: `https://api.aimodels.cloud/v1/billing/webhooks/stripe`
3. Subscribe to events (see Webhook Handler above)
4. Copy signing secret to `STRIPE_WEBHOOK_SECRET`

## Fraud Detection Strategy

### Detectors

**1. Usage Spike Detection**
- Compares current usage to 7-day average
- Triggers if > 3x average
- Severity: HIGH

**2. Rapid Requests Detection**
- Checks for 100+ requests in 5 minutes
- Indicates potential bot/abuse
- Severity: HIGH

**3. Unusual Pattern Detection**
- Compares today's requests to daily average
- Triggers if > 5x average
- Severity: MEDIUM

### Response Actions

| Severity | Status | Action |
|----------|--------|--------|
| MEDIUM | Caution | Monitor, notify admin |
| HIGH | Risky | Block requests, notify user |
| 2+ HIGH | Risky | Suspend account, freeze billing |

### Example Flow

```python
# When processing a request
from src.services.fraud_detection_service import FraudDetectionService

should_block, reason = FraudDetectionService.should_block_request(db, customer_id)

if should_block:
    raise HTTPException(status_code=429, detail=reason)

# Track the request
BillingService.record_usage(db, customer_id, model_id, tokens_in, tokens_out)

# Periodically check status
status = FraudDetectionService.check_account_status(db, customer_id)
```

## Testing

### Unit Tests

```python
def test_create_customer():
    stripe_service = StripeService()
    customer = stripe_service.create_customer(db, "acc_1", "test@example.com", "Test")
    assert customer.account_id == "acc_1"

def test_usage_tracking():
    BillingService.record_usage(db, customer_id, "gpt-4", 1000, 500)
    usage_data = BillingService.get_monthly_usage(db, customer_id)
    assert usage_data["total_cost"] > 0

def test_rate_limiting():
    result = rate_limit_service.check_rate_limit(db, customer_id)
    assert result["allowed"] == True
```

### Integration Tests

```bash
# Start test server
poetry run pytest tests/test_billing.py -v

# Run with coverage
poetry run pytest tests/ --cov=src --cov-report=html
```

## Monitoring

### Metrics to Track

- **Daily active users**: count(distinct customer_id) per day
- **MoM growth**: revenue comparison month-over-month
- **ARPU**: average revenue per user (total revenue / active users)
- **Churn rate**: (cancelled subscriptions / active subs) per month
- **Payment success rate**: (successful payments / total attempts)

### Alerts

Setup monitoring for:
- Payment failure rate > 10%
- Fraud alert rate > 100 per day
- Revenue anomaly (30% spike vs baseline)
- Database query performance (>500ms)

### Example Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

billing_total_revenue = Counter('billing_total_revenue_usd', 'Total revenue')
active_customers = Gauge('billing_active_customers', 'Active customers')
usage_cost = Histogram('billing_usage_cost', 'Cost per request')
invoice_payment_time = Histogram('billing_invoice_payment_days', 'Days to payment')
```

## Deployment Checklist

- [ ] Stripe account created with API keys
- [ ] Webhook secret configured in environment
- [ ] Database migrations applied
- [ ] Rate limit tiers initialized
- [ ] SMTP credentials configured
- [ ] Redis connection tested
- [ ] Payment methods tested (use test cards)
- [ ] Invoice email template tested
- [ ] Fraud detection thresholds tuned
- [ ] Monitoring and alerts configured
- [ ] Rate limit headers added to API responses
- [ ] Documentation updated for customers
- [ ] Support process documented

## Cost Optimization

### For Customers

1. **Batch Requests**: Multiple inferences in one call = better rate
2. **Model Selection**: Local models are free
3. **Caching**: Enable result caching to reduce redundant calls
4. **Off-peak Usage**: Could offer time-based pricing

### For Platform

1. **VLL Quantization**: Reduce model size (4-bit quantization)
2. **Request Batching**: Process multiple requests together
3. **Model Caching**: Keep popular models in memory
4. **CDN for Static Assets**: Reduce bandwidth

## Revenue Projections

### Assumptions
- 100 Pro users @ $29/month = $2,900
- 10 Enterprise customers @ $500/month = $5,000
- 50% usage-based overage @ $50/customer = $2,500
- **Total: $10,400/month**

### Year 1 Growth Target
- Month 1: 100 Pro
- Month 6: 500 Pro + 20 Enterprise
- Month 12: 1000 Pro + 50 Enterprise
- **Year 1 ARR: ~$500K**

## References

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Stripe Payment Methods](https://stripe.com/docs/payments/payment-methods)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
