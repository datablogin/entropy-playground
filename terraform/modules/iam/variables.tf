variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "s3_bucket_arns" {
  description = "ARNs of S3 buckets that agents need access to"
  type        = list(string)
}