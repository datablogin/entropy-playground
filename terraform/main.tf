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

# EC2 Module for Agent Instances
module "ec2_agents" {
  source = "./modules/ec2"

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