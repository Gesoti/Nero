#!/usr/bin/env bash
# One-command AWS deployment for WaterLevels (nero.cy)
# Usage: ./scripts/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$PROJECT_ROOT/terraform"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

confirm() {
  local prompt="${1:-Continue?}"
  read -rp "$(echo -e "${YELLOW}$prompt [y/N]:${NC} ")" answer
  [[ "$answer" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }
}

# ── Step 1: Preflight checks ──────────────────────────────────────────────────
info "Step 1/11: Preflight checks"

for cmd in aws terraform docker; do
  command -v "$cmd" &>/dev/null || fail "'$cmd' not found. Please install it first."
  ok "$cmd found"
done

if command -v gh &>/dev/null; then
  ok "gh CLI found (will configure GitHub secrets)"
  HAS_GH=true
else
  warn "gh CLI not found — skipping GitHub Actions secrets setup"
  HAS_GH=false
fi

# ── Step 2: AWS account ID ────────────────────────────────────────────────────
info "Step 2/11: Getting AWS account ID"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) \
  || fail "AWS CLI not configured. Run 'aws configure' first."
AWS_REGION="${AWS_REGION:-eu-west-1}"
ok "Account: $AWS_ACCOUNT_ID | Region: $AWS_REGION"

# ── Step 3: Bootstrap state bucket ────────────────────────────────────────────
info "Step 3/11: Bootstrapping Terraform state bucket"

STATE_BUCKET="waterlevels-tfstate-${AWS_ACCOUNT_ID}"

if aws s3api head-bucket --bucket "$STATE_BUCKET" 2>/dev/null; then
  ok "State bucket already exists: $STATE_BUCKET"
else
  info "Creating state bucket: $STATE_BUCKET"
  STATE_DIR="$TF_DIR/modules/state"

  cat > "$STATE_DIR/bootstrap.tf" <<EOF
provider "aws" {
  region = "$AWS_REGION"
}
module "state" {
  source         = "."
  aws_account_id = "$AWS_ACCOUNT_ID"
}
EOF

  (cd "$STATE_DIR" && terraform init -input=false && terraform apply -auto-approve)
  rm -f "$STATE_DIR/bootstrap.tf"
  rm -rf "$STATE_DIR/.terraform" "$STATE_DIR/.terraform.lock.hcl" "$STATE_DIR/terraform.tfstate"*
  ok "State bucket created: $STATE_BUCKET"
fi

# ── Step 4: Generate backend.hcl ──────────────────────────────────────────────
info "Step 4/11: Generating backend.hcl"

cat > "$TF_DIR/backend.hcl" <<EOF
bucket = "$STATE_BUCKET"
key    = "terraform.tfstate"
region = "$AWS_REGION"
EOF
ok "Written: terraform/backend.hcl"

# ── Step 5: Auto-discover AMI ─────────────────────────────────────────────────
info "Step 5/11: Discovering latest Ubuntu 24.04 AMI"

AMI_ID=$(aws ec2 describe-images \
  --region "$AWS_REGION" \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
  --owners 099720109477 \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text 2>/dev/null) || fail "Could not find Ubuntu 24.04 AMI"
ok "AMI: $AMI_ID"

# ── Step 6: SSH key pair ──────────────────────────────────────────────────────
info "Step 6/11: Selecting SSH key pair"

KEY_PAIRS=$(aws ec2 describe-key-pairs --region "$AWS_REGION" --query 'KeyPairs[*].KeyName' --output text 2>/dev/null)

if [[ -z "$KEY_PAIRS" ]]; then
  fail "No EC2 key pairs found in $AWS_REGION. Create one first: aws ec2 create-key-pair --key-name mykey --region $AWS_REGION"
fi

# Convert to array
IFS=$'\t' read -ra KEYS <<< "$KEY_PAIRS"

if [[ ${#KEYS[@]} -eq 1 ]]; then
  KEY_PAIR_NAME="${KEYS[0]}"
  ok "Using only available key pair: $KEY_PAIR_NAME"
else
  echo ""
  echo "Available key pairs:"
  for i in "${!KEYS[@]}"; do
    echo "  $((i+1)). ${KEYS[$i]}"
  done
  echo ""
  read -rp "Select key pair [1-${#KEYS[@]}]: " choice
  KEY_PAIR_NAME="${KEYS[$((choice-1))]}"
  ok "Selected: $KEY_PAIR_NAME"
fi

# ── Step 7: Detect caller IP ──────────────────────────────────────────────────
info "Step 7/11: Detecting your public IP"

MY_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null) || MY_IP=""

if [[ -z "$MY_IP" ]]; then
  read -rp "Could not auto-detect IP. Enter your public IP: " MY_IP
fi
SSH_CIDR="${MY_IP}/32"
ok "SSH allowed from: $SSH_CIDR"

# ── Step 8: Generate terraform.tfvars ──────────────────────────────────────────
info "Step 8/11: Generating terraform.tfvars"

DOMAIN_NAME="${DOMAIN_NAME:-nero.cy}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

cat > "$TF_DIR/terraform.tfvars" <<EOF
aws_region       = "$AWS_REGION"
ami_id           = "$AMI_ID"
key_pair_name    = "$KEY_PAIR_NAME"
domain_name      = "$DOMAIN_NAME"
ssh_allowed_cidr = "$SSH_CIDR"
alert_email      = "$ALERT_EMAIL"
EOF
ok "Written: terraform/terraform.tfvars"

# ── Step 9: Terraform init + plan + apply ──────────────────────────────────────
info "Step 9/11: Terraform init + plan + apply"

cd "$TF_DIR"
terraform init -backend-config=backend.hcl -input=false
terraform plan -out=tfplan

echo ""
confirm "Apply this Terraform plan?"
terraform apply tfplan
rm -f tfplan

ELASTIC_IP=$(terraform output -raw elastic_ip)
ECR_URL=$(terraform output -raw ecr_repository_url)
NAME_SERVERS=$(terraform output -json name_servers)
SSH_CMD=$(terraform output -raw ssh_command)
ok "Infrastructure deployed!"
ok "Elastic IP: $ELASTIC_IP"
cd "$PROJECT_ROOT"

# ── Step 10: Build & push Docker image ─────────────────────────────────────────
info "Step 10/11: Building and pushing Docker image"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ECR_URL%%/*}"

docker build -t "$ECR_URL:latest" -t "$ECR_URL:$(git rev-parse --short HEAD)" "$PROJECT_ROOT"
docker push "$ECR_URL:latest"
docker push "$ECR_URL:$(git rev-parse --short HEAD)"
ok "Image pushed to ECR"

# ── Step 11: GitHub Actions secrets ────────────────────────────────────────────
if [[ "$HAS_GH" == "true" ]]; then
  info "Step 11/11: Setting GitHub Actions secrets"
  echo ""
  warn "This step requires a GitHub Actions OIDC role ARN."
  warn "If you haven't set up OIDC yet, you can skip and do it later."
  echo ""
  read -rp "Enter AWS_ROLE_ARN (or press Enter to skip): " ROLE_ARN

  if [[ -n "$ROLE_ARN" ]]; then
    gh secret set AWS_ROLE_ARN --body "$ROLE_ARN"
    gh secret set EC2_HOST --body "$ELASTIC_IP"

    PEM_PATH="$HOME/.ssh/${KEY_PAIR_NAME}.pem"
    if [[ -f "$PEM_PATH" ]]; then
      gh secret set EC2_SSH_KEY < "$PEM_PATH"
      ok "GitHub secrets set (AWS_ROLE_ARN, EC2_HOST, EC2_SSH_KEY)"
    else
      warn "PEM file not found at $PEM_PATH"
      warn "Set EC2_SSH_KEY manually: gh secret set EC2_SSH_KEY < /path/to/key.pem"
      ok "GitHub secrets set (AWS_ROLE_ARN, EC2_HOST)"
    fi
  else
    warn "Skipping GitHub secrets — set them manually later"
  fi
else
  info "Step 11/11: Skipping GitHub secrets (gh CLI not installed)"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Elastic IP:${NC}     $ELASTIC_IP"
echo -e "  ${CYAN}ECR Repo:${NC}       $ECR_URL"
echo -e "  ${CYAN}SSH:${NC}            $SSH_CMD"
echo -e "  ${CYAN}Domain:${NC}         $DOMAIN_NAME"
echo ""
echo -e "  ${CYAN}Name Servers:${NC}   Set these at your .cy registrar:"
echo "  $NAME_SERVERS"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo "  1. Set NS records at your .cy domain registrar (above values)"
echo "  2. Wait for DNS propagation (can take up to 48h for .cy)"
echo "  3. SSH in and run certbot if HTTPS didn't auto-configure:"
echo "     $SSH_CMD"
echo "     sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME"
echo ""
