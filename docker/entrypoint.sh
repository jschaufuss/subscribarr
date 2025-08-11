#!/usr/bin/env bash
set -euo pipefail

# Apply migrations
python manage.py makemigrations
python manage.py migrate --noinput

# Create admin user if provided
if [[ -n "${ADMIN_USERNAME:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
  echo "Creating admin user ${ADMIN_USERNAME}"
  python - <<'PY'
import os
from django.contrib.auth import get_user_model
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subscribarr.settings')
django.setup()
User = get_user_model()
username = os.environ['ADMIN_USERNAME']
password = os.environ['ADMIN_PASSWORD']
email = os.environ.get('ADMIN_EMAIL') or f"{username}@local"
user, created = User.objects.get_or_create(username=username, defaults={'email': email})
user.set_password(password)
user.is_superuser = True
user.is_staff = True
user.is_admin = True
user.save()
print("Admin ready")
PY
fi

# Seed AppSettings from environment if provided
python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subscribarr.settings')
django.setup()
from settingspanel.models import AppSettings
s = AppSettings.current()
# Jellyfin
jf_url = os.environ.get('JELLYFIN_URL')
jf_key = os.environ.get('JELLYFIN_API_KEY')
if jf_url: s.jellyfin_server_url = jf_url
if jf_key: s.jellyfin_api_key = jf_key
# Sonarr / Radarr
sonarr_url = os.environ.get('SONARR_URL')
sonarr_key = os.environ.get('SONARR_API_KEY')
radarr_url = os.environ.get('RADARR_URL')
radarr_key = os.environ.get('RADARR_API_KEY')
if sonarr_url: s.sonarr_url = sonarr_url
if sonarr_key: s.sonarr_api_key = sonarr_key
if radarr_url: s.radarr_url = radarr_url
if radarr_key: s.radarr_api_key = radarr_key
# Mail
mail_host = os.environ.get('MAIL_HOST')
mail_port = os.environ.get('MAIL_PORT')
mail_secure = os.environ.get('MAIL_SECURE')
mail_user = os.environ.get('MAIL_USER')
mail_password = os.environ.get('MAIL_PASSWORD')
mail_from = os.environ.get('MAIL_FROM')
if mail_host: s.mail_host = mail_host
if mail_port: s.mail_port = int(mail_port)
if mail_secure: s.mail_secure = mail_secure
if mail_user: s.mail_user = mail_user
if mail_password: s.mail_password = mail_password
if mail_from: s.mail_from = mail_from
s.save()
print("AppSettings seeded from environment (if provided)")
PY

# Setup cron if schedule provided
if [[ -n "${CRON_SCHEDULE:-}" ]]; then
  echo "Configuring cron: ${CRON_SCHEDULE}"
  echo "${CRON_SCHEDULE} cd /app && /usr/local/bin/python manage.py check_new_media >> /app/cron.log 2>&1" > /etc/cron.d/subscribarr
  chmod 0644 /etc/cron.d/subscribarr
  crontab /etc/cron.d/subscribarr
  /usr/sbin/cron
fi

# Run server
exec python manage.py runserver 0.0.0.0:8000
