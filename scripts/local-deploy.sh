#!/usr/bin/env bash
# Local deployment pipeline using LocalStack.
# Builds the app, starts LocalStack, provisions infra via Terraform.
#
# Prerequisites: docker, docker compose, terraform
# Usage: ./scripts/local-deploy.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.dev.yml"
TF_LOCAL_DIR="$REPO_ROOT/terraform/local"

echo "=== WaterLevels Local Deploy ==="

# ── Step 1: Build the app image ──────────────────────────────────────────────
echo ""
echo "▸ Building Docker image..."
docker build -t waterlevels:local "$REPO_ROOT"

# ── Step 2: Start services (LocalStack + app) ───────────────────────────────
echo ""
echo "▸ Starting LocalStack + app..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "▸ Waiting for LocalStack to be healthy..."
timeout=60
elapsed=0
while ! curl -sf http://localhost:4566/_localstack/health > /dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo "✗ LocalStack failed to start within ${timeout}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "✓ LocalStack is healthy"

# ── Step 3: Wait for app to be healthy ───────────────────────────────────────
echo ""
echo "▸ Waiting for app to be healthy..."
elapsed=0
while ! curl -sf http://localhost:8000/health > /dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo "✗ App failed to start within ${timeout}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "✓ App is healthy at http://localhost:8000"

# ── Step 4: Provision infrastructure on LocalStack ───────────────────────────
echo ""
echo "▸ Running Terraform against LocalStack..."
cd "$TF_LOCAL_DIR"
terraform init -input=false
terraform apply -auto-approve -input=false

echo ""
echo "=== Local Deploy Complete ==="
echo ""
echo "  App:        http://localhost:8000"
echo "  Health:     http://localhost:8000/health"
echo "  LocalStack: http://localhost:4566"
echo ""
echo "  Terraform outputs:"
terraform output
echo ""
echo "  Teardown:   ./scripts/local-teardown.sh"
