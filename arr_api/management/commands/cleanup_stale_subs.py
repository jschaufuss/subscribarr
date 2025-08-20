from django.core.management.base import BaseCommand
from arr_api.models import Movie4KSubscription, MovieSubscription, SeriesSubscription
from arr_api.services import tmdb_has_4k_any_instance
from arr_api.notifications import radarr_movie_has_file, _enabled_instances, _sonarr_get


class Command(BaseCommand):
    help = "Remove stale subscriptions: 4K subs where 4K is available, movies with files, and ended series."

    def handle(self, *args, **options):
        removed_4k = removed_movies = removed_series = 0

        # 4K subs: remove all where movie is available in 4K anywhere
        for sub in Movie4KSubscription.objects.all():
            try:
                if tmdb_has_4k_any_instance(sub.tmdb_id):
                    sub.delete()
                    removed_4k += 1
            except Exception:
                continue

        # Movie subs: remove where hasFile
        for sub in MovieSubscription.objects.all():
            try:
                if radarr_movie_has_file(sub.movie_id):
                    sub.delete()
                    removed_movies += 1
            except Exception:
                continue

        # Series subs: remove where series ended
        for sub in SeriesSubscription.objects.all():
            try:
                ended = False
                for inst in _enabled_instances('sonarr'):
                    s = _sonarr_get(inst.base_url, inst.api_key, f"/api/v3/series/{sub.series_id}") or {}
                    status = (s.get('status') or '').lower()
                    if status == 'ended':
                        ended = True
                        break
                if ended:
                    sub.delete()
                    removed_series += 1
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(
            f"cleanup_stale_subs: 4k={removed_4k} movies={removed_movies} series={removed_series}"
        ))
