# Quick Reference — aimodels.cloud Deployment

Fast lookup guide for common deployment operations.

## Deployment

### Deploy to Production
```bash
./deploy.sh production
```
⏱️ Typical time: 5-10 minutes

### Deploy to Staging
```bash
./deploy.sh staging
```

### Deploy to Development
```bash
./deploy.sh development
```

## Monitoring

### View Real-Time Logs
```bash
aws logs tail /ecs/aimodels-api --follow
```

### Check Service Status
```bash
aws ecs describe-services \
  --cluster aimodels-prod \
  --services aimodels-api \
  --query 'services[0].{running:runningCount,desired:desiredCount,status:status}'
```

### View Task Status
```bash
aws ecs list-tasks --cluster aimodels-prod --service-name aimodels-api
aws ecs describe-tasks --cluster aimodels-prod --tasks <TASK_ID>
```

### Check ALB Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/aimodels-api-tg/*
```

### Monitor CPU & Memory
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=aimodels-api Name=ClusterName,Value=aimodels-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

## Rollback

### Manual Rollback to Previous Version
```bash
# Get previous task definition
aws ecs list-task-definitions \
  --family-prefix aimodels-api \
  --sort DESC \
  --query 'taskDefinitionArns[1]'

# Rollback
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --task-definition aimodels-api:PREVIOUS_VERSION
```

### Check Deployment History
```bash
aws ecs describe-services \
  --cluster aimodels-prod \
  --services aimodels-api \
  --query 'services[0].deployments[*].[taskDefinition,status,runningCount]'
```

## Database

### Connect to Production Database
```bash
psql -h aimodels-prod-db.XXXXXXX.us-east-1.rds.amazonaws.com \
     -U aimodels \
     -d aimodels_prod
```

### Check Database Size
```bash
# From psql terminal
SELECT pg_size_pretty(pg_database_size('aimodels_prod'));
```

### Run Database Migrations
```bash
# In ECS task
poetry run alembic upgrade head
```

### Backup Database
```bash
aws rds create-db-snapshot \
  --db-instance-identifier aimodels-prod-db \
  --db-snapshot-identifier aimodels-prod-db-backup-$(date +%Y%m%d-%H%M%S)
```

## Scaling

### Scale to Specific Task Count
```bash
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --desired-count 5
```

### Check Auto-Scaling Policies
```bash
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api
```

### Temporarily Disable Auto-Scaling
```bash
aws application-autoscaling deregister-scalable-target \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api \
  --scalable-dimension ecs:service:DesiredCount
```

## Secrets

### View Secret (Masked)
```bash
aws secretsmanager describe-secret \
  --secret-id aimodels/prod/openai-api-key \
  --query 'ARN'
```

### Retrieve Secret Value (Use with caution!)
```bash
aws secretsmanager get-secret-value \
  --secret-id aimodels/prod/openai-api-key \
  --query 'SecretString' \
  --output text
```

### Rotate Secret
```bash
aws secretsmanager rotate-secret \
  --secret-id aimodels/prod/openai-api-key \
  --rotation-rules AutomaticallyAfterDays=30
```

## CloudWatch

### Create Dashboard
```bash
aws cloudwatch put-dashboard \
  --dashboard-name aimodels-api-dashboard \
  --dashboard-body file://infrastructure/cloudwatch-config.json
```

### Query Logs with Insights
```bash
aws logs start-query \
  --log-group-name /ecs/aimodels-api \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count()'
```

### List Recent Errors
```bash
aws logs tail /ecs/aimodels-api --filter-pattern "ERROR" --follow
```

## Health Checks

### Test Health Endpoint
```bash
curl https://api.aimodels.cloud/health
```

Expected response:
```json
{"status": "healthy", "service": "aicloud-api"}
```

### Test API
```bash
curl -X POST https://api.aimodels.cloud/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-YOUR_API_KEY" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Docker

### Build Local Image
```bash
docker build -t aimodels-api:local backend/
docker run -p 8000:8000 aimodels-api:local
```

### Push to ECR
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/aimodels-api:TAG
```

### Test with Docker Compose
```bash
docker-compose up -d
docker-compose logs -f api
docker-compose down
```

## Local Development

### Install Dependencies
```bash
poetry install
```

### Run Tests
```bash
pytest tests/ --cov=src
```

### Format Code
```bash
black src/
ruff check --fix src/
isort src/
```

### Type Check
```bash
mypy src/
```

### Start Development Server
```bash
poetry run uvicorn src.main:app --reload --port 8000
```

## Alarms & Alerts

### List Active Alarms
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix aimodels-api \
  --query 'MetricAlarms[*].[AlarmName,StateValue]'
```

### Trigger Test Alert
```bash
aws cloudwatch set-alarm-state \
  --alarm-name aimodels-api-cpu-high \
  --state-value ALARM \
  --state-reason "Manual test"
```

### View Alarm History
```bash
aws cloudwatch describe-alarm-history \
  --alarm-name aimodels-api-cpu-high \
  --max-records 10
```

## DNS

### Check DNS Resolution
```bash
dig api.aimodels.cloud @8.8.8.8
nslookup api.aimodels.cloud
```

### Get ALB DNS Name
```bash
aws elbv2 describe-load-balancers \
  --region us-east-1 \
  --query "LoadBalancers[?tags[?Key=='Service' && Value=='aimodels-api']].DNSName" \
  --output text
```

## Cleanup & Decommissioning

### Scale Down to Zero (Stop Service)
```bash
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --desired-count 0
```

### Delete Task Definition
```bash
aws ecs deregister-task-definition \
  --task-definition aimodels-api:VERSION
```

### Delete Service
```bash
aws ecs delete-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --force
```

## Troubleshooting Quick Checks

### 1. Service Won't Start?
```bash
# Check logs
aws logs tail /ecs/aimodels-api --follow

# Check task details
aws ecs describe-tasks --cluster aimodels-prod --tasks TASK_ID

# Check image exists in ECR
aws ecr describe-images --repository-name aimodels-api
```

### 2. High Error Rate?
```bash
# Check recent errors
aws logs tail /ecs/aimodels-api --filter-pattern ERROR

# Check external service status
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
curl https://api.anthropic.com/v1/status -H "x-api-key: $ANTHROPIC_API_KEY"
```

### 3. Database Connection Failing?
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier aimodels-prod-db

# Test connection from local
psql -h aimodels-prod-db.XXXXXXX.us-east-1.rds.amazonaws.com -U aimodels -d aimodels_prod
```

### 4. High Latency?
```bash
# Check response time metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --start-time $(date -u -d '30 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Maximum

# Check task count
aws ecs describe-services --cluster aimodels-prod --services aimodels-api
```

## Useful Links

- AWS Console: https://console.aws.amazon.com
- ECS Dashboard: https://console.aws.amazon.com/ecs/
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/
- Health Endpoint: https://api.aimodels.cloud/health
- API Documentation: https://api.aimodels.cloud/docs

## Emergency Contacts

- On-call: Check team calendar
- Support: ops@aimodels.cloud
- Escalation: tech-lead@aimodels.cloud

---

**Pro Tips:**
- Save AWS account ID and cluster names as shell aliases
- Use AWS CLI profiles for multiple environments
- Set up CloudWatch dashboard for visual monitoring
- Configure SNS alerts to Slack for critical alarms
- Keep this file in your terminal history for quick access
