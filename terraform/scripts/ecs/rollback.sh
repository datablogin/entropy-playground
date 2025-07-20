#!/bin/bash
set -euo pipefail

# ECS Rollback Script
# This script handles rollback of ECS deployments

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Default values
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME=${PROJECT_NAME:-entropy-playground}

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

Rollback ECS service to a previous task definition

Options:
    -e, --environment    Environment (default: dev)
    -r, --region        AWS region (default: us-east-1)
    -s, --service       Service name to rollback
    -c, --cluster       ECS cluster name
    -n, --revisions     Number of previous revisions to show (default: 5)
    -v, --revision      Specific revision to rollback to
    -w, --wait          Wait for rollback to complete
    -h, --help          Show this help message

Examples:
    $0 -e prod -v 42 -w
    $0 --environment staging --revisions 10
EOF
}

# Parse command line arguments
SHOW_REVISIONS=5
WAIT_FOR_ROLLBACK=false

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
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -n|--revisions)
            SHOW_REVISIONS="$2"
            shift 2
            ;;
        -v|--revision)
            TARGET_REVISION="$2"
            shift 2
            ;;
        -w|--wait)
            WAIT_FOR_ROLLBACK=true
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

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Check jq is installed
if ! command -v jq &> /dev/null; then
    log_error "jq is not installed. Please install it first."
    exit 1
fi

log_info "ECS Rollback Tool"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "Cluster: $CLUSTER_NAME"
log_info "Service: $SERVICE_NAME"

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text 2>/dev/null)

if [[ -z "$CURRENT_TASK_DEF" ]]; then
    log_error "Could not find service: $SERVICE_NAME"
    exit 1
fi

CURRENT_REVISION=$(echo "$CURRENT_TASK_DEF" | grep -oE '[0-9]+$')
log_info "Current task definition revision: $CURRENT_REVISION"

# If no target revision specified, show recent revisions
if [[ -z "${TARGET_REVISION:-}" ]]; then
    log_info "Fetching recent task definition revisions..."

    # List recent task definitions
    REVISIONS=$(aws ecs list-task-definitions \
        --family-prefix "$TASK_FAMILY" \
        --region "$AWS_REGION" \
        --sort DESC \
        --max-items "$((SHOW_REVISIONS + 1))" \
        --output json | jq -r '.taskDefinitionArns[]')

    echo
    echo "Recent task definition revisions:"
    echo "================================="

    while IFS= read -r arn; do
        REVISION=$(echo "$arn" | grep -oE '[0-9]+$')

        # Get task definition details
        TASK_DEF_INFO=$(aws ecs describe-task-definition \
            --task-definition "$arn" \
            --region "$AWS_REGION" \
            --query 'taskDefinition.{RegisteredAt:registeredAt,Image:containerDefinitions[0].image}' \
            --output json)

        REGISTERED_AT=$(echo "$TASK_DEF_INFO" | jq -r '.RegisteredAt')
        IMAGE=$(echo "$TASK_DEF_INFO" | jq -r '.Image')

        if [[ "$REVISION" == "$CURRENT_REVISION" ]]; then
            echo -e "${GREEN}► Revision $REVISION (CURRENT)${NC}"
        else
            echo "  Revision $REVISION"
        fi
        echo "    Registered: $REGISTERED_AT"
        echo "    Image: $IMAGE"
        echo
    done <<< "$REVISIONS"

    echo
    read -p "Enter revision number to rollback to (or Ctrl+C to cancel): " TARGET_REVISION
fi

# Validate target revision
if ! [[ "$TARGET_REVISION" =~ ^[0-9]+$ ]]; then
    log_error "Invalid revision number: $TARGET_REVISION"
    exit 1
fi

if [[ "$TARGET_REVISION" == "$CURRENT_REVISION" ]]; then
    log_warning "Target revision is the same as current revision. Nothing to do."
    exit 0
fi

# Construct task definition ARN
TASK_DEF_ARN="arn:aws:ecs:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):task-definition/${TASK_FAMILY}:${TARGET_REVISION}"

# Verify task definition exists
if ! aws ecs describe-task-definition \
    --task-definition "$TASK_DEF_ARN" \
    --region "$AWS_REGION" &> /dev/null; then
    log_error "Task definition not found: $TASK_DEF_ARN"
    exit 1
fi

# Confirm rollback
echo
log_warning "You are about to rollback from revision $CURRENT_REVISION to revision $TARGET_REVISION"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    log_info "Rollback cancelled"
    exit 0
fi

# Perform rollback
log_info "Rolling back to revision $TARGET_REVISION..."
aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE_NAME" \
    --task-definition "$TASK_DEF_ARN" \
    --region "$AWS_REGION" \
    --output json > /dev/null

if [[ $? -ne 0 ]]; then
    log_error "Failed to update service"
    exit 1
fi

log_info "Rollback initiated"

# Wait for rollback if requested
if [[ "$WAIT_FOR_ROLLBACK" == "true" ]]; then
    log_info "Waiting for rollback to complete..."

    if aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null; then
        log_info "Rollback completed successfully!"
    else
        log_error "Rollback failed or timed out"
        exit 1
    fi
else
    log_info "Rollback initiated. Use 'aws ecs describe-services' to check status."
fi

log_info "Rollback script completed"
