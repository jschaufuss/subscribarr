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

    # Notifications - NTFY
    ntfy_server_url = models.URLField(blank=True, null=True, help_text="Base URL of ntfy server, e.g. https://ntfy.sh")
    ntfy_topic_default = models.CharField(max_length=200, blank=True, null=True, help_text="Default topic if user hasn't set one")
    ntfy_user = models.CharField(max_length=255, blank=True, null=True)
    ntfy_password = models.CharField(max_length=255, blank=True, null=True)
    ntfy_token = models.CharField(max_length=255, blank=True, null=True, help_text="Bearer token, alternative to user/password")

    # Notifications - Apprise (default target URLs, optional)
    apprise_default_url = models.TextField(blank=True, null=True, help_text="Apprise URL(s). Multiple allowed, one per line.")

    # Notification behavior
    notify_lookahead_days = models.PositiveSmallIntegerField(default=1, help_text="How many days ahead to consider for notifications (early availability). Set to 0 or 1 for only today.")

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


class ArrInstance(models.Model):
    KIND_CHOICES = (
        ("sonarr", "Sonarr"),
        ("radarr", "Radarr"),
    )

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=100, help_text="Friendly name, e.g. Home, 4K, Anime")
    base_url = models.URLField()
    api_key = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Sort order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("kind", "name")]

    def __str__(self):
        return f"{self.get_kind_display()} – {self.name}"
