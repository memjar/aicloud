# Emergency Key Rotation Playbook

Procedures for responding to compromised or leaked API keys.

## Table of Contents

1. [Incident Classification](#incident-classification)
2. [Immediate Response (0-15 minutes)](#immediate-response-0-15-minutes)
3. [Containment (15-60 minutes)](#containment-15-60-minutes)
4. [Recovery (1-4 hours)](#recovery-1-4-hours)
5. [Post-Incident (24-48 hours)](#post-incident-24-48-hours)
6. [Contact List](#contact-list)

---

## Incident Classification

### Severity Levels

**CRITICAL (P0):** Stripe keys or database credentials compromised
- Immediate action required
- Notify leadership, legal, security
- Potential financial/data breach

**HIGH (P1):** LLM provider keys (OpenAI, Anthropic, Together)
- Act within 15 minutes
- Can cause service disruption or cost impact
- Notify engineering leads

**MEDIUM (P2):** Redis key or internal secrets
- Act within 1 hour
- Limited external impact
- Notify team leads

---

## Immediate Response (0-15 minutes)

### 1. Declare Incident

**1a. Activate incident channel**

```bash
# Slack
/create emergency-key-incident-2025-01-15

# Notify on-call
@oncall-eng CRITICAL: API key compromised
- Key type: [OPENAI_API_KEY / ANTHROPIC_API_KEY / etc]
- Suspected compromise time: [timestamp]
- Impact: [service affected]
```

**1b. Gather initial information**

- Where was the key leaked? (GitHub, logs, config, email)
- Approximate time of leak
- Who has access to the key
- What services depend on this key
- Current usage patterns

### 2. Stop Using Compromised Key

**Immediate deployment of null key to prevent further use:**

```bash
# DO NOT try to edit files - directly update config
# This prevents new requests using compromised key

aws secretsmanager update-secret \
  --secret-id aimodels/api/keys \
  --secret-string '{
    "openai_api_key": "",
    ...other_keys...
  }' \
  --region us-east-1

# Restart API servers to clear caches
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --force-new-deployment
```

### 3. Notify Affected Services

**For LLM provider keys:**

OpenAI:
```bash
# Go to https://platform.openai.com/account/api-keys
# Immediately delete the compromised key
# Take screenshot as evidence
```

Anthropic:
```bash
# Go to https://console.anthropic.com/account/keys
# Revoke the compromised key
# Take screenshot as evidence
```

Stripe:
```bash
# Go to https://dashboard.stripe.com/account/apikeys
# Revoke compromised key
# Update all webhook endpoints with new signing secrets
```

### 4. Alert Customers (if applicable)

**Draft notification (security team approval required):**

```
Subject: Scheduled Maintenance - Brief Service Interruption

We are performing emergency maintenance to ensure platform security.
Service may be unavailable for 15-30 minutes starting at [timestamp].

We will notify you when service is restored.

[Do NOT mention compromised key unless legally required]
```

---

## Containment (15-60 minutes)

### 5. Generate New Keys

**Parallel generation of replacement keys:**

```bash
# OpenAI
# 1. Go to https://platform.openai.com/account/api-keys
# 2. Click "Create new secret key"
# 3. Name: emergency-openai-$(date +%Y%m%d-%H%M%S)
# 4. Copy key (visible only once)

# Anthropic
# 1. Go to https://console.anthropic.com/account/keys
# 2. Click "Create key"
# 3. Name: emergency-anthropic-$(date +%Y%m%d-%H%M%S)
# 4. Copy key

# Stripe
# 1. Go to https://dashboard.stripe.com/account/apikeys
# 2. Click "Create restricted key" or create new key
# 3. Set same restrictions as old key
# 4. Copy key
```

### 6. Stage New Configuration

**Update AWS Secrets Manager with new keys:**

```bash
# Create JSON with new keys
cat > /tmp/new_secrets.json << 'EOF'
{
  "openai_api_key": "sk_live_NEW_KEY_FROM_OPENAI",
  "anthropic_api_key": "sk_ant_NEW_KEY_FROM_ANTHROPIC",
  "together_api_key": "xxx_unchanged",
  "stripe_api_key": "sk_live_NEW_KEY_FROM_STRIPE",
  "stripe_webhook_key": "whsec_NEW_KEY_FROM_STRIPE",
  "database_url": "postgresql://...",
  "redis_url": "redis://..."
}
EOF

# Update secret
aws secretsmanager update-secret \
  --secret-id aimodels/api/keys \
  --secret-string file:///tmp/new_secrets.json \
  --region us-east-1

# Verify update
aws secretsmanager get-secret-value \
  --secret-id aimodels/api/keys \
  --region us-east-1 | jq '.SecretString' | jq 'keys'
```

### 7. Verify New Keys

**Test each key before full deployment:**

```bash
# OpenAI test
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk_live_NEW_KEY" 2>&1 | grep -q "data"
echo "OpenAI: $?"

# Anthropic test
curl https://api.anthropic.com/v1/models \
  -H "x-api-key: sk_ant_NEW_KEY" 2>&1 | grep -q "model_id"
echo "Anthropic: $?"

# Together test
curl https://api.together.ai/models/list \
  -H "Authorization: Bearer xxx_NEW_KEY" 2>&1 | grep -q "results"
echo "Together: $?"
```

### 8. Deploy New Configuration

```bash
# Update ECS service with force new deployment
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --force-new-deployment \
  --region us-east-1

# Monitor rollout
watch "aws ecs describe-services \
  --cluster aimodels-prod \
  --services aimodels-api | jq '.services[0].deployments'"

# Wait for: running_count == desired_count
```

### 9. Verify Service Recovery

```bash
# Health check
curl https://api.aimodels.cloud/health
# Expected: {"status": "healthy", "service": "aicloud-api"}

# Test key APIs
curl -X POST https://api.aimodels.cloud/v1/chat/completions \
  -H "Authorization: Bearer $TEST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}'

# Check error rates
aws cloudwatch get-metric-statistics \
  --namespace aimodels \
  --metric-name APIErrors \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum
```

---

## Recovery (1-4 hours)

### 10. Deactivate Compromised Key

Wait for all instances to be running new config, then:

**OpenAI:**
```
1. Go to https://platform.openai.com/account/api-keys
2. Find and delete the compromised key
3. Take screenshot
4. Document the deletion
```

**Anthropic:**
```
1. Go to https://console.anthropic.com/account/keys
2. Revoke the compromised key
3. Take screenshot
4. Document the revocation
```

**Stripe:**
```
1. Go to https://dashboard.stripe.com/account/apikeys
2. Delete compromised API key
3. For webhooks: go to https://dashboard.stripe.com/webhooks
4. Update all endpoints with new signing secret
```

### 11. Audit Key Usage

**Check if compromised key was used maliciously:**

```bash
# Get usage audit from before compromise
python -c "
from src.utils.key_logging import get_key_logger
logger = get_key_logger('production')
events = logger.get_recent_events(hours=48)
for event in events:
    print(event)
"

# Check CloudWatch for suspicious activity
aws logs filter-log-events \
  --log-group-name /aimodels/api \
  --filter-pattern '"auth_failure" OR "invalid_key"' \
  --start-time $(date -d '1 hour ago' +%s)000

# Check for unusual billing activity (Stripe/OpenAI)
# Manual check: https://platform.openai.com/account/billing/overview
# Manual check: https://dashboard.stripe.com/dashboard
```

### 12. Review Access Logs

**Check who had access to the compromised key:**

```bash
# Search git history for key (if accidentally committed)
git log --all -p | grep -i "sk_live_\|sk_ant_\|COMPROMISED_KEY" | head -20

# Search config backups
grep -r "COMPROMISED_KEY" /var/backups/config* || echo "Not in backups"

# Check environment audit
grep -i "compromised\|api_key" /var/log/auth.log | tail -50
```

### 13. Root Cause Analysis

**Determine how the key was compromised:**

Possible sources:
- GitHub commit (search history)
- Exposed .env file
- Slack message or email
- Buggy logging
- Dependency vulnerability
- Insider access
- Infrastructure misconfiguration

Document findings in incident report.

### 14. Notify Providers (if using shared accounts)

**If compromised key was for a shared account:**

```bash
# Stripe
# Email: security@stripe.com
# Subject: Security incident - rotated API key
# Details: [brief description, dates]

# OpenAI
# Email: security@openai.com
# Subject: API key rotation - security incident
# Details: [brief description, dates]
```

---

## Post-Incident (24-48 hours)

### 15. Post-Incident Review

**Schedule meeting within 24 hours:**

```markdown
## Incident Post-Mortem

**Date/Time:** [incident timestamp]
**Severity:** [P0/P1/P2]
**Duration:** [start to recovery time]

### Timeline
- T+0: Key compromised at [time]
- T+X: Incident detected by [method]
- T+Y: Containment action taken
- T+Z: Service recovered

### Root Cause
[How was the key leaked/exposed]

### Impact
- Services affected: [list]
- Customers impacted: [estimate/actual]
- Data exposed: [if any]
- Cost impact: [if any]

### What Went Well
- [Fast detection]
- [Quick response]
- [Clear procedures]

### What Could Improve
- [Earlier detection possible?]
- [Faster response possible?]
- [Process improvements]

### Action Items
- [ ] Implement [preventive measure]
- [ ] Update documentation
- [ ] Schedule training
- [ ] Update monitoring/alerting
```

### 16. Implement Preventive Measures

**Prevent future incidents:**

```bash
# Add pre-commit hook to catch potential key leaks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
git diff --cached | grep -E 'sk_live_|sk_ant_|whsec_' && {
  echo "ERROR: Potential API key in commit"
  exit 1
}
EOF
chmod +x .git/hooks/pre-commit

# Add git-secrets scanning
git secrets --install --force
git secrets --register-aws
git secrets --add 'sk_live_'
git secrets --add 'sk_ant_'

# Update .env.example to remove any sample real keys
# Update deployment to use Secrets Manager only (no .env in prod)
```

### 17. Update Monitoring/Alerting

**Add alerts for key compromise indicators:**

```yaml
# CloudWatch alarm example
KeyCompromiseIndicators:
  - High auth failure rate (>5 failures/min)
  - Unusual API usage patterns
  - Access from unexpected IP ranges
  - Multiple concurrent requests from same key
  - Requests outside normal business hours
  - Cost spikes on LLM provider accounts
```

### 18. Documentation Update

**Update procedures based on lessons learned:**

```bash
# Review this playbook
vi backend/docs/EMERGENCY_ROTATION_PLAYBOOK.md

# Update rotation guide
vi backend/docs/KEY_ROTATION_GUIDE.md

# Create incident report template
cat > docs/INCIDENT_REPORT_TEMPLATE.md << 'EOF'
# Incident Report: [Date] - [Key Type]

[Sections filled from post-mortem above]
EOF
```

### 19. Team Training

**Ensure team knows procedures:**

- [ ] Review playbook with engineering team
- [ ] Run mock incident drill
- [ ] Update runbooks
- [ ] Brief customer success on what happened (sanitized)
- [ ] Update SLAs if needed

### 20. Close Incident

```bash
# Archive incident artifacts
mkdir -p archives/incidents/2025-01-15-key-compromise
cp logs/key_usage.log archives/incidents/2025-01-15-key-compromise/
cp backups/key_audit_*.json archives/incidents/2025-01-15-key-compromise/

# Update rotation log
cat >> docs/KEY_ROTATION_LOG.md << 'EOF'

## 2025-01-15 — EMERGENCY ROTATION: OpenAI Key Compromise

**Key Type:** OPENAI_API_KEY
**Incident Type:** Key leaked to GitHub
**Detection Time:** 2025-01-15 13:45 UTC
**Response Time:** 12 minutes
**Old Key Deactivated:** 2025-01-15 14:30 UTC
**New Key Deployed:** 2025-01-15 14:25 UTC
**Service Recovery:** 2025-01-15 14:35 UTC
**Completed By:** incident-commander
**Notes:** Post-mortem scheduled for 2025-01-16 10:00 UTC
EOF

# Update status
echo "INCIDENT CLOSED" > incident-status.txt
```

---

## Contact List

### On-Call Rotation

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Engineering Lead | [Name] | [Phone] | [Email] |
| Security Officer | [Name] | [Phone] | [Email] |
| Incident Commander | [Name] | [Phone] | [Email] |
| VP Engineering | [Name] | [Phone] | [Email] |

### External Contacts

**Stripe Support:** support@stripe.com / https://dashboard.stripe.com
**OpenAI Security:** security@openai.com
**Anthropic Support:** support@anthropic.com
**AWS Support:** https://console.aws.amazon.com/support/

### Escalation

1. **15 minutes:** Notify engineering lead
2. **30 minutes:** Notify VP Engineering + Security Officer
3. **1 hour:** Consider customer notification
4. **2 hours:** Notify CEO/Board (if severe)

---

## Quick Reference Checklist

Print and post near desk:

```
EMERGENCY KEY ROTATION CHECKLIST

☐ Declare incident in Slack
☐ Stop using compromised key (set to "" in secrets)
☐ Restart API servers (force-new-deployment)
☐ Generate new key at provider
☐ Test new key (curl commands)
☐ Deploy new configuration
☐ Verify service health
☐ Deactivate old key at provider
☐ Audit usage before compromise
☐ Schedule post-mortem
☐ Update documentation
☐ Close incident ticket
```

---

## Testing This Playbook

Run a mock incident drill quarterly:

```bash
# Mock incident scenario
# Assume OPENAI_API_KEY was compromised 1 hour ago
# Do NOT actually compromise anything

# Time the response
time ./scripts/run-mock-incident-drill.sh openai

# Expected completion time: <45 minutes from detection to recovery
```
