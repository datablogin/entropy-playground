# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-cache-subnet"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-cache-subnet"
  })
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis${split(".", var.engine_version)[0]}"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-redis-params"
  })
}

# ElastiCache Redis Cluster
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine               = "redis"
  node_type            = var.node_type
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.main.name
  engine_version       = var.engine_version
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = var.security_group_ids

  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window         = var.snapshot_window
  maintenance_window      = var.maintenance_window

  notification_topic_arn = var.notification_topic_arn

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-redis"
  })
}
