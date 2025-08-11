from django.db import models

class AppSettings(models.Model):
    # Singleton pattern via fixed ID
    singleton_id = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    # Jellyfin
    jellyfin_server_url = models.URLField(blank=True, null=True)
    jellyfin_api_key = models.CharField(max_length=255, blank=True, null=True)

    # Arr
    sonarr_url = models.URLField(blank=True, null=True)
    sonarr_api_key = models.CharField(max_length=255, blank=True, null=True)
    radarr_url = models.URLField(blank=True, null=True)
    radarr_api_key = models.CharField(max_length=255, blank=True, null=True)

    # Mail
    mail_host = models.CharField(max_length=255, blank=True, null=True)
    mail_port = models.PositiveIntegerField(blank=True, null=True)
    mail_secure = models.CharField(
        max_length=10, blank=True, null=True,
        choices=(
            ("", "No TLS/SSL"),
            ("starttls", "STARTTLS (Port 587)"),
            ("ssl", "SSL/TLS (Port 465)"),
            ("tls", "TLS (alias STARTTLS)"),
        )
    )
    mail_user = models.CharField(max_length=255, blank=True, null=True)
    mail_password = models.CharField(max_length=255, blank=True, null=True)
    mail_from = models.EmailField(blank=True, null=True)

    # Account
    acc_username = models.CharField(max_length=150, blank=True, null=True)
    acc_email = models.EmailField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "AppSettings"

    @classmethod
    def current(cls):
        """Get the current settings instance or create a new one"""
        obj, _ = cls.objects.get_or_create(singleton_id=1)
        return obj
        
    def get_jellyfin_url(self):
        """Get the Jellyfin server URL with proper formatting"""
        if not self.jellyfin_server_url:
            return None
        url = self.jellyfin_server_url
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        return url.rstrip('/')
