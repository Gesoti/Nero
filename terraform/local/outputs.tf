output "elastic_ip" {
  description = "Elastic IP (LocalStack mock)"
  value       = module.compute.elastic_ip
}

output "instance_id" {
  description = "EC2 instance ID (LocalStack mock)"
  value       = module.compute.instance_id
}
