from collections import defaultdict
from django.shortcuts import render
from django.views import View
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from settingspanel.models import AppSettings
from .services import sonarr_calendar, radarr_calendar, ArrServiceError


def _get_int(request, key, default):
    try:
        v = int(request.GET.get(key, default))
        return max(1, min(365, v))
    except (TypeError, ValueError):
        return default

def _arr_conf_from_db():
    cfg = AppSettings.current()
    return {
        "sonarr_url": cfg.sonarr_url,
        "sonarr_key": cfg.sonarr_api_key,
        "radarr_url": cfg.radarr_url,
        "radarr_key": cfg.radarr_api_key,
    }


class SonarrAiringView(APIView):
    def get(self, request):
        days = _get_int(request, "days", 30)
        conf = _arr_conf_from_db()
        try:
            data = sonarr_calendar(days=days, base_url=conf["sonarr_url"], api_key=conf["sonarr_key"])
            return Response({"count": len(data), "results": data})
        except ArrServiceError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class RadarrUpcomingMoviesView(APIView):
    def get(self, request):
        days = _get_int(request, "days", 60)
        conf = _arr_conf_from_db()
        try:
            data = radarr_calendar(days=days, base_url=conf["radarr_url"], api_key=conf["radarr_key"])
            return Response({"count": len(data), "results": data})
        except ArrServiceError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class ArrIndexView(View):
    def get(self, request):
        q = (request.GET.get("q") or "").lower().strip()
        kind = (request.GET.get("kind") or "all").lower()
        days = _get_int(request, "days", 30)

        conf = _arr_conf_from_db()

        eps, movies = [], []
        # Sonarr robust laden
        try:
            eps = sonarr_calendar(days=days, base_url=conf["sonarr_url"], api_key=conf["sonarr_key"])
        except ArrServiceError as e:
            messages.error(request, f"Sonarr nicht erreichbar: {e}")

        # Radarr robust laden
        try:
            movies = radarr_calendar(days=days, base_url=conf["radarr_url"], api_key=conf["radarr_key"])
        except ArrServiceError as e:
            messages.error(request, f"Radarr nicht erreichbar: {e}")

        # Suche
        if q:
            eps = [e for e in eps if q in (e.get("seriesTitle") or "").lower()]
            movies = [m for m in movies if q in (m.get("title") or "").lower()]

        # Gruppierung nach Serie
        groups = defaultdict(lambda: {
            "seriesId": None, "seriesTitle": None, "seriesPoster": None,
            "seriesOverview": "", "seriesGenres": [], "episodes": [],
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
            series_grouped.append(g)

        return render(request, "arr_api/index.html", {
            "query": q,
            "kind": kind,
            "days": days,
            "show_series": kind in ("all", "series"),
            "show_movies": kind in ("all", "movies"),
            "series_grouped": series_grouped,
            "movies": movies,
        })