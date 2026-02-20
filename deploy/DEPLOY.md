# Deployment Checklist — Cyprus Water Levels Dashboard

All commands run as **root** unless prefixed with `sudo -u waterlevels`.
Replace `yourdomain.com` everywhere with your actual domain before starting.

---

## Phase A — Server baseline

```bash
apt update && apt upgrade -y
apt install -y nginx git curl snapd ufw
```

Configure the firewall:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

> **Note:** Point your DNS A record (and AAAA if using IPv6) to the VPS IP
> before running Certbot in Phase F. Certbot's HTTP-01 challenge requires
> the domain to resolve to the server.

---

## Phase B — Install uv system-wide

```bash
curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR="/usr/local/bin" sh
uv --version
```

> **Why the override?** The default install target is `~/.local/bin`, which is
> not on the PATH of system services. The `UV_INSTALL_DIR` override places the
> binary in `/usr/local/bin` so the systemd unit can call it without a full
> path hack.

---

## Phase C — Deploy app

Create the system user (no login shell, no home directory):

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin waterlevels
```

Clone the repository and set up directories:

```bash
git clone https://github.com/Gesoti/WaterLevels /opt/waterlevels
mkdir -p /opt/waterlevels/data /opt/waterlevels/.uv-cache
chown -R waterlevels:waterlevels /opt/waterlevels
```

Pre-build the virtualenv as the service user:

```bash
sudo -u waterlevels /usr/local/bin/uv sync --frozen --no-dev --project /opt/waterlevels
```

Create the secrets file:

```bash
mkdir -p /etc/waterlevels
cp /opt/waterlevels/deploy/env.example /etc/waterlevels/env
# Edit /etc/waterlevels/env and fill in real values
nano /etc/waterlevels/env
chmod 640 /etc/waterlevels/env
chown root:waterlevels /etc/waterlevels/env
```

---

## Phase D — systemd

```bash
cp /opt/waterlevels/deploy/waterlevels.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable waterlevels
systemctl start waterlevels
```

Watch the logs until startup is confirmed:

```bash
journalctl -u waterlevels -f
```

Look for `Application startup complete`. On first run the DB seed takes
roughly 10 seconds — this is normal.

---

## Phase E — Nginx

```bash
cp /opt/waterlevels/deploy/nginx-waterlevels.conf /etc/nginx/sites-available/waterlevels
```

Edit the config and replace all occurrences of `yourdomain.com`:

```bash
nano /etc/nginx/sites-available/waterlevels
```

Enable the site and remove the default placeholder:

```bash
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/waterlevels /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

> At this point the site is reachable over HTTP only. HTTPS is added in Phase F.
> Nginx will log TLS errors until the certificate exists — that is expected.

---

## Phase F — SSL via Certbot

```bash
snap install core && snap refresh core
snap install --classic certbot
ln -s /snap/bin/certbot /usr/local/bin/certbot
```

Obtain the certificate and auto-patch the Nginx config:

```bash
certbot --nginx \
  -d yourdomain.com -d www.yourdomain.com \
  --agree-tos \
  --email you@example.com \
  --redirect \
  --no-eff-email
systemctl reload nginx
```

Verify auto-renewal works (dry run, no certificate issued):

```bash
certbot renew --dry-run
```

---

## Phase G — Smoke test

```bash
# Main page returns 200
curl -I https://yourdomain.com

# HTTP redirects to HTTPS
curl -I http://yourdomain.com

# Static asset served by Nginx (not Python)
curl https://yourdomain.com/static/js/charts.js -o /dev/null -w "%{http_code}\n"

# Key pages
curl -o /dev/null -w "%{http_code}\n" https://yourdomain.com/
curl -o /dev/null -w "%{http_code}\n" https://yourdomain.com/about
curl -o /dev/null -w "%{http_code}\n" https://yourdomain.com/privacy
curl -o /dev/null -w "%{http_code}\n" https://yourdomain.com/dam/Kouris
```

All should return `200`. The HTTP request should return `301`.

---

## Ongoing operations

| Task | Command |
|---|---|
| View live logs | `journalctl -u waterlevels -f` |
| Deploy an update | `git -C /opt/waterlevels pull && systemctl restart waterlevels` |
| Check service status | `systemctl status waterlevels` |
| Check cert expiry | `certbot certificates` |

---

## Security hardening — after 48 h

The app ships with `Content-Security-Policy-Report-Only` so you can observe
violations in logs before enforcing. After confirming no legitimate resources
are blocked, flip to enforcement:

1. In `app/security.py`, change `Content-Security-Policy-Report-Only` to
   `Content-Security-Policy`.
2. Restart the service:
   ```bash
   systemctl restart waterlevels
   ```
