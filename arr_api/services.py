# arr_api/services.py
import os
import requests
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from settingspanel.models import ArrInstance
from django.core.cache import cache
import hashlib
import json
from django.core.cache import cache

# ENV-Fallbacks
ENV_SONARR_URL = os.getenv("SONARR_URL", "")
ENV_SONARR_KEY = os.getenv("SONARR_API_KEY", "")
ENV_RADARR_URL = os.getenv("RADARR_URL", "")
ENV_RADARR_KEY = os.getenv("RADARR_API_KEY", "")
DEFAULT_DAYS = int(os.getenv("ARR_DEFAULT_DAYS", "30"))
M4K_LIST_TTL = int(os.getenv("ARR_4K_LIST_TTL", "180"))  # seconds
RADARR_LIST_TTL = int(os.getenv("ARR_RADARR_LIST_TTL", "300"))
HAS4K_TTL = int(os.getenv("ARR_HAS4K_TTL", "300"))
LOOKUP_TTL = int(os.getenv("ARR_LOOKUP_TTL", "300"))
MOVIE_AVAIL_TTL = int(os.getenv("ARR_MOVIE_AVAIL_TTL", "300"))

class ArrServiceError(Exception):
    pass

def _get(url, headers, params=None, timeout=5):
    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as ve:
            # Return first 120 chars of body to help debug wrong URL or auth
            snippet = (r.text or "")[:120].replace("\n", " ")
            raise ArrServiceError(f"Invalid JSON from {url} — check base URL and API key. Body: {snippet}") from ve
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


def radarr_lookup_movie_by_tmdb_id(tmdb_id: int, base_url: str | None = None, api_key: str | None = None) -> dict | None:
    """Lookup a movie by TMDB id via Radarr /api/v3/movie/lookup?term=tmdb:<id>."""
    if not tmdb_id:
        return None
    base = (base_url or ENV_RADARR_URL).strip()
    key  = (api_key  or ENV_RADARR_KEY).strip()
    if not base or not key:
        return None
    url = f"{base.rstrip('/')}/api/v3/movie/lookup"
    headers = {"X-Api-Key": key}
    try:
        data = _get(url, headers, params={"term": f"tmdb:{tmdb_id}"}) or []
    except ArrServiceError:
        data = []
    if not data:
        return None
    best = data[0]
    poster = None
    for img in (best.get("images") or []):
        if (img.get("coverType") or "").lower() == "poster":
            poster = img.get("remoteUrl") or _abs_url(base, img.get("url"))
            if poster:
                break
    return {
        "movie_id": best.get("id") or 0,
        "title": best.get("title") or "",
        "poster": poster,
        "overview": best.get("overview") or "",
        "genres": best.get("genres") or [],
        "year": best.get("year"),
        "tmdbId": best.get("tmdbId"),
    }


def _radarr_get(base: str, key: str, path: str, params: dict | None = None):
    if not base or not key:
        return None
    url = f"{base.rstrip('/')}{path}"
    try:
        r = requests.get(url, headers={"X-Api-Key": key}, params=params or {}, timeout=8)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def list_movies_missing_4k_across_instances() -> list[dict]:
    """
    Return unique movies known to Radarr instances that do NOT have any 4K file across all enabled Radarr instances.
    Uses qualityProfile/hasFile + mediaInfo.videoCodec/width heuristics.
    Output entries: { tmdbId, title, year, poster, overview }
    """
    movies_by_tmdb: dict[int, dict] = {}
    instances = list(ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id'))

    # Cache the aggregated list per instances fingerprint
    def _fp(insts: list[ArrInstance]) -> str:
        arr = []
        for i in insts:
            arr.append({
                'id': i.id,
                'base_url': (i.base_url or '').rstrip('/'),
                'enabled': bool(i.enabled),
                'order': i.order,
                'updated_at': i.updated_at.isoformat() if getattr(i, 'updated_at', None) else None,
            })
        raw = json.dumps(arr, sort_keys=True, separators=(',', ':'))
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    cache_key = f"arr:missing4k:v1:{_fp(instances)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    for inst in instances:
        # pull all movies; may be heavy for big libs, but acceptable MVP
        list_key = f"arr:radarr:v1:{inst.id}:movie_list"
        data = cache.get(list_key)
        if data is None:
            data = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie") or []
            cache.set(list_key, data, RADARR_LIST_TTL)
        for m in data:
            tmdb = m.get('tmdbId')
            if not tmdb:
                continue
            cur = movies_by_tmdb.get(tmdb)
            if not cur:
                # Keep basic fields and availability flags
                poster = None
                for img in (m.get('images') or []):
                    if (img.get('coverType') or '').lower() == 'poster':
                        poster = img.get('remoteUrl') or _abs_url(inst.base_url, img.get('url'))
                        if poster:
                            break
                movies_by_tmdb[tmdb] = {
                    'tmdbId': tmdb,
                    'title': m.get('title'),
                    'year': m.get('year'),
                    'poster': poster,
                    'overview': m.get('overview') or '',
                    '_has4k': False,
                }
        # Check 4K availability in this instance (cached)
        if _movie_has_4k_in_instance_cached(inst, m.get('id')):
                movies_by_tmdb[tmdb]['_has4k'] = True
    # Return only those that do not have 4K anywhere
    result = [v for v in movies_by_tmdb.values() if not v.get('_has4k')]
    cache.set(cache_key, result, M4K_LIST_TTL)
    return result


def _movie_has_4k_in_instance(base_url: str, api_key: str, movie_id: int) -> bool:
    if not base_url or not api_key or not movie_id:
        return False
    # Fetch movie file(s) to inspect resolution/mediainfo
    movie_obj = _radarr_get(base_url, api_key, f"/api/v3/movie/{movie_id}") or {}
    mf = movie_obj.get('movieFile') or {}
    files_list = None
    if not mf:
        # Fallback to explicit moviefile endpoint
        files_list = _radarr_get(base_url, api_key, f"/api/v3/moviefile", params={"movieId": movie_id}) or []
    else:
        files_list = [mf]
    if not files_list:
        return False
    # Heuristics for 4K: either width >= 3800 or quality name includes '2160p'/'UHD'/'4K'
    for f in files_list:
        try:
            width = int((f.get('mediaInfo') or {}).get('width') or 0)
        except Exception:
            width = 0
        qname = (((f.get('quality') or {}).get('quality') or {}).get('name') or '').lower()
        if width >= 3800 or any(k in qname for k in ('2160p','uhd','4k')):
            return True
    return False


def _movie_has_4k_in_instance_cached(inst: ArrInstance, movie_id: int) -> bool:
    if not inst or not movie_id:
        return False
    key = f"arr:radarr:v1:{inst.id}:has4k:{movie_id}"
    val = cache.get(key)
    if val is not None:
        return bool(val)
    ok = _movie_has_4k_in_instance(inst.base_url, inst.api_key, movie_id)
    cache.set(key, bool(ok), HAS4K_TTL)
    return ok


def tmdb_has_4k_any_instance(tmdb_id: int) -> bool:
    """Check if any enabled Radarr instance has a 4K file for a movie with this TMDB id."""
    instances = list(ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id'))
    for inst in instances:
        # Lookup by TMDB id on this instance
        data = None
        # Try to use cached full list first
        list_key = f"arr:radarr:v1:{inst.id}:movie_list"
        full = cache.get(list_key)
        if full is None:
            full = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie") or []
            cache.set(list_key, full, RADARR_LIST_TTL)
        # Filter for tmdb match in library
        data = [m for m in (full or []) if m.get('tmdbId') == tmdb_id]
        # If not found in library, fallback to lookup (cached)
        if not data:
            lk = f"arr:radarr:v1:{inst.id}:lookup:tmdb:{tmdb_id}"
            data = cache.get(lk)
            if data is None:
                data = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie/lookup", params={"term": f"tmdb:{tmdb_id}"}) or []
                cache.set(lk, data, LOOKUP_TTL)
        # If not found via lookup, try full list as fallback
        if not data:
            data = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie") or []
        for m in data:
            if m.get('tmdbId') == tmdb_id:
                if _movie_has_4k_in_instance_cached(inst, m.get('id')):
                    return True
    return False


# Jellyfin availability helper removed; Jellyfin is used for SSO only.

def _movie_is_available_in_instance(base_url: str, api_key: str, movie_id: int) -> bool:
    """Check if a Radarr movie has an available file in this instance."""
    if not base_url or not api_key or not movie_id:
        return False
    movie_obj = _radarr_get(base_url, api_key, f"/api/v3/movie/{movie_id}") or {}
    if movie_obj.get('hasFile') or movie_obj.get('isAvailable'):
        return True
    # Fallback: explicit moviefile query
    files_list = _radarr_get(base_url, api_key, f"/api/v3/moviefile", params={"movieId": movie_id}) or []
    return bool(files_list)

def _movie_is_available_in_instance_cached(inst: ArrInstance, movie_id: int) -> bool:
    if not inst or not movie_id:
        return False
    key = f"arr:radarr:v1:{inst.id}:hasfile:{movie_id}"
    val = cache.get(key)
    if val is not None:
        return bool(val)
    ok = _movie_is_available_in_instance(inst.base_url, inst.api_key, movie_id)
    cache.set(key, bool(ok), MOVIE_AVAIL_TTL)
    return ok

def tmdb_is_available_any_instance(tmdb_id: int) -> bool:
    """True if any enabled Radarr instance has the movie (tmdb_id) with a downloaded/available file."""
    if not tmdb_id:
        return False
    instances = list(ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id'))
    for inst in instances:
        # Try cached full list first
        list_key = f"arr:radarr:v1:{inst.id}:movie_list"
        full = cache.get(list_key)
        if full is None:
            full = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie") or []
            cache.set(list_key, full, RADARR_LIST_TTL)
        data = [m for m in (full or []) if m.get('tmdbId') == tmdb_id]
        if not data:
            # Fallback to lookup
            lk = f"arr:radarr:v1:{inst.id}:lookup:tmdb:{tmdb_id}"
            data = cache.get(lk)
            if data is None:
                data = _radarr_get(inst.base_url, inst.api_key, "/api/v3/movie/lookup", params={"term": f"tmdb:{tmdb_id}"}) or []
                cache.set(lk, data, LOOKUP_TTL)
        if not data:
            continue
        for m in data:
            if m.get('tmdbId') == tmdb_id:
                mid = m.get('id')
                if mid and _movie_is_available_in_instance_cached(inst, mid):
                    return True
    return False
