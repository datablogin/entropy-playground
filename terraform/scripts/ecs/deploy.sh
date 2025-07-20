#!/bin/bash
set -euo pipefail

# ECS Deployment Script
# This script handles deployments to ECS/Fargate

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Default values
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME=${PROJECT_NAME:-entropy-playground}
IMAGE_TAG=${IMAGE_TAG:-latest}
DEPLOYMENT_TIMEOUT=${DEPLOYMENT_TIMEOUT:-600}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy the application to ECS/Fargate

Options:
    -e, --environment    Environment to deploy to (default: dev)
    -r, --region        AWS region (default: us-east-1)
    -t, --tag           Docker image tag (default: latest)
    -s, --service       Service name to deploy (default: agent-service)
    -c, --cluster       ECS cluster name (default: auto-detected)
    -w, --wait          Wait for deployment to complete
    -h, --help          Show this help message

Examples:
    $0 -e prod -t v1.0.0 -w
    $0 --environment staging --tag main-abc123
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -w|--wait)
            WAIT_FOR_DEPLOYMENT=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Set derived values
SERVICE_NAME=${SERVICE_NAME:-"${PROJECT_NAME}-${ENVIRONMENT}-agent-service"}
CLUSTER_NAME=${CLUSTER_NAME:-"${PROJECT_NAME}-${ENVIRONMENT}-cluster"}
TASK_FAMILY="${PROJECT_NAME}-${ENVIRONMENT}-agent"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be one of: dev, staging, prod"
    exit 1
fi

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

log_info "Starting deployment..."
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "Cluster: $CLUSTER_NAME"
log_info "Service: $SERVICE_NAME"
log_info "Image Tag: $IMAGE_TAG"

# Get current task definition
log_info "Fetching current task definition..."
TASK_DEFINITION=$(aws ecs describe-task-definition \
    --task-definition "$TASK_FAMILY" \
    --region "$AWS_REGION" \
    --query 'taskDefinition' \
    --output json 2>/dev/null || echo "")

if [[ -z "$TASK_DEFINITION" ]]; then
    log_error "Task definition not found: $TASK_FAMILY"
    exit 1
fi

# Update image tag in task definition
NEW_TASK_DEF=$(echo "$TASK_DEFINITION" | jq \
    --arg IMAGE_TAG "$IMAGE_TAG" \
    '.containerDefinitions[0].image |= sub(":.*$"; ":" + $IMAGE_TAG)')

# Remove fields that shouldn't be in the new task definition
NEW_TASK_DEF=$(echo "$NEW_TASK_DEF" | jq \
    'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

# Register new task definition
log_info "Registering new task definition..."
NEW_TASK_ARN=$(aws ecs register-task-definition \
    --cli-input-json "$NEW_TASK_DEF" \
    --region "$AWS_REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

if [[ -z "$NEW_TASK_ARN" ]]; then
    log_error "Failed to register new task definition"
    exit 1
fi

log_info "New task definition registered: $NEW_TASK_ARN"

# Update service
log_info "Updating ECS service..."
aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE_NAME" \
    --task-definition "$NEW_TASK_ARN" \
    --region "$AWS_REGION" \
    --output json > /dev/null

if [[ $? -ne 0 ]]; then
    log_error "Failed to update service"
    exit 1
fi

log_info "Service update initiated"

# Wait for deployment if requested
if [[ "${WAIT_FOR_DEPLOYMENT:-false}" == "true" ]]; then
    log_info "Waiting for deployment to complete (timeout: ${DEPLOYMENT_TIMEOUT}s)..."
    
    if aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null; then
        log_info "Deployment completed successfully!"
    else
        log_error "Deployment failed or timed out"
        
        # Get deployment events for debugging
        log_warning "Recent deployment events:"
        aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$SERVICE_NAME" \
            --region "$AWS_REGION" \
            --query 'services[0].events[0:5]' \
            --output table
        
        exit 1
    fi
else
    log_info "Deployment initiated. Use 'aws ecs describe-services' to check status."
fi

log_info "Deployment script completed"