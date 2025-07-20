variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "entropy-playground"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# VPC Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnets" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway for all private subnets"
  type        = bool
  default     = true
}

# EC2 Variables
variable "agent_instance_type" {
  description = "Instance type for agent nodes"
  type        = string
  default     = "t3.medium"
}

variable "agent_instance_count" {
  description = "Number of agent instances"
  type        = number
  default     = 2
}

variable "agent_ami_id" {
  description = "AMI ID for agent instances (defaults to latest Amazon Linux 2023)"
  type        = string
  default     = ""
}

variable "agent_root_volume_size" {
  description = "Root volume size in GB for agent instances"
  type        = number
  default     = 30
}

variable "agent_root_volume_type" {
  description = "Root volume type for agent instances"
  type        = string
  default     = "gp3"
}

# S3 Variables
variable "s3_force_destroy" {
  description = "Force destroy S3 buckets even if they contain objects"
  type        = bool
  default     = false
}

variable "s3_lifecycle_days" {
  description = "Number of days to retain objects in S3 before transitioning to cheaper storage"
  type        = number
  default     = 30
}

# ECS/Fargate Variables
variable "use_fargate" {
  description = "Use ECS/Fargate instead of EC2 instances"
  type        = bool
  default     = false
}

variable "agent_container_image" {
  description = "Docker image for the agent container"
  type        = string
  default     = ""
}

variable "agent_task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "512"
}

variable "agent_task_memory" {
  description = "Memory for ECS task in MB"
  type        = string
  default     = "1024"
}

variable "agent_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "redis_url" {
  description = "Redis connection URL (if not using ElastiCache)"
  type        = string
  default     = ""
}

variable "ecs_secrets" {
  description = "Secrets to inject from AWS Parameter Store"
  type = list(object({
    name      = string
    valueFrom = string
  }))
  default = []
}

variable "enable_ecs_health_check" {
  description = "Enable ECS container health check"
  type        = bool
  default     = true
}

variable "enable_ecs_load_balancer" {
  description = "Enable Application Load Balancer for ECS"
  type        = bool
  default     = false
}

variable "enable_ecs_service_discovery" {
  description = "Enable AWS Service Discovery for ECS"
  type        = bool
  default     = true
}

variable "enable_ecs_autoscaling" {
  description = "Enable auto-scaling for ECS service"
  type        = bool
  default     = true
}

variable "ecs_min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "ecs_cpu_target" {
  description = "Target CPU utilization for auto-scaling"
  type        = number
  default     = 70
}

variable "ecs_memory_target" {
  description = "Target memory utilization for auto-scaling"
  type        = number
  default     = 80
}

# Redis/ElastiCache Variables
variable "enable_redis" {
  description = "Enable ElastiCache Redis"
  type        = bool
  default     = true
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 1
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
