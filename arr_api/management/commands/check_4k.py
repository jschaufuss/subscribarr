from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from arr_api.models import Movie4KSubscription, Movie4KSentNotification
from arr_api.services import tmdb_has_4k_any_instance, radarr_lookup_movie_by_tmdb_id
from settingspanel.models import ArrInstance
from arr_api.notifications import _dispatch_user_notification


class Command(BaseCommand):
    help = "Check 4K availability for subscribed movies and notify users when available on any Radarr instance."

    def handle(self, *args, **options):
        subs = Movie4KSubscription.objects.select_related('user').all()
        now = timezone.now()
        notified = 0
        for sub in subs:
            try:
                if tmdb_has_4k_any_instance(sub.tmdb_id):
                    # Enrich details (poster/overview) from any enabled Radarr
                    details = None
                    try:
                        for inst in ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id'):
                            details = radarr_lookup_movie_by_tmdb_id(sub.tmdb_id, base_url=inst.base_url, api_key=inst.api_key)
                            if details:
                                break
                    except Exception:
                        details = None
                    # Notify only once
                    if not Movie4KSentNotification.objects.filter(user=sub.user, tmdb_id=sub.tmdb_id).exists():
                        Movie4KSentNotification.objects.create(user=sub.user, tmdb_id=sub.tmdb_id, title=sub.title)
                        subject = f"4K available: {sub.title}"
                        html = None
                        try:
                            ctx = {
                                'username': sub.user.username,
                                'title': sub.title,
                                'type': 'Film',
                                'overview': (details.get('overview') if details else None) or '',
                                'poster_url': (details.get('poster') if details else None) or (sub.poster or ''),
                                'episode_title': None,
                                'season': None,
                                'episode': None,
                                'air_date': None,
                                'year': details.get('year') if details else None,
                                'release_type': '4K',
                            }
                            html = render_to_string('arr_api/email/new_media_notification.html', ctx)
                        except Exception:
                            html = None
                        body_text = f"{sub.title} is now available in 4K on at least one of your Radarr instances."
                        _dispatch_user_notification(sub.user, subject=subject, body_text=body_text, html_message=html)
                        notified += 1
                    # Always remove the subscription once 4K is available
                    try:
                        sub.delete()
                    except Exception:
                        pass
            except Exception:
                continue
        self.stdout.write(self.style.SUCCESS(f"check_4k: notified={notified}"))
