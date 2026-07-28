# API Key Management System

Comprehensive guide to the secure API key management system for aimodels.cloud backend.

## Quick Start (5 minutes)

### Local Development

```bash
cd backend

# Copy development config
cp .env.example .env.development

# Load and verify
export $(cat .env.development | grep -v '^#' | xargs)

# Test configuration
python scripts/validate-config.py --env development

# Start application
poetry run uvicorn src.main:app --reload
```

### Production Setup

```bash
# Initialize AWS Secrets Manager
./scripts/setup-aws-secrets.sh production

# This will:
# 1. Create secret in AWS Secrets Manager
# 2. Prompt you to enter real API keys
# 3. Validate JSON and required keys
# 4. Store securely in AWS

# Deploy
./scripts/deploy.sh production
```

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│          Config Loader (src/config.py)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Load environment variables                        │    │
│  │ 2. Load from .env files                              │    │
│  │ 3. Load from AWS Secrets Manager (if enabled)        │    │
│  │ 4. Validate required keys                            │    │
│  │ 5. Return immutable AppConfig object                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
           ┌──────────────────┬──────────────────┐
           ↓                  ↓
    ┌──────────────┐   ┌──────────────────┐
    │ Environment  │   │ AWS Secrets      │
    │ Variables    │   │ Manager          │
    │ & .env files │   │                  │
    └──────────────┘   └──────────────────┘
```

### Key Features

| Feature | Benefit |
|---------|---------|
| **Multi-environment** | Different keys for dev, staging, prod |
| **AWS Secrets Manager** | Secure, audited, centralized key storage |
| **Key Validation** | Fails fast on startup if keys missing |
| **Secure Logging** | Logs key usage without exposing values |
| **Key Hashing** | Tracks keys by hash, not value |
| **Rotation Support** | Easy key rotation with rollback |
| **Compliance Ready** | Audit trails, versioning, access control |

---

## Components

### 1. Configuration Files

| File | Purpose | Environment | Version Control |
|------|---------|-------------|-----------------|
| `.env.example` | Template with all settings | Reference | Yes |
| `.env.development` | Local development | Development | Yes |
| `.env.staging` | Staging server | Staging | Yes |
| `.env.production` | Production (placeholders) | Production | Yes |
| `.env.local` | Local overrides | Development | No (git-ignored) |

### 2. Configuration Loader (config.py)

Loads and validates configuration from multiple sources:

```python
from src.config import get_config, AppConfig

# Get configuration (singleton)
config: AppConfig = get_config()

# Access configuration
config.environment          # Current environment
config.llm_providers        # LLM API keys
config.database             # Database configuration
config.redis               # Redis configuration
config.stripe              # Stripe configuration
config.aws                 # AWS configuration
```

**Features:**
- Loads from environment variables first
- Falls back to .env files
- Supports AWS Secrets Manager
- Validates required keys
- Type-safe access via dataclasses
- Singleton pattern (one instance per process)

### 3. Key Logging (utils/key_logging.py)

Monitors key usage without exposing sensitive data:

```python
from src.utils.key_logging import get_key_logger, KeyType, KeyEvent

logger = get_key_logger()

# Register a key
logger.register_key(KeyType.OPENAI, api_key)

# Log usage event
logger.log_key_event(KeyType.OPENAI, KeyEvent.USED, status='success')

# Get usage summary
summary = logger.get_usage_summary()

# Detect anomalies
anomalies = logger.detect_anomalies()

# Export audit log
logger.export_audit_log('backup/audit.json')
```

**Logged Information:**
- Key type (OpenAI, Anthropic, etc.)
- Event type (used, failed, rotated)
- Timestamp
- Key hash (not actual key)
- Status (success, failure, etc.)
- Source and user ID (if applicable)

**Never Logged:**
- Actual API key values
- Request/response bodies with keys
- Credentials in any form

### 4. AWS Secrets Manager Integration

Stores secrets securely in AWS with:

```bash
# Setup
./scripts/setup-aws-secrets.sh production

# Structure
{
  "openai_api_key": "sk_live_xxx",
  "anthropic_api_key": "sk_ant_xxx",
  "database_url": "postgresql://...",
  "redis_url": "redis://...",
  ...
}

# Retrieval (automatic via config.py)
aws secretsmanager get-secret-value \
  --secret-id aimodels/production/api-keys \
  --region us-east-1
```

**Features:**
- Encryption at rest (AWS KMS)
- Encryption in transit (TLS)
- Automatic versioning
- Audit logging
- Access control via IAM
- Rotation support

### 5. Scripts

#### validate-config.py
```bash
python scripts/validate-config.py --env production
```
Validates configuration is complete and correct.

#### setup-aws-secrets.sh
```bash
./scripts/setup-aws-secrets.sh staging
```
Initializes AWS Secrets Manager with encrypted secrets.

---

## Required API Keys

### LLM Providers (Production)

| Key | Provider | Endpoint | Cost |
|-----|----------|----------|------|
| OPENAI_API_KEY | OpenAI | https://platform.openai.com/account/api-keys | Per-usage |
| ANTHROPIC_API_KEY | Anthropic | https://console.anthropic.com/account/keys | Per-usage |
| TOGETHER_API_KEY | Together.ai | https://www.together.ai/account/keys | Per-usage |

### Infrastructure (Production)

| Key | Service | Type | Access |
|-----|---------|------|--------|
| DATABASE_URL | PostgreSQL | Connection string | RDS endpoint |
| REDIS_URL | Redis | Connection string | ElastiCache endpoint |
| JWT_SECRET_KEY | Security | Random string | Generated offline |

### Payment Processing (Production)

| Key | Provider | Type | Scope |
|-----|----------|------|-------|
| STRIPE_API_KEY | Stripe | API key | Payments, billing |
| STRIPE_WEBHOOK_KEY | Stripe | Signing secret | Webhook verification |

---

## Security Best Practices

### Development

```bash
# ✓ DO
✓ Use test/development keys from providers
✓ Store in .env.local (git-ignored)
✓ Rotate keys when leaving the company
✓ Never commit real keys

# ✗ DON'T
✗ Use production keys in development
✗ Commit .env files with real keys
✗ Share keys via Slack/email
✗ Store keys in notes or docs
```

### Staging

```bash
# ✓ DO
✓ Use separate staging keys/accounts
✓ Isolate from production database
✓ Store in AWS Secrets Manager
✓ Rotate every 180 days
✓ Use IAM roles for access

# ✗ DON'T
✗ Use production keys
✗ Share staging keys with developers
✗ Log sensitive data
✗ Use HTTP (always HTTPS)
```

### Production

```bash
# ✓ DO
✓ Use only AWS Secrets Manager
✓ Rotate keys every 90 days
✓ Use IAM roles (no access keys)
✓ Enable CloudWatch logging
✓ Monitor for unauthorized access
✓ Audit key usage regularly

# ✗ DON'T
✗ Store keys in .env files
✗ Commit keys to git
✗ Use HTTP (always HTTPS)
✗ Share access to production secrets
✗ Use weak JWT secrets
✗ Enable DEBUG mode
```

---

## Key Rotation

### Scheduled Rotation (90 days - Production)

See [KEY_ROTATION_GUIDE.md](KEY_ROTATION_GUIDE.md) for complete procedures:

1. Export current audit metrics
2. Generate new key at provider
3. Update AWS Secrets Manager
4. Deploy new configuration
5. Verify new key works
6. Deactivate old key
7. Log rotation in audit trail

**Timeline:** 2-4 hours

### Emergency Rotation (Compromised Key)

See [EMERGENCY_ROTATION_PLAYBOOK.md](EMERGENCY_ROTATION_PLAYBOOK.md) for immediate action:

1. Declare incident (Slack)
2. Stop using compromised key
3. Generate new key immediately
4. Deploy new configuration
5. Verify service health
6. Deactivate compromised key
7. Audit usage for damage
8. Post-mortem and prevention

**Timeline:** 45 minutes to 2 hours

---

## Compliance

### Audit Trail

All key events are logged to:
- Application logs: `logs/key_usage.log`
- CloudWatch: `/aimodels/api`
- Audit exports: `backups/key_audit_*.json`
- Rotation log: `docs/KEY_ROTATION_LOG.md`

### Requirements Met

- ✓ SOC2 Type II: Key logging, access control, incident response
- ✓ HIPAA: Encrypted storage, audit trails, rotation procedures
- ✓ GDPR: Data minimization (no key storage in logs), access control
- ✓ PCI-DSS: Encryption, regular rotation, access control

### Reviews

- **Weekly:** Check key health metrics in dashboard
- **Monthly:** Review rotation schedule and logs
- **Quarterly:** SOC2/compliance audit of logs
- **Annually:** Full security review and penetration testing

---

## Troubleshooting

### Configuration Not Loading

```bash
# Check environment file
ls -la .env.*

# Load specific environment
python -c "from src.config import get_config; print(get_config('.env.production').environment)"

# Verify env vars
echo $ENVIRONMENT
echo $OPENAI_API_KEY
```

### Missing Required Keys

```bash
# List all required keys
python scripts/validate-config.py --env production

# Check each key
echo "OPENAI_API_KEY: $OPENAI_API_KEY"
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
```

### AWS Secrets Manager Errors

```bash
# Verify secret exists
aws secretsmanager describe-secret \
  --secret-id aimodels/production/api-keys \
  --region us-east-1

# Check IAM permissions
aws sts get-caller-identity

# View secret value (use with caution)
aws secretsmanager get-secret-value \
  --secret-id aimodels/production/api-keys \
  --region us-east-1 | jq '.SecretString' | jq .
```

### Debug Logs

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -c "from src.config import get_config; get_config()"

# Check key usage logs
tail -f logs/key_usage.log
```

---

## Files & Locations

```
backend/
├── .env.example                 # Master template
├── .env.development             # Dev settings
├── .env.staging                 # Staging settings
├── .env.production              # Production settings (no real keys)
│
├── src/
│   ├── config.py               # Config loader + classes
│   ├── utils/
│   │   └── key_logging.py      # Key usage monitoring
│   └── main.py                 # FastAPI app
│
├── scripts/
│   ├── setup-aws-secrets.sh    # AWS Secrets Manager setup
│   └── validate-config.py      # Configuration validator
│
├── docs/
│   ├── CONFIGURATION.md         # Configuration guide
│   ├── KEY_ROTATION_GUIDE.md    # Scheduled rotation procedures
│   ├── EMERGENCY_ROTATION_PLAYBOOK.md  # Emergency procedures
│   ├── KEY_ROTATION_LOG.md     # Audit trail
│   └── API_KEY_MANAGEMENT.md   # This file
│
├── logs/
│   └── key_usage.log           # Key event logs
│
└── backups/
    └── key_audit_*.json        # Exported audit trails
```

---

## Support & Escalation

### On-Call Support
- Slack: `#incidents`
- On-call: `@oncall-eng`
- Critical: Page operations

### Escalation Path
1. Engineering Lead (15 min)
2. VP Engineering (30 min)
3. CTO + Security (1 hour)
4. CEO/Board (2+ hours if critical)

---

## References

- [Configuration Guide](CONFIGURATION.md)
- [Key Rotation Guide](KEY_ROTATION_GUIDE.md)
- [Emergency Playbook](EMERGENCY_ROTATION_PLAYBOOK.md)
- [Rotation Log](KEY_ROTATION_LOG.md)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/settings/)

---

## Contacts

**Team Leads:**
- Infrastructure: [name]
- Security: [name]
- Engineering: [name]

**AWS Account:** [Account ID]
**Region:** us-east-1
**Support:** team@aimodels.cloud
