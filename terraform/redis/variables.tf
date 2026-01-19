variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "hyperscale"
}

variable "vpc_id" {
  description = "VPC ID where Redis will be created"
  type        = string
}

variable "cache_subnet_group_name" {
  description = "ElastiCache subnet group name"
  type        = string
}

variable "eks_security_group_id" {
  description = "EKS security group ID for Redis access"
  type        = string
}

variable "redis_node_type" {
  description = "Node type for Redis"
  type        = string
  default     = "cache.r7g.large"
}

variable "redis_num_shards" {
  description = "Number of shards (node groups) for Redis cluster"
  type        = number
  default     = 3
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "HyperScale"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
