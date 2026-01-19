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
  description = "VPC ID where MSK will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for MSK brokers"
  type        = list(string)
}

variable "eks_security_group_id" {
  description = "EKS security group ID for Kafka access"
  type        = string
}

variable "kafka_instance_type" {
  description = "Instance type for Kafka brokers"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_volume_size" {
  description = "EBS volume size for Kafka brokers in GB"
  type        = number
  default     = 500
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
