provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}

terraform {
  backend "s3" {
    # Configured via -backend-config or backend.hcl
    # bucket = "waterlevels-tfstate-ACCOUNT_ID"
    # key    = "terraform.tfstate"
    # region = "eu-west-1"
  }
}

module "networking" {
  source = "./modules/networking"

  project_name     = var.project_name
  ssh_allowed_cidr = var.ssh_allowed_cidr
}

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
}

module "compute" {
  source = "./modules/compute"

  project_name      = var.project_name
  instance_type     = var.instance_type
  ami_id            = var.ami_id
  key_pair_name     = var.key_pair_name
  domain_name       = var.domain_name
  app_image         = "${module.ecr.repository_url}:latest"
  alert_email       = var.alert_email
  subnet_id         = module.networking.subnet_id
  security_group_id = module.networking.security_group_id
}

module "dns" {
  source = "./modules/dns"

  domain_name = var.domain_name
  elastic_ip  = module.compute.elastic_ip
}
