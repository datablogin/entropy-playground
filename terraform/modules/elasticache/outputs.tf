output "cluster_id" {
  description = "The cluster ID"
  value       = aws_elasticache_cluster.main.id
}

output "cache_nodes" {
  description = "List of node objects"
  value       = aws_elasticache_cluster.main.cache_nodes
}

output "primary_endpoint" {
  description = "The primary endpoint address"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  description = "The port number"
  value       = aws_elasticache_cluster.main.port
}

output "configuration_endpoint" {
  description = "The configuration endpoint"
  value       = aws_elasticache_cluster.main.configuration_endpoint
}
