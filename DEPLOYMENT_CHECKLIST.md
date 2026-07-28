# Production Deployment Checklist — aimodels.cloud

Use this checklist to ensure everything is properly configured before deploying to production.

## Pre-Deployment Verification

### AWS Account Setup
- [ ] AWS Account created and IAM user configured
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS credentials set (Access Key ID & Secret Access Key)
- [ ] ECR repository created or auto-created by deploy script
- [ ] CloudWatch log group created (`/ecs/aimodels-api`)
- [ ] VPC and security groups configured
- [ ] Application Load Balancer created and configured
- [ ] ECS cluster created (`aimodels-prod`)

### Database & Cache
- [ ] RDS PostgreSQL instance running (`aimodels-prod-db`)
- [ ] Database backups enabled (30-day retention)
- [ ] Multi-AZ deployment enabled
- [ ] ElastiCache Redis cluster running (`aimodels-prod-cache`)
- [ ] Database connection tested: `psql -h <RDS_ENDPOINT> -U aimodels -d aimodels_prod`
- [ ] Redis connection tested: `redis-cli -h <REDIS_ENDPOINT> ping`
- [ ] Database migrations run: `alembic upgrade head`

### API Keys & Secrets
- [ ] OpenAI API key obtained and stored in AWS Secrets Manager
- [ ] Anthropic API key obtained and stored in AWS Secrets Manager
- [ ] Together.ai API key obtained and stored in AWS Secrets Manager
- [ ] Stripe API key obtained and stored in AWS Secrets Manager
- [ ] JWT secret generated (32+ chars) and stored
- [ ] All secrets in AWS Secrets Manager with proper IAM permissions
- [ ] Secrets tested: `aws secretsmanager get-secret-value --secret-id aimodels/prod/openai-api-key`

### Domain & DNS
- [ ] Domain `aimodels.cloud` registered and active
- [ ] API subdomain `api.aimodels.cloud` created
- [ ] DNS records updated to point to ALB:
  - [ ] `api.aimodels.cloud` → ALB DNS name or Elastic IP
  - [ ] Certificate requested in AWS Certificate Manager
  - [ ] Certificate validation completed (check email or DNS)
  - [ ] HTTPS listener added to ALB on port 443

### Environment Configuration
- [ ] `.env.production` file created with all required variables
- [ ] All API keys are production keys (not test/sandbox)
- [ ] Database URL uses RDS endpoint (not localhost)
- [ ] Redis URL uses ElastiCache endpoint (not localhost)
- [ ] ALLOWED_ORIGINS includes `https://aimodels.cloud` and `https://api.aimodels.cloud`
- [ ] LOG_LEVEL set to `INFO` (not DEBUG)
- [ ] ENVIRONMENT set to `production`
- [ ] SENTRY_DSN configured for error tracking

### Code Quality
- [ ] All code linted: `ruff check .`
- [ ] Code formatted: `black src/`
- [ ] Type checks pass: `mypy src/`
- [ ] Unit tests pass: `pytest tests/`
- [ ] Test coverage > 80%: `pytest --cov=src tests/`
- [ ] No hardcoded secrets in code
- [ ] No TODOs or FIXMEs blocking deployment

### Docker & Container Setup
- [ ] Dockerfile created at `backend/Dockerfile`
- [ ] Docker builds successfully: `docker build -t aimodels-api backend/`
- [ ] Docker image runs locally: `docker run -p 8000:8000 aimodels-api`
- [ ] Health check endpoint responds: `curl http://localhost:8000/health`
- [ ] Image size reasonable (< 500MB)

### ECS Configuration
- [ ] ECS task definition created and validated
- [ ] Task definition includes:
  - [ ] Correct image URI
  - [ ] All environment variables
  - [ ] Secrets from AWS Secrets Manager
  - [ ] CloudWatch log configuration
  - [ ] Health check configuration
  - [ ] Resource limits (CPU, memory)
  - [ ] Port mapping (8000 → 8000)
- [ ] ECS service created with:
  - [ ] Load balancer integration
  - [ ] Desired task count ≥ 2 (for HA)
  - [ ] Auto-scaling enabled
  - [ ] Health check grace period set to 60s
  - [ ] Deployment strategy set to rolling update
- [ ] IAM roles configured:
  - [ ] ecsTaskExecutionRole has AmazonECSTaskExecutionRolePolicy
  - [ ] aimodelsApiTaskRole has S3, Secrets Manager, CloudWatch permissions

### Auto-Scaling
- [ ] Auto-scaling target registered (min: 2, max: 10)
- [ ] CPU-based scaling policy created (target: 70%)
- [ ] Memory-based scaling policy created (target: 80%)
- [ ] Request count scaling policy created
- [ ] Scaling cooldown periods appropriate (60s out, 300s in)
- [ ] Spot instances configured (if cost optimization needed)

### Monitoring & Alerting
- [ ] CloudWatch log group created with retention policy
- [ ] CloudWatch dashboard created
- [ ] CloudWatch alarms configured:
  - [ ] CPU utilization > 80% (warning)
  - [ ] Memory utilization > 85% (warning)
  - [ ] Error rate > 5% (critical)
  - [ ] Response time > 5s (warning)
  - [ ] Unhealthy host count < 1 (critical)
- [ ] SNS topic created for alerts
- [ ] Email notifications configured
- [ ] Slack webhook configured (optional)
- [ ] Sentry DSN configured for error tracking
- [ ] Prometheus metrics enabled (optional)

### Security
- [ ] Security groups allow:
  - [ ] Inbound: Port 8000 from ALB
  - [ ] Inbound: Port 5432 from ECS tasks (database)
  - [ ] Inbound: Port 6379 from ECS tasks (Redis)
  - [ ] Outbound: All (or restricted as needed)
- [ ] IAM policies follow least privilege principle
- [ ] S3 bucket for logs has encryption enabled
- [ ] RDS database encrypted at rest
- [ ] Secrets Manager encryption enabled
- [ ] VPC endpoint for Secrets Manager configured (optional)
- [ ] HTTPS enabled (port 443 on ALB)
- [ ] No hardcoded credentials anywhere

### Deployment Script
- [ ] `deploy.sh` script is executable: `chmod +x deploy.sh`
- [ ] Script tested on development environment
- [ ] Script has proper error handling
- [ ] Script includes rollback functionality
- [ ] Script validates AWS credentials before proceeding
- [ ] Script has appropriate confirmation prompts

### Local Testing
- [ ] docker-compose.yml works: `docker-compose up && docker-compose down`
- [ ] All services start correctly
- [ ] Health checks pass for all services
- [ ] API responds to test requests
- [ ] Database migrations applied successfully
- [ ] Environment variables work as expected

### Staging Deployment
- [ ] Deployed to staging first
- [ ] Staging health checks pass
- [ ] Staging endpoints responsive
- [ ] Staging monitoring working
- [ ] Load tested on staging
- [ ] Rollback tested on staging

### Final Pre-Production Checks
- [ ] All team members notified of deployment
- [ ] On-call engineer assigned
- [ ] Rollback plan documented
- [ ] Communication channel (Slack) ready for updates
- [ ] Production database backed up
- [ ] Production secrets rotated recently
- [ ] No ongoing incidents or incidents in last 24h
- [ ] Maintenance window scheduled (off-peak time)
- [ ] Deployment window communicated to users

## Deployment Steps

### During Deployment
1. [ ] Announce deployment in team channel
2. [ ] Run pre-deployment health checks on production
3. [ ] Execute deployment script: `./deploy.sh production`
4. [ ] Monitor CloudWatch logs in real-time
5. [ ] Verify ECS service is updating tasks
6. [ ] Check ALB target group health
7. [ ] Monitor error rates and response times
8. [ ] Verify health checks passing

### Post-Deployment Verification
1. [ ] Verify new image tag is deployed: `aws ecs describe-services --cluster aimodels-prod --services aimodels-api`
2. [ ] Confirm running task count matches desired count
3. [ ] Test API endpoints:
   - [ ] Health check: `curl https://api.aimodels.cloud/health`
   - [ ] Models list: `curl https://api.aimodels.cloud/v1/models`
   - [ ] Test inference with sample request
4. [ ] Check CloudWatch metrics are being collected
5. [ ] Review logs for any errors
6. [ ] Monitor error rate for 15 minutes (should be < 0.1%)
7. [ ] Load test with expected traffic
8. [ ] Verify billing data is being tracked
9. [ ] Send post-deployment notification

### Rollback Decision Criteria
- [ ] Error rate > 5%
- [ ] Response time p99 > 10 seconds
- [ ] Unhealthy host count > 0
- [ ] Critical errors in logs
- [ ] Database connection failures
- [ ] Authentication/authorization failures

## Post-Deployment

### Monitor (First 24 Hours)
- [ ] Error rate < 1%
- [ ] p99 latency < 5s
- [ ] All tasks healthy
- [ ] No scaling cascades
- [ ] Database performance normal
- [ ] Redis performance normal

### Monitor (First Week)
- [ ] Error rate stable
- [ ] No performance degradation
- [ ] Cost within budget
- [ ] Billing data accurate
- [ ] User reports positive (if any)

### Document
- [ ] Update deployment log
- [ ] Document any issues encountered
- [ ] Update run-books if needed
- [ ] Record deployment time and status
- [ ] Collect metrics for retrospective

## Rollback Criteria

Rollback if within first hour of deployment:
- [ ] Error rate spike > 10%
- [ ] Critical service errors
- [ ] Database connection issues
- [ ] Authentication failures
- [ ] Billing/payment processing errors

## Approval Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DevOps Lead | | | |
| Engineering Manager | | | |
| On-Call Engineer | | | |

---

**Deployment Date:** ________________
**Deployed By:** ________________
**Image Tag:** ________________
**Status:** ☐ Success ☐ Rollback ☐ Partial

**Notes:**
