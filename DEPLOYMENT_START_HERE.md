# START HERE — aimodels.cloud Production Deployment Guide

Welcome! This guide will walk you through deploying the FastAPI backend for aimodels.cloud to production.

## What Gets Deployed?

The FastAPI backend API server for `api.aimodels.cloud`:
- **Language:** Python 3.11
- **Framework:** FastAPI with Gunicorn + Uvicorn workers
- **Infrastructure:** AWS ECS (Fargate) + ALB
- **Region:** US East 1
- **HA:** 2-10 auto-scaling tasks
- **Database:** AWS RDS PostgreSQL (15.3)
- **Cache:** AWS ElastiCache Redis (7.0)

## 5-Minute Overview

```
User Request → ALB:443 → ECS Task → FastAPI → Database/Cache → Response
```

1. Users call `api.aimodels.cloud` (domain points to AWS ALB)
2. ALB routes to ECS task (2-10 instances based on load)
3. FastAPI processes request using model adapters (OpenAI, Anthropic, Together.ai)
4. Results logged to database for billing
5. Response returned to user

## Step-by-Step Instructions

### Phase 1: Planning (30 minutes)

**Read these files in order:**

1. **[DEPLOYMENT_FILES_SUMMARY.md](./DEPLOYMENT_FILES_SUMMARY.md)** ← Start here
   - Overview of all deployment files
   - Architecture diagram
   - Cost estimation

2. **[PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)** ← Detailed guide
   - AWS infrastructure setup
   - Environment configuration
   - Step-by-step deployment instructions
   - Troubleshooting guide

3. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** ← Pre-deployment verification
   - 150+ items to verify before deploying
   - In order: AWS setup → Code quality → Infrastructure → Deployment

### Phase 2: Setup (2-4 hours for first time)

**Only required for first-time production setup:**

```bash
# 1. Create AWS infrastructure (1-2 hours)
# Follow instructions in PRODUCTION_DEPLOYMENT.md sections:
# - "AWS Infrastructure Setup"
# - "Environment Configuration"

# 2. Start local testing
docker-compose up -d
curl http://localhost:8000/health
docker-compose down

# 3. Verify all checklist items in DEPLOYMENT_CHECKLIST.md
```

### Phase 3: Deploy (10-15 minutes)

**The actual deployment:**

```bash
# 1. Ensure all prerequisites are met
# aws cli, docker, AWS credentials configured

# 2. Set environment variable (optional)
export AWS_REGION=us-east-1

# 3. Run the deployment script
chmod +x deploy.sh
./deploy.sh production

# 4. Wait for completion (5-10 min)
# Script handles:
# - Docker build and push to ECR
# - ECS task definition registration
# - Service update with rolling deployment
# - Health check verification
# - Automatic rollback on failure

# 5. Monitor logs
aws logs tail /ecs/aimodels-api --follow

# 6. Test endpoint
curl https://api.aimodels.cloud/health
```

## For Different Roles

### DevOps / Platform Engineer

1. Read: [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
2. Follow: "AWS Infrastructure Setup" section
3. Execute: `./deploy.sh production`
4. Monitor: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

### Application Engineer

1. Read: [DEPLOYMENT_FILES_SUMMARY.md](./DEPLOYMENT_FILES_SUMMARY.md)
2. Verify: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
3. Test locally: `docker-compose up -d`
4. Support deployment with code fixes as needed

### Operations / On-Call

1. Bookmark: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
2. Familiarize with monitoring commands
3. Know rollback procedure: Manual Rollback section in QUICK_REFERENCE.md
4. Contact: ops@aimodels.cloud for issues

### Project Manager

- Deployment takes **10-15 minutes**
- Testing takes **5-10 minutes additional**
- Can be done during off-peak hours
- Automatic rollback on failure (no manual intervention needed)

## Files Created

### Container & Deployment
- `backend/Dockerfile` - Multi-stage Docker build
- `docker-compose.yml` - Local development environment
- `deploy.sh` - Automated deployment script (executable)

### Configuration
- `.env.production.example` - Production environment variables template
- `pyproject.toml` - Updated Python dependencies (production-ready)

### Infrastructure
- `infrastructure/ecs-task-definition.json` - ECS task configuration
- `infrastructure/autoscaling-policy.json` - Auto-scaling rules
- `infrastructure/cloudwatch-config.json` - Monitoring & alerting

### Database
- `database/init.sql` - Schema, tables, indexes, seed data

### Documentation
- `DEPLOYMENT_FILES_SUMMARY.md` - Overview of all files
- `PRODUCTION_DEPLOYMENT.md` - Complete deployment guide
- `DEPLOYMENT_CHECKLIST.md` - Pre/post-deployment verification
- `QUICK_REFERENCE.md` - Operator quick reference
- `DEPLOYMENT_START_HERE.md` - This file!

## Key Features

✅ **Production Ready**
- Multi-stage Docker build for minimal image size
- Gunicorn + Uvicorn for production WSGI/ASGI serving
- Health checks at container and ECS level
- Structured logging to CloudWatch

✅ **High Availability**
- 2-10 auto-scaling ECS tasks
- Application Load Balancer with connection draining
- RDS Multi-AZ deployment
- ElastiCache Redis cluster

✅ **Security**
- Non-root container execution
- Secrets stored in AWS Secrets Manager
- IAM role-based access control
- VPC isolation with security groups

✅ **Monitoring & Observability**
- CloudWatch logs and metrics
- Automated alarms for critical issues
- Health check integration
- Request/response logging

✅ **Cost Optimized**
- Auto-scaling prevents overspending
- Spot instances supported (optional)
- Right-sized instances (1024 CPU, 2GB RAM)
- Old ECR images auto-cleaned

✅ **Easy Rollback**
- Automatic rollback on deployment failure
- Manual rollback to previous version (1 command)
- No data loss or migration issues

## Quick Commands Reference

```bash
# Local testing
docker-compose up -d && docker-compose logs -f api

# Deploy to production
./deploy.sh production

# View logs
aws logs tail /ecs/aimodels-api --follow

# Check status
aws ecs describe-services --cluster aimodels-prod --services aimodels-api

# Manual rollback
aws ecs update-service --cluster aimodels-prod --service aimodels-api \
  --task-definition aimodels-api:PREVIOUS_VERSION

# Monitor health
curl https://api.aimodels.cloud/health
```

## Typical Timeline

| Phase | Duration | What Happens |
|-------|----------|--------------|
| Planning | 30 min | Read documentation |
| First-time AWS setup | 1-2 hours | Create RDS, ElastiCache, ALB, ECS |
| Local testing | 5-10 min | Test with docker-compose |
| Deployment | 10-15 min | Deploy script runs (mostly automated) |
| Verification | 10-15 min | Test endpoints, monitor logs |
| **Total First Time** | **2-3 hours** | Ready for production! |
| **Subsequent Deploys** | **15-20 min** | Just run deploy.sh + verify |

## Important Notes

⚠️ **Before Deploying to Production:**
- [ ] Complete all items in DEPLOYMENT_CHECKLIST.md
- [ ] Test on staging first: `./deploy.sh staging`
- [ ] Have team on standby for rollback
- [ ] Database backed up recently
- [ ] No ongoing incidents
- [ ] Off-peak deployment window

✅ **After Deployment:**
- [ ] Monitor CloudWatch logs for 15 minutes
- [ ] Test all API endpoints
- [ ] Verify billing data recorded
- [ ] Check error rate < 0.1%
- [ ] Announce success to team

🔄 **Rollback (if needed):**
- [ ] `deploy.sh` auto-rollbacks on failure
- [ ] Or manually: See QUICK_REFERENCE.md
- [ ] Takes ~2-3 minutes
- [ ] Zero data loss guaranteed

## Support & Help

### I have questions about...

**Deployment process:** See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
**Files created:** See [DEPLOYMENT_FILES_SUMMARY.md](./DEPLOYMENT_FILES_SUMMARY.md)
**Pre-deployment checklist:** See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
**Common operations:** See [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**Troubleshooting:** Section in PRODUCTION_DEPLOYMENT.md
**Architecture:** See DEPLOYMENT_FILES_SUMMARY.md section

### I'm stuck. What do I do?

1. Check QUICK_REFERENCE.md for your issue
2. Check PRODUCTION_DEPLOYMENT.md "Troubleshooting" section
3. Check CloudWatch logs: `aws logs tail /ecs/aimodels-api`
4. Check task logs: `aws ecs describe-tasks --cluster aimodels-prod --tasks TASK_ID`
5. Contact ops@aimodels.cloud with logs

## Next Action Items

### Right Now (5 minutes)
- [ ] Read this file completely
- [ ] Bookmark QUICK_REFERENCE.md

### Today (1-2 hours)
- [ ] Read DEPLOYMENT_FILES_SUMMARY.md
- [ ] Skim PRODUCTION_DEPLOYMENT.md
- [ ] Run local test: `docker-compose up -d`

### This Week (if first-time production)
- [ ] Complete AWS infrastructure setup
- [ ] Review and complete DEPLOYMENT_CHECKLIST.md
- [ ] Deploy to staging: `./deploy.sh staging`

### Before Production Deployment
- [ ] All DEPLOYMENT_CHECKLIST.md items checked
- [ ] Team briefed and standing by
- [ ] Rollback procedure understood
- [ ] Execute: `./deploy.sh production`

## Success Criteria

✅ **Deployment is successful when:**
- ECS service shows 2+ running tasks
- Health check endpoint returns HTTP 200
- CloudWatch metrics showing normal traffic
- Error rate < 1% in first hour
- Team can call API successfully
- No rollback needed

---

**Ready to deploy?** → Start with [DEPLOYMENT_FILES_SUMMARY.md](./DEPLOYMENT_FILES_SUMMARY.md)

**Questions?** → Check [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

**Need details?** → Read [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)

---

**Version:** 1.0
**Status:** ✅ Ready for Production
**Last Updated:** 2026-07-28
