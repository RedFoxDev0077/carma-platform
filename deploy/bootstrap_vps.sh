#!/usr/bin/env bash
# One-time VPS preparation for CARMA auto-deploy.
# Run as root on the Hostinger VPS (Ubuntu 24.04):
#   bash bootstrap_vps.sh
set -euo pipefail

APP_DIR=/opt/carma
DEPLOY_KEY=~/.ssh/carma_deploy

echo "==> Installing Docker (if missing)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> Creating app directory: $APP_DIR"
mkdir -p "$APP_DIR/reports"

echo "==> Creating deploy key pair for GitHub Actions"
if [ ! -f "$DEPLOY_KEY" ]; then
  ssh-keygen -t ed25519 -N "" -C "carma-github-actions" -f "$DEPLOY_KEY"
  cat "$DEPLOY_KEY.pub" >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
fi

echo "==> Opening firewall for HTTP/HTTPS + app port (if ufw present)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

echo
echo "======================================================================"
echo " NEXT STEPS"
echo "----------------------------------------------------------------------"
echo " 1. Create $APP_DIR/.env from .env.example and fill in real secrets."
echo " 2. Add these GitHub repository secrets (Settings > Secrets > Actions):"
echo "      VPS_HOST   = <this server's IP>"
echo "      VPS_USER   = $(whoami)"
echo "      VPS_PORT   = 22        (optional; defaults to 22)"
echo "      VPS_SSH_KEY= (paste the PRIVATE key printed below)"
echo "----------------------------------------------------------------------"
echo " PRIVATE deploy key to paste into the VPS_SSH_KEY secret:"
echo "======================================================================"
cat "$DEPLOY_KEY"
echo "======================================================================"
echo " Keep this key secret. After copying it, you may clear your screen."
