# Deployment Files Summary — aimodels.cloud

Complete reference of all deployment files created for production deployment of the FastAPI backend to `api.aimodels.cloud`.

## Overview

This deployment package includes everything needed to deploy the FastAPI backend to AWS ECS with production-grade reliability, monitoring, and auto-scaling.

**Deployment Target:** `api.aimodels.cloud` on AWS ECS (Fargate)
**Region:** US East 1 (us-east-1)
**Environment:** Production

## Files Created

### 1. Container Configuration

#### `backend/Dockerfile`
- **Purpose:** Multi-stage Docker build for the FastAPI application
- **Key Features:**
  - Optimized layer caching with separate build and runtime stages
  - Non-root user execution (security best practice)
  - Health checks built into container
  - Gunicorn + Uvicorn for production-grade serving
  - Minimal final image size
- **Used By:** Docker build process, ECR push
- **Commands:**
  ```bash
  docker build -t aimodels-api backend/
  docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
  ```

### 2. Local Development & Testing

#### `docker-compose.yml`
- **Purpose:** Complete local development environment matching production
- **Includes:**
  - FastAPI application container
  - PostgreSQL 15 database
  - Redis 7 cache
  - PgAdmin for database management (optional)
- **Features:**
  - Health checks for all services
  - Volume mounting for live code reload
  - Named volumes for data persistence
  - Environment variable configuration
- **Usage:**
  ```bash
  docker-compose up -d
  docker-compose logs -f api
  docker-compose down
  ```

### 3. Environment Configuration

#### `.env.production.example`
- **Purpose:** Template for production environment variables
- **Required Setup:** Copy to `.env.production` and fill in actual values
- **Contains:**
  - Database configuration (RDS)
  - Cache configuration (ElastiCache)
  - API provider keys (OpenAI, Anthropic, Together.ai)
  - Stripe billing keys
  - JWT secrets
  - Rate limiting settings
  - CloudWatch/monitoring configuration
- **Security:** Never commit actual `.env.production` file
- **AWS Secrets Manager:** All sensitive values stored in AWS instead of env file

### 4. AWS Infrastructure Configuration

#### `infrastructure/ecs-task-definition.json`
- **Purpose:** ECS task definition for running the FastAPI application
- **Specifies:**
  - Docker image URI and tag
  - CPU and memory allocation (1024 CPU, 2048 MB memory)
  - Port mappings (container 8000 → 8000)
  - CloudWatch log configuration
  - Health check configuration
  - Secret injection from AWS Secrets Manager
  - IAM role associations
- **Usage:**
  ```bash
  aws ecs register-task-definition --cli-input-json file://infrastructure/ecs-task-definition.json
  ```

#### `infrastructure/autoscaling-policy.json`
- **Purpose:** Auto-scaling configuration for ECS service
- **Policies Included:**
  - CPU-based scaling (target: 70%)
  - Memory-based scaling (target: 80%)
  - Request count scaling (target: 1000 req/min)
- **CloudWatch Alarms:**
  - High CPU (> 80%)
  - High memory (> 85%)
  - High error rate (> 5%)
  - High response time (> 5 seconds)
  - Low healthy host count
- **Min/Max Tasks:** 2-10 (HA + cost control)
- **Usage:**
  ```bash
  aws application-autoscaling put-scaling-policy \
    --policy-name aimodels-api-cpu-scaling \
    --cli-input-json file://infrastructure/autoscaling-policy.json
  ```

#### `infrastructure/cloudwatch-config.json`
- **Purpose:** CloudWatch monitoring and alerting configuration
- **Includes:**
  - Log groups and retention policies
  - Metric filters for errors, slow requests, auth failures
  - CloudWatch dashboard definition
  - CloudWatch Insights rules
  - SNS topic configuration for alerts
  - Alarm thresholds
- **Key Metrics Tracked:**
  - Request count (5-min intervals)
  - Error rate (5xx errors)
  - Response time (average, p99)
  - CPU utilization
  - Memory utilization
  - Active task count
  - Healthy host count
- **Usage:**
  ```bash
  aws cloudwatch put-dashboard --dashboard-name aimodels-api-dashboard \
    --dashboard-body file://infrastructure/cloudwatch-config.json
  ```

### 5. Deployment Automation

#### `deploy.sh`
- **Purpose:** Automated deployment script with safety checks and rollback
- **Features:**
  - Environment validation (dev/staging/production)
  - Pre-deployment health checks (DB, Redis, API keys)
  - Docker image build and push to ECR
  - ECS task definition registration
  - Service update with rolling deployment
  - Deployment progress monitoring
  - Health check verification
  - Automatic rollback on failure
  - Deployment notifications
- **Usage:**
  ```bash
  chmod +x deploy.sh
  ./deploy.sh production  # Requires confirmation for production
  ./deploy.sh staging
  ./deploy.sh development
  ```
- **Execution Steps:**
  1. Validates environment and AWS credentials
  2. Loads environment-specific variables
  3. Creates/verifies ECR repository
  4. Builds Docker image
  5. Pushes to ECR with git commit SHA tag
  6. Runs health checks
  7. Updates ECS task definition with new image
  8. Updates service with force-new-deployment
  9. Waits up to 10 minutes for deployment
  10. Verifies health through ALB
  11. Rolls back if any step fails

#### `pyproject.toml` (Updated)
- **Purpose:** Python project configuration and dependencies
- **Added Production Dependencies:**
  - Gunicorn for production ASGI server
  - Additional AI provider SDKs (OpenAI, Anthropic, Together)
  - PyJWT and python-jose for authentication
  - Sentry SDK for error tracking
  - Prometheus client for metrics
  - OpenTelemetry for distributed tracing
  - Structlog for structured logging
  - Redis and aioredis for caching
- **Dev Dependencies:**
  - pytest with asyncio and coverage
  - mypy for type checking
  - Code formatters (black, ruff, isort)
- **Tool Configuration:**
  - Black formatter settings
  - Ruff linter configuration
  - MyPy type checking settings
  - Pytest configuration with coverage

### 6. Database Setup

#### `database/init.sql`
- **Purpose:** Database schema initialization and seed data
- **Creates Tables:**
  - `accounts` - User/organization accounts
  - `api_keys` - API key management
  - `oauth_tokens` - OAuth integration
  - `models` - Available AI models
  - `model_endpoints` - Model deployment endpoints
  - `inference_requests` - Request logging for billing
  - `billing_cycles` - Monthly billing records
  - `webhooks` - Webhook subscriptions
  - `metrics` - Analytics data
  - `audit_logs` - Action audit trail
- **Features:**
  - UUID primary keys
  - Proper foreign key constraints
  - Indexes on common query patterns
  - GIN indexes for JSONB columns
  - Automatic timestamp triggers
  - Seed data with supported models
  - Extension enablement (uuid, pg_trgm)
- **Usage:**
  ```bash
  psql -h <RDS_ENDPOINT> -U aimodels -d aimodels_prod < database/init.sql
  ```

### 7. Deployment Documentation

#### `PRODUCTION_DEPLOYMENT.md`
- **Purpose:** Comprehensive production deployment guide
- **Contents:**
  - Prerequisites (tools, AWS permissions)
  - Local testing instructions (Docker Compose)
  - AWS infrastructure setup (RDS, ElastiCache, VPC, ALB, ECS)
  - Environment configuration (Secrets Manager, IAM roles)
  - Automated and manual deployment procedures
  - Monitoring and logging setup
  - Auto-scaling configuration
  - Health check configuration
  - Rollback procedures (automatic and manual)
  - Troubleshooting guide
  - DNS configuration
- **Target Audience:** DevOps engineers, platform engineers
- **When to Use:** First-time production deployment setup

#### `DEPLOYMENT_CHECKLIST.md`
- **Purpose:** Pre-deployment and post-deployment verification checklist
- **Sections:**
  - AWS account setup (12 items)
  - Database & cache (6 items)
  - API keys & secrets (8 items)
  - Domain & DNS (4 items)
  - Environment configuration (8 items)
  - Code quality (6 items)
  - Docker & container setup (5 items)
  - ECS configuration (13 items)
  - Auto-scaling (4 items)
  - Monitoring & alerting (9 items)
  - Security (9 items)
  - Deployment script (5 items)
  - Local testing (7 items)
  - Staging deployment (4 items)
  - Final pre-production checks (8 items)
  - During deployment (8 items)
  - Post-deployment verification (9 items)
  - First 24 hours monitoring
  - First week monitoring
  - Documentation tasks
  - Rollback criteria
  - Sign-off section
- **Usage:** Check off each item before deploying to production

#### `DEPLOYMENT_FILES_SUMMARY.md` (This File)
- **Purpose:** Complete reference of all deployment files
- **Contents:** Descriptions, purposes, and usage for every file

## Quick Start Guide

### 1. Local Testing (5-10 minutes)

```bash
# Start local environment
docker-compose up -d

# Verify services
curl http://localhost:8000/health
docker-compose logs -f api

# Stop when done
docker-compose down
```

### 2. First-Time Production Setup (1-2 hours)

```bash
# 1. Read and follow PRODUCTION_DEPLOYMENT.md entirely
# 2. Create AWS resources (RDS, ElastiCache, VPC, ALB, ECS)
# 3. Store secrets in AWS Secrets Manager
# 4. Configure IAM roles and policies
# 5. Create ECS task definition and service
# 6. Configure auto-scaling policies
# 7. Set up CloudWatch monitoring
```

### 3. Deploy to Production (10-15 minutes)

```bash
# 1. Verify DEPLOYMENT_CHECKLIST.md is complete
# 2. Run deployment script
./deploy.sh production

# 3. Monitor deployment in CloudWatch
aws logs tail /ecs/aimodels-api --follow

# 4. Verify health checks pass
curl https://api.aimodels.cloud/health
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Users / Client Applications                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│    AWS Application Load Balancer (ALB)                   │
│    - api.aimodels.cloud:443 → :8000                      │
│    - Health checks every 30s                             │
│    - SSL/TLS termination                                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│           AWS ECS (Fargate) - aimodels-prod              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Task 1: FastAPI + Gunicorn + Uvicorn          │    │
│  │ - Image: ECR aimodels-api:latest              │    │
│  │ - 1024 CPU, 2048 MB memory                    │    │
│  │ - Port 8000                                    │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Task 2: FastAPI + Gunicorn + Uvicorn          │    │
│  │ (Auto-scaled 2-10 tasks based on load)        │    │
│  └─────────────────────────────────────────────────┘    │
└────┬──────────────────┬───────────────────────┬──────────┘
     │                  │                       │
     ▼                  ▼                       ▼
┌─────────────┐  ┌──────────────┐    ┌─────────────────┐
│   RDS       │  │   Redis      │    │   S3 / Logs     │
│ PostgreSQL  │  │  ElastiCache │    │   CloudWatch    │
│   (Multi-   │  │              │    │                 │
│    AZ)      │  │   (Cluster)  │    │   Monitoring    │
└─────────────┘  └──────────────┘    └─────────────────┘
```

## File Dependencies

```
deploy.sh
├── docker build
│   └── backend/Dockerfile
│       ├── pyproject.toml (dependencies)
│       └── backend/src/ (application code)
├── ECR repository creation
├── infrastructure/ecs-task-definition.json
│   └── environment/.env.production
│       └── AWS Secrets Manager values
├── ECS service update
└── Health check verification

docker-compose.yml
├── backend/Dockerfile
├── database/init.sql
└── .env (or environment variables)

PRODUCTION_DEPLOYMENT.md
├── DEPLOYMENT_CHECKLIST.md
├── infrastructure/cloudwatch-config.json
├── infrastructure/autoscaling-policy.json
└── infrastructure/ecs-task-definition.json
```

## Key Configurations

### Task Definition
- **CPU:** 1024 CPU units (1 vCPU)
- **Memory:** 2048 MB (2 GB)
- **Image:** `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest`
- **Port:** 8000
- **Log Group:** `/ecs/aimodels-api`
- **Health Check:** `curl http://localhost:8000/health`

### Auto-Scaling
- **Min Capacity:** 2 tasks (high availability)
- **Max Capacity:** 10 tasks (cost control)
- **CPU Target:** 70%
- **Memory Target:** 80%
- **Scale-Out Cooldown:** 60 seconds
- **Scale-In Cooldown:** 300 seconds

### Monitoring Thresholds
- **Error Rate Alert:** > 5% errors
- **Latency Alert:** P99 > 5 seconds
- **CPU Alert:** > 80%
- **Memory Alert:** > 85%
- **Unhealthy Hosts Alert:** < 1 healthy host (critical)

## Networking

### Security Groups
- **Inbound (ECS):** Port 8000 from ALB
- **Inbound (Database):** Port 5432 from ECS
- **Inbound (Cache):** Port 6379 from ECS
- **Outbound:** All protocols (or restricted)

### DNS
- Primary domain: `aimodels.cloud`
- API endpoint: `api.aimodels.cloud`
- ALB endpoint: `aimodels-api-alb-*.us-east-1.elb.amazonaws.com`

## Secrets Management

All sensitive data stored in AWS Secrets Manager:

```
aimodels/prod/database-url
aimodels/prod/redis-url
aimodels/prod/openai-api-key
aimodels/prod/anthropic-api-key
aimodels/prod/together-api-key
aimodels/prod/stripe-api-key
aimodels/prod/jwt-secret
```

## Rollback Strategy

1. **Automatic:** `deploy.sh` detects failures and rolls back to previous task definition
2. **Manual:** Use AWS CLI to update service with previous task definition
3. **Timing:** Rollback typically takes 2-3 minutes
4. **Criteria:** Triggered if health checks fail within first 10 minutes

## Cost Estimation (Monthly)

| Service | Instance | Quantity | Cost |
|---------|----------|----------|------|
| ECS (Fargate) | 1024 CPU, 2GB RAM | 2-10 tasks | $50-250 |
| RDS PostgreSQL | db.t3.medium | 1 (Multi-AZ) | $150 |
| ElastiCache Redis | cache.t3.medium | 1 | $45 |
| ALB | Standard | 1 | $20 |
| CloudWatch | Logs + Metrics | - | $15 |
| **Total Base Infra** | | | **~$280-510/mo** |
| API Provider Costs (Pass-through) | - | - | **Variable** |

## Support & Troubleshooting

See `PRODUCTION_DEPLOYMENT.md` for:
- Detailed troubleshooting guide
- Common issues and solutions
- CloudWatch log analysis
- Health check verification
- Performance optimization

## Next Steps

1. Review `PRODUCTION_DEPLOYMENT.md`
2. Complete `DEPLOYMENT_CHECKLIST.md`
3. Run `./deploy.sh staging` to test
4. Run `./deploy.sh production` for production deployment
5. Monitor logs: `aws logs tail /ecs/aimodels-api --follow`

---

**Document Version:** 1.0
**Last Updated:** 2026-07-28
**Status:** Ready for Production Deployment
