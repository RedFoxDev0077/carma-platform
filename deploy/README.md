# Deployment

Auto-deploy: every push to `main` runs lint + tests, then (on success) syncs the
code to the VPS and rolls out with Docker Compose. Pipeline: `.github/workflows/deploy.yml`.

## One-time setup

### 1. Prepare the VPS
Copy `deploy/bootstrap_vps.sh` to the server and run it as root:

```bash
scp deploy/bootstrap_vps.sh root@<VPS_IP>:/root/
ssh root@<VPS_IP> 'bash /root/bootstrap_vps.sh'
```

It installs Docker, creates `/opt/carma`, generates a deploy key, and prints the
**private key** to paste into GitHub.

### 2. Create the production `.env` on the VPS
```bash
ssh root@<VPS_IP>
cd /opt/carma
nano .env        # base it on .env.example, fill in real secrets
```
> `.env` is **never** synced from CI (it's excluded from rsync), so your secrets
> live only on the server.

### 3. Add GitHub repository secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `VPS_HOST` | the VPS IP |
| `VPS_USER` | `root` (or a dedicated deploy user) |
| `VPS_PORT` | `22` (optional) |
| `VPS_SSH_KEY` | the **private** deploy key printed by the bootstrap script |

### 4. Push
Push to `main` → watch **Actions** tab. On green, the app is live on the VPS at
`http://<VPS_IP>:8000/health`.

## Notes / hardening
- Put a reverse proxy (Caddy or Nginx) in front for TLS on `api.carma.pe`; only
  expose 80/443 publicly and keep 8000 internal.
- Prefer a non-root `deploy` user over `root` for the SSH deploy key.
- The image build runs **on the VPS**. Docker layer caching means only app-code
  changes rebuild fast; the heavy Playwright layer rebuilds only when
  `requirements.txt` changes. On the current 1-vCPU box the first build is slow —
  consider resizing to ≥2 vCPU, or switch to building in CI + pushing to GHCR
  (ask and I'll convert the workflow).
