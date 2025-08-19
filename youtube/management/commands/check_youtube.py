from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from youtube.models import YouTubeSubscription, YTSentNotification
from youtube.services import build_feed_url, fetch_feed_entries
from arr_api.notifications import _dispatch_user_notification


class Command(BaseCommand):
    help = 'Checks YouTube subscriptions and sends notifications for new videos.'

    def add_arguments(self, parser):
        parser.add_argument('--since', type=str, help='Only consider videos published since this ISO datetime (optional).')

    def handle(self, *args, **options):
        since_dt = None
        if options.get('since'):
            try:
                since_dt = timezone.datetime.fromisoformat(options['since'])
            except Exception:
                self.stderr.write('Invalid --since value, ignoring.')

        count_checked = 0
        count_notified = 0
        now = timezone.now()
        for sub in YouTubeSubscription.objects.select_related('user').all():
            feed_url = build_feed_url(sub.kind, sub.target_id)
            if not feed_url:
                continue
            entries = fetch_feed_entries(feed_url)
            count_checked += 1
            for ent in entries:
                published = ent.get('published') or now
                # Gate: publish date must be on/after subscription date
                if sub.created_at and published.date() < sub.created_at.date():
                    continue
                # Optional global gate
                if since_dt and published < since_dt:
                    continue
                vid = ent['video_id']
                # Deduplicate per user+video
                try:
                    with transaction.atomic():
                        token, created = YTSentNotification.objects.get_or_create(
                            user=sub.user,
                            video_id=vid,
                            defaults={
                                'published_date': published.date(),
                                'title': ent.get('title') or '',
                                'channel_title': ent.get('channel_title') or '',
                            }
                        )
                    if not created:
                        continue
                except Exception:
                    continue
                title = ent.get('title') or 'New video'
                channel = ent.get('channel_title') or ''
                url = ent.get('url') or f'https://www.youtube.com/watch?v={vid}'
                subj = f"New YouTube video: {title}"
                body = f"{title}\n{channel}\n{url}"
                ok = _dispatch_user_notification(sub.user, subject=subj, body_text=body, html_message=None, click_url=url)
                if ok:
                    count_notified += 1
                else:
                    # rollback token so we can retry later
                    try:
                        YTSentNotification.objects.filter(user=sub.user, video_id=vid).delete()
                    except Exception:
                        pass
        self.stdout.write(self.style.SUCCESS(f'Checked {count_checked} subscription feeds, sent {count_notified} notifications.'))
