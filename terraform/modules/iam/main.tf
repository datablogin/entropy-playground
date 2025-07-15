# IAM Role for Agent Instances
resource "aws_iam_role" "agent" {
  name = "${var.project_name}-${var.environment}-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-agent-role"
  }
}

# IAM Policy for Agent S3 Access
resource "aws_iam_policy" "agent_s3" {
  name        = "${var.project_name}-${var.environment}-agent-s3-policy"
  description = "Policy for agent S3 access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = concat(
          var.s3_bucket_arns,
          [for arn in var.s3_bucket_arns : "${arn}/*"]
        )
      }
    ]
  })
}

# IAM Policy for CloudWatch Logs
resource "aws_iam_policy" "agent_cloudwatch" {
  name        = "${var.project_name}-${var.environment}-agent-cloudwatch-policy"
  description = "Policy for agent CloudWatch access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/${var.project_name}-${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "${var.project_name}/${var.environment}"
          }
        }
      }
    ]
  })
}

# IAM Policy for SSM Parameter Store (for secrets)
resource "aws_iam_policy" "agent_ssm" {
  name        = "${var.project_name}-${var.environment}-agent-ssm-policy"
  description = "Policy for agent SSM Parameter Store access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${data.aws_region.current.name}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# IAM Policy for ECR (Docker image registry)
resource "aws_iam_policy" "agent_ecr" {
  name        = "${var.project_name}-${var.environment}-agent-ecr-policy"
  description = "Policy for agent ECR access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "agent_s3" {
  role       = aws_iam_role.agent.name
  policy_arn = aws_iam_policy.agent_s3.arn
}

resource "aws_iam_role_policy_attachment" "agent_cloudwatch" {
  role       = aws_iam_role.agent.name
  policy_arn = aws_iam_policy.agent_cloudwatch.arn
}

resource "aws_iam_role_policy_attachment" "agent_ssm" {
  role       = aws_iam_role.agent.name
  policy_arn = aws_iam_policy.agent_ssm.arn
}

resource "aws_iam_role_policy_attachment" "agent_ecr" {
  role       = aws_iam_role.agent.name
  policy_arn = aws_iam_policy.agent_ecr.arn
}

# Attach AWS managed policies
resource "aws_iam_role_policy_attachment" "agent_ssm_managed" {
  role       = aws_iam_role.agent.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance Profile for EC2
resource "aws_iam_instance_profile" "agent" {
  name = "${var.project_name}-${var.environment}-agent-profile"
  role = aws_iam_role.agent.name
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}