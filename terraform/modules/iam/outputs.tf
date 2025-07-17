output "agent_role_arn" {
  description = "ARN of the IAM role for agents"
  value       = aws_iam_role.agent.arn
}

output "agent_role_name" {
  description = "Name of the IAM role for agents"
  value       = aws_iam_role.agent.name
}

output "agent_instance_profile_name" {
  description = "Name of the IAM instance profile for agents"
  value       = aws_iam_instance_profile.agent.name
}

output "agent_instance_profile_arn" {
  description = "ARN of the IAM instance profile for agents"
  value       = aws_iam_instance_profile.agent.arn
}
