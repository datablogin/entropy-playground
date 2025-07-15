# Entropy-Playground AWS Infrastructure

This directory contains Terraform configurations for provisioning AWS infrastructure for the Entropy-Playground agent framework.

## Architecture Overview

The infrastructure consists of:

- **VPC**: Isolated network with public and private subnets across multiple availability zones
- **EC2 Instances**: Agent nodes running in private subnets
- **IAM Roles**: Least-privilege roles for agent operations
- **S3 Buckets**: Separate buckets for artifacts and logs with lifecycle policies
- **Security Groups**: Restrictive security groups allowing only necessary traffic

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.5.0
3. **AWS CLI** configured with credentials
4. **S3 Bucket** for Terraform state (optional but recommended)

## Directory Structure

```
terraform/
├── main.tf                 # Main Terraform configuration
├── variables.tf            # Variable definitions
├── outputs.tf              # Output definitions
├── modules/                # Reusable Terraform modules
│   ├── ec2/                # EC2 instance configuration
│   ├── vpc/                # VPC and networking
│   ├── iam/                # IAM roles and policies
│   └── s3/                 # S3 buckets
├── environments/           # Environment-specific configurations
│   ├── dev/                # Development environment
│   └── prod/               # Production environment
└── scripts/                # Helper scripts
    └── agent-init.sh       # EC2 user data script
```

## Quick Start

### 1. Configure Backend (Recommended)

Create a backend configuration file:

```hcl
# backend.conf
bucket         = "your-terraform-state-bucket"
key            = "entropy-playground/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-state-lock"
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init -backend-config=backend.conf
```

### 3. Create Environment Configuration

Copy and modify the example configuration:

```bash
cp environments/dev/terraform.tfvars.example environments/dev/terraform.tfvars
# Edit terraform.tfvars with your settings
```

### 4. Plan and Apply

```bash
# For development environment
terraform plan -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars

# For production environment
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

## Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `environment` | Environment name (dev, prod) | Required |
| `aws_region` | AWS region | us-east-1 |
| `vpc_cidr` | CIDR block for VPC | 10.0.0.0/16 |
| `agent_instance_type` | EC2 instance type for agents | t3.medium |
| `agent_instance_count` | Number of agent instances | 2 |

See `variables.tf` for complete list.

## Cost Optimization

### Development Environment
- Single NAT Gateway to reduce costs
- Smaller instance types (t3.small)
- Shorter S3 lifecycle policies
- Auto-shutdown tags for non-business hours

### Production Environment
- NAT Gateway per AZ for high availability
- Larger instance types for better performance
- Standard S3 lifecycle policies
- No auto-shutdown

## Security Considerations

1. **Network Security**:
   - Agents run in private subnets
   - No direct internet access (egress through NAT)
   - Security groups restrict traffic

2. **IAM Security**:
   - Least-privilege policies
   - No hardcoded credentials
   - Instance profiles for EC2

3. **Data Security**:
   - S3 buckets encrypted at rest
   - Public access blocked
   - Versioning enabled for artifacts

4. **Instance Security**:
   - IMDSv2 enforced
   - EBS volumes encrypted
   - SSM Session Manager for access

## Monitoring

The infrastructure includes:

- CloudWatch alarms for CPU and disk usage
- CloudWatch Logs for agent and system logs
- Cost allocation tags for tracking expenses

## Maintenance

### Updating Infrastructure

```bash
# Always plan before applying
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply changes
terraform apply -var-file=environments/dev/terraform.tfvars
```

### Destroying Infrastructure

```bash
# WARNING: This will delete all resources
terraform destroy -var-file=environments/dev/terraform.tfvars
```

### State Management

- State is stored in S3 with versioning
- State locking via DynamoDB
- Regular state backups recommended

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure AWS credentials have necessary permissions
2. **Resource Limits**: Check AWS service quotas
3. **State Lock**: Use `terraform force-unlock` if needed

### Debug Commands

```bash
# Show current state
terraform show

# List resources
terraform state list

# Validate configuration
terraform validate

# Format configuration
terraform fmt -recursive
```

## Cost Estimation

Approximate monthly costs (us-east-1):

- **Development**: ~$50-100
  - 1 x t3.small EC2
  - 1 x NAT Gateway
  - S3 storage

- **Production**: ~$300-500
  - 3 x t3.large EC2
  - 3 x NAT Gateways
  - S3 storage with replication

## Next Steps

1. Review and customize the configuration for your needs
2. Set up monitoring and alerting
3. Configure backup strategies
4. Implement auto-scaling if needed
5. Set up CI/CD for infrastructure changes