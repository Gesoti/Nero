# LocalStack-targeted Terraform config.
# Uses the same modules as production but with local backend and LocalStack endpoints.

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "aws" {
  access_key = "test"
  secret_key = "test"
  region     = var.aws_region

  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2        = "http://localhost:4566"
    s3         = "http://localhost:4566"
    iam        = "http://localhost:4566"
    sts        = "http://localhost:4566"
    cloudwatch = "http://localhost:4566"
    sns        = "http://localhost:4566"
  }

  default_tags {
    tags = {
      Project     = var.project_name
      ManagedBy   = "terraform"
      Environment = "local"
    }
  }
}

module "networking" {
  source = "../modules/networking"

  project_name     = var.project_name
  ssh_allowed_cidr = var.ssh_allowed_cidr
}

module "compute" {
  source = "../modules/compute"

  project_name      = var.project_name
  instance_type     = var.instance_type
  ami_id            = var.ami_id
  key_pair_name     = var.key_pair_name
  domain_name       = var.domain_name
  app_image         = var.app_image
  alert_email       = var.alert_email
  subnet_id         = module.networking.subnet_id
  security_group_id = module.networking.security_group_id
}
