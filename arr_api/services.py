# arr_api/services.py
import os
import requests
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

# ENV-Fallbacks
ENV_SONARR_URL = os.getenv("SONARR_URL", "")
ENV_SONARR_KEY = os.getenv("SONARR_API_KEY", "")
ENV_RADARR_URL = os.getenv("RADARR_URL", "")
ENV_RADARR_KEY = os.getenv("RADARR_API_KEY", "")
DEFAULT_DAYS = int(os.getenv("ARR_DEFAULT_DAYS", "30"))

class ArrServiceError(Exception):
    pass

def _get(url, headers, params=None, timeout=5):
    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        raise ArrServiceError(str(e))

def _abs_url(base: str, p: str | None) -> str | None:
    if not p:
        return None
    return f"{base.rstrip('/')}{p}" if p.startswith("/") else p

def sonarr_calendar(days: int | None = None, base_url: str | None = None, api_key: str | None = None):
    base = (base_url or ENV_SONARR_URL).strip()
    key  = (api_key  or ENV_SONARR_KEY).strip()
    if not base or not key:
        return []
    d = days or DEFAULT_DAYS
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=d)

    url = f"{base.rstrip('/')}/api/v3/calendar"
    headers = {"X-Api-Key": key}
    data = _get(url, headers, params={
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "unmonitored": "false",
        "includeSeries": "true",
    })

    out = []
    for ep in data:
        series = ep.get("series") or {}
        # Poster finden
        poster = None
        for img in (series.get("images") or []):
            if (img.get("coverType") or "").lower() == "poster":
                poster = img.get("remoteUrl") or _abs_url(base, img.get("url"))
                if poster:
                    break

        aired = isoparse(ep["airDateUtc"]).isoformat() if ep.get("airDateUtc") else None
        out.append({
            "seriesId": series.get("id"),
            "seriesTitle": series.get("title"),
            "seriesStatus": (series.get("status") or "").lower(),
            "seriesPoster": poster,
            "seriesOverview": series.get("overview") or "",
            "seriesGenres": series.get("genres") or [],
            "episodeId": ep.get("id"),
            "seasonNumber": ep.get("seasonNumber"),
            "episodeNumber": ep.get("episodeNumber"),
            "title": ep.get("title"),
            "airDateUtc": aired,
            "tvdbId": series.get("tvdbId"),
            "imdbId": series.get("imdbId"),
            "network": series.get("network"),
        })
    return [x for x in out if x["seriesStatus"] == "continuing"]

def radarr_calendar(days: int | None = None, base_url: str | None = None, api_key: str | None = None):
    base = (base_url or ENV_RADARR_URL).strip()
    key  = (api_key  or ENV_RADARR_KEY).strip()
    if not base or not key:
        return []
    d = days or DEFAULT_DAYS
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=d)

    url = f"{base.rstrip('/')}/api/v3/calendar"
    headers = {"X-Api-Key": key}
    data = _get(url, headers, params={
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "unmonitored": "false",
        "includeMovie": "true",
    })

    out = []
    for it in data:
        movie = it.get("movie") or it
        # Poster finden
        poster = None
        for img in (movie.get("images") or []):
            if (img.get("coverType") or "").lower() == "poster":
                poster = img.get("remoteUrl") or _abs_url(base, img.get("url"))
                if poster:
                    break

        out.append({
            "movieId": movie.get("id"),
            "title": movie.get("title"),
            "year": movie.get("year"),
            "tmdbId": movie.get("tmdbId"),
            "imdbId": movie.get("imdbId"),
            "posterUrl": poster,
            "overview": movie.get("overview") or "",
            "inCinemas": movie.get("inCinemas"),
            "physicalRelease": movie.get("physicalRelease"),
            "digitalRelease": movie.get("digitalRelease"),
            "hasFile": movie.get("hasFile"),
            "isAvailable": movie.get("isAvailable"),
        })

    def is_upcoming(m):
        for k in ("inCinemas", "physicalRelease", "digitalRelease"):
            v = m.get(k)
            if v:
                try:
                    if isoparse(v) > datetime.now(timezone.utc):
                        return True
                except Exception:
                    pass
        return False

    return [m for m in out if is_upcoming(m)]
