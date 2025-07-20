#!/bin/bash
set -euo pipefail

# ECS Monitoring Script
# This script provides monitoring and status information for ECS services

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Default values
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME=${PROJECT_NAME:-entropy-playground}
REFRESH_INTERVAL=${REFRESH_INTERVAL:-5}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

Monitor ECS services and tasks

Options:
    -e, --environment    Environment (default: dev)
    -r, --region        AWS region (default: us-east-1)
    -s, --service       Service name to monitor
    -c, --cluster       ECS cluster name
    -t, --tasks         Show task details
    -l, --logs          Show recent logs
    -m, --metrics       Show CloudWatch metrics
    -w, --watch         Watch mode (refresh every N seconds)
    -i, --interval      Refresh interval in seconds (default: 5)
    -h, --help          Show this help message

Examples:
    $0 -e prod -t
    $0 --environment staging --watch --interval 10
    $0 -e dev --logs
EOF
}

# Parse command line arguments
SHOW_TASKS=false
SHOW_LOGS=false
SHOW_METRICS=false
WATCH_MODE=false

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
        -t|--tasks)
            SHOW_TASKS=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -m|--metrics)
            SHOW_METRICS=true
            shift
            ;;
        -w|--watch)
            WATCH_MODE=true
            shift
            ;;
        -i|--interval)
            REFRESH_INTERVAL="$2"
            shift 2
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
LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}/agent"

# Function to display service status
show_service_status() {
    local service_info=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)

    if [[ -z "$service_info" ]]; then
        log_error "Could not find service: $SERVICE_NAME"
        return 1
    fi

    # Extract service details
    local status=$(echo "$service_info" | jq -r '.services[0].status')
    local desired_count=$(echo "$service_info" | jq -r '.services[0].desiredCount')
    local running_count=$(echo "$service_info" | jq -r '.services[0].runningCount')
    local pending_count=$(echo "$service_info" | jq -r '.services[0].pendingCount')
    local task_definition=$(echo "$service_info" | jq -r '.services[0].taskDefinition' | grep -oE '[^/]+$')

    echo -e "\n${BLUE}=== ECS Service Status ===${NC}"
    echo "Cluster: $CLUSTER_NAME"
    echo "Service: $SERVICE_NAME"
    echo "Status: $(format_status "$status")"
    echo "Task Definition: $task_definition"
    echo -e "Tasks: ${GREEN}$running_count${NC} running / ${YELLOW}$pending_count${NC} pending / $desired_count desired"

    # Show recent events
    echo -e "\n${BLUE}Recent Events:${NC}"
    echo "$service_info" | jq -r '.services[0].events[0:5][] |
        "\(.createdAt | strftime("%Y-%m-%d %H:%M:%S")) - \(.message)"' |
        while IFS= read -r line; do
            echo "  $line"
        done
}

# Function to display task details
show_tasks() {
    echo -e "\n${BLUE}=== ECS Tasks ===${NC}"

    local tasks=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --output json | jq -r '.taskArns[]')

    if [[ -z "$tasks" ]]; then
        echo "No running tasks found"
        return
    fi

    local task_details=$(aws ecs describe-tasks \
        --cluster "$CLUSTER_NAME" \
        --tasks $tasks \
        --region "$AWS_REGION" \
        --output json)

    echo "$task_details" | jq -r '.tasks[] |
        "Task: \(.taskArn | split("/") | last)
        Status: \(.lastStatus)
        Health: \(.healthStatus // "N/A")
        CPU: \(.cpu) / Memory: \(.memory)
        Started: \(.startedAt // "N/A")
        Container Status: \(.containers[0].lastStatus)
        "' | while IFS= read -r line; do
            echo "  $line"
        done
}

# Function to show logs
show_logs() {
    echo -e "\n${BLUE}=== Recent Logs ===${NC}"

    # Get recent log streams
    local streams=$(aws logs describe-log-streams \
        --log-group-name "$LOG_GROUP" \
        --order-by LastEventTime \
        --descending \
        --max-items 1 \
        --region "$AWS_REGION" \
        --output json 2>/dev/null | jq -r '.logStreams[0].logStreamName // empty')

    if [[ -z "$streams" ]]; then
        echo "No log streams found"
        return
    fi

    # Get recent log events
    aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-names "$streams" \
        --max-items 20 \
        --region "$AWS_REGION" \
        --output json | jq -r '.events[] |
        "\(.timestamp | ./1000 | strftime("%Y-%m-%d %H:%M:%S")) \(.message)"' |
        while IFS= read -r line; do
            echo "$line"
        done
}

# Function to show metrics
show_metrics() {
    echo -e "\n${BLUE}=== CloudWatch Metrics (Last Hour) ===${NC}"

    local end_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    local start_time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)

    # CPU Utilization
    local cpu_stats=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name CPUUtilization \
        --dimensions Name=ServiceName,Value="$SERVICE_NAME" Name=ClusterName,Value="$CLUSTER_NAME" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 300 \
        --statistics Average,Maximum \
        --region "$AWS_REGION" \
        --output json)

    echo -e "\nCPU Utilization:"
    echo "$cpu_stats" | jq -r '.Datapoints | sort_by(.Timestamp) | .[-5:][] |
        "  \(.Timestamp | strftime("%H:%M")) - Avg: \(.Average | tostring | .[0:5])% Max: \(.Maximum | tostring | .[0:5])%"'

    # Memory Utilization
    local memory_stats=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name MemoryUtilization \
        --dimensions Name=ServiceName,Value="$SERVICE_NAME" Name=ClusterName,Value="$CLUSTER_NAME" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 300 \
        --statistics Average,Maximum \
        --region "$AWS_REGION" \
        --output json)

    echo -e "\nMemory Utilization:"
    echo "$memory_stats" | jq -r '.Datapoints | sort_by(.Timestamp) | .[-5:][] |
        "  \(.Timestamp | strftime("%H:%M")) - Avg: \(.Average | tostring | .[0:5])% Max: \(.Maximum | tostring | .[0:5])%"'
}

# Format status with color
format_status() {
    case $1 in
        ACTIVE)
            echo -e "${GREEN}$1${NC}"
            ;;
        DRAINING|PROVISIONING)
            echo -e "${YELLOW}$1${NC}"
            ;;
        INACTIVE)
            echo -e "${RED}$1${NC}"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

# Main monitoring function
monitor() {
    clear
    echo -e "${BLUE}ECS Monitor - ${ENVIRONMENT} Environment${NC}"
    echo "Time: $(date)"
    echo "Region: $AWS_REGION"

    show_service_status

    if [[ "$SHOW_TASKS" == "true" ]]; then
        show_tasks
    fi

    if [[ "$SHOW_LOGS" == "true" ]]; then
        show_logs
    fi

    if [[ "$SHOW_METRICS" == "true" ]]; then
        show_metrics
    fi
}

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Main execution
if [[ "$WATCH_MODE" == "true" ]]; then
    log_info "Starting watch mode (refresh every ${REFRESH_INTERVAL}s, press Ctrl+C to exit)"
    while true; do
        monitor
        sleep "$REFRESH_INTERVAL"
    done
else
    monitor
fi
