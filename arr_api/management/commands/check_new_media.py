from django.core.management.base import BaseCommand
from django.utils import timezone
from arr_api.notifications import check_and_notify_users

class Command(BaseCommand):
    help = 'Prüft neue Medien und sendet Benachrichtigungen'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'[{timezone.now()}] Starte Medien-Check...')
        try:
            check_and_notify_users()
            self.stdout.write(self.style.SUCCESS(f'[{timezone.now()}] Medien-Check erfolgreich beendet'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[{timezone.now()}] Fehler beim Medien-Check: {str(e)}'))
