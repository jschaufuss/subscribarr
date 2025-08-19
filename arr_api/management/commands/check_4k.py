from django.core.management.base import BaseCommand
from django.utils import timezone
from arr_api.models import Movie4KSubscription, Movie4KSentNotification
from arr_api.services import tmdb_has_4k_any_instance
from arr_api.notifications import _dispatch_user_notification


class Command(BaseCommand):
    help = "Check 4K availability for subscribed movies and notify users when available on any Radarr instance."

    def handle(self, *args, **options):
        subs = Movie4KSubscription.objects.select_related('user').all()
        now = timezone.now()
        notified = 0
        for sub in subs:
            try:
                # Skip if already notified for this tmdb_id
                if Movie4KSentNotification.objects.filter(user=sub.user, tmdb_id=sub.tmdb_id).exists():
                    continue
                if tmdb_has_4k_any_instance(sub.tmdb_id):
                    # Reserve token then dispatch
                    Movie4KSentNotification.objects.create(user=sub.user, tmdb_id=sub.tmdb_id, title=sub.title)
                    title = f"4K available: {sub.title}"
                    body = f"{sub.title} is now available in 4K on at least one of your Radarr instances."
                    _dispatch_user_notification(sub.user, subject=title, body_text=body, html_message=None)
                    notified += 1
            except Exception:
                continue
        self.stdout.write(self.style.SUCCESS(f"check_4k: notified={notified}"))
