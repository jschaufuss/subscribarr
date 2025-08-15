from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom User Model with additional fields and permissions.
    Regular users can only edit their own data.
    Admin users can edit everything.
    """
    email = models.EmailField(_("email address"), unique=True)
    bio = models.TextField(max_length=500, blank=True)
    is_admin = models.BooleanField(default=False)
    
    # Jellyfin fields
    jellyfin_user_id = models.CharField(max_length=100, blank=True, null=True)
    jellyfin_token = models.CharField(max_length=500, blank=True, null=True)
    jellyfin_server = models.CharField(max_length=200, blank=True, null=True)

    # Notifications
    NOTIFY_EMAIL = 'email'
    NOTIFY_NTFY = 'ntfy'
    NOTIFY_APPRISE = 'apprise'
    NOTIFY_CHOICES = [
        (NOTIFY_EMAIL, 'Email'),
        (NOTIFY_NTFY, 'ntfy'),
        (NOTIFY_APPRISE, 'Apprise'),
    ]
    notification_channel = models.CharField(
        max_length=10,
        choices=NOTIFY_CHOICES,
        default=NOTIFY_EMAIL,
    )
    # Optional per-user targets/overrides
    ntfy_topic = models.CharField(max_length=200, blank=True, null=True)
    apprise_url = models.TextField(blank=True, null=True)
    
    def check_jellyfin_admin(self):
        """Check if user is Jellyfin admin on the server"""
        from accounts.utils import JellyfinClient
        if not self.jellyfin_user_id or not self.jellyfin_token:
            return False
        try:
            client = JellyfinClient()
            return client.is_admin(self.jellyfin_user_id, self.jellyfin_token)
        except:
            # On error, fall back to local status
            return self.is_admin
            
    @property 
    def is_jellyfin_admin(self):
        """Check if user is admin either locally or on Jellyfin server"""
        return self.is_admin or self.check_jellyfin_admin()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
