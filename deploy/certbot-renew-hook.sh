#!/bin/bash
# Certbot deploy hook — restarts nginx after SSL certificate renewal.
# Install: sudo cp deploy/certbot-renew-hook.sh /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
#          sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
#
# Certbot runs hooks in /etc/letsencrypt/renewal-hooks/deploy/ after each
# successful renewal. Nginx needs a reload to pick up the new certificate.

systemctl reload nginx
