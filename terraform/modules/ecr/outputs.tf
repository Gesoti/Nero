output "repository_url" {
  description = "Full ECR repository URL (ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/NAME)"
  value       = aws_ecr_repository.app.repository_url
}

output "registry_id" {
  description = "AWS account ID that owns the ECR registry"
  value       = aws_ecr_repository.app.registry_id
}
