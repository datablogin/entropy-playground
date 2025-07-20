# ECS/Fargate Deployment Guide

This guide explains how to deploy the Entropy-Playground agents using AWS ECS with Fargate.

## Overview

The ECS/Fargate deployment provides a serverless container orchestration solution that:
- Automatically manages infrastructure
- Scales based on demand
- Provides zero-downtime deployments
- Integrates with AWS services

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   ECS Cluster   │     │  ElastiCache    │
│                 │     │     Redis       │
│  ┌───────────┐  │     └────────┬────────┘
│  │   Task    │  │              │
│  │  (Agent)  ├──┼──────────────┘
│  └───────────┘  │
│                 │     ┌─────────────────┐
│  ┌───────────┐  │     │  CloudWatch     │
│  │   Task    │  ├─────┤     Logs        │
│  │  (Agent)  │  │     └─────────────────┘
│  └───────────┘  │
└─────────────────┘
```

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Docker image pushed to ECR
3. Terraform >= 1.5.0
4. GitHub token stored in AWS Parameter Store

## Quick Start

### 1. Prepare Your Container Image

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t entropy-playground .
docker tag entropy-playground:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/entropy-playground:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/entropy-playground:latest
```

### 2. Store Secrets in Parameter Store

```bash
# Store GitHub token
aws ssm put-parameter \
  --name "/entropy-playground/dev/github-token" \
  --value "ghp_YOUR_TOKEN" \
  --type "SecureString" \
  --description "GitHub token for Entropy-Playground dev"
```

### 3. Configure Terraform Variables

Copy the example file and update values:
```bash
cp environments/dev/terraform.tfvars.ecs.example environments/dev/terraform.tfvars
# Edit the file with your values
```

### 4. Deploy Infrastructure

```bash
# Initialize Terraform
make init

# Plan deployment
make plan-dev

# Apply changes
make apply-dev
```

## Deployment Operations

### Deploy New Version

```bash
# Deploy specific version
make deploy-ecs ENV=dev TAG=v1.0.0

# Or use the script directly
./scripts/ecs/deploy.sh -e dev -t v1.0.0 -w
```

### Rollback to Previous Version

```bash
# Interactive rollback
make rollback-ecs ENV=dev

# Or specify version
./scripts/ecs/rollback.sh -e dev -v 42 -w
```

### Monitor Services

```bash
# Real-time monitoring
make monitor-ecs ENV=dev

# One-time check
./scripts/ecs/monitor.sh -e dev -t -l -m
```

## Configuration Options

### Container Resources

```hcl
# CPU and Memory combinations for Fargate
# CPU: 256, 512, 1024, 2048, 4096
# Memory: Based on CPU selection

agent_task_cpu    = "512"   # 0.5 vCPU
agent_task_memory = "1024"  # 1 GB RAM
```

### Auto-scaling

```hcl
enable_ecs_autoscaling = true
ecs_min_capacity       = 1
ecs_max_capacity       = 10
ecs_cpu_target         = 70    # Scale up at 70% CPU
ecs_memory_target      = 80    # Scale up at 80% memory
```

### Load Balancer (Optional)

```hcl
enable_ecs_load_balancer = true
# Requires additional ALB configuration
```

### Service Discovery

```hcl
enable_ecs_service_discovery = true
# Creates private DNS: agent.entropy-playground-dev.local
```

## Cost Optimization

1. **Use Fargate Spot** for non-critical workloads (up to 70% savings)
2. **Right-size containers** - Monitor actual usage and adjust
3. **Use auto-scaling** to match demand
4. **Set log retention** appropriately
5. **Consider Reserved Capacity** for predictable workloads

## Monitoring and Logging

### CloudWatch Logs

Logs are automatically sent to CloudWatch:
- Log Group: `/ecs/entropy-playground-{env}/agent`
- Log retention: 7 days (configurable)

### CloudWatch Metrics

Available metrics:
- CPU Utilization
- Memory Utilization
- Task Count
- Service Health

### Alarms (Optional)

```bash
# Create CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "ecs-high-cpu" \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## Troubleshooting

### Common Issues

1. **Tasks failing to start**
   - Check CloudWatch logs
   - Verify IAM roles have correct permissions
   - Ensure container image exists in ECR

2. **Out of memory errors**
   - Increase task memory
   - Check for memory leaks
   - Enable memory auto-scaling

3. **Cannot pull image**
   - Verify ECR permissions
   - Check VPC endpoints
   - Ensure task execution role has ECR access

### Debug Commands

```bash
# List tasks
aws ecs list-tasks --cluster entropy-playground-dev-cluster

# Describe task
aws ecs describe-tasks \
  --cluster entropy-playground-dev-cluster \
  --tasks arn:aws:ecs:...

# View logs
aws logs tail /ecs/entropy-playground-dev/agent --follow
```

## Security Best Practices

1. **Use Parameter Store** for secrets
2. **Enable VPC Flow Logs** for network monitoring
3. **Use private subnets** for tasks
4. **Enable Container Insights** for detailed monitoring
5. **Regularly update base images**
6. **Scan images for vulnerabilities**

## Migration from EC2

To migrate from EC2 to Fargate:

1. Set `use_fargate = true` in terraform.tfvars
2. Configure container image URL
3. Run `terraform plan` to see changes
4. Apply changes with `terraform apply`

The Terraform configuration supports both EC2 and Fargate deployments.