# API Key Rotation Guide

Complete procedure for rotating API keys in aimodels.cloud backend.

## Table of Contents

1. [Overview](#overview)
2. [Key Types](#key-types)
3. [Rotation Schedule](#rotation-schedule)
4. [Pre-Rotation Checklist](#pre-rotation-checklist)
5. [Step-by-Step Rotation](#step-by-step-rotation)
6. [Verification](#verification)
7. [Rollback](#rollback)
8. [Monitoring](#monitoring)

---

## Overview

API key rotation is a critical security practice to:
- Limit the window of exposure if a key is compromised
- Meet compliance requirements (SOC2, HIPAA, GDPR)
- Reduce insider threat risk
- Prepare for key leaks or compromises

**Rotation Frequency:**
- Production keys: Every 90 days
- Staging keys: Every 180 days
- Development keys: No fixed schedule (but recommend 30 days)

---

## Key Types

### External LLM Provider Keys

**OpenAI API Key (OPENAI_API_KEY)**
- Provider: OpenAI
- Rotation portal: https://platform.openai.com/account/api-keys
- Impact: Chat completions, embeddings
- Backward compatibility: Full (key format unchanged)

**Anthropic API Key (ANTHROPIC_API_KEY)**
- Provider: Anthropic
- Rotation portal: https://console.anthropic.com/account/keys
- Impact: Claude model access
- Backward compatibility: Full

**Together.ai API Key (TOGETHER_API_KEY)**
- Provider: Together.ai
- Rotation portal: https://www.together.ai/account/keys
- Impact: Open-source model serving
- Backward compatibility: Full

### Infrastructure Keys

**Database Connection (DATABASE_URL)**
- Type: PostgreSQL credentials
- Scope: Production database access
- Rotation: Through database admin
- Impact: All database operations

**Redis Connection (REDIS_URL)**
- Type: Redis auth token
- Scope: Cache and session management
- Rotation: Through Redis admin
- Impact: Cache invalidation on rotation

### Payment Processing Keys

**Stripe API Key (STRIPE_API_KEY)**
- Type: Restricted API key
- Scope: Payment processing
- Rotation portal: https://dashboard.stripe.com/account/apikeys
- Impact: Billing, payments, webhooks

**Stripe Webhook Key (STRIPE_WEBHOOK_KEY)**
- Type: Endpoint signing secret
- Scope: Webhook verification
- Rotation portal: https://dashboard.stripe.com/webhooks
- Impact: Event handling integrity

---

## Rotation Schedule

### Production Keys

| Key | Rotation Interval | Last Rotated | Next Due |
|-----|-------------------|-------------|----------|
| OPENAI_API_KEY | 90 days | TBD | TBD |
| ANTHROPIC_API_KEY | 90 days | TBD | TBD |
| TOGETHER_API_KEY | 90 days | TBD | TBD |
| STRIPE_API_KEY | 90 days | TBD | TBD |
| STRIPE_WEBHOOK_KEY | 90 days | TBD | TBD |
| DATABASE_URL | 180 days | TBD | TBD |
| REDIS_URL | 180 days | TBD | TBD |

**Tracking:** Update `docs/KEY_ROTATION_LOG.md` after each rotation.

---

## Pre-Rotation Checklist

Before rotating any key, verify:

- [ ] Team is aware of upcoming rotation
- [ ] Maintenance window is scheduled (if needed)
- [ ] Rollback plan is documented
- [ ] All dependent services are identified
- [ ] Current key audit is complete
- [ ] Key usage metrics are exported
- [ ] Backup/snapshot of current config exists
- [ ] Team leads have signed off

---

## Step-by-Step Rotation

### 1. Export Current Metrics

```bash
cd backend
python -c "
from src.utils.key_logging import get_key_logger
logger = get_key_logger('production')
logger.export_audit_log('backups/key_audit_before_rotation.json')
print('Audit exported')
"
```

### 2. Generate New Key

Varies by provider:

**OpenAI:**
1. Go to https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Name it with date: `prod-openai-2025-01-15`
4. Copy the new key (visible only once)
5. Verify it works with a test API call
6. Keep old key active temporarily

**Anthropic:**
1. Go to https://console.anthropic.com/account/keys
2. Click "Create key"
3. Name it with date: `prod-anthropic-2025-01-15`
4. Copy the new key
5. Verify it works
6. Keep old key active temporarily

**Similar process for other providers**

### 3. Update AWS Secrets Manager

```bash
# For dev/staging (if using local .env)
cp backend/.env backend/.env.backup
# Manually edit backend/.env with new key
# Test locally

# For production (AWS Secrets Manager)
aws secretsmanager update-secret \
  --secret-id aimodels/api/keys \
  --secret-string '{
    "openai_api_key": "sk_live_NEW_KEY_HERE",
    ...
  }' \
  --region us-east-1

# Verify update
aws secretsmanager get-secret-value \
  --secret-id aimodels/api/keys \
  --region us-east-1
```

### 4. Deploy New Configuration

```bash
# Stage changes
git add backend/src/config.py  # if config code changed
git commit -m "chore: update key rotation references"

# Deploy to production
./scripts/deploy.sh production

# Clear config cache to reload secrets
# Either restart app or if cache clear is implemented:
curl -X POST http://api.aimodels.cloud/admin/clear-config-cache
```

### 5. Verify New Key Works

```bash
# Test inference with new key
curl -X POST http://api.aimodels.cloud/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "test"}]
  }'

# Monitor logs for errors
aws logs tail /aimodels/api --follow

# Check metrics for anomalies
python -c "
from src.utils.key_logging import get_key_logger
logger = get_key_logger('production')
anomalies = logger.detect_anomalies()
print('Anomalies:', anomalies)
"
```

### 6. Deactivate Old Key

Wait 24-48 hours for any cached references to be cleared, then:

**OpenAI:**
1. Go to https://platform.openai.com/account/api-keys
2. Click "Delete" on old key
3. Confirm deletion

**Anthropic:**
1. Go to https://console.anthropic.com/account/keys
2. Click "Revoke" on old key
3. Confirm

**Stripe:**
1. Go to https://dashboard.stripe.com/account/apikeys
2. Delete old key
3. For webhooks: update endpoint signing secret

**Similar for other providers**

### 7. Log Rotation

Update `docs/KEY_ROTATION_LOG.md`:

```markdown
## 2025-01-15 — OpenAI Key Rotation

**Key Type:** OPENAI_API_KEY
**Old Key Hash:** abc123...
**New Key Hash:** xyz789...
**Deployed:** 2025-01-15 14:30 UTC
**Verified:** 2025-01-15 14:45 UTC
**Old Key Deactivated:** 2025-01-16 15:00 UTC
**Completed By:** team-member
**Notes:** Routine 90-day rotation, no issues
```

---

## Verification

### Functional Tests

```bash
# Test each API that uses the rotated key

# OpenAI
curl -X POST http://api.aimodels.cloud/v1/chat/completions \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"model": "gpt-4", "messages": [...]}'

# Anthropic
curl -X POST http://api.aimodels.cloud/v1/chat/completions \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"model": "claude-3", "messages": [...]}'

# Together.ai
curl -X POST http://api.aimodels.cloud/v1/chat/completions \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"model": "mistral-7b", "messages": [...]}'
```

### Metrics Check

```python
from src.utils.key_logging import get_key_logger

logger = get_key_logger()
summary = logger.get_usage_summary()

for key_type, stats in summary['keys'].items():
    print(f"{key_type}: {stats['health']}")
    print(f"  Last used: {stats['last_used']}")
    print(f"  Use count: {stats['use_count']}")
    print(f"  Errors: {stats['error_count']}")
```

### Health Dashboard

1. Navigate to monitoring dashboard: `https://monitoring.aimodels.cloud`
2. Check "Key Health" panel
3. Verify all keys show green status
4. Check error rates haven't increased
5. Verify latency is normal

---

## Rollback

If rotation fails or causes issues:

### Quick Rollback (within 5 minutes)

```bash
# Restore from backup
cp backend/.env.backup backend/.env

# Restart app
systemctl restart aimodels-api

# Verify old key works
curl http://api.aimodels.cloud/health
```

### AWS Secrets Manager Rollback

```bash
# List versions
aws secretsmanager list-secret-version-ids \
  --secret-id aimodels/api/keys

# Restore previous version
aws secretsmanager update-secret \
  --secret-id aimodels/api/keys \
  --secret-string '{...old_keys...}'

# Redeploy
./scripts/deploy.sh production
```

### Restore Old Key (if deactivated)

1. Contact the service provider
2. Request restoration of old key
3. Update configuration
4. Redeploy
5. Re-verify

---

## Monitoring

### Post-Rotation Monitoring (48 hours)

- [ ] Monitor error rates (should remain <0.1%)
- [ ] Check API latency (should be normal)
- [ ] Review auth failure logs (should be zero)
- [ ] Verify customer reports (check support channel)
- [ ] Check resource usage (no spikes)
- [ ] Review cost metrics (no unexpected changes)

### Automated Alerts

Set up CloudWatch alerts for:

```yaml
KeyRotationIssues:
  - Auth failures spike > 5/min
  - API errors spike > 0.5%
  - Key usage anomalies detected
  - Health check failures
```

### Audit Trail

Key usage is automatically logged to:
- `logs/key_usage.log` (local)
- CloudWatch Logs: `/aimodels/api` (production)
- Audit exports: `backups/key_audit_*.json`

Access the audit log:

```bash
aws logs filter-log-events \
  --log-group-name /aimodels/api \
  --filter-pattern "key_event" \
  --start-time $(date -d '24 hours ago' +%s)000
```

---

## Emergency Rotation

See `EMERGENCY_ROTATION_PLAYBOOK.md` for procedures if a key is compromised.

---

## References

- [AWS Secrets Manager Rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets.html)
- [OWASP API Key Security](https://owasp.org/www-community/attacks/API_key_exposure)
- [OpenAI API Key Management](https://platform.openai.com/docs/guides/api-overview)
- [Anthropic API Documentation](https://docs.anthropic.com/)
