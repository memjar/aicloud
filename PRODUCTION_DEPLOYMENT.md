# Production Deployment Guide — aimodels.cloud FastAPI Backend

Complete guide to deploying the FastAPI backend to production at `api.aimodels.cloud`.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Testing](#local-testing)
3. [AWS Infrastructure Setup](#aws-infrastructure-setup)
4. [Environment Configuration](#environment-configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring & Logging](#monitoring--logging)
7. [Auto-Scaling Configuration](#auto-scaling-configuration)
8. [Health Checks](#health-checks)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- Docker (v20.10+)
- AWS CLI v2
- AWS Account with appropriate IAM permissions
- Git
- Python 3.11+
- Poetry (for local development)

### AWS Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "elbv2:*",
        "ec2:*",
        "logs:*",
        "secretsmanager:*",
        "rds:*",
        "elasticache:*",
        "cloudwatch:*",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

## Local Testing

### Option 1: Using Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/aimodels/aimodels-cloud.git
cd aimodels-cloud

# Create environment file
cp .env.development .env
# Edit .env with your API keys for testing

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Run health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "aicloud-api"}

# Test inference endpoint
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Stop services
docker-compose down
```

### Option 2: Local Development

```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start Redis
redis-server

# Start API server
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## AWS Infrastructure Setup

### Step 1: Create AWS Resources

```bash
# Set variables
export AWS_REGION=us-east-1
export ENVIRONMENT=production
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create S3 bucket for logs and artifacts
aws s3api create-bucket \
  --bucket aimodels-prod-logs-${ACCOUNT_ID} \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Create RDS PostgreSQL database
aws rds create-db-instance \
  --db-instance-identifier aimodels-prod-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.3 \
  --master-username aimodels \
  --master-user-password CHANGE_ME \
  --allocated-storage 100 \
  --storage-encrypted \
  --multi-az \
  --backup-retention-period 30

# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id aimodels-prod-cache \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --automatic-failover-enabled
```

### Step 2: Create VPC and Network Resources

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' \
  --output text)

# Create subnets
SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --query 'Subnet.SubnetId' \
  --output text)

SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --query 'Subnet.SubnetId' \
  --output text)

# Create security group for ECS
SG=$(aws ec2 create-security-group \
  --group-name aimodels-api-sg \
  --description "Security group for aimodels API" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Allow inbound HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id $SG \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

# Allow outbound to all
aws ec2 authorize-security-group-egress \
  --group-id $SG \
  --protocol -1 \
  --cidr 0.0.0.0/0
```

### Step 3: Create Application Load Balancer

```bash
# Create Application Load Balancer
ALB=$(aws elbv2 create-load-balancer \
  --name aimodels-api-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $SG \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Create target group
TG=$(aws elbv2 create-target-group \
  --name aimodels-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG

# Get ALB DNS name
aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

### Step 4: Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name aimodels-prod \
  --cluster-settings name=containerInsights,value=enabled

# Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /ecs/aimodels-api \
  --region $AWS_REGION

aws logs put-retention-policy \
  --log-group-name /ecs/aimodels-api \
  --retention-in-days 30
```

## Environment Configuration

### Step 1: Create Secrets Manager Entries

```bash
# Database URL
aws secretsmanager create-secret \
  --name aimodels/prod/database-url \
  --secret-string "postgresql://aimodels:PASSWORD@DB_HOST:5432/aimodels_prod"

# Redis URL
aws secretsmanager create-secret \
  --name aimodels/prod/redis-url \
  --secret-string "redis://CACHE_HOST:6379/0"

# OpenAI API Key
aws secretsmanager create-secret \
  --name aimodels/prod/openai-api-key \
  --secret-string "sk-..."

# Anthropic API Key
aws secretsmanager create-secret \
  --name aimodels/prod/anthropic-api-key \
  --secret-string "sk-ant-..."

# Together.ai API Key
aws secretsmanager create-secret \
  --name aimodels/prod/together-api-key \
  --secret-string "..."

# Stripe API Key
aws secretsmanager create-secret \
  --name aimodels/prod/stripe-api-key \
  --secret-string "sk_live_..."

# JWT Secret
aws secretsmanager create-secret \
  --name aimodels/prod/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"
```

### Step 2: Create IAM Roles

```bash
# Create ECS task execution role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create ECS task role
aws iam create-role \
  --role-name aimodelsApiTaskRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Add inline policy for S3, Secrets Manager access
aws iam put-role-policy \
  --role-name aimodelsApiTaskRole \
  --policy-name aimodels-api-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        "Resource": "arn:aws:s3:::aimodels-prod-*/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "secretsmanager:GetSecretValue"
        ],
        "Resource": "arn:aws:secretsmanager:*:*:secret:aimodels/prod/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*"
      }
    ]
  }'
```

## Deployment Process

### Automated Deployment (Recommended)

```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy to production
./deploy.sh production

# Or to staging
./deploy.sh staging

# Or to development
./deploy.sh development
```

The script will:
1. Validate AWS configuration
2. Build Docker image
3. Push to ECR
4. Register new ECS task definition
5. Update ECS service
6. Wait for deployment to complete
7. Run health checks
8. Rollback on failure

### Manual Deployment

```bash
# Build and push image
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t aimodels-api:latest backend/
docker tag aimodels-api:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://infrastructure/ecs-task-definition.json

# Update service
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --force-new-deployment

# Wait for deployment
aws ecs wait services-stable \
  --cluster aimodels-prod \
  --services aimodels-api
```

## Monitoring & Logging

### CloudWatch Logs

```bash
# View real-time logs
aws logs tail /ecs/aimodels-api --follow

# Query logs with Insights
aws logs start-query \
  --log-group-name /ecs/aimodels-api \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count()'
```

### CloudWatch Metrics

```bash
# View CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=aimodels-api Name=ClusterName,Value=aimodels-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

### Configure CloudWatch Dashboard

```bash
aws cloudwatch put-dashboard \
  --dashboard-name aimodels-api-dashboard \
  --dashboard-body file://infrastructure/cloudwatch-config.json
```

## Auto-Scaling Configuration

### Create Auto Scaling Target

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10 \
  --region us-east-1
```

### Create Scaling Policies

```bash
# CPU-based scaling
aws application-autoscaling put-scaling-policy \
  --policy-name aimodels-api-cpu-scaling \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'

# Memory-based scaling
aws application-autoscaling put-scaling-policy \
  --policy-name aimodels-api-memory-scaling \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 80,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageMemoryUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

## Health Checks

### Application Health Endpoint

The API provides a health check endpoint:

```bash
# Health check
curl https://api.aimodels.cloud/health

# Expected response:
# {"status": "healthy", "service": "aicloud-api"}
```

### ALB Health Check Configuration

The ALB is configured to:
- Check `/health` endpoint every 30 seconds
- Expect HTTP 200 response
- Require 2 consecutive successful checks before marking healthy
- Mark unhealthy after 3 consecutive failures
- Timeout set to 5 seconds

## Rollback Procedures

### Automatic Rollback

If deployment health checks fail, the `deploy.sh` script automatically rolls back:

```bash
# The script will:
# 1. Detect failure
# 2. Get previous task definition
# 3. Update service with previous version
# 4. Verify rollback successful
```

### Manual Rollback

```bash
# List available task definition versions
aws ecs describe-task-definition \
  --task-definition aimodels-api \
  --query 'taskDefinition.taskDefinitionArn'

# Get previous revision
PREVIOUS_REVISION=$(aws ecs list-task-definitions \
  --family-prefix aimodels-api \
  --sort DESC \
  --query 'taskDefinitionArns[1]' \
  --output text)

# Rollback to previous version
aws ecs update-service \
  --cluster aimodels-prod \
  --service aimodels-api \
  --task-definition $PREVIOUS_REVISION
```

## Troubleshooting

### Common Issues

#### 1. Tasks fail to start

```bash
# Check task logs
aws ecs describe-tasks \
  --cluster aimodels-prod \
  --tasks <TASK_ID> \
  --query 'tasks[0].stoppedReason'

# View CloudWatch logs
aws logs tail /ecs/aimodels-api --follow
```

#### 2. Connection refused to database

```bash
# Verify RDS is running
aws rds describe-db-instances \
  --db-instance-identifier aimodels-prod-db \
  --query 'DBInstances[0].DBInstanceStatus'

# Check security group allows access
aws ec2 describe-security-groups \
  --group-ids <SG_ID> \
  --query 'SecurityGroups[0].IpPermissions'
```

#### 3. High CPU/Memory usage

```bash
# Check running task count
aws ecs describe-services \
  --cluster aimodels-prod \
  --services aimodels-api \
  --query 'services[0].runningCount'

# Check autoscaling policies
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/aimodels-prod/aimodels-api
```

#### 4. API timeouts

```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn <TG_ARN> \
  --query 'TargetHealthDescriptions'

# Check ALB response time
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/aimodels-api-alb/* \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

### Support

For issues or questions:
- Check CloudWatch logs: `/ecs/aimodels-api`
- View ECS service status: `aws ecs describe-services --cluster aimodels-prod --services aimodels-api`
- Contact: ops@aimodels.cloud

## Appendix: DNS Configuration

Update your domain DNS to point to the ALB:

```
api.aimodels.cloud  CNAME  aimodels-api-alb-123456789.us-east-1.elb.amazonaws.com
```

Or use Route53:

```bash
# Create alias record
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.aimodels.cloud",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "aimodels-api-alb-123456789.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```
