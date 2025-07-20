variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "The deployment environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the cache will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the cache subnet group"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for the cache cluster"
  type        = list(string)
}

variable "node_type" {
  description = "The compute and memory capacity of the nodes"
  type        = string
  default     = "cache.t3.micro"
}

variable "num_cache_nodes" {
  description = "The number of cache nodes"
  type        = number
  default     = 1
}

variable "engine_version" {
  description = "Version of Redis to use"
  type        = string
  default     = "7.0"
}

variable "snapshot_retention_limit" {
  description = "Number of days to retain snapshots"
  type        = number
  default     = 5
}

variable "snapshot_window" {
  description = "Daily time range for snapshots"
  type        = string
  default     = "03:00-05:00"
}

variable "maintenance_window" {
  description = "Weekly time range for maintenance"
  type        = string
  default     = "sun:05:00-sun:07:00"
}

variable "notification_topic_arn" {
  description = "ARN of SNS topic for notifications"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
