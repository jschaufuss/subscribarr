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
    return f"{base.rstrip('/')}" + p if p.startswith("/") else p

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

def sonarr_get_series(series_id: int, base_url: str | None = None, api_key: str | None = None) -> dict | None:
    """Fetch a single series by id from Sonarr, return dict with title, overview, poster and genres."""
    base = (base_url or ENV_SONARR_URL).strip()
    key  = (api_key  or ENV_SONARR_KEY).strip()
    if not base or not key:
        return None
    url = f"{base.rstrip('/')}/api/v3/series/{series_id}"
    headers = {"X-Api-Key": key}
    data = _get(url, headers)
    # Poster
    poster = None
    for img in (data.get("images") or []):
        if (img.get("coverType") or "").lower() == "poster":
            poster = img.get("remoteUrl") or _abs_url(base, img.get("url"))
            if poster:
                break
    return {
        "series_id": data.get("id"),
        "series_title": data.get("title"),
        "series_overview": data.get("overview") or "",
        "series_genres": data.get("genres") or [],
        "series_poster": poster,
    }

def radarr_lookup_movie_by_title(title: str, base_url: str | None = None, api_key: str | None = None) -> dict | None:
    """Lookup a movie by title via Radarr /api/v3/movie/lookup. Returns title, poster, overview, genres, year, tmdbId, and id if present."""
    base = (base_url or ENV_RADARR_URL).strip()
    key  = (api_key  or ENV_RADARR_KEY).strip()
    if not base or not key or not title:
        return None
    url = f"{base.rstrip('/')}/api/v3/movie/lookup"
    headers = {"X-Api-Key": key}
    data = _get(url, headers, params={"term": title})
    if not data:
        return None
    # naive pick: exact match by title (case-insensitive), else first
    best = None
    for it in data:
        if (it.get("title") or "").lower() == title.lower():
            best = it
            break
    if not best:
        best = data[0]
    poster = None
    for img in (best.get("images") or []):
        if (img.get("coverType") or "").lower() == "poster":
            poster = img.get("remoteUrl") or _abs_url(base, img.get("url"))
            if poster:
                break
    return {
        "movie_id": best.get("id") or 0,
        "title": best.get("title") or title,
        "poster": poster,
        "overview": best.get("overview") or "",
        "genres": best.get("genres") or [],
        "year": best.get("year"),
        "tmdbId": best.get("tmdbId"),
    }
