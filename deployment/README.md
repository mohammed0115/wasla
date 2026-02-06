# Deployment (Ubuntu + Gunicorn + Nginx)

These scripts deploy the Wasla Django app to an Ubuntu server using:
- `systemd` + `gunicorn` (unix socket)
- `nginx` reverse proxy
- optional `certbot` SSL (requires a real domain)

## Before you start

1) Make sure the server has Ubuntu 20.04+.
2) Open firewall ports: `80` (HTTP) and optionally `443` (HTTPS).
3) Decide how you will get code onto the server:
   - **Recommended:** push your repo to GitHub/GitLab and set `GIT_REPO_URL`.
   - Otherwise: upload files manually, then skip `01_git_sync.sh`.

## Quick deploy (domain + SSL)

On the server (as root):

```bash
export PROJECT_NAME=wasla
export PROJECT_ROOT=/opt/wasla
export BACKEND_PATH=/opt/wasla/app
export GIT_REPO_URL="https://github.com/<you>/<repo>.git"
export GIT_BRANCH=main
export DOMAIN_NAME="yourdomain.com"

bash deployment/00_env_check.sh
bash deployment/01_git_sync.sh
bash deployment/02_system_setup.sh
bash deployment/04_gunicorn_service.sh
bash deployment/05_nginx_setup.sh
bash deployment/06_ssl_setup.sh
```

Notes:
- Step `06_ssl_setup.sh` enables `DJANGO_SECURE_SSL_REDIRECT=1` and secure cookies in `/etc/<project>/django.env`.
- SSL will not work for a bare IP (Let’s Encrypt does not issue certs for IPs).

## Deploy using server IP only (HTTP)

If you only have the server IP (example: `76.13.143.149`) and no domain yet:

```bash
export PROJECT_NAME=wasla
export PROJECT_ROOT=/opt/wasla
export BACKEND_PATH=/opt/wasla/app
export GIT_REPO_URL="https://github.com/<you>/<repo>.git"
export GIT_BRANCH=main
export DOMAIN_NAME="76.13.143.149"

bash deployment/00_env_check.sh
bash deployment/01_git_sync.sh
bash deployment/02_system_setup.sh
bash deployment/04_gunicorn_service.sh
bash deployment/05_nginx_setup.sh
```

Do **not** run `deployment/06_ssl_setup.sh` (it will fail without a real domain).

## Where config lives

- Django runtime env: `/etc/<project>/django.env`
- OCR env (optional): `/etc/<project>/ocr.env`
- Static files: `/var/lib/<project>/static`
- Media uploads: `/var/lib/<project>/media`
- Gunicorn service: `gunicorn-<project>.service`
- Nginx logs: `/var/log/nginx/<project>.*.log`

## Useful commands

```bash
systemctl status gunicorn-wasla --no-pager
journalctl -u gunicorn-wasla -n 200 --no-pager
nginx -t
systemctl reload nginx
```

