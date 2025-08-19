> [!WARNING] 
> This project was largely written with GitHub Copilot. I apologize to all developers out there for using GitHub Copilot. I’m looking for a competent maintainer. If multiple users rely on it and no maintainer steps up, I’ll level up my Django skills and take it over myself.

<p align="center">
  <img src="./static/images/logo.png" alt="Subscribarr" width="450" height="150" />
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/python-3.13-blue.svg" alt="Python 3.13">
  <img src="https://img.shields.io/badge/django-5.x-092e20?logo=django&logoColor=white" alt="Django 5">
  <a href="https://hub.docker.com/r/10010011/subscribarr"><img src="https://img.shields.io/docker/pulls/10010011/subscribarr" alt="docker pulls"></a>
  <img src="https://img.shields.io/badge/ntfy-supported-4c1" alt="ntfy supported">
  <img src="https://img.shields.io/badge/Apprise-supported-4c1" alt="Apprise supported">
</p>

<!-- Optional dynamic badges (uncomment and replace OWNER/REPO / IMAGE if you want):
<p align="center">
  <a href="https://github.com/OWNER/REPO/releases"><img src="https://img.shields.io/github/v/release/OWNER/REPO?sort=semver" alt="latest release"></a>
  <a href="https://hub.docker.com/r/OWNER/IMAGE"><img src="https://img.shields.io/docker/pulls/OWNER/IMAGE" alt="docker pulls"></a>
  <a href="https://github.com/OWNER/REPO/commits/main"><img src="https://img.shields.io/github/commit-activity/m/OWNER/REPO" alt="commit activity"></a>
</p>
-->

Lightweight web UI for Sonarr/Radarr subscriptions with Jellyfin login, calendar, and flexible notifications via Email, ntfy, and Apprise.

## Features
- Sign in with Jellyfin
- Sonarr/Radarr‑style calendar (upcoming episodes/movies)
- Subscribe/unsubscribe from the UI (series & movies)
- Admin overview of all users subscriptions
- Per‑user notification channels:
  - Email (SMTP)
  - ntfy (Bearer token or Basic Auth)
  - Apprise (Discord, Gotify, Pushover, Webhooks, and many more)
- Docker‑ready
- Multiple Sonarr/Radarr instances
- Early‑availability notifications (configurable lookahead)
- Duplicate suppression per user/item/day and admin tooling (send test, reset tokens)
- 4K subscriptions: detection across all Radarr instances
- YouTube subscriptions

## Screenshots
<p align="center">
  <img src="./screenshots/SCR-20250811-lfrm.png" alt="Settings" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfvc.png" alt="Subscriptions" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfod.png" alt="Overview" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfyq.png" alt="Search" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lgau.png" alt="Details" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lgcz.png" alt="Notifications" width="800">
</p>

## Quickstart (Docker Compose)
1) Ensure the lockfile matches your Pipfile (e.g., after adding packages):
```bash
git clone https://github.com/jschaufuss/subscribarr.git
cd subscribarr
```
2) run the container:
```bash
docker compose up -d
```
3) Open the app and complete the first‑run setup (Jellyfin + Arr URLs/keys).
```
http://127.0.0.1:8081
```

Important environment variables (examples):
- `DJANGO_ALLOWED_HOSTS=subscribarr.example.com,localhost,127.0.0.1`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://subscribarr.example.com,http://subscribarr.example.com`
- Reverse proxy/TLS:
  - `USE_X_FORWARDED_HOST=true`
  - `DJANGO_SECURE_PROXY_SSL_HEADER=true`
  - `DJANGO_CSRF_COOKIE_SECURE=true`
  - `DJANGO_SESSION_COOKIE_SECURE=true`

> Note: `DJANGO_CSRF_TRUSTED_ORIGINS` must include the exact scheme+host (+port if used).

## In‑App Configuration
- Settings → Jellyfin: server URL + API key
- Settings →Sonarr/Radarr: base URLs + API keys (with “Test” button)
- Settings →Mail server: SMTP (host/port/TLS/SSL/user/password/from)
- Settings →Notifications:
  - ntfy: server URL, default topic, Basic Auth or Bearer token
  - Apprise: default URL(s) (one per line)
- Profile (per user):
  - Choose channel: Email, ntfy, or Apprise
  - ntfy topic (optional, overrides default)
  - Apprise URL(s) (optional, appended to defaults)

## ntfy Notes
- Server URL: e.g., `https://ntfy.sh` or your own server
- Auth:
  - Bearer token (Authorization header)
  - Basic Auth (username/password)
- Topic selection:
  - Per user in the profile, or a global default topic in Settings

## Apprise Notes
Provide one or more destination URLs (one per line), e.g.:
- `gotify://TOKEN@gotify.example.com/`
- `discord://webhook_id/webhook_token`
- `mailto://user:pass@smtp.example.com`
- `pover://user@token`
- `json://webhook.example.com/path`

User URLs are added in addition to global defaults.

## Notification Logic
- Series: on the air date, Subscribarr checks Sonarr for the episode and only notifies when episode is downloaded and present.
- Movies: similar via Radarr when movie is downloaded and present.
- Duplicate suppression: entries are recorded in `SentNotification` per user/title/day; if sending fails, no record is stored.
- Fallback: if ntfy/Apprise fail, Subscribarr falls back to Email (when configured).

## Jobs / Manual Trigger
- Periodic check via management command (e.g., cron):
```bash
docker exec -it subscribarr python manage.py check_new_media
```

## Security & Proxy
- Set `DJANGO_ALLOWED_HOSTS` to your hostnames.
- Include all used origins in `DJANGO_CSRF_TRUSTED_ORIGINS` (http/https and port where applicable).
- Behind a reverse proxy with TLS: enable `USE_X_FORWARDED_HOST`, `DJANGO_SECURE_PROXY_SSL_HEADER`, and secure cookie flags.

## Tech Stack
- Backend: Django 5 + DRF
- Integrations: Sonarr/Radarr (API v3)
- Auth: Jellyfin
- Notifications: SMTP, ntfy (HTTP), Apprise
- Frontend: Templates + FullCalendar
- DB: SQLite (default)

## License
MIT (see `LICENSE`).

