variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  type        = string
}

variable "key_pair_name" {
  description = "EC2 key pair name for SSH"
  type        = string
}

variable "domain_name" {
  description = "Domain name for Nginx and Certbot"
  type        = string
}

variable "app_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "alert_email" {
  description = "Email for CloudWatch alarm (empty to skip SNS)"
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Subnet ID to launch the instance in"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID for the instance"
  type        = string
}
