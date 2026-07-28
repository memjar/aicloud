# Stripe Setup Guide

Complete setup instructions for integrating Stripe billing into aimodels.cloud.

## Prerequisites

- Stripe account (https://stripe.com)
- Python 3.11+
- PostgreSQL database
- Redis instance
- SMTP credentials (SendGrid, etc.)

## Step 1: Create Stripe Account

1. Go to https://stripe.com/register
2. Sign up with business email
3. Verify email and complete onboarding
4. Go to Dashboard → Settings → API Keys
5. Copy test keys (starts with `sk_test_`)

## Step 2: Configure Environment

Copy `.env.example` to `.env.local`:

```bash
cp backend/.env.example backend/.env.local
```

Edit `backend/.env.local` with your credentials:

```env
# Stripe (from API Keys page)
STRIPE_API_KEY=sk_test_XXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXX (we'll get this in step 4)

# Prices (we'll create these in step 3)
STRIPE_PRICE_PRO=price_XXXXX
STRIPE_PRICE_ENTERPRISE=price_XXXXX

# Database
DATABASE_URL=postgresql://user:password@localhost/aimodels_dev

# Redis
REDIS_URL=redis://localhost:6379

# Email (SendGrid example)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.XXXXX
FROM_EMAIL=noreply@aimodels.cloud
```

## Step 3: Create Stripe Products & Prices

### In Stripe Dashboard:

**1. Create PRO Product**

- Settings → Products
- Click "Create product"
- Name: "PRO"
- Price type: "Recurring"
- Billing period: "Monthly"
- Price: $29.00
- Create product
- Copy `price_` ID to `STRIPE_PRICE_PRO`

**2. Create ENTERPRISE Product**

- Create another product
- Name: "ENTERPRISE"
- Price: Use custom price or leave as-is
- Copy `price_` ID to `STRIPE_PRICE_ENTERPRISE`

Alternatively, use Stripe CLI:

```bash
stripe products create --name="PRO" --type=service

stripe prices create \
  --unit-amount=2900 \
  --currency=usd \
  --recurring='{"interval":"month"}' \
  --product=<PRODUCT_ID>
```

## Step 4: Setup Webhooks

### In Stripe Dashboard:

1. Go to Settings → Webhooks
2. Click "Add endpoint"
3. Endpoint URL: `https://api.aimodels.cloud/v1/billing/webhooks/stripe`
   - For local testing: `http://localhost:8000/v1/billing/webhooks/stripe`
4. Events to send:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `charge.refunded`
5. Click "Create endpoint"
6. Copy signing secret (starts with `whsec_`) to `STRIPE_WEBHOOK_SECRET`

### Alternative: Using Stripe CLI for Local Development

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe  # macOS
# or https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe

# Copy the webhook signing secret
# Add to .env.local as STRIPE_WEBHOOK_SECRET
```

## Step 5: Install Dependencies

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
poetry install
```

## Step 6: Setup Database

```bash
# Create PostgreSQL database
createdb aimodels_dev

# Run migrations (if using Alembic)
poetry run alembic upgrade head

# Or initialize tables directly
poetry run python setup_billing.py
```

This will:
- Create all billing tables
- Initialize rate limit tiers (FREE, PRO, ENTERPRISE)
- Verify configuration

## Step 7: Start Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start API server
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# View API docs at http://localhost:8000/docs
```

## Step 8: Test Endpoints

### Test Customer Creation

```bash
curl -X POST http://localhost:8000/v1/billing/customers \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "acc_test_1",
    "email": "test@example.com",
    "name": "Test User"
  }'
```

Response:
```json
{
  "customer_id": "cust_xxx",
  "stripe_customer_id": "cus_xxx",
  "tier": "free",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Test Usage Tracking

```bash
curl -X POST http://localhost:8000/v1/billing/usage/track \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "acc_test_1",
    "model_id": "gpt-4",
    "tokens_input": 1000,
    "tokens_output": 500
  }'
```

### Test Get Usage

```bash
curl http://localhost:8000/v1/billing/usage/acc_test_1
```

### Test Rate Limiting

```bash
curl -X POST http://localhost:8000/v1/billing/rate-limit/check \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "acc_test_1",
    "limit_type": "requests_per_minute"
  }'
```

## Step 9: Test with Stripe Test Cards

Use these test card numbers in Stripe's hosted payment page:

| Card Number | Expiry | CVC | Result |
|---|---|---|---|
| 4242 4242 4242 4242 | 12/25 | 123 | Success |
| 4000 0000 0000 0002 | 12/25 | 123 | Card declined |
| 4000 0025 0000 3155 | 12/25 | 123 | CVC fails |

## Step 10: Testing Webhooks Locally

```bash
# Terminal 1: Start API server
cd backend
poetry run uvicorn src.main:app --reload --port 8000

# Terminal 2: Forward webhooks
stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe

# Terminal 3: Trigger test webhook
stripe trigger payment_intent.succeeded
```

Check server logs for webhook processing.

## Step 11: Production Deployment

### 1. Update Environment Variables

Set production values in your deployment platform:

```bash
# AWS: Systems Manager Parameter Store, Secrets Manager
# Vercel: Project Settings → Environment Variables
# Heroku: Config Vars

STRIPE_API_KEY=sk_live_XXXXX  # Live key!
STRIPE_WEBHOOK_SECRET=whsec_live_XXXXX
DATABASE_URL=postgresql://prod-user:password@prod-host/aimodels_prod
REDIS_URL=redis://prod-redis-host:6379
SMTP_PASSWORD=SG.prod_key
```

### 2. Verify SSL/TLS

Stripe requires HTTPS for all endpoints:

```bash
# Test SSL
curl -I https://api.aimodels.cloud/v1/billing/webhooks/stripe
# Should respond with 400 Bad Request (no signature), not SSL error
```

### 3. Run Database Migrations

```bash
poetry run alembic upgrade head
```

### 4. Initialize Rate Limits

```bash
poetry run python setup_billing.py
```

### 5. Configure Production Webhooks

In Stripe Dashboard:
1. Switch to Live mode
2. Go to Settings → Webhooks
3. Add endpoint with production URL
4. Copy live webhook secret

### 6. Test Production

```bash
# Use live test mode card
curl -X POST https://api.aimodels.cloud/v1/billing/customers \
  -H "Content-Type: application/json" \
  -d '{"account_id": "prod_1", "email": "prod@example.com", "name": "Prod Test"}'

# Monitor webhook logs in Stripe Dashboard
```

## Troubleshooting

### Issue: "Invalid API Key"

**Solution:** Verify key in `.env.local`:
```bash
grep STRIPE_API_KEY backend/.env.local
```

Key should start with `sk_test_` (development) or `sk_live_` (production).

### Issue: "Webhook Signature Verification Failed"

**Solution:** Verify webhook secret matches:

```bash
grep STRIPE_WEBHOOK_SECRET backend/.env.local
```

In Stripe Dashboard, check the signing secret matches exactly.

### Issue: "Customer Not Found"

**Solution:** Customer must exist before usage tracking:

```bash
# Create customer first
curl -X POST http://localhost:8000/v1/billing/customers \
  -H "Content-Type: application/json" \
  -d '{"account_id": "acc_test", "email": "test@example.com", "name": "Test"}'
```

### Issue: Redis Connection Error

**Solution:** Verify Redis is running:

```bash
redis-cli ping
# Should respond: PONG

# If not running, start it
redis-server
```

### Issue: Database Connection Error

**Solution:** Verify PostgreSQL:

```bash
psql -U postgres -d aimodels_dev -c "SELECT 1"
# Should return: 1
```

### Issue: Email Not Sending

**Solution:** Verify SMTP credentials:

```bash
# Test with telnet
telnet smtp.sendgrid.net 587

# Or enable debug logging
LOG_LEVEL=DEBUG poetry run uvicorn src.main:app --reload
```

## Monitoring

### Check Stripe Activity

```bash
# List recent events
stripe events list

# View specific event
stripe events retrieve evt_XXXXX

# View payment intents
stripe paymentintents list
```

### Check API Metrics

```bash
# View API usage in Stripe Dashboard
# Settings → Usage

# Check webhook delivery
# Webhooks → View details → Event log
```

### Database Queries

```sql
-- Check customer count
SELECT COUNT(*) FROM stripe_customers;

-- Check total usage this month
SELECT SUM(cost_usd) FROM usage_records WHERE EXTRACT(MONTH FROM timestamp) = EXTRACT(MONTH FROM NOW());

-- Check fraud alerts
SELECT * FROM fraud_alerts WHERE is_resolved = FALSE;

-- Check failed invoices
SELECT * FROM invoices WHERE status = 'failed';
```

## Security Best Practices

1. **Never commit API keys** to git
   ```bash
   echo "*.env.local" >> .gitignore
   ```

2. **Rotate keys regularly**
   - Quarterly key rotation
   - Immediately if compromised

3. **Use webhook signatures**
   - Always verify `stripe-signature` header
   - Never trust request without verification

4. **Restrict API key permissions**
   - In Stripe Dashboard → API Keys → Restricted keys
   - Only grant necessary permissions

5. **Enable 2FA**
   - Stripe Dashboard → Account settings → 2-factor authentication

6. **Monitor charges**
   - Set up alerts for unusual activity
   - Review customer disputes promptly

## References

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)
- [Production Readiness](https://stripe.com/docs/keys#monitoring)

## Getting Help

- **Stripe Support:** https://support.stripe.com
- **API Reference:** https://stripe.com/docs/api
- **GitHub Issues:** Report bugs in this project
- **Community:** https://stackoverflow.com/questions/tagged/stripe
