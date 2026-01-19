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

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "cluster_endpoint" {
  description = "EKS cluster endpoint"
  type        = string
}

variable "cluster_ca_data" {
  description = "EKS cluster certificate authority data"
  type        = string
  sensitive   = true
}

variable "cluster_id" {
  description = "EKS cluster ID for dependency"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where EKS is deployed"
  type        = string
}

variable "alb_controller_role_arn" {
  description = "IAM role ARN for AWS Load Balancer Controller"
  type        = string
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
