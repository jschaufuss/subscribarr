from django.core.management.base import BaseCommand
from django.utils import timezone
from arr_api.notifications import check_and_notify_users

class Command(BaseCommand):
    help = 'Checks for new media and sends notifications'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'[{timezone.now()}] Starting media check...')
        try:
            check_and_notify_users()
            self.stdout.write(self.style.SUCCESS(f'[{timezone.now()}] Media check finished successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[{timezone.now()}] Error during media check: {str(e)}'))
