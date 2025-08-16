from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from arr_api.notifications import send_notification_email


class Command(BaseCommand):
    help = "Send a test notification email to verify SMTP configuration"

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Recipient email address')
        parser.add_argument('--username', default='testuser', help='Username to associate with the email')
        parser.add_argument('--type', default='movie', choices=['movie', 'series'], help='Media type for the template')
        parser.add_argument('--title', default='Subscribarr Test', help='Title to show in the email')

    def handle(self, *args, **opts):
        User = get_user_model()
        email = opts['to']
        username = opts['username']
        media_type = opts['type']
        title = opts['title']

        user, _ = User.objects.get_or_create(username=username, defaults={'email': email})
        if user.email != email:
            user.email = email
            user.save(update_fields=['email'])

        # Use current time as air_date for nicer formatting
        send_notification_email(
            user=user,
            media_title=title,
            media_type=media_type,
            overview='This is a test email from Subscribarr to verify your mail settings.',
            poster_url=None,
            episode_title='Pilot' if media_type == 'series' else None,
            season=1 if media_type == 'series' else None,
            episode=1 if media_type == 'series' else None,
            air_date=timezone.now(),
            year=timezone.now().year if media_type == 'movie' else None,
            release_type='Test'
        )

        self.stdout.write(self.style.SUCCESS(f"Test email queued/sent to {email}"))
