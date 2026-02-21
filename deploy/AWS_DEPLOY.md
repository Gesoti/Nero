# AWS Free-Tier Deployment Guide

Deploy the WaterLevels dashboard to AWS using Terraform (IaC) and Docker.

**Architecture**: EC2 t2.micro + Nginx + Let's Encrypt + Docker container, with a separate EBS volume for SQLite persistence.

## Prerequisites

- **AWS CLI** configured with credentials (`aws configure`)
- **Terraform** >= 1.7 installed
- **Docker Hub** account (free tier, for image hosting)
- **SSH key pair** created in your target AWS region
- **Domain name** with DNS you can control (for A record)

## Step 1: Bootstrap Terraform State Bucket

The state bucket must exist before the main infrastructure. Run this once:

```bash
cd terraform/modules/state

# Create a temporary main.tf for bootstrapping
cat > bootstrap.tf <<'EOF'
provider "aws" {
  region = "eu-west-1"
}
module "state" {
  source         = "."
  aws_account_id = "YOUR_ACCOUNT_ID"
}
EOF

terraform init
terraform apply

# Note the bucket name from the output, then clean up
rm bootstrap.tf
cd ../..
```

## Step 2: Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

| Variable | How to find it |
|----------|---------------|
| `ami_id` | `aws ec2 describe-images --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" --owners 099720109477 --query 'Images \| sort_by(@, &CreationDate) \| [-1].ImageId' --output text` |
| `key_pair_name` | `aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName'` |
| `domain_name` | Your chosen subdomain (e.g. `water.example.com`) |
| `app_image` | `yourusername/waterlevels:latest` |
| `ssh_allowed_cidr` | Your IP: `curl -s ifconfig.me`/32 |

## Step 3: Configure Backend

Create `terraform/backend.hcl`:

```hcl
bucket = "waterlevels-tfstate-YOUR_ACCOUNT_ID"
key    = "terraform.tfstate"
region = "eu-west-1"
```

## Step 4: Deploy Infrastructure

```bash
cd terraform
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Note the outputs:
- `elastic_ip` — the public IP for your DNS A record
- `ssh_command` — how to SSH into the instance

## Step 5: DNS Setup

Create an **A record** pointing your domain to the Elastic IP:

| Type | Name | Value |
|------|------|-------|
| A | water.example.com | (elastic_ip from output) |

## Step 6: SSL Certificate

If Certbot didn't succeed during bootstrap (DNS wasn't ready), SSH in and run:

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@ELASTIC_IP
sudo certbot --nginx -d your.domain.com
```

## Step 7: GitHub Actions Secrets

Set these in your repo → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not password) |
| `EC2_HOST` | Elastic IP from terraform output |
| `EC2_SSH_KEY` | Contents of your `.pem` private key |

After this, every push to `main` will auto-deploy.

## Verify

```bash
# Check the site loads
curl -I https://your.domain.com

# Check health endpoint
curl https://your.domain.com/health

# SSH and check Docker logs
ssh -i ~/.ssh/your-key.pem ubuntu@ELASTIC_IP
docker logs waterlevels
```

## Cost Summary (Free Tier)

| Resource | Free Limit | Usage |
|----------|-----------|-------|
| EC2 t2.micro | 750 hrs/mo | 744 hrs/mo |
| EBS gp3 | 30 GB | 9 GB (8 root + 1 data) |
| S3 | 5 GB | <1 MB |
| CloudWatch | 10 alarms | 1 |
| Elastic IP | Free if attached | 1 |

**$0/month** within the 12-month AWS free tier. Only DNS costs are external.

## Teardown

```bash
cd terraform
terraform destroy
```

> **Note**: The EBS data volume and S3 state bucket have `prevent_destroy` lifecycle rules. To fully remove them, comment out those rules first.
