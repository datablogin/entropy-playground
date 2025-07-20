# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

# EC2 Outputs (when using EC2)
output "agent_instance_ids" {
  description = "IDs of agent EC2 instances"
  value       = var.use_fargate ? [] : module.ec2_agents[0].instance_ids
}

output "agent_private_ips" {
  description = "Private IP addresses of agent instances"
  value       = var.use_fargate ? [] : module.ec2_agents[0].private_ips
}

# ECS Outputs (when using Fargate)
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = var.use_fargate ? module.ecs[0].cluster_name : null
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = var.use_fargate ? module.ecs[0].cluster_arn : null
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = var.use_fargate ? module.ecs[0].service_name : null
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = var.use_fargate ? module.ecs[0].task_definition_arn : null
}

output "ecs_log_group_name" {
  description = "CloudWatch log group for ECS tasks"
  value       = var.use_fargate ? module.ecs[0].log_group_name : null
}

output "ecs_alb_dns_name" {
  description = "DNS name of the ECS Application Load Balancer"
  value       = var.use_fargate && var.enable_ecs_load_balancer ? module.ecs[0].alb_dns_name : null
}

# ElastiCache Outputs (when enabled)
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = var.enable_redis ? module.elasticache[0].primary_endpoint : null
}

output "redis_port" {
  description = "Redis port"
  value       = var.enable_redis ? module.elasticache[0].port : null
}

# S3 Outputs
output "artifacts_bucket_name" {
  description = "Name of the S3 bucket for artifacts"
  value       = module.s3.artifacts_bucket_name
}

output "logs_bucket_name" {
  description = "Name of the S3 bucket for logs"
  value       = module.s3.logs_bucket_name
}

output "artifacts_bucket_arn" {
  description = "ARN of the S3 bucket for artifacts"
  value       = module.s3.artifacts_bucket_arn
}

output "logs_bucket_arn" {
  description = "ARN of the S3 bucket for logs"
  value       = module.s3.logs_bucket_arn
}

# IAM Outputs
output "agent_role_arn" {
  description = "ARN of the IAM role for agents"
  value       = module.iam.agent_role_arn
}

output "agent_instance_profile_name" {
  description = "Name of the IAM instance profile for agents"
  value       = module.iam.agent_instance_profile_name
}
