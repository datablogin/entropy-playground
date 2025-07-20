output "cluster_id" {
  description = "The ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "service_id" {
  description = "The ID of the ECS service"
  value       = aws_ecs_service.agent.id
}

output "service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.agent.name
}

output "task_definition_arn" {
  description = "The ARN of the task definition"
  value       = aws_ecs_task_definition.agent.arn
}

output "task_definition_family" {
  description = "The family of the task definition"
  value       = aws_ecs_task_definition.agent.family
}

output "log_group_name" {
  description = "The name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.agent.name
}

output "service_discovery_namespace_id" {
  description = "The ID of the service discovery namespace"
  value       = try(aws_service_discovery_private_dns_namespace.main[0].id, null)
}

output "service_discovery_service_arn" {
  description = "The ARN of the service discovery service"
  value       = try(aws_service_discovery_service.agent[0].arn, null)
}

output "alb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = try(aws_lb.main[0].dns_name, null)
}

output "alb_zone_id" {
  description = "The zone ID of the load balancer"
  value       = try(aws_lb.main[0].zone_id, null)
}

output "target_group_arn" {
  description = "The ARN of the target group"
  value       = try(aws_lb_target_group.agent[0].arn, null)
}