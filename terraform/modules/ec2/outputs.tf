output "instance_ids" {
  description = "IDs of created EC2 instances"
  value       = aws_instance.agent[*].id
}

output "private_ips" {
  description = "Private IP addresses of instances"
  value       = aws_instance.agent[*].private_ip
}

output "public_ips" {
  description = "Public IP addresses of instances"
  value       = aws_instance.agent[*].public_ip
}

output "instance_arns" {
  description = "ARNs of created EC2 instances"
  value       = aws_instance.agent[*].arn
}
