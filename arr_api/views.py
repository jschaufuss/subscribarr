from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from settingspanel.models import AppSettings, ArrInstance
from .services import sonarr_calendar, radarr_calendar, ArrServiceError, list_movies_missing_4k_across_instances, tmdb_has_4k_any_instance, radarr_lookup_movie_by_tmdb_id, jellyfin_has_movie_by_tmdb, tmdb_is_available_any_instance
from .models import SeriesSubscription, MovieSubscription, Movie4KSubscription
from django.utils import timezone


def _get_int(request, key, default):
    try:
        v = int(request.GET.get(key, default))
        return max(1, min(365, v))
    except (TypeError, ValueError):
        return default

def _arr_instances():
    inst = list(ArrInstance.objects.filter(enabled=True).order_by("order", "id"))
    if inst:
        return inst
    # Fallback to legacy single-instance fields for backward compatibility
    cfg = AppSettings.current()
    fallback = []
    if cfg.sonarr_url and cfg.sonarr_api_key:
        fallback.append(ArrInstance(kind="sonarr", name="Default", base_url=cfg.sonarr_url, api_key=cfg.sonarr_api_key))
    if cfg.radarr_url and cfg.radarr_api_key:
        fallback.append(ArrInstance(kind="radarr", name="Default", base_url=cfg.radarr_url, api_key=cfg.radarr_api_key))
    return fallback


#class SonarrAiringView(APIView):
#    def get(self, request):
#        days = _get_int(request, "days", 30)
#        conf = _arr_conf_from_db()
#        try:
#            data = sonarr_calendar(days=days, base_url=conf["sonarr_url"], api_key=conf["sonarr_key"])
#            return Response({"count": len(data), "results": data})
#        except ArrServiceError as e:
#            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


#class RadarrUpcomingMoviesView(APIView):
#    def get(self, request):
#        days = _get_int(request, "days", 60)
#        conf = _arr_conf_from_db()
#        try:
#            data = radarr_calendar(days=days, base_url=conf["radarr_url"], api_key=conf["radarr_key"])
#            return Response({"count": len(data), "results": data})
#        except ArrServiceError as e:
#            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


@method_decorator(login_required, name='dispatch')
class ArrIndexView(View):
    def get(self, request):
        q = (request.GET.get("q") or "").lower().strip()
        kind = (request.GET.get("kind") or "all").lower()
        days = _get_int(request, "days", 30)

        eps, movies = [], []
        for inst in _arr_instances():
            if inst.kind == "sonarr":
                try:
                    eps.extend(sonarr_calendar(days=days, base_url=inst.base_url, api_key=inst.api_key))
                except ArrServiceError as e:
                    messages.error(request, f"Sonarr ({inst.name}) is not reachable: {e}")
            elif inst.kind == "radarr":
                try:
                    movies.extend(radarr_calendar(days=days, base_url=inst.base_url, api_key=inst.api_key))
                except ArrServiceError as e:
                    messages.error(request, f"Radarr ({inst.name}) is not reachable: {e}")

        # Suche
        if q:
            eps = [e for e in eps if q in (e.get("seriesTitle") or "").lower()]
            movies = [m for m in movies if q in (m.get("title") or "").lower()]

        # Abonnierte Serien und Filme pro aktuellem Nutzer
        if request.user.is_authenticated:
            subscribed_series_ids = set(SeriesSubscription.objects.filter(user=request.user).values_list('series_id', flat=True))
            subscribed_movie_ids = set(MovieSubscription.objects.filter(user=request.user).values_list('movie_id', flat=True))
        else:
            subscribed_series_ids = set()
            subscribed_movie_ids = set()

        # Gruppierung nach Serie
        groups = defaultdict(lambda: {
            "seriesId": None, "seriesTitle": None, "seriesPoster": None,
            "seriesOverview": "", "seriesGenres": [], "episodes": [], "is_subscribed": False,
        })
        for e in eps:
            sid = e["seriesId"]
            g = groups[sid]
            g["seriesId"] = sid
            g["seriesTitle"] = e["seriesTitle"]
            g["seriesPoster"] = g["seriesPoster"] or e.get("seriesPoster")
            if not g["seriesOverview"] and e.get("seriesOverview"):
                g["seriesOverview"] = e["seriesOverview"]
            if not g["seriesGenres"] and e.get("seriesGenres"):
                g["seriesGenres"] = e["seriesGenres"]
            g["episodes"].append({
                "episodeId": e["episodeId"],
                "seasonNumber": e["seasonNumber"],
                "episodeNumber": e["episodeNumber"],
                "title": e["title"],
                "airDateUtc": e["airDateUtc"],
            })

        series_grouped = []
        for g in groups.values():
            g["episodes"].sort(key=lambda x: (x["airDateUtc"] or ""))
            g["is_subscribed"] = g["seriesId"] in subscribed_series_ids
            series_grouped.append(g)

        # Filter: hide movies already available (downloaded) in any configured Radarr instance by tmdbId
        def avail_filter(m):
            try:
                tid = int(m.get('tmdbId') or 0)
            except Exception:
                tid = 0
            if not tid:
                return True
            return not tmdb_is_available_any_instance(tid)
        movies = [m for m in movies if avail_filter(m)]

        # Markiere abonnierte Filme
        for movie in movies:
            movie["is_subscribed"] = movie.get("movieId") in subscribed_movie_ids

        return render(request, "arr_api/index.html", {
            "query": q,
            "kind": kind,
            "days": days,
            "show_series": kind in ("all", "series"),
            "show_movies": kind in ("all", "movies"),
            "series_grouped": series_grouped,
            "movies": movies,
        })


@method_decorator(login_required, name='dispatch')
class CalendarView(View):
    def get(self, request):
        days = _get_int(request, "days", 60)
        return render(request, "arr_api/calendar.html", {"days": days})


@method_decorator(login_required, name='dispatch')
class CalendarEventsApi(APIView):
    def get(self, request):
        days = _get_int(request, "days", 60)
        eps, movies = [], []
        for inst in _arr_instances():
            if inst.kind == "sonarr":
                try:
                    eps.extend(sonarr_calendar(days=days, base_url=inst.base_url, api_key=inst.api_key))
                except ArrServiceError:
                    pass
            elif inst.kind == "radarr":
                try:
                    movies.extend(radarr_calendar(days=days, base_url=inst.base_url, api_key=inst.api_key))
                except ArrServiceError:
                    pass

        series_sub = set(SeriesSubscription.objects.filter(user=request.user).values_list('series_id', flat=True))
        movie_sub_titles = set(MovieSubscription.objects.filter(user=request.user).values_list('title', flat=True))

        events = []
        for e in eps:
            when = e.get("airDateUtc")
            if not when:
                continue
            events.append({
                "id": f"s:{e.get('seriesId')}:{e.get('episodeId')}",
                "title": f"{e.get('seriesTitle','')} — S{e.get('seasonNumber')}E{e.get('episodeNumber')}",
                "start": when,
                "allDay": False,
                "extendedProps": {
                    "kind": "series",
                    "seriesId": e.get('seriesId'),
                    "seriesTitle": e.get('seriesTitle'),
                    "seasonNumber": e.get('seasonNumber'),
                    "episodeNumber": e.get('episodeNumber'),
                    "episodeTitle": e.get('title'),
                    "overview": e.get('seriesOverview') or "",
                    "poster": e.get('seriesPoster') or "",
                    "subscribed": int(e.get('seriesId') or 0) in series_sub,
                }
            })

        for m in movies:
            # Skip movies already available (downloaded) in any Radarr instance (by tmdbId)
            try:
                tid = int(m.get('tmdbId') or 0)
            except Exception:
                tid = 0
            if tid and tmdb_is_available_any_instance(tid):
                continue
            when = m.get('digitalRelease') or m.get('physicalRelease') or m.get('inCinemas')
            if not when:
                continue
            events.append({
                "id": f"m:{m.get('movieId') or m.get('title')}",
                "title": m.get('title') or "(movie)",
                "start": when,
                "allDay": True,
                "extendedProps": {
                    "kind": "movie",
                    "movieId": m.get('movieId'),
                    "title": m.get('title'),
                    "overview": m.get('overview') or "",
                    "poster": m.get('posterUrl') or "",
                    "subscribed": (m.get('title') or '') in movie_sub_titles,
                }
            })

        return Response({"events": events})


 


@require_POST
@login_required
def subscribe_series(request, series_id):
    """Subscribe to a series"""
    try:
        # Existiert bereits?
        if SeriesSubscription.objects.filter(user=request.user, series_id=series_id).exists():
            return JsonResponse({'success': True, 'already_subscribed': True})

        # Hole Serien-Details vom Sonarr
        conf = _arr_conf_from_db()
        # TODO: Sonarr API Call für Series Details

        # Erstelle Subscription
        sub = SeriesSubscription.objects.create(
            user=request.user,
            series_id=series_id,
            series_title=request.POST.get('title', ''),
            series_poster=request.POST.get('poster', ''),
            series_overview=request.POST.get('overview', ''),
            series_genres=request.POST.getlist('genres[]', [])
        )
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_POST
@login_required
def unsubscribe_series(request, series_id):
    """Unsubscribe from a series"""
    try:
        SeriesSubscription.objects.filter(user=request.user, series_id=series_id).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def is_subscribed_series(request, series_id):
    """Check if a series is subscribed"""
    is_subbed = SeriesSubscription.objects.filter(user=request.user, series_id=series_id).exists()
    return JsonResponse({'subscribed': is_subbed})

@require_POST
@login_required
def subscribe_movie(request, movie_id):
    """Subscribe to a movie"""
    try:
        # Existiert bereits?
        if MovieSubscription.objects.filter(user=request.user, movie_id=movie_id).exists():
            return JsonResponse({'success': True, 'already_subscribed': True})

        # Hole Film-Details vom Radarr
        conf = _arr_conf_from_db()
        # TODO: Radarr API Call für Movie Details

        # Erstelle Subscription
        sub = MovieSubscription.objects.create(
            user=request.user,
            movie_id=movie_id,
            title=request.POST.get('title', ''),
            poster=request.POST.get('poster', ''),
            overview=request.POST.get('overview', ''),
            genres=request.POST.getlist('genres[]', []),
            release_date=request.POST.get('release_date')
        )
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_POST
@login_required
def unsubscribe_movie(request, movie_id):
    """Unsubscribe from a movie"""
    try:
        MovieSubscription.objects.filter(user=request.user, movie_id=movie_id).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def is_subscribed_movie(request, movie_id):
    """Check if a movie is subscribed"""
    is_subbed = MovieSubscription.objects.filter(user=request.user, movie_id=movie_id).exists()
    return JsonResponse({'subscribed': is_subbed})

@login_required
def get_subscriptions(request):
    """Get all subscriptions for the user"""
    series = SeriesSubscription.objects.filter(user=request.user).values_list('series_id', flat=True)
    movies = MovieSubscription.objects.filter(user=request.user).values_list('movie_id', flat=True)
    return JsonResponse({
        'series': list(series),
        'movies': list(movies)
    })


@method_decorator(login_required, name='dispatch')
class SeriesSubscribeView(APIView):
    def post(self, request, series_id):
        from .services import sonarr_get_series
        # Try enabled Sonarr instances first, fallback to legacy single instance
        details = None
        try:
            inst = ArrInstance.objects.filter(enabled=True, kind='sonarr').order_by('order', 'id')
            for s in inst:
                try:
                    details = sonarr_get_series(series_id, base_url=s.base_url, api_key=s.api_key)
                    if details:
                        break
                except Exception:
                    continue
            if not details:
                cfg = AppSettings.current()
                if cfg.sonarr_url and cfg.sonarr_api_key:
                    details = sonarr_get_series(series_id, base_url=cfg.sonarr_url, api_key=cfg.sonarr_api_key)
        except Exception:
            details = None
        defaults = {
            'series_title': request.data.get('title', '') if request.data else '',
            'series_poster': request.data.get('poster', '') if request.data else '',
            'series_overview': request.data.get('overview', '') if request.data else '',
            'series_genres': request.data.get('genres', []) if request.data else [],
        }
        if details:
            defaults.update({
                'series_title': details.get('series_title') or defaults['series_title'],
                'series_poster': details.get('series_poster') or defaults['series_poster'],
                'series_overview': details.get('series_overview') or defaults['series_overview'],
                'series_genres': details.get('series_genres') or defaults['series_genres'],
            })
        sub, created = SeriesSubscription.objects.get_or_create(
            user=request.user,
            series_id=series_id,
            defaults=defaults
        )
        return Response({'status': 'subscribed'}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@method_decorator(login_required, name='dispatch')
class SeriesUnsubscribeView(APIView):
    def post(self, request, series_id):
        SeriesSubscription.objects.filter(user=request.user, series_id=series_id).delete()
        return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)

@method_decorator(login_required, name='dispatch')
class MovieSubscribeView(APIView):
    def post(self, request, title):
        from .services import radarr_lookup_movie_by_title
        # Try enabled Radarr instances first, fallback to legacy single instance
        details = None
        try:
            inst = ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order', 'id')
            for r in inst:
                try:
                    details = radarr_lookup_movie_by_title(title, base_url=r.base_url, api_key=r.api_key)
                    if details and (details.get('movie_id') or 0) != 0:
                        break
                except Exception:
                    continue
            if not details:
                cfg = AppSettings.current()
                if cfg.radarr_url and cfg.radarr_api_key:
                    details = radarr_lookup_movie_by_title(title, base_url=cfg.radarr_url, api_key=cfg.radarr_api_key)
        except Exception:
            details = None
        defaults = {
            'movie_id': (request.data.get('movie_id', 0) if request.data else 0) or 0,
            'poster': request.data.get('poster', '') if request.data else '',
            'overview': request.data.get('overview', '') if request.data else '',
            'genres': request.data.get('genres', []) if request.data else [],
        }
        if details:
            defaults.update({
                'movie_id': details.get('movie_id') or defaults['movie_id'],
                'poster': details.get('poster') or defaults['poster'],
                'overview': details.get('overview') or defaults['overview'],
                'genres': details.get('genres') or defaults['genres'],
            })
        sub, created = MovieSubscription.objects.get_or_create(
            user=request.user,
            title=title,
            defaults=defaults
        )
        return Response({'status': 'subscribed'}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@method_decorator(login_required, name='dispatch')
class MovieUnsubscribeView(APIView):
    def post(self, request, title):
        MovieSubscription.objects.filter(user=request.user, title=title).delete()
        return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)

@method_decorator(login_required, name='dispatch')
class ListSeriesSubscriptionsView(APIView):
    def get(self, request):
        subs = SeriesSubscription.objects.filter(user=request.user).values_list('series_id', flat=True)
        return Response(list(subs))

@method_decorator(login_required, name='dispatch')
class ListMovieSubscriptionsView(APIView):
    def get(self, request):
        subs = MovieSubscription.objects.filter(user=request.user).values_list('title', flat=True)
        return Response(list(subs))


@method_decorator(login_required, name='dispatch')
class FourKIndexView(View):
    def get(self, request):
        # Aggregate list of movies missing 4K across all Radarr instances
        q = (request.GET.get('q') or '').strip().lower()
        page = request.GET.get('page') or '1'
        pp_raw = (request.GET.get('pp') or '').strip().lower()
        try:
            page = max(1, int(page))
        except Exception:
            page = 1
        # per-page options: 15,25,50,100 or 'all'; default 25
        per_page_options = [15, 25, 50, 100]
        per_page = 25
        pp_is_all = False
        if pp_raw in ('all', 'alle'):
            pp_is_all = True
            per_page = None
        else:
            try:
                pp_int = int(pp_raw) if pp_raw else per_page
                if pp_int in per_page_options:
                    per_page = pp_int
            except Exception:
                pass

        items = []
        try:
            items = list_movies_missing_4k_across_instances()
        except Exception:
            items = []

        if q:
            items = [it for it in items if q in (str(it.get('title') or '').lower())]

        # sort stable by title/year
        items.sort(key=lambda it: (str(it.get('title') or '').lower(), it.get('year') or 0))

        total = len(items)
        if not pp_is_all and per_page:
            start = (page - 1) * per_page
            end = start + per_page
            items = items[start:end]

        # Mark already 4K-subscribed ones for current user
        sub_tmdb = set(Movie4KSubscription.objects.filter(user=request.user).values_list('tmdb_id', flat=True))
        for it in items:
            it['is_subscribed_4k'] = int(it.get('tmdbId') or 0) in sub_tmdb

        if pp_is_all or not per_page:
            pages = 1
            page = 1
            has_prev = has_next = False
        else:
            pages = (total + per_page - 1) // per_page if total else 1
            has_prev = page > 1
            has_next = page < pages

        return render(request, "arr_api/movies_4k.html", {
            "items": items,
            "q": q,
            "page": page,
            "pages": pages,
            "total": total,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": page - 1 if has_prev else None,
            "next_page": page + 1 if has_next else None,
            "pp": ("all" if pp_is_all else per_page),
            "per_page_options": per_page_options,
            "pp_is_all": pp_is_all,
        })


@method_decorator(login_required, name='dispatch')
class Movie4KSubscribeView(APIView):
    def post(self, request, tmdb_id: int):
        # If the movie is already available in 4K anywhere, we can send notification immediately and still store token to dedupe future.
        # Store a friendly title/poster for UI by looking up metadata from any Radarr.
        title = request.data.get('title') if request.data else None
        poster = request.data.get('poster') if request.data else None
        details = None
        if not title or not poster:
            try:
                # Try across enabled instances
                for inst in ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id'):
                    details = radarr_lookup_movie_by_tmdb_id(tmdb_id, base_url=inst.base_url, api_key=inst.api_key)
                    if details:
                        break
            except Exception:
                details = None
        sub, created = Movie4KSubscription.objects.get_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            defaults={
                'title': (title or (details.get('title') if details else '')) or '',
                'poster': (poster or (details.get('poster') if details else '')) or '',
            }
        )
        return Response({'status': 'subscribed'}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@method_decorator(login_required, name='dispatch')
class Movie4KUnsubscribeView(APIView):
    def post(self, request, tmdb_id: int):
        Movie4KSubscription.objects.filter(user=request.user, tmdb_id=tmdb_id).delete()
        return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)