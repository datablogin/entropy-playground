#!/bin/bash
# Agent initialization script

set -euo pipefail

# Update system
yum update -y

# Install dependencies
yum install -y \
    docker \
    git \
    jq \
    aws-cli \
    python3-pip

# Start Docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<EOF
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/aws/ec2/entropy-playground/system",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/home/ec2-user/agent/logs/*.log",
            "log_group_name": "/aws/ec2/entropy-playground/agent",
            "log_stream_name": "{instance_id}-{ip_address}"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "EntropyPlayground",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {
            "name": "cpu_usage_idle",
            "rename": "CPU_USAGE_IDLE",
            "unit": "Percent"
          },
          {
            "name": "cpu_usage_iowait",
            "rename": "CPU_USAGE_IOWAIT",
            "unit": "Percent"
          },
          "cpu_time_guest"
        ],
        "totalcpu": false,
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          {
            "name": "used_percent",
            "rename": "DISK_USED_PERCENT",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "MEM_USED_PERCENT",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Create agent directory structure
mkdir -p /home/ec2-user/agent/{logs,data,config}
chown -R ec2-user:ec2-user /home/ec2-user/agent

# Install Python dependencies for agents
pip3 install \
    boto3 \
    redis \
    pyyaml \
    structlog

# Signal completion
touch /tmp/agent-init-complete