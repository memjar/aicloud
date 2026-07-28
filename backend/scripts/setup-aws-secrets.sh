#!/bin/bash

# Setup AWS Secrets Manager for aimodels.cloud API
# Usage:
#   ./scripts/setup-aws-secrets.sh [environment]
#
# Environments: development, staging, production
# Default: staging

set -e

ENVIRONMENT="${1:-staging}"
REGION="${2:-us-east-1}"
PROJECT_NAME="aimodels"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

log_info() {
    echo "ℹ $1"
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Valid options: development, staging, production"
    exit 1
fi

if [ "$ENVIRONMENT" = "production" ]; then
    read -p "⚠️  This will configure PRODUCTION secrets. Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warning "Setup cancelled"
        exit 0
    fi
fi

log_info "Setting up AWS Secrets Manager for $ENVIRONMENT environment"
log_info "Region: $REGION"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Check credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

log_success "AWS credentials verified"

# Secret name based on environment
SECRET_NAME="$PROJECT_NAME/$ENVIRONMENT/api-keys"

log_info "Secret name: $SECRET_NAME"

# Check if secret exists
if aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" > /dev/null 2>&1; then
    log_warning "Secret already exists: $SECRET_NAME"
    read -p "Overwrite existing secret? (yes/no): " overwrite
    if [ "$overwrite" != "yes" ]; then
        log_info "Skipping secret creation"
        exit 0
    fi
fi

# Create secret JSON template
cat > /tmp/aimodels_secrets_${ENVIRONMENT}.json << 'EOF'
{
  "openai_api_key": "sk_live_REPLACE_WITH_REAL_KEY",
  "anthropic_api_key": "sk_ant_REPLACE_WITH_REAL_KEY",
  "together_api_key": "REPLACE_WITH_REAL_KEY",
  "database_url": "postgresql://user:password@host:5432/dbname",
  "redis_url": "redis://host:6379/0",
  "stripe_api_key": "sk_live_REPLACE_WITH_REAL_KEY",
  "stripe_webhook_key": "whsec_REPLACE_WITH_REAL_KEY",
  "jwt_secret_key": "GENERATE_OFFLINE_MIN_32_CHARS"
}
EOF

log_info "Created template at /tmp/aimodels_secrets_${ENVIRONMENT}.json"
log_info "Please edit this file with your actual secrets:"
echo ""
echo "  nano /tmp/aimodels_secrets_${ENVIRONMENT}.json"
echo ""

# Wait for user to confirm they've edited
read -p "Press Enter after updating the secrets file..."

# Validate JSON
if ! jq . /tmp/aimodels_secrets_${ENVIRONMENT}.json > /dev/null 2>&1; then
    log_error "Invalid JSON in secrets file"
    exit 1
fi

log_success "JSON is valid"

# Check for placeholder values
PLACEHOLDER_COUNT=$(grep -c "REPLACE_WITH_REAL_KEY\|GENERATE_OFFLINE" /tmp/aimodels_secrets_${ENVIRONMENT}.json || true)
if [ "$PLACEHOLDER_COUNT" -gt 0 ]; then
    log_error "Secrets file still contains placeholder values"
    exit 1
fi

log_success "All placeholders replaced"

# Create or update secret
log_info "Creating/updating secret in AWS Secrets Manager..."

if aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" > /dev/null 2>&1; then
    # Update existing secret
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string file:///tmp/aimodels_secrets_${ENVIRONMENT}.json \
        --region "$REGION" > /dev/null

    log_success "Secret updated: $SECRET_NAME"
    SECRET_VERSION=$(aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$REGION" | jq -r '.VersionIdsToStages | keys[0]')
else
    # Create new secret
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "API keys for $PROJECT_NAME $ENVIRONMENT environment" \
        --secret-string file:///tmp/aimodels_secrets_${ENVIRONMENT}.json \
        --region "$REGION" > /dev/null

    log_success "Secret created: $SECRET_NAME"
    SECRET_VERSION=$(aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$REGION" | jq -r '.VersionIdsToStages | keys[0]')
fi

log_success "Secret version: $SECRET_VERSION"

# Configure tags
log_info "Adding tags to secret..."
aws secretsmanager tag-resource \
    --secret-id "$SECRET_NAME" \
    --tags Key=Environment,Value=$ENVIRONMENT Key=Project,Value=$PROJECT_NAME Key=ManagedBy,Value=terraform \
    --region "$REGION"

log_success "Tags configured"

# Test secret retrieval
log_info "Testing secret retrieval..."
if aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" > /dev/null 2>&1; then
    log_success "Secret retrieval successful"
else
    log_error "Failed to retrieve secret"
    exit 1
fi

# Verify credentials
SECRET_DATA=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query 'SecretString' \
    --output text | jq .)

log_success "Secret verified in AWS Secrets Manager"

# Show configuration
echo ""
echo "========================================"
echo "Configuration Summary"
echo "========================================"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Secret Name: $SECRET_NAME"
echo "Secret Version: $SECRET_VERSION"
echo ""
echo "Next steps:"
echo "1. Update .env.$ENVIRONMENT with AWS_SECRETS_MANAGER_ENABLED=true"
echo "2. Deploy with: ./scripts/deploy.sh $ENVIRONMENT"
echo "3. Verify with: curl https://api.aimodels.cloud/health"
echo ""
echo "To view secret (use with caution):"
echo "  aws secretsmanager get-secret-value --secret-id '$SECRET_NAME' --region $REGION"
echo ""

# Cleanup
rm -f /tmp/aimodels_secrets_${ENVIRONMENT}.json

log_success "AWS Secrets Manager setup complete"
