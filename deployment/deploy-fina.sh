#!/bin/bash
set -e

bash 00_env_check.sh
bash 01_git_sync.sh
bash 02_system_setup.sh
bash 03_ocr_setup.sh
bash 04_gunicorn_service.sh
bash 05_nginx_setup.sh
bash 06_ssl_setup.sh
bash 07_monitoring.sh
bash 08_notifications.sh

echo "✅ Deployment Completed Successfully"
