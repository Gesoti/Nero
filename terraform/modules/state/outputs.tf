output "bucket_name" {
  description = "S3 bucket name for Terraform state"
  value       = aws_s3_bucket.tfstate.id
}

output "bucket_arn" {
  description = "S3 bucket ARN for Terraform state"
  value       = aws_s3_bucket.tfstate.arn
}
