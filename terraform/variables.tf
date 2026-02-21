variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-1"
}

variable "instance_type" {
  description = "EC2 instance type (t2.micro for free tier)"
  type        = string
  default     = "t2.micro"
}

variable "ami_id" {
  description = "Ubuntu 24.04 LTS AMI ID for the chosen region"
  type        = string
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the site (e.g. water.example.com)"
  type        = string
}

variable "app_image" {
  description = "Docker image to deploy (e.g. username/waterlevels:latest)"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance (e.g. your IP/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "waterlevels"
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications (optional)"
  type        = string
  default     = ""
}
