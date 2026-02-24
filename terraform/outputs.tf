output "elastic_ip" {
  description = "Public IP address — point your DNS A record here"
  value       = module.compute.elastic_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = module.compute.instance_id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${module.compute.elastic_ip}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = module.ecr.repository_url
}

output "name_servers" {
  description = "NS records to configure at your .cy registrar"
  value       = module.dns.name_servers
}
