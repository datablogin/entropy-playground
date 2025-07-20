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

output "ecs_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_execution_role_name" {
  description = "Name of the ECS task execution role"
  value       = aws_iam_role.ecs_execution.name
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_task_role_name" {
  description = "Name of the ECS task role"
  value       = aws_iam_role.ecs_task.name
}
