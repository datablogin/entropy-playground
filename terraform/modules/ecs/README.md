# ECS/Fargate Module

This module creates and manages ECS clusters and services running on AWS Fargate.

## Features

- ECS Cluster with Container Insights enabled
- Fargate task definitions with customizable resources
- ECS services with deployment circuit breaker
- Optional Application Load Balancer integration
- Optional Service Discovery via AWS Cloud Map
- Auto-scaling policies based on CPU and memory metrics
- CloudWatch logging
- Zero-downtime deployments

## Usage

```hcl
module "ecs" {
  source = "./modules/ecs"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  vpc_id       = module.vpc.vpc_id

  # Networking
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.ecs_security_group_id]

  # Container configuration
  agent_image  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/entropy-playground:latest"
  task_cpu     = "512"
  task_memory  = "1024"
  desired_count = 2

  # IAM roles
  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  # Configuration
  log_level = "INFO"
  redis_url = "redis://redis.example.com:6379"

  # Secrets from Parameter Store
  secrets_from_parameter_store = [
    {
      name      = "GITHUB_TOKEN"
      valueFrom = "arn:aws:ssm:us-east-1:123456789012:parameter/entropy-playground/github-token"
    }
  ]

  # Optional features
  enable_health_check      = true
  enable_load_balancer     = true
  enable_service_discovery = true
  enable_autoscaling       = true

  # Load balancer configuration (if enabled)
  alb_subnet_ids         = module.vpc.public_subnet_ids
  alb_security_group_ids = [module.vpc.alb_security_group_id]

  # Auto-scaling configuration (if enabled)
  min_capacity        = 1
  max_capacity        = 10
  cpu_target_value    = 70
  memory_target_value = 80

  tags = var.tags
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | The name of the project | string | - | yes |
| environment | The deployment environment | string | - | yes |
| aws_region | AWS region | string | - | yes |
| vpc_id | VPC ID where resources will be created | string | - | yes |
| subnet_ids | List of subnet IDs for ECS tasks | list(string) | - | yes |
| security_group_ids | List of security group IDs for ECS tasks | list(string) | - | yes |
| agent_image | Docker image for the agent container | string | - | yes |
| task_cpu | CPU units for the task | string | "512" | no |
| task_memory | Memory for the task in MB | string | "1024" | no |
| desired_count | Desired number of tasks | number | 1 | no |
| execution_role_arn | ARN of the ECS task execution role | string | - | yes |
| task_role_arn | ARN of the ECS task role | string | - | yes |
| log_level | Log level for the application | string | "INFO" | no |
| redis_url | Redis connection URL | string | - | yes |
| log_retention_days | Number of days to retain logs | number | 7 | no |
| enable_health_check | Enable container health check | bool | false | no |
| enable_load_balancer | Enable Application Load Balancer | bool | false | no |
| enable_service_discovery | Enable AWS Service Discovery | bool | false | no |
| enable_autoscaling | Enable auto-scaling | bool | false | no |
| min_capacity | Minimum number of tasks for auto-scaling | number | 1 | no |
| max_capacity | Maximum number of tasks for auto-scaling | number | 10 | no |
| cpu_target_value | Target CPU utilization percentage | number | 70 | no |
| memory_target_value | Target memory utilization percentage | number | 70 | no |

## Outputs

| Name | Description |
|------|-------------|
| cluster_id | The ID of the ECS cluster |
| cluster_arn | The ARN of the ECS cluster |
| cluster_name | The name of the ECS cluster |
| service_id | The ID of the ECS service |
| service_name | The name of the ECS service |
| task_definition_arn | The ARN of the task definition |
| log_group_name | The name of the CloudWatch log group |
| alb_dns_name | The DNS name of the load balancer (if enabled) |

## Deployment Scripts

The module includes helper scripts in the `scripts/ecs/` directory:

### deploy.sh

Deploys new versions of the application to ECS:

```bash
./scripts/ecs/deploy.sh -e prod -t v1.0.0 -w
```

### rollback.sh

Rolls back to a previous task definition revision:

```bash
./scripts/ecs/rollback.sh -e prod -v 42 -w
```

### monitor.sh

Monitors ECS services and tasks:

```bash
./scripts/ecs/monitor.sh -e prod -t -l -m -w
```

## IAM Requirements

The ECS tasks require two IAM roles:

### Execution Role

The execution role needs permissions to:

- Pull images from ECR
- Create CloudWatch log streams
- Read secrets from Parameter Store/Secrets Manager

### Task Role

The task role needs permissions based on your application requirements:

- Access to S3 buckets
- Access to other AWS services
- GitHub API access (if stored in Parameter Store)

## Security Considerations

- Tasks run in private subnets by default
- Use Parameter Store or Secrets Manager for sensitive data
- Enable VPC endpoints for AWS services to avoid internet traffic
- Use security groups to restrict network access
- Enable Container Insights for monitoring

## Cost Optimization

- Use Fargate Spot for non-critical workloads
- Set appropriate CPU/memory limits
- Enable auto-scaling to match demand
- Use CloudWatch Logs retention policies
- Consider using Application Load Balancer only when necessary
