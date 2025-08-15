# Subscribarr

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/python-3.13-blue.svg" alt="Python 3.13">
  <img src="https://img.shields.io/badge/django-5.x-092e20?logo=django&logoColor=white" alt="Django 5">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker ready">
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

Ein leichtgewichtiges Web‑Frontend für Benachrichtigungen und Abos rund um Sonarr/Radarr – mit Jellyfin‑Login, Kalender, Abo‑Verwaltung und flexiblen Notifications per E‑Mail, ntfy und Apprise.

## Features
- Jellyfin‑Login (kein eigener Userstore nötig)
- Kalender im Sonarr/Radarr‑Stil (kommende Episoden/Filme)
- Abonnieren/Abbestellen direkt aus dem UI (Serien & Filme)
- Admin‑Übersicht aller Abos je Nutzer inkl. Poster
- Benachrichtigungen pro Nutzer wählbar:
  - E‑Mail (SMTP)
  - ntfy (Token oder Basic Auth)
  - Apprise (zahlreiche Ziele wie Discord, Gotify, Pushover, Webhooks u. v. m.)
- Docker‑fertig, env‑gesteuerte Security‑Settings (ALLOWED_HOSTS, CSRF, Proxy)

## Schnellstart

## Screenshots
<p align="center">
  <img src="./screenshots/SCR-20250811-lfrm.png" alt="Screenshot 1" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfvc.png" alt="Screenshot 2" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfod.png" alt="Screenshot 3" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lfyq.png" alt="Screenshot 4" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lgau.png" alt="Screenshot 5" width="800"><br/>
  <img src="./screenshots/SCR-20250811-lgcz.png" alt="Screenshot 6" width="800">
</p>

### Mit Docker Compose
1) Lockfile aktuell halten (wenn `Pipfile` geändert wurde):
```bash
pipenv lock
```
2) Image bauen/Starten:
```bash
docker compose build
docker compose up -d
```
3) Öffne die App und führe das First‑Run‑Setup (Jellyfin + Arr‑URLs/Keys) durch.

Wichtige Umgebungsvariablen (Beispiele):
- `DJANGO_ALLOWED_HOSTS=subscribarr.example.com,localhost,127.0.0.1`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://subscribarr.example.com,http://subscribarr.example.com`
- Reverse‑Proxy/TLS:
  - `USE_X_FORWARDED_HOST=true`
  - `DJANGO_SECURE_PROXY_SSL_HEADER=true`
  - `DJANGO_CSRF_COOKIE_SECURE=true`
  - `DJANGO_SESSION_COOKIE_SECURE=true`

> Hinweis: In `DJANGO_CSRF_TRUSTED_ORIGINS` muss Schema+Host (und ggf. Port) exakt stimmen.

### Lokal (Pipenv)
```bash
pipenv sync
pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

## Konfiguration im UI
- Einstellungen → Jellyfin: Server‑URL + API‑Key
- Einstellungen → Sonarr/Radarr: Base‑URLs + API‑Keys (inkl. „Test“-Knopf)
- Einstellungen → Mailserver: SMTP (Host/Port/TLS/SSL/Benutzer/Passwort/From)
- Einstellungen → Notifications:
  - ntfy: Server‑URL, Default‑Topic, Basic‑Auth oder Bearer‑Token
  - Apprise: Default‑URL(s) (eine pro Zeile)
- Profil (pro Nutzer):
  - Kanal wählen: E‑Mail, ntfy oder Apprise
  - ntfy Topic (optional, überschreibt Default)
  - Apprise URL(s) (optional, ergänzen die Defaults)

## ntfy – Hinweise
- Server‑URL: z. B. `https://ntfy.sh` oder eigener Server
- Auth:
  - Bearer‑Token (Header)
  - Basic‑Auth (Benutzer/Passwort)
- Topic:
  - pro Nutzer frei wählbar (Profil) oder globales Default‑Topic (Einstellungen)

## Apprise – Hinweise
- Trag eine oder mehrere Ziel‑URLs ein (pro Zeile), z. B.:
  - `gotify://TOKEN@gotify.example.com/`  
  - `discord://webhook_id/webhook_token`  
  - `mailto://user:pass@smtp.example.com`  
  - `pover://user@token`  
  - `json://webhook.example.com/path`
- Nutzer können eigene URLs ergänzen; die globalen Defaults bleiben zusätzlich aktiv.

## Benachrichtigungslogik
- Serien: Es wird pro Abo am Release‑Tag geprüft, ob die Episode bereits als Datei vorhanden ist (Sonarr `hasFile`).
- Filme: Analog über Radarr `hasFile` und Release‑Datum (Digital/Disc/Kino‐Tag).
- Doppelversand wird per `SentNotification` unterdrückt (täglich pro Item/Nutzer).
- Fallback: Wenn ntfy/Apprise scheitern, wird E‑Mail versendet (falls konfiguriert).

## Jobs / Manuell anstoßen
- Regelmäßiger Check per Management Command (z. B. via Cron):
```bash
pipenv run python manage.py check_new_media
```
- In Docker:
```bash
docker compose exec web python manage.py check_new_media
```

## Sicherheit & Proxy
- Setze `DJANGO_ALLOWED_HOSTS` auf deine(n) Hostnamen.
- Füge alle genutzten Ursprünge in `DJANGO_CSRF_TRUSTED_ORIGINS` hinzu (http/https und Port beachten).
- Hinter Reverse‑Proxy TLS aktivieren: `USE_X_FORWARDED_HOST`, `DJANGO_SECURE_PROXY_SSL_HEADER`, Cookie‑Flags.

## Tech‑Stack
- Backend: Django 5 + DRF
- Integrationen: Sonarr/Radarr (API v3)
- Auth: Jellyfin
- Notifications: SMTP, ntfy (HTTP), Apprise
- Frontend: Templates + FullCalendar
- DB: SQLite (default)

## Lizenz
MIT
# Subscribarr

# Subscribarr

Subscribarr is a notification tool for the *Arr ecosystem (Sonarr, Radarr) and Jellyfin. Users can subscribe to shows/movies; when new episodes/releases are available (and actually present), Subscribarr sends email notifications.

---

## Screenshots

![Overview](screenshots/SCR-20250811-lfod.png)
![Settings](screenshots/SCR-20250811-lfrm.png)
![Subscriptions](screenshots/SCR-20250811-lfvc.png)
![Search](screenshots/SCR-20250811-lfyq.png)
![Details](screenshots/SCR-20250811-lgau.png)
![Notifications](screenshots/SCR-20250811-lgcz.png)

---

## Features

- **Login via Jellyfin** (use your Jellyfin account; admin status respected)
- **Subscriptions** for series and movies; duplicate-send protection per user/day
- **Email notifications** (SMTP configurable)
- **Sonarr/Radarr integration** (calendar/status; optional file-presence check)
- **Settings UI** for Jellyfin/Arr/Mail/Account
- **Periodic check via cron** calling `manage.py check_new_media`

---

## Architecture / Tech Stack

- **Backend:** Django + Django REST Framework  
- **Apps (examples):** `arr_api`, `accounts`, `settingspanel`  
- **Database:** SQLite by default (path configurable via env)  
- **Auth:** Jellyfin API (admin mirrored from Jellyfin policy)

---

## Quickstart (Docker)

### 1) Clone & run
```bash
git clone https://gitea.js-devop.de/jschaufuss/Subscribarr.git
cd Subscribarr
docker compose up -d --build
```

- Default app port inside the container: **8000**  
- Optional: set `CRON_SCHEDULE` (e.g., `*/30 * * * *`) to enable periodic checks

### 2) Minimal `docker-compose.yml` (example)
```yaml
---
services:
  subscribarr:
    build: .
    container_name: subscribarr
    ports:
      - "8081:8000"
    environment:
      # Django
      - DJANGO_DEBUG=true
      - USE_X_FORWARDED_HOST=true
      - DJANGO_SECURE_PROXY_SSL_HEADER=true
      - DJANGO_CSRF_COOKIE_SECURE=true
      - DJANGO_SESSION_COOKIE_SECURE=true
      - DJANGO_ALLOWED_HOSTS=*
      - DJANGO_SECRET_KEY=change-me
      - DB_PATH=/app/data/db.sqlite3
      - NOTIFICATIONS_ALLOW_DUPLICATES=false
      - DJANGO_CSRF_TRUSTED_ORIGINS="https://subscribarr.local.js-devop.de"
      # App Settings (optional, otherwise use first-run setup)
      #- JELLYFIN_URL=
      #- JELLYFIN_API_KEY=
      #- SONARR_URL=
      #- SONARR_API_KEY=
      #- RADARR_URL=
      #- RADARR_API_KEY=
      #- MAIL_HOST=
      #- MAIL_PORT=
      #- MAIL_SECURE=
      #- MAIL_USER=
      #- MAIL_PASSWORD=
      #- MAIL_FROM=
      # Admin bootstrap (optional)
      #- ADMIN_USERNAME=
      #- ADMIN_PASSWORD=
      #- ADMIN_EMAIL=
      # Cron schedule (default every 30min)
      - CRON_SCHEDULE=*/30 * * * *
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## Environment Variables (selection)

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | `true` / `false` (disable in production). |
| `DJANGO_ALLOWED_HOSTS` | Comma list of allowed hosts (e.g., `example.com,localhost`). |
| `DJANGO_SECRET_KEY` | Django secret key. |
| `DB_PATH` | SQLite path, e.g., `/app/data/db.sqlite3`. |
| `NOTIFICATIONS_ALLOW_DUPLICATES` | Allow duplicate sends (`true`/`false`). |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` | Optional: bootstrap an admin user on first run. |
| `JELLYFIN_URL` / `JELLYFIN_API_KEY` | Base URL + API key for Jellyfin. |
| `SONARR_URL` / `SONARR_API_KEY` | Base URL + API key for Sonarr. |
| `RADARR_URL` / `RADARR_API_KEY` | Base URL + API key for Radarr. |
| `MAIL_HOST` / `MAIL_PORT` / `MAIL_SECURE` | SMTP host/port/security (`starttls` / `ssl` / empty). |
| `MAIL_USER` / `MAIL_PASSWORD` / `MAIL_FROM` | SMTP auth + sender address. |
| `CRON_SCHEDULE` | Cron interval for periodic checks (e.g., `*/30 * * * *`). |

---

## First Run

1. Start the container (or dev server) and open `http://<host>:8081`.  
2. Complete the **first-time setup**: Jellyfin URL/API key (required), optional Sonarr/Radarr, SMTP.  
3. **Sign in** with Jellyfin credentials (admin users in Jellyfin become admins in Subscribarr).  
4. Adjust settings later at `/settings/`.

---

## Notifications & Cron

- The periodic job calls `check_new_media` which determines today’s items via Sonarr/Radarr calendars.  
- Email is sent only if the item is **present** (e.g., `hasFile`/downloaded) and not already recorded in the sent-log (duplicate guard).  
- Cron is configured using `CRON_SCHEDULE` and runs `python manage.py check_new_media`. Output is typically logged to `/app/cron.log` in the container.

---

## Routes / Endpoints (selected)

- `GET /` — Overview page with search/filter and subscribe actions  
- `GET/POST /settings/` — Jellyfin/Arr/Mail/Account configuration (auth required; admin for some actions)  
- Example subscribe endpoints (subject to change):  
  - `POST /api/series/subscribe/<series_id>/`, `POST /api/series/unsubscribe/<series_id>/`  
  - `POST /api/movies/subscribe/<movie_id>/`, `POST /api/movies/unsubscribe/<movie_id>/`

---

## Local Development (without Docker)

> Requires Python 3.12+ (recommended).

### 1) Clone
```bash
git clone https://gitea.js-devop.de/jschaufuss/Subscribarr.git
cd Subscribarr
```

### 2) Create & activate a virtualenv
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

### 3) Install dependencies (including Django)
If the repository provides `requirements.txt`:
```bash
pip install --upgrade pip wheel
pip install -r requirements.txt
```
If not, install the core stack explicitly:
```bash
pip install --upgrade pip wheel
pip install "Django>=5" djangorestframework python-dotenv
# add any additional libs your project uses as needed
```

### 4) Configure environment (dev)
Create a `.env` (or export env vars) with at least:
```env
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=dev-secret
DJANGO_ALLOWED_HOSTS=*
DB_PATH=./data/db.sqlite3
```
Create the `data/` directory if it doesn’t exist.

### 5) Database setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6) (Optional) Create a superuser for the Django admin
```bash
python manage.py createsuperuser
```

### 7) Run the dev server
```bash
python manage.py runserver 0.0.0.0:8000
```

---

## Data Model (high level)

- **User** (`accounts.User`): custom user with Jellyfin link and admin flag.  
- **Subscriptions** (`arr_api.SeriesSubscription`, `arr_api.MovieSubscription`): unique per user/title.  
- **SentNotification**: records delivered emails to avoid duplicates.  
- **AppSettings**: singleton for Jellyfin/Arr/Mail/Account configuration.

---

## Production Notes

- Set **`DEBUG=false`**, a strong **`DJANGO_SECRET_KEY`**, and proper **`DJANGO_ALLOWED_HOSTS`**.  
- Run behind a reverse proxy with HTTPS.  
- Collect static files if served by Django:  
  ```bash
  python manage.py collectstatic --noinput
  ```
- Use a persistent database volume (or switch to Postgres/MySQL) for production.

---

## License

MIT (see `LICENSE`).
