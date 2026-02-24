resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = { Name = "${var.domain_name}-zone" }
}

resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [var.elastic_ip]
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [var.elastic_ip]
}
