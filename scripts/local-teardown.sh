#!/usr/bin/env bash
# Tear down the local LocalStack deployment.
# Usage: ./scripts/local-teardown.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.dev.yml"
TF_LOCAL_DIR="$REPO_ROOT/terraform/local"

echo "=== WaterLevels Local Teardown ==="

# ── Step 1: Destroy Terraform resources ──────────────────────────────────────
if [ -f "$TF_LOCAL_DIR/terraform.tfstate" ]; then
    echo ""
    echo "▸ Destroying Terraform resources on LocalStack..."
    cd "$TF_LOCAL_DIR"
    terraform destroy -auto-approve -input=false 2>/dev/null || true
    rm -f terraform.tfstate terraform.tfstate.backup
fi

# ── Step 2: Stop and remove containers + volumes ────────────────────────────
echo ""
echo "▸ Stopping containers..."
docker compose -f "$COMPOSE_FILE" down -v

echo ""
echo "=== Teardown Complete ==="
