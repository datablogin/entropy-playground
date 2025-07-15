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

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}