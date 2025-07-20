output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ids" {
  description = "IDs of NAT gateways"
  value       = aws_nat_gateway.main[*].id
}

output "agent_security_group_id" {
  description = "ID of the security group for agents"
  value       = aws_security_group.agent.id
}

output "alb_security_group_id" {
  description = "ID of the security group for Application Load Balancer"
  value       = aws_security_group.alb.id
}

output "redis_security_group_id" {
  description = "ID of the security group for Redis"
  value       = aws_security_group.redis.id
}

output "s3_endpoint_id" {
  description = "ID of the S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.id
}
