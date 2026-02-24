output "name_servers" {
  description = "NS records to configure at your domain registrar"
  value       = aws_route53_zone.main.name_servers
}

output "zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.main.zone_id
}
