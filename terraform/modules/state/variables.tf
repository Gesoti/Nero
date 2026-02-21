variable "project_name" {
  description = "Name prefix for the state bucket"
  type        = string
  default     = "waterlevels"
}

variable "aws_account_id" {
  description = "AWS account ID (used to make bucket name unique)"
  type        = string
}
