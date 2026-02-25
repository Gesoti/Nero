variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-south-2"
  # eu-south-2 (Spain) quirks:
  #   - No t2.micro — use t3.micro (also free-tier eligible)
  #   - t3 instances use NVMe device names (/dev/nvme*n1), not /dev/xvdf
  #     — user_data scripts must auto-detect the device path
}

variable "instance_type" {
  description = "EC2 instance type — t3.micro required for eu-south-2 (no t2 family)"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "Ubuntu 24.04 LTS AMI ID for the chosen region"
  type        = string
  # Ubuntu 24.04 removed awscli from apt — install AWS CLI v2 via the
  # official zip installer in user_data, not apt or snap.
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the site"
  type        = string
  default     = "nero.cy"
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance (e.g. your IP/32)"
  type        = string
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
