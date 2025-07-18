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

# EC2 Outputs
output "agent_instance_ids" {
  description = "IDs of agent EC2 instances"
  value       = module.ec2_agents.instance_ids
}

output "agent_private_ips" {
  description = "Private IP addresses of agent instances"
  value       = module.ec2_agents.private_ips
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
