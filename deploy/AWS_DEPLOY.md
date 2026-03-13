# AWS Deployment Guide

Deploy the WaterLevels dashboard to AWS with a single command.

**Architecture**: EC2 t2.micro + Nginx + Let's Encrypt + Docker container, with a separate EBS volume for SQLite persistence. Images stored in AWS ECR. DNS via Route53.

## Quick Start

```bash
./scripts/deploy.sh
```

The script handles everything automatically:

| Step | What it does |
|------|-------------|
| 1 | Checks prerequisites (`aws`, `terraform`, `docker`) |
| 2 | Gets your AWS account ID |
| 3 | Creates the Terraform state S3 bucket (idempotent) |
| 4 | Generates `backend.hcl` for remote state |
| 5 | Finds the latest Ubuntu 24.04 AMI |
| 6 | Prompts you to select an SSH key pair |
| 7 | Auto-detects your public IP for SSH access |
| 8 | Generates `terraform.tfvars` with all values |
| 9 | Runs `terraform init + plan + apply` (with confirmation) |
| 10 | Builds and pushes the Docker image to ECR |
| 11 | Sets GitHub Actions secrets (if `gh` CLI available) |

### Prerequisites

- **AWS CLI** configured with credentials (`aws configure`)
- **Terraform** >= 1.7
- **Docker** running locally
- **SSH key pair** in your target AWS region (`aws ec2 create-key-pair --key-name mykey --region eu-west-1`)
- **gh CLI** (optional, for GitHub Actions secrets)

### Environment Variables

Override defaults by exporting before running:

```bash
export AWS_REGION=eu-west-1          # default
export DOMAIN_NAME=nero.cy           # default
export ALERT_EMAIL=you@example.com   # optional, for CloudWatch alarms
```

## Post-Deploy: Set NS Records

After deployment, the script prints Route53 name servers. You **must** set these at your `.cy` domain registrar:

1. Log in to your `.cy` registrar
2. Find DNS / Nameserver settings for `nero.cy`
3. Replace existing NS records with the 4 values from the script output
4. Wait for propagation (up to 48h for `.cy` domains)

## Post-Deploy: SSL Certificate

If Certbot didn't auto-configure during bootstrap (DNS wasn't ready):

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@ELASTIC_IP
sudo certbot --nginx -d nero.cy -d www.nero.cy
```

### Automatic Renewal Hook

Nginx must reload after certbot renews the SSL certificate, otherwise it
continues serving the old cert until the next manual restart. Install the
deploy hook:

```bash
sudo cp deploy/certbot-renew-hook.sh /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
```

Test it works: `sudo certbot renew --dry-run`

## CI/CD

After deployment, every push to `main` triggers the GitHub Actions pipeline:

1. **Test** — runs `pytest`
2. **Build & Push** — builds Docker image, pushes to ECR
3. **Deploy** — SSHs into EC2 and pulls the new image

Required GitHub secrets (set automatically by `deploy.sh` if `gh` is available):

| Secret | Value |
|--------|-------|
| `AWS_ROLE_ARN` | IAM OIDC role ARN for GitHub Actions |
| `EC2_HOST` | Elastic IP from Terraform |
| `EC2_SSH_KEY` | Contents of your `.pem` private key |

For OIDC setup, see [GitHub docs](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services).

## Local Testing with LocalStack

Test the full stack locally before deploying to AWS:

```bash
./scripts/local-deploy.sh       # Build + deploy to LocalStack
# App: http://localhost:8000
./scripts/local-teardown.sh     # Tear down everything
```

## Cost Summary (Free Tier)

| Resource | Free Limit | Usage |
|----------|-----------|-------|
| EC2 t2.micro | 750 hrs/mo | 744 hrs/mo |
| EBS gp3 | 30 GB | 9 GB (8 root + 1 data) |
| ECR | 500 MB/mo | ~100 MB |
| S3 | 5 GB | <1 MB |
| Route53 | — | ~$0.50/mo (hosted zone) |
| CloudWatch | 10 alarms | 1 |
| Elastic IP | Free if attached | 1 |

**~$0.50/month** (Route53 hosted zone). All other resources within 12-month free tier.

## Teardown

```bash
cd terraform
terraform destroy
```

> **Note**: The EBS data volume and S3 state bucket have `prevent_destroy` lifecycle rules. To fully remove them, comment out those rules first.

## Manual Deployment (Advanced)

<details>
<summary>Click to expand manual steps</summary>

If you prefer to run each step manually instead of using `deploy.sh`:

### 1. Create Terraform State Bucket

```bash
cd terraform/modules/state
cat > bootstrap.tf <<'EOF'
provider "aws" { region = "eu-west-1" }
module "state" {
  source         = "."
  aws_account_id = "YOUR_ACCOUNT_ID"
}
EOF
terraform init && terraform apply
rm bootstrap.tf
```

### 2. Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Configure Backend

Create `terraform/backend.hcl`:

```hcl
bucket = "waterlevels-tfstate-YOUR_ACCOUNT_ID"
key    = "terraform.tfstate"
region = "eu-west-1"
```

### 4. Deploy

```bash
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

### 5. Build & Push Docker Image

```bash
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin "${ECR_URL%%/*}"
docker build -t "$ECR_URL:latest" .
docker push "$ECR_URL:latest"
```

### 6. Set NS Records

Set the `name_servers` output values at your domain registrar.

### 7. SSL Certificate

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@ELASTIC_IP
sudo certbot --nginx -d nero.cy -d www.nero.cy
```

### 8. GitHub Actions Secrets

```bash
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::ACCOUNT_ID:role/github-actions-waterlevels"
gh secret set EC2_HOST --body "ELASTIC_IP"
gh secret set EC2_SSH_KEY < ~/.ssh/your-key.pem
```

</details>
