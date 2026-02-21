variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
}
