# ── IAM role for CloudWatch Logs ──────────────────────────────────────────────

resource "aws_iam_role" "ec2" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "cloudwatch_logs" {
  name = "${var.project_name}-cloudwatch-logs"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ]
      Resource = "arn:aws:logs:*:*:*"
    }]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# ── EC2 instance ─────────────────────────────────────────────────────────────

resource "aws_instance" "app" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  dynamic "root_block_device" {
    for_each = var.local_mode ? [] : [1]
    content {
      volume_size = 8
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = templatefile("${path.module}/templates/user_data.sh.tpl", {
    domain_name = var.domain_name
    app_image   = var.app_image
    aws_region  = data.aws_region.current.name
  })

  tags = { Name = "${var.project_name}-app" }

  lifecycle {
    ignore_changes = [user_data]
  }
}

data "aws_region" "current" {}

# ── EBS data volume (SQLite persistence) ─────────────────────────────────────

resource "aws_ebs_volume" "data" {
  count             = var.local_mode ? 0 : 1
  availability_zone = aws_instance.app.availability_zone
  size              = 1
  type              = "gp3"
  encrypted         = true

  tags = { Name = "${var.project_name}-data" }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_volume_attachment" "data" {
  count       = var.local_mode ? 0 : 1
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.data[0].id
  instance_id = aws_instance.app.id
}

# ── Elastic IP ───────────────────────────────────────────────────────────────

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = { Name = "${var.project_name}-eip" }
}

# ── CloudWatch CPU alarm ─────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  count = var.alert_email != "" ? 1 : 0
  name  = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "CPU > 80% for 10 minutes"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = { Name = "${var.project_name}-cpu-alarm" }
}
