# Data source for latest Amazon Linux 2023 AMI if not specified
data "aws_ami" "amazon_linux_2023" {
  count = var.ami_id == "" ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# EC2 Instances
resource "aws_instance" "agent" {
  count = var.instance_count

  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2023[0].id
  instance_type          = var.instance_type
  subnet_id              = element(var.subnet_ids, count.index)
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile   = var.iam_instance_profile

  root_block_device {
    volume_type = var.root_volume_type
    volume_size = var.root_volume_size
    encrypted   = true

    tags = merge(
      var.tags,
      {
        Name = "${var.project_name}-${var.environment}-agent-${count.index + 1}-root"
      }
    )
  }

  user_data = var.user_data_script

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2
    http_put_response_hop_limit = 1
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-agent-${count.index + 1}"
      Type = "agent"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# CloudWatch monitoring for instances
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count = var.instance_count

  alarm_name          = "${var.project_name}-${var.environment}-agent-${count.index + 1}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors CPU utilization"

  dimensions = {
    InstanceId = aws_instance.agent[count.index].id
  }

  tags = var.tags
}

# CloudWatch monitoring for disk usage
resource "aws_cloudwatch_metric_alarm" "high_disk" {
  count = var.instance_count

  alarm_name          = "${var.project_name}-${var.environment}-agent-${count.index + 1}-high-disk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "disk_used_percent"
  namespace           = "CWAgent"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors disk utilization"

  dimensions = {
    InstanceId = aws_instance.agent[count.index].id
    path       = "/"
    device     = "xvda1"
    fstype     = "xfs"
  }

  tags = var.tags
}
