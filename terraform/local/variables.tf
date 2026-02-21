# Same variables as production — re-declared for the local workspace.
# Defaults are set for LocalStack (dummy values where needed).

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "ami_id" {
  type    = string
  default = "ami-00000000000000000"
}

variable "key_pair_name" {
  type    = string
  default = "local-dev"
}

variable "domain_name" {
  type    = string
  default = "localhost"
}

variable "app_image" {
  type    = string
  default = "waterlevels:local"
}

variable "ssh_allowed_cidr" {
  type    = string
  default = "0.0.0.0/0"
}

variable "project_name" {
  type    = string
  default = "waterlevels-local"
}

variable "alert_email" {
  type    = string
  default = ""
}
