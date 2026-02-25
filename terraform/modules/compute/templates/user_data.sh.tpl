#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log) 2>&1

echo "=== WaterLevels bootstrap starting ==="

# ── System packages ──────────────────────────────────────────────────────────
apt-get update -y
apt-get install -y nginx docker.io ufw snapd

# SSM Agent (pre-installed via snap on Ubuntu, ensure it's running)
snap start amazon-ssm-agent 2>/dev/null || true

systemctl enable --now docker
usermod -aG docker ubuntu

# ── Mount EBS data volume ────────────────────────────────────────────────────
# On NVMe instances (t3, etc.) /dev/xvdf appears as /dev/nvme*n1.
# Wait for either device name, then resolve the actual path.
DATA_DEV=""
for i in $(seq 1 60); do
  if [ -b /dev/xvdf ]; then
    DATA_DEV="/dev/xvdf"
    break
  fi
  # Find NVMe device that is NOT the root disk (1G data volume)
  for dev in /dev/nvme*n1; do
    [ -b "$dev" ] || continue
    SIZE_GB=$(lsblk -bdno SIZE "$dev" 2>/dev/null | awk '{printf "%d", $1/1073741824}')
    if [ "$SIZE_GB" -le 2 ] 2>/dev/null; then
      DATA_DEV="$dev"
      break 2
    fi
  done
  echo "Waiting for data volume... ($i/60)"
  sleep 2
done

if [ -z "$DATA_DEV" ]; then
  echo "ERROR: Data volume not found after 120s"
  exit 1
fi
echo "Data volume found at $DATA_DEV"

# Only format if the volume has no filesystem (safe on reboot)
if ! blkid "$DATA_DEV"; then
  mkfs.ext4 -L waterlevels-data "$DATA_DEV"
fi

mkdir -p /data
mount "$DATA_DEV" /data

# Persist mount across reboots using label (stable across device name changes)
if ! grep -q 'waterlevels-data' /etc/fstab; then
  echo 'LABEL=waterlevels-data /data ext4 defaults,nofail 0 2' >> /etc/fstab
fi

chown ubuntu:ubuntu /data

# ── Docker container ─────────────────────────────────────────────────────────
# Authenticate with ECR (install AWS CLI v2)
if ! command -v aws &>/dev/null; then
  apt-get install -y unzip
  curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  cd /tmp && unzip -q awscliv2.zip && ./aws/install
  cd /
fi
aws ecr get-login-password --region ${aws_region} | docker login --username AWS --password-stdin $(echo "${app_image}" | cut -d'/' -f1)
docker pull ${app_image}
docker run -d \
  --name waterlevels \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  -v /data:/data \
  --log-driver awslogs \
  --log-opt awslogs-region=${aws_region} \
  --log-opt awslogs-group=/waterlevels/app \
  --log-opt awslogs-create-group=true \
  ${app_image}

# ── Nginx reverse proxy ─────────────────────────────────────────────────────
cat > /etc/nginx/sites-available/waterlevels <<'NGINX'
server {
    listen 80;
    server_name ${domain_name};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/waterlevels /etc/nginx/sites-enabled/waterlevels
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── Certbot (Let's Encrypt) ─────────────────────────────────────────────────
snap install --classic certbot || true
ln -sf /snap/bin/certbot /usr/bin/certbot || true

# Attempt certificate issuance — will fail gracefully if DNS not yet pointing
certbot --nginx -d ${domain_name} --non-interactive --agree-tos \
  --email ${alert_email} --redirect || {
  echo "WARNING: Certbot failed (DNS may not be ready). Run manually after DNS setup:"
  echo "  sudo certbot --nginx -d ${domain_name}"
}

# ── Firewall ─────────────────────────────────────────────────────────────────
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== WaterLevels bootstrap complete ==="
