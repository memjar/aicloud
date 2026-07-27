# Deployment Guide — aimodels.cloud

Complete deployment instructions for Vercel frontend + custom backend API.

## Domains

- **Primary:** aimodels.cloud (Active until Jun 19, 2027)
- **Secondary:** aimodel.com.im (Active until Jun 24, 2027)

Both have SSL/privacy protection enabled via Namecheap.

## Frontend Deployment (Vercel)

### Step 1: Connect to Vercel

```bash
npm i -g vercel
vercel link  # In your project root
```

### Step 2: Configure Domains

In Vercel Project Settings → Domains, add:
- `aimodels.cloud`
- `www.aimodels.cloud`
- `aimodel.com.im` (optional redirect)
- `www.aimodel.com.im` (optional redirect)

### Step 3: Update DNS Records (Namecheap)

For **aimodels.cloud** (via Namecheap Advanced DNS):

```
Type     Name           Value                    TTL
CNAME    @              cname.vercel-dns.com.    3600
CNAME    www            cname.vercel-dns.com.    3600
A        api            [Backend IP]             3600
CNAME    api.vercel     cname.vercel-dns.com.    3600
```

For **aimodel.com.im** (optional):
- Same pattern as above, or redirect all traffic to aimodels.cloud

### Step 4: Auto-Deploy on Push

```bash
git push origin main
# Vercel automatically builds and deploys
```

## Backend Deployment (Docker + ECS)

### Prerequisites
- AWS Account with ECS access
- Docker installed locally
- `api.aimodels.cloud` DNS pointing to ALB

### Step 1: Containerize Backend

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY src/ ./src/

CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Build & Push to ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com

docker build -t aimodels-api backend/
docker tag aimodels-api:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
```

### Step 3: Deploy to ECS

```bash
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --force-new-deployment
```

## DNS Summary

### What Each Record Does

| Record | Purpose | Points To |
|--------|---------|-----------|
| `aimodels.cloud` (A/CNAME) | Main website | Vercel CDN |
| `www.aimodels.cloud` (CNAME) | www redirect | Vercel CDN |
| `api.aimodels.cloud` (A) | API endpoint | AWS ALB (backend) |
| `.com.im` variants | Backup domain | Same as above or redirect |

### Expected Behavior

1. **https://aimodels.cloud** → Vercel → Next.js landing page
2. **https://www.aimodels.cloud** → Vercel → Same landing page
3. **https://api.aimodels.cloud/v1/models** → AWS ALB → FastAPI backend
4. **Dashboard at /dashboard** → Vercel (frontend route)

## Environment Variables

### Frontend (.env.production)

```env
NEXT_PUBLIC_API_URL=https://api.aimodels.cloud
NEXT_PUBLIC_ANALYTICS_KEY=phc_xxxxx (PostHog)
NEXT_PUBLIC_STRIPE_KEY=pk_live_xxxxx
```

### Backend (.env)

```env
DATABASE_URL=postgresql://user:pass@db.rds.amazonaws.com/aimodels
REDIS_URL=redis://cache.elasticache.amazonaws.com:6379
API_PORT=8000
LOG_LEVEL=INFO
STRIPE_API_KEY=sk_live_xxxxx
```

## SSL Certificates

Vercel automatically provisions Let's Encrypt SSL for `aimodels.cloud` (no action needed).

For backend API (`api.aimodels.cloud`), use AWS Certificate Manager:
```bash
aws acm request-certificate \
  --domain-name api.aimodels.cloud \
  --validation-method DNS
```

## Monitoring

### Frontend (Vercel)
- Vercel Analytics → https://vercel.com/dashboard
- Real-time logs: `vercel logs --follow`

### Backend (CloudWatch)
- Logs: `aws logs tail /ecs/aimodels-api --follow`
- Metrics: CloudWatch Dashboard
- Alarms: Email/SNS on error rate > 5%

## Rollback

### Frontend
```bash
vercel rollback
# or revert in GitHub and re-push
```

### Backend
```bash
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --task-definition aimodels-api:PREVIOUS_VERSION
```

## Troubleshooting

### DNS Not Resolving
```bash
dig aimodels.cloud @8.8.8.8
nslookup aimodels.cloud
```
Expected: Points to Vercel or your ALB IP

### SSL Certificate Error
- Wait 24 hours for DNS propagation
- Check Namecheap DNS settings match Vercel recommendation
- Force renewal: `vercel certs --rm && vercel certs --create`

### API Timeouts
- Check backend ECS health: `aws ecs describe-services --cluster aimodels-prod --services aimodels-api`
- Check ALB target group: `aws elbv2 describe-target-health --target-group-arn arn:aws:...`
- Check security groups allow port 8000 inbound

## Next Steps

1. ✅ Create Vercel account and link repo
2. ✅ Add domains to Vercel
3. ✅ Update Namecheap DNS to point to Vercel
4. ⏳ Deploy backend to AWS ECS
5. ⏳ Wire up database (RDS PostgreSQL)
6. ⏳ Configure Redis cache
7. ⏳ Set environment variables on Vercel + ECS
8. ⏳ Enable monitoring (PostHog, CloudWatch)
9. ⏳ Launch public beta
