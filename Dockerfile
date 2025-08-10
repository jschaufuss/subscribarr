# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (include cron)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY Pipfile Pipfile.lock /app/
RUN pip install pipenv && PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --system

COPY . /app

# Optional non-root user (not used as default to allow cron)
RUN useradd -ms /bin/bash app && chown -R app:app /app
# USER app

# Runtime env defaults
ENV DJANGO_DEBUG=true \
    DJANGO_ALLOWED_HOSTS=* \
    DB_PATH=/app/data/db.sqlite3 \
    NOTIFICATIONS_ALLOW_DUPLICATES=false \
    CRON_SCHEDULE="*/30 * * * *" \
    ADMIN_USERNAME= \
    ADMIN_PASSWORD= \
    ADMIN_EMAIL=

# create data dir for sqlite
RUN mkdir -p /app/data

# Entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["/entrypoint.sh"]
