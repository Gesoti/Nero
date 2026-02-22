#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log) 2>&1

echo "=== WaterLevels bootstrap starting ==="

# ── System packages ──────────────────────────────────────────────────────────
apt-get update -y
apt-get install -y nginx docker.io ufw snapd

systemctl enable --now docker
usermod -aG docker ubuntu

# ── Mount EBS data volume ────────────────────────────────────────────────────
# Wait for the volume to appear (may take a few seconds after attachment)
while [ ! -b /dev/xvdf ]; do
  echo "Waiting for /dev/xvdf..."
  sleep 2
done

# Only format if the volume has no filesystem (safe on reboot)
if ! blkid /dev/xvdf; then
  mkfs.ext4 -L waterlevels-data /dev/xvdf
fi

mkdir -p /data
mount /dev/xvdf /data

# Persist mount across reboots
if ! grep -q '/dev/xvdf' /etc/fstab; then
  echo '/dev/xvdf /data ext4 defaults,nofail 0 2' >> /etc/fstab
fi

chown ubuntu:ubuntu /data

# ── Docker container ─────────────────────────────────────────────────────────
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
