terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Backend configuration should be provided via backend config file or CLI flags
    # Example: terraform init -backend-config=backend.conf
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = {
    Project     = "entropy-playground"
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "https://github.com/datablogin/entropy-playground"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name     = var.project_name
  environment      = var.environment
  vpc_cidr         = var.vpc_cidr
  azs              = var.availability_zones
  private_subnets  = var.private_subnets
  public_subnets   = var.public_subnets
  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = var.single_nat_gateway
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  s3_bucket_arns = [module.s3.artifacts_bucket_arn, module.s3.logs_bucket_arn]
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

# EC2 Module for Agent Instances (optional - use either EC2 or ECS/Fargate)
module "ec2_agents" {
  source = "./modules/ec2"
  count  = var.use_fargate ? 0 : 1

  project_name          = var.project_name
  environment           = var.environment
  instance_type         = var.agent_instance_type
  instance_count        = var.agent_instance_count
  ami_id                = var.agent_ami_id
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  security_group_ids    = [module.vpc.agent_security_group_id]
  iam_instance_profile  = module.iam.agent_instance_profile_name
  user_data_script      = file("${path.module}/scripts/agent-init.sh")

  root_volume_size      = var.agent_root_volume_size
  root_volume_type      = var.agent_root_volume_type

  tags = {
    Role = "agent"
  }
}

# ECS/Fargate Module for Agent Containers (optional - use either EC2 or ECS/Fargate)
module "ecs" {
  source = "./modules/ecs"
  count  = var.use_fargate ? 1 : 0

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  vpc_id       = module.vpc.vpc_id

  # Networking
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.agent_security_group_id]

  # Container configuration
  agent_image   = var.agent_container_image
  task_cpu      = var.agent_task_cpu
  task_memory   = var.agent_task_memory
  desired_count = var.agent_desired_count

  # IAM roles
  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  # Configuration
  log_level = var.log_level
  redis_url = var.redis_url != "" ? var.redis_url : "redis://${module.elasticache[0].primary_endpoint}:6379"

  # Secrets from Parameter Store
  secrets_from_parameter_store = var.ecs_secrets

  # Optional features
  enable_health_check      = var.enable_ecs_health_check
  enable_load_balancer     = var.enable_ecs_load_balancer
  enable_service_discovery = var.enable_ecs_service_discovery
  enable_autoscaling       = var.enable_ecs_autoscaling

  # Load balancer configuration (if enabled)
  alb_subnet_ids         = var.enable_ecs_load_balancer ? module.vpc.public_subnet_ids : []
  alb_security_group_ids = var.enable_ecs_load_balancer ? [module.vpc.alb_security_group_id] : []

  # Auto-scaling configuration (if enabled)
  min_capacity        = var.ecs_min_capacity
  max_capacity        = var.ecs_max_capacity
  cpu_target_value    = var.ecs_cpu_target
  memory_target_value = var.ecs_memory_target

  tags = local.common_tags
}

# ElastiCache Redis Module (optional)
module "elasticache" {
  source = "./modules/elasticache"
  count  = var.enable_redis ? 1 : 0

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.redis_security_group_id]

  node_type          = var.redis_node_type
  num_cache_nodes    = var.redis_num_nodes
  engine_version     = var.redis_engine_version

  tags = local.common_tags
}
