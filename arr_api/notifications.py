from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from settingspanel.models import AppSettings
# from accounts.utils import JellyfinClient  # not needed for availability; use Sonarr/Radarr instead
import requests
from dateutil.parser import isoparse
import logging

logger = logging.getLogger(__name__)

def _set_runtime_email_settings():
    app_settings = AppSettings.current()
    sec = (app_settings.mail_secure or '').strip().lower()
    use_tls = sec in ('tls', 'starttls', 'start_tls', 'tls1.2', 'tls1_2')
    use_ssl = sec in ('ssl', 'smtps')
    # Prefer SSL over TLS if both matched somehow
    if use_ssl:
        use_tls = False

    # Apply email settings dynamically for this process
    settings.EMAIL_HOST = (app_settings.mail_host or settings.EMAIL_HOST)
    # Port defaults if not provided
    if app_settings.mail_port:
        settings.EMAIL_PORT = int(app_settings.mail_port)
    else:
        if use_ssl and not settings.EMAIL_PORT:
            settings.EMAIL_PORT = 465
        elif use_tls and not settings.EMAIL_PORT:
            settings.EMAIL_PORT = 587

    settings.EMAIL_USE_TLS = use_tls
    settings.EMAIL_USE_SSL = use_ssl

    settings.EMAIL_HOST_USER = app_settings.mail_user or settings.EMAIL_HOST_USER
    settings.EMAIL_HOST_PASSWORD = app_settings.mail_password or settings.EMAIL_HOST_PASSWORD

    # From email fallback
    if app_settings.mail_from:
        settings.DEFAULT_FROM_EMAIL = app_settings.mail_from
    elif not getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        host = (settings.EMAIL_HOST or 'localhost')
        settings.DEFAULT_FROM_EMAIL = f'noreply@{host}'

    # return summary for debugging
    return {
        'host': settings.EMAIL_HOST,
        'port': settings.EMAIL_PORT,
        'use_tls': settings.EMAIL_USE_TLS,
        'use_ssl': settings.EMAIL_USE_SSL,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'auth_user_set': bool(settings.EMAIL_HOST_USER),
    }


def send_notification_email(
    user,
    media_title,
    media_type,
    overview=None,
    poster_url=None,
    episode_title=None,
    season=None,
    episode=None,
    air_date=None,
    year=None,
    release_type=None,
):
    """
    Sendet eine Benachrichtigungs-E-Mail an einen User mit erweiterten Details
    """
    eff = _set_runtime_email_settings()
    logger.info(
        "Email settings: host=%s port=%s tls=%s ssl=%s from=%s auth_user_set=%s",
        eff['host'], eff['port'], eff['use_tls'], eff['use_ssl'], eff['from_email'], eff['auth_user_set']
    )

    # Format air date if provided
    air_date_str = None
    if air_date:
        try:
            from dateutil.parser import isoparse as _iso
            dt = _iso(air_date) if isinstance(air_date, str) else air_date
            try:
                tz = timezone.get_current_timezone()
                dt = dt.astimezone(tz)
            except Exception:
                pass
            air_date_str = dt.strftime('%d.%m.%Y %H:%M')
        except Exception:
            air_date_str = str(air_date)

    context = {
        'username': user.username,
        'title': media_title,
        'type': 'Serie' if media_type == 'series' else 'Film',
        'overview': overview,
        'poster_url': poster_url,
        'episode_title': episode_title,
        'season': season,
        'episode': episode,
        'air_date': air_date_str,
        'year': year,
        'release_type': release_type,
    }

    subject = f"Neue {context['type']} verfügbar: {media_title}"
    message = render_to_string('arr_api/email/new_media_notification.html', context)

    # Fallback to dispatch respecting user preference
    try:
        # strip HTML tags for body_text basic fallback
        import re
        body_text = re.sub('<[^<]+?>', '', message)
    except Exception:
        body_text = message
    _dispatch_user_notification(user, subject=subject, body_text=body_text, html_message=message)


def _send_ntfy(user, title: str, message: str, click_url: str | None = None):
    cfg = AppSettings.current()
    base = (cfg.ntfy_server_url or '').strip().rstrip('/')
    if not base:
        return False
    topic = (user.ntfy_topic or cfg.ntfy_topic_default or '').strip()
    if not topic:
        return False
    url = f"{base}/{topic}"
    headers = {"Title": title}
    if click_url:
        headers["Click"] = click_url
    if cfg.ntfy_token:
        headers["Authorization"] = f"Bearer {cfg.ntfy_token}"
    elif cfg.ntfy_user and cfg.ntfy_password:
        # basic auth via requests
        auth = (cfg.ntfy_user, cfg.ntfy_password)
    else:
        auth = None
    try:
        r = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=8, auth=auth if 'auth' in locals() else None)
        return r.status_code // 100 == 2
    except Exception:
        return False


def _send_apprise(user, title: str, message: str):
    # Lazy import apprise, optional dependency
    try:
        import apprise
    except Exception:
        return False
    cfg = AppSettings.current()
    urls = []
    if user.apprise_url:
        urls.extend([u.strip() for u in str(user.apprise_url).splitlines() if u.strip()])
    if cfg.apprise_default_url:
        urls.extend([u.strip() for u in str(cfg.apprise_default_url).splitlines() if u.strip()])
    if not urls:
        return False
    app = apprise.Apprise()
    for u in urls:
        app.add(u)
    return app.notify(title=title, body=message)


def _dispatch_user_notification(user, subject: str, body_text: str, html_message: str | None = None, click_url: str | None = None):
    channel = getattr(user, 'notification_channel', 'email') or 'email'
    if channel == 'ntfy':
        ok = _send_ntfy(user, title=subject, message=body_text, click_url=click_url)
        if ok:
            return True
        # fallback to email
    if channel == 'apprise':
        ok = _send_apprise(user, title=subject, message=body_text)
        if ok:
            return True
        # fallback to email
    try:
        send_mail(
            subject=subject,
            message=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def _get_arr_cfg():
    cfg = AppSettings.current()
    return {
        'sonarr_url': (cfg.sonarr_url or '').strip(),
        'sonarr_key': (cfg.sonarr_api_key or '').strip(),
        'radarr_url': (cfg.radarr_url or '').strip(),
        'radarr_key': (cfg.radarr_api_key or '').strip(),
    }


def _sonarr_get(url_base, api_key, path, params=None, timeout=10):
    if not url_base or not api_key:
        return None
    url = f"{url_base.rstrip('/')}{path}"
    try:
        r = requests.get(url, headers={"X-Api-Key": api_key}, params=params or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def _radarr_get(url_base, api_key, path, params=None, timeout=10):
    if not url_base or not api_key:
        return None
    url = f"{url_base.rstrip('/')}{path}"
    try:
        r = requests.get(url, headers={"X-Api-Key": api_key}, params=params or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def sonarr_episode_has_file(series_id: int, season: int, episode: int) -> bool:
    cfg = _get_arr_cfg()
    data = _sonarr_get(cfg['sonarr_url'], cfg['sonarr_key'], "/api/v3/episode", params={"seriesId": series_id}) or []
    for ep in data:
        if ep.get("seasonNumber") == season and ep.get("episodeNumber") == episode:
            return bool(ep.get("hasFile"))
    return False


def radarr_movie_has_file(movie_id: int) -> bool:
    cfg = _get_arr_cfg()
    data = _radarr_get(cfg['radarr_url'], cfg['radarr_key'], f"/api/v3/movie/{movie_id}")
    if not data:
        return False
    return bool(data.get("hasFile"))


def get_todays_sonarr_calendar():
    from .services import sonarr_calendar
    cfg = _get_arr_cfg()
    items = sonarr_calendar(days=1, base_url=cfg['sonarr_url'], api_key=cfg['sonarr_key']) or []
    today = timezone.now().date()
    todays = []
    for it in items:
        try:
            ad = isoparse(it.get("airDateUtc")) if it.get("airDateUtc") else None
            if ad and ad.date() == today:
                todays.append(it)
        except Exception:
            pass
    return todays


def get_todays_radarr_calendar():
    from .services import radarr_calendar
    cfg = _get_arr_cfg()
    items = radarr_calendar(days=1, base_url=cfg['radarr_url'], api_key=cfg['radarr_key']) or []
    today = timezone.now().date()
    todays = []
    for it in items:
        # consider any of the dates equal today
        for k in ("inCinemas", "physicalRelease", "digitalRelease"):
            v = it.get(k)
            if not v:
                continue
            try:
                d = isoparse(v).date()
                if d == today:
                    todays.append(it)
                    break
            except Exception:
                continue
    return todays


def check_jellyfin_availability(user, media_id, media_type):
    """
    Ersetzt: Wir prüfen Verfügbarkeit über Sonarr/Radarr (hasFile),
    was zuverlässig ist, wenn Jellyfin dieselben Ordner scannt.
    """
    # user is unused here; kept for backward compatibility
    if media_type == 'series':
        # cannot decide without season/episode here; will be handled in main loop
        return False
    else:
        return radarr_movie_has_file(media_id)


def check_and_notify_users():
    """
    Hauptfunktion die periodisch aufgerufen wird.
    Prüft neue Medien und sendet Benachrichtigungen.
    """
    from .models import SeriesSubscription, MovieSubscription, SentNotification

    # calendars for today
    todays_series = get_todays_sonarr_calendar()
    todays_movies = get_todays_radarr_calendar()

    # index by ids for quick lookup
    series_idx = {}
    for it in todays_series:
        sid = it.get("seriesId")
        if not sid:
            continue
        series_idx.setdefault(sid, []).append(it)

    movie_idx = {it.get("movieId"): it for it in todays_movies if it.get("movieId")}

    today = timezone.now().date()

    # Serien-Abos
    for sub in SeriesSubscription.objects.select_related('user').all():
        if sub.series_id not in series_idx:
            continue
        # iterate today's episodes for this series
        for ep in series_idx[sub.series_id]:
            season = ep.get("seasonNumber")
            number = ep.get("episodeNumber")
            if season is None or number is None:
                continue

            # duplicate guard (per series per day per user)
            if not getattr(settings, 'NOTIFICATIONS_ALLOW_DUPLICATES', False):
                already_notified = SentNotification.objects.filter(
                    media_id=sub.series_id,
                    media_type='series',
                    air_date=today,
                    user=sub.user
                ).exists()
                if already_notified:
                    continue

            # check availability via Sonarr hasFile
            if sonarr_episode_has_file(sub.series_id, season, number):
                if not sub.user.email:
                    continue
                # Build subject/body
                subj = f"New episode available: {sub.series_title} S{season:02d}E{number:02d}"
                body = f"{sub.series_title} S{season:02d}E{number:02d} is now available."
                # Prefer HTML email rendering if channel falls back to email
                html = None
                try:
                    ctx = {
                        'username': sub.user.username,
                        'title': sub.series_title,
                        'type': 'Serie',
                        'overview': sub.series_overview,
                        'poster_url': ep.get('seriesPoster'),
                        'episode_title': ep.get('title'),
                        'season': season,
                        'episode': number,
                        'air_date': ep.get('airDateUtc'),
                    }
                    html = render_to_string('arr_api/email/new_media_notification.html', ctx)
                except Exception:
                    pass
                ok = _dispatch_user_notification(sub.user, subject=subj, body_text=body, html_message=html)
                # mark as sent unless duplicates are allowed
                if ok and not getattr(settings, 'NOTIFICATIONS_ALLOW_DUPLICATES', False):
                    SentNotification.objects.create(
                        user=sub.user,
                        media_id=sub.series_id,
                        media_type='series',
                        media_title=sub.series_title,
                        air_date=today
                    )

    # Film-Abos
    for sub in MovieSubscription.objects.select_related('user').all():
        it = movie_idx.get(sub.movie_id)
        if not it:
            continue

        if not getattr(settings, 'NOTIFICATIONS_ALLOW_DUPLICATES', False):
            already_notified = SentNotification.objects.filter(
                media_id=sub.movie_id,
                media_type='movie',
                air_date=today,
                user=sub.user
            ).exists()
            if already_notified:
                continue

        if radarr_movie_has_file(sub.movie_id):
            if not sub.user.email:
                continue
            # detect which release matched today
            rel = None
            try:
                for key, name in (("digitalRelease", "Digital"), ("physicalRelease", "Disc"), ("inCinemas", "Kino")):
                    v = it.get(key)
                    if not v:
                        continue
                    d = isoparse(v).date()
                    if d == today:
                        rel = name
                        break
            except Exception:
                pass

            subj = f"New movie available: {sub.title}"
            if rel:
                subj += f" ({rel})"
            body = f"{sub.title} is now available."
            html = None
            try:
                ctx = {
                    'username': sub.user.username,
                    'title': sub.title,
                    'type': 'Film',
                    'overview': sub.overview,
                    'poster_url': it.get('posterUrl'),
                    'year': it.get('year'),
                    'release_type': rel,
                }
                html = render_to_string('arr_api/email/new_media_notification.html', ctx)
            except Exception:
                pass
            ok = _dispatch_user_notification(sub.user, subject=subj, body_text=body, html_message=html)
            if ok and not getattr(settings, 'NOTIFICATIONS_ALLOW_DUPLICATES', False):
                SentNotification.objects.create(
                    user=sub.user,
                    media_id=sub.movie_id,
                    media_type='movie',
                    media_title=sub.title,
                    air_date=today
                )


def has_new_episode_today(series_id):
    """
    Legacy helper no longer used directly.
    """
    return True


def has_movie_release_today(movie_id):
    """
    Legacy helper no longer used directly.
    """
    return True
