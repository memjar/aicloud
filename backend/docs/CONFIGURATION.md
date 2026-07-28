# Configuration Management Guide

Comprehensive guide to managing API keys and environment configuration for aimodels.cloud backend.

## Table of Contents

1. [Overview](#overview)
2. [Configuration Hierarchy](#configuration-hierarchy)
3. [Environment Setup](#environment-setup)
4. [AWS Secrets Manager](#aws-secrets-manager)
5. [Local Development](#local-development)
6. [Configuration Classes](#configuration-classes)
7. [Validation & Error Handling](#validation--error-handling)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The configuration system provides:
- **Multi-environment support** (development, staging, production)
- **AWS Secrets Manager integration** for secure key storage
- **Environment variable loading** from .env files
- **Configuration validation** with clear error messages
- **Key logging and monitoring** without exposing sensitive data
- **Type-safe configuration** using dataclasses

### Key Files

```
backend/
├── .env.example              # Template for all configuration
├── .env.development          # Development settings
├── .env.staging              # Staging settings
├── .env.production           # Production settings (no real keys)
├── src/
│   ├── config.py             # Configuration loader + classes
│   ├── utils/
│   │   └── key_logging.py    # Key usage monitoring
│   └── main.py               # FastAPI app
├── scripts/
│   └── setup-aws-secrets.sh  # Initialize AWS Secrets Manager
└── docs/
    ├── CONFIGURATION.md      # This file
    ├── KEY_ROTATION_GUIDE.md # Key rotation procedures
    └── EMERGENCY_ROTATION_PLAYBOOK.md
```

---

## Configuration Hierarchy

Configuration is loaded in this order (later overrides earlier):

1. **Hardcoded defaults** in `config.py`
2. **.env.example** (reference only, not loaded)
3. **.env file** (if ENVIRONMENT not set)
4. **Environment-specific .env** (.env.development, .env.staging, .env.production)
5. **Environment variables** (process-level)
6. **AWS Secrets Manager** (if enabled)

### Example Resolution

```python
# For OPENAI_API_KEY with AWS Secrets Manager enabled:
1. Check environment variable OPENAI_API_KEY
   → If not found, check AWS Secrets Manager
2. Check .env.production
   → Value is "set_via_aws_secrets_manager" (placeholder)
3. AWS Secrets Manager provides actual key
   → Key is loaded securely without appearing in logs
```

---

## Environment Setup

### Development

```bash
cd backend

# Copy development template
cp .env.example .env.development

# Or use the provided development config
# .env.development already configured for localhost

# Load it
export ENVIRONMENT=development
export $(cat .env.development | grep -v '^#' | xargs)

# Start app
poetry run uvicorn src.main:app --reload --port 8000
```

### Staging

```bash
# Copy staging template
cp .env.example .env.staging

# Edit with staging values
nano .env.staging

# Initialize AWS Secrets Manager
./scripts/setup-aws-secrets.sh staging

# Deploy
./scripts/deploy.sh staging
```

### Production

```bash
# Copy production template (placeholder values only)
cp .env.example .env.production

# DO NOT edit .env.production with real keys!

# Setup AWS Secrets Manager first
./scripts/setup-aws-secrets.sh production

# Deploy
./scripts/deploy.sh production
```

---

## AWS Secrets Manager

### Setup

**One-time setup per environment:**

```bash
# Initialize secrets for staging
./scripts/setup-aws-secrets.sh staging

# Initialize secrets for production (requires confirmation)
./scripts/setup-aws-secrets.sh production
```

The script will:
1. Create a secret in AWS Secrets Manager
2. Prompt you to edit with real values
3. Validate JSON and required keys
4. Store in AWS Secrets Manager
5. Tag the secret for tracking

### Structure

AWS Secrets Manager stores a single JSON secret with all API keys:

```json
{
  "openai_api_key": "sk_live_xxx",
  "anthropic_api_key": "sk_ant_xxx",
  "together_api_key": "xxx",
  "database_url": "postgresql://...",
  "redis_url": "redis://...",
  "stripe_api_key": "sk_live_xxx",
  "stripe_webhook_key": "whsec_xxx",
  "jwt_secret_key": "xxxxxxx"
}
```

### Retrieving Secrets

```bash
# View all secrets (production)
aws secretsmanager get-secret-value \
  --secret-id aimodels/production/api-keys \
  --region us-east-1 \
  --query 'SecretString' \
  --output text | jq .

# View specific key
aws secretsmanager get-secret-value \
  --secret-id aimodels/production/api-keys \
  --region us-east-1 \
  --query 'SecretString' \
  --output text | jq '.openai_api_key'
```

### Permissions

App requires IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:ACCOUNT_ID:secret:aimodels/*"
    }
  ]
}
```

---

## Local Development

### Quick Start

```bash
cd backend

# Create .env.local from template
cp .env.development .env.local

# Edit test API keys (optional, many endpoints don't need real keys)
nano .env.local

# Load environment
source .env.local

# Or via python-dotenv (automatic in config.py)
python -c "from src.config import get_config; cfg = get_config('.env.local'); print(cfg.environment)"
```

### Using Test Keys

For local testing, you can use placeholder values:

```bash
# OpenAI test key (won't actually work, but validates format)
OPENAI_API_KEY=sk_test_placeholder_key

# Anthropic test key
ANTHROPIC_API_KEY=sk_ant_test_placeholder

# These are validated only on startup
# API calls will fail, but app loads
```

### Disabling Secrets Manager

Development defaults to disabled:

```env
AWS_SECRETS_MANAGER_ENABLED=false
ENVIRONMENT=development
```

Change to enable (requires AWS credentials):

```env
AWS_SECRETS_MANAGER_ENABLED=true
AWS_SECRETS_MANAGER_SECRET_NAME=aimodels/development/api-keys
```

---

## Configuration Classes

### AppConfig (main container)

```python
from src.config import AppConfig, get_config

config = get_config()

# Access configuration
print(config.environment)           # 'production'
print(config.debug)                 # False
print(config.database.url)          # 'postgresql://...'
print(config.llm_providers.openai_api_key)  # 'sk_live_xxx'
```

### Sub-configurations

```python
# Database
config.database.url
config.database.pool_size
config.database.echo

# Redis
config.redis.url
config.redis.decode_responses

# Security
config.security.jwt_secret_key
config.security.jwt_algorithm
config.security.rate_limit_requests_per_minute

# LLM Providers
config.llm_providers.openai_api_key
config.llm_providers.anthropic_api_key
config.llm_providers.together_api_key

# AWS
config.aws.secrets_manager_enabled
config.aws.region

# Observability
config.observability.sentry_dsn
config.observability.posthog_api_key
```

### Using in FastAPI

```python
from fastapi import FastAPI, Depends
from src.config import get_config, AppConfig

app = FastAPI()

def get_current_config() -> AppConfig:
    return get_config()

@app.get("/config-status")
def config_status(config: AppConfig = Depends(get_current_config)):
    return {
        "environment": config.environment,
        "has_openai_key": bool(config.llm_providers.openai_api_key),
        "database_configured": bool(config.database.url),
    }
```

---

## Validation & Error Handling

### Required Keys

The configuration validates these required keys:

```python
REQUIRED_KEYS = {
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'TOGETHER_API_KEY',
    'DATABASE_URL',
    'REDIS_URL',
    'STRIPE_API_KEY',
    'STRIPE_WEBHOOK_KEY',
}
```

Missing keys raise `ValueError`:

```python
try:
    config = get_config()
except ValueError as e:
    print(f"Config error: {e}")
    # Output: Config error: Missing required configuration keys: OPENAI_API_KEY, ANTHROPIC_API_KEY
```

### Production Validation

Additional checks in production:

```python
if environment == 'production' and config.debug:
    raise ValueError("DEBUG mode must be disabled in production")

if not config.security.jwt_secret_key:
    raise ValueError("JWT_SECRET_KEY must be set in production")
```

### Configuration Logging

Configuration is logged without exposing keys:

```
DEBUG: Loaded config: ENVIRONMENT
DEBUG: Loaded config: LOG_LEVEL
DEBUG: Loaded config: OPENAI_API_KEY
DEBUG: Loaded config: DATABASE_URL
INFO: Configuration loaded for environment: production
```

Keys are never logged even at DEBUG level.

---

## Security Best Practices

### Do's ✓

- [ ] Use AWS Secrets Manager for production
- [ ] Rotate keys every 90 days (production)
- [ ] Use different keys for different environments
- [ ] Enable DEBUG only in development
- [ ] Use IAM roles instead of access keys
- [ ] Audit key usage regularly
- [ ] Version control .env templates only
- [ ] Use strong JWT secrets (min 32 chars)

### Don'ts ✗

- [ ] Never commit real keys to version control
- [ ] Never use same keys across environments
- [ ] Never enable DEBUG in production
- [ ] Never log actual API keys
- [ ] Never share .env files via email
- [ ] Never use default/weak JWT secrets
- [ ] Never skip validation in production
- [ ] Never use HTTP in production (HTTPS required)

### Key Storage Guidelines

| Environment | Storage | Rotation | Access |
|-------------|---------|----------|--------|
| Development | .env.local (git-ignored) | Manual | Developer |
| Staging | AWS Secrets Manager | Every 180 days | Developers + CI/CD |
| Production | AWS Secrets Manager | Every 90 days | App via IAM role |

---

## Troubleshooting

### Config Not Loading

```python
# Check if .env file exists
import os
print(os.path.exists('.env.development'))

# Verify environment variable
print(os.getenv('ENVIRONMENT'))

# Load with explicit path
from src.config import get_config
config = get_config('.env.development')
```

### Missing Required Keys Error

```
ValueError: Missing required configuration keys: OPENAI_API_KEY
```

**Solution:**
1. Check .env file exists
2. Verify key name spelling
3. Confirm value is not empty
4. Check AWS Secrets Manager if enabled

### AWS Secrets Manager Not Found

```
ERROR: Failed to retrieve secret aimodels/production/api-keys
```

**Solution:**
```bash
# Verify secret exists
aws secretsmanager describe-secret \
  --secret-id aimodels/production/api-keys \
  --region us-east-1

# Check IAM permissions
aws sts get-caller-identity

# Verify region matches
echo $AWS_REGION
```

### Wrong Environment Loaded

```python
from src.config import get_config
config = get_config()
print(config.environment)  # Should show current environment

# Explicitly load staging
config = get_config('.env.staging')
```

### Debug Configuration

Enable verbose logging:

```bash
# Environment variable
export LOG_LEVEL=DEBUG

# In .env file
LOG_LEVEL=DEBUG
VERBOSE=true

# In Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Key Validation During Startup

```bash
# Test configuration loading
cd backend
python -c "
from src.config import get_config
config = get_config()
print('✓ Configuration valid')
print(f'Environment: {config.environment}')
print(f'Database: {config.database.url[:20]}...')
print(f'Redis: {config.redis.url[:20]}...')
"
```

---

## Advanced Usage

### Custom Configuration Loading

```python
from src.config import ConfigLoader

# Load from custom .env file
loader = ConfigLoader('.env.custom')
config = loader.load()

# Or load without .env file (environment variables only)
loader = ConfigLoader()
config = loader.load()
```

### Manual Secret Retrieval

```python
from src.config import SecretsManager, AWSConfig

aws_config = AWSConfig(
    secrets_manager_enabled=True,
    secrets_manager_secret_name='aimodels/production/api-keys'
)
secrets_manager = SecretsManager(aws_config)
secrets = secrets_manager.get_secret('aimodels/production/api-keys')

print(secrets['openai_api_key'])
```

### Key Usage Monitoring

```python
from src.utils.key_logging import get_key_logger, KeyType, KeyEvent

logger = get_key_logger('production')

# Register a key
logger.register_key(KeyType.OPENAI, 'sk_live_xxx', metadata={'provider': 'openai'})

# Log usage
logger.log_key_event(KeyType.OPENAI, KeyEvent.USED, status='success')

# Get summary
summary = logger.get_usage_summary()
print(summary)

# Export audit log
logger.export_audit_log('backup/audit.json')
```

### Configuration Hot Reload

```python
# Clear cache to reload configuration
from src.config import get_config, ConfigLoader
import importlib

# Force reload
importlib.reload(src.config)
config = get_config()  # Loads fresh
```

---

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Python python-dotenv](https://github.com/theskumar/python-dotenv)
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/settings/)
- [Key Rotation Guide](KEY_ROTATION_GUIDE.md)
- [Emergency Playbook](EMERGENCY_ROTATION_PLAYBOOK.md)
