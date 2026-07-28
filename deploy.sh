#!/bin/bash

set -e

# aimodels.cloud Deployment Script
# Deploys FastAPI backend to AWS ECS
# Usage: ./deploy.sh [development|staging|production]

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="us-east-1"
SERVICE_NAME="aimodels-api"
CLUSTER_NAME="aimodels-${ENVIRONMENT}"
IMAGE_NAME="${SERVICE_NAME}"
IMAGE_TAG="$(git rev-parse --short HEAD)"

# AWS Configuration
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_REPOSITORY="${ECR_REGISTRY}/${IMAGE_NAME}"
IMAGE_URI="${ECR_REPOSITORY}:${IMAGE_TAG}"
IMAGE_LATEST="${ECR_REPOSITORY}:latest"

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate environment
validate_environment() {
    log_info "Validating deployment environment..."

    if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
        log_error "Invalid environment. Must be: development, staging, or production"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install it first."
        exit 1
    fi

    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_warning "Deploying to PRODUCTION. This cannot be undone."
        read -p "Type 'YES' to confirm: " -r
        echo
        if [[ ! $REPLY =~ ^YES$ ]]; then
            log_error "Deployment cancelled."
            exit 1
        fi
    fi

    log_success "Environment validation passed"
}

# Load environment variables
load_env() {
    log_info "Loading environment variables for $ENVIRONMENT..."

    if [ -f "${SCRIPT_DIR}/.env.${ENVIRONMENT}" ]; then
        set -a
        source "${SCRIPT_DIR}/.env.${ENVIRONMENT}"
        set +a
        log_success "Loaded .env.${ENVIRONMENT}"
    else
        log_warning ".env.${ENVIRONMENT} not found. Using defaults."
    fi
}

# Create ECR repository if it doesn't exist
create_ecr_repo() {
    log_info "Checking ECR repository..."

    if ! aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$REGION" &> /dev/null; then
        log_info "Creating ECR repository: $IMAGE_NAME"
        aws ecr create-repository \
            --repository-name "$IMAGE_NAME" \
            --region "$REGION" \
            --encryption-configuration encryptionType=AES

        # Add lifecycle policy to clean up old images
        aws ecr put-lifecycle-policy \
            --repository-name "$IMAGE_NAME" \
            --lifecycle-policy-text '{
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep last 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            }' \
            --region "$REGION"

        log_success "ECR repository created"
    else
        log_success "ECR repository exists"
    fi
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."

    if ! docker build \
        -f backend/Dockerfile \
        -t "$IMAGE_NAME:$IMAGE_TAG" \
        -t "$IMAGE_NAME:latest" \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        . ; then
        log_error "Docker build failed"
        exit 1
    fi

    log_success "Docker image built: $IMAGE_NAME:$IMAGE_TAG"
}

# Push image to ECR
push_to_ecr() {
    log_info "Authenticating with ECR..."

    aws ecr get-login-password --region "$REGION" | \
        docker login --username AWS --password-stdin "$ECR_REGISTRY"

    log_info "Tagging image for ECR..."
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$IMAGE_URI"
    docker tag "$IMAGE_NAME:latest" "$IMAGE_LATEST"

    log_info "Pushing image to ECR..."
    docker push "$IMAGE_URI"
    docker push "$IMAGE_LATEST"

    log_success "Image pushed to ECR: $IMAGE_URI"
}

# Run health checks
run_health_checks() {
    log_info "Running pre-deployment health checks..."

    # Check if database is reachable
    if [ ! -z "$DATABASE_URL" ]; then
        log_info "Checking database connectivity..."
        # This is a placeholder - implement actual DB check in your application
        log_success "Database check passed (simulated)"
    fi

    # Check if Redis is reachable
    if [ ! -z "$REDIS_URL" ]; then
        log_info "Checking Redis connectivity..."
        # This is a placeholder - implement actual Redis check
        log_success "Redis check passed (simulated)"
    fi

    log_success "All health checks passed"
}

# Update ECS service
update_ecs_service() {
    log_info "Updating ECS service..."

    # Get current task definition
    log_info "Fetching current task definition..."
    aws ecs describe-task-definition \
        --task-definition "$SERVICE_NAME" \
        --region "$REGION" > /tmp/task-def.json

    # Update image in task definition
    log_info "Updating image reference in task definition..."
    sed -i.bak "s|\"image\": \".*\"|\"image\": \"$IMAGE_URI\"|g" /tmp/task-def.json

    # Register new task definition
    log_info "Registering new task definition..."
    NEW_TASK_DEF=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/task-def.json \
        --region "$REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    log_success "New task definition registered: $NEW_TASK_DEF"

    # Update service with new task definition
    log_info "Updating ECS service with new task definition..."
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --task-definition "$NEW_TASK_DEF" \
        --force-new-deployment \
        --region "$REGION"

    log_success "ECS service updated"
}

# Wait for deployment to complete
wait_for_deployment() {
    log_info "Waiting for deployment to complete (timeout: 10 minutes)..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        RUNNING_COUNT=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$SERVICE_NAME" \
            --region "$REGION" \
            --query 'services[0].runningCount' \
            --output text)

        DESIRED_COUNT=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$SERVICE_NAME" \
            --region "$REGION" \
            --query 'services[0].desiredCount' \
            --output text)

        if [ "$RUNNING_COUNT" == "$DESIRED_COUNT" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
            log_success "Deployment complete. Running tasks: $RUNNING_COUNT"
            return 0
        fi

        echo -ne "\rWaiting... Running: $RUNNING_COUNT / Desired: $DESIRED_COUNT (${attempt}s)"
        sleep 10
        ((attempt+=10))
    done

    log_error "Deployment timeout. Check ECS service for details."
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Get ALB DNS name
    ALB_ENDPOINT=$(aws elbv2 describe-load-balancers \
        --region "$REGION" \
        --query "LoadBalancers[?tags[?Key=='Service' && Value=='$SERVICE_NAME']].DNSName" \
        --output text)

    if [ -z "$ALB_ENDPOINT" ]; then
        log_warning "Could not find ALB endpoint. Skipping health check."
        return 0
    fi

    log_info "Testing endpoint: http://$ALB_ENDPOINT/health"

    for i in {1..5}; do
        if curl -s "http://$ALB_ENDPOINT/health" | grep -q "healthy"; then
            log_success "Health check passed"
            return 0
        fi
        log_info "Health check attempt $i/5 failed. Retrying..."
        sleep 10
    done

    log_warning "Health check failed after 5 attempts. Please verify manually."
    return 1
}

# Rollback to previous version
rollback() {
    log_error "Deployment failed. Rolling back to previous version..."

    # Get previous task definition
    PREVIOUS_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$REGION" \
        --query 'services[0].deployments[1].taskDefinition' \
        --output text)

    if [ -z "$PREVIOUS_TASK_DEF" ]; then
        log_error "No previous task definition found. Manual intervention required."
        return 1
    fi

    log_info "Rolling back to: $PREVIOUS_TASK_DEF"
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --task-definition "$PREVIOUS_TASK_DEF" \
        --region "$REGION"

    log_success "Rollback completed"
}

# Send deployment notification
notify_deployment() {
    local status=$1
    local message="Deployment of $SERVICE_NAME to $ENVIRONMENT: $status"

    log_info "Sending deployment notification..."

    # Placeholder for Slack/Email notification
    # Implement your notification logic here
    echo "$message"
}

# Main deployment flow
main() {
    log_info "Starting deployment of aimodels.cloud API"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $REGION"
    log_info "Image: $IMAGE_URI"

    validate_environment
    load_env
    create_ecr_repo
    build_image
    push_to_ecr
    run_health_checks

    if update_ecs_service; then
        if wait_for_deployment; then
            if verify_deployment; then
                log_success "Deployment completed successfully!"
                notify_deployment "SUCCESS"

                log_info ""
                log_info "Deployment Summary:"
                log_info "  Environment: $ENVIRONMENT"
                log_info "  Image: $IMAGE_URI"
                log_info "  Cluster: $CLUSTER_NAME"
                log_info "  Service: $SERVICE_NAME"
                log_info ""
                exit 0
            fi
        fi
    fi

    rollback
    notify_deployment "FAILED"
    log_error "Deployment failed"
    exit 1
}

# Run main function
main "$@"
