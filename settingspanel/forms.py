from django import forms
from urllib.parse import urlparse
from django.forms import modelformset_factory
from .models import ArrInstance

WIDE = {"class": "input-wide"}

class FirstRunSetupForm(forms.Form):
    # Jellyfin (Required)
    jellyfin_server_url = forms.URLField(
        label="Jellyfin Server URL",
        required=True,
    help_text="URL of your Jellyfin server"
    )
    jellyfin_api_key = forms.CharField(
        label="Jellyfin API Key",
        required=True,
        widget=forms.PasswordInput(render_value=True),
    help_text="API key from Jellyfin settings"
    )
    
    # Sonarr (Optional)
    sonarr_url = forms.URLField(
        label="Sonarr URL",
        required=False,
    help_text="URL of your Sonarr server"
    )
    sonarr_api_key = forms.CharField(
        label="Sonarr API Key",
        required=False,
        widget=forms.PasswordInput(render_value=True)
    )
    
    # Radarr (Optional)
    radarr_url = forms.URLField(
        label="Radarr URL",
        required=False,
    help_text="URL of your Radarr server"
    )
    radarr_api_key = forms.CharField(
        label="Radarr API Key",
        required=False,
        widget=forms.PasswordInput(render_value=True)
    )

class JellyfinSettingsForm(forms.Form):
    jellyfin_server_url = forms.URLField(
        label="Jellyfin Server URL",
        required=False,
        widget=forms.URLInput(attrs=WIDE),
    help_text="e.g. http://localhost:8096"
    )
    jellyfin_api_key = forms.CharField(
        label="Jellyfin API Key",
        required=False,
        widget=forms.PasswordInput(render_value=True, attrs=WIDE),
    help_text="Admin API key from Jellyfin settings"
    )

class ArrSettingsForm(forms.Form):
    sonarr_url     = forms.URLField(label="Sonarr URL", required=False,
                                    widget=forms.URLInput(attrs=WIDE))
    sonarr_api_key = forms.CharField(label="Sonarr API Key", required=False,
                                    widget=forms.PasswordInput(render_value=True, attrs=WIDE))
    radarr_url     = forms.URLField(label="Radarr URL", required=False,
                                    widget=forms.URLInput(attrs=WIDE))
    radarr_api_key = forms.CharField(label="Radarr API Key", required=False,
                                    widget=forms.PasswordInput(render_value=True, attrs=WIDE))

class NotificationSettingsForm(forms.Form):
    # ntfy
    ntfy_server_url = forms.URLField(label="ntfy Server URL", required=False, widget=forms.URLInput(attrs=WIDE),
                                     help_text="e.g., https://ntfy.sh")
    ntfy_topic_default = forms.CharField(label="Default Topic", required=False, widget=forms.TextInput(attrs=WIDE))
    ntfy_user = forms.CharField(label="ntfy Username", required=False)
    ntfy_password = forms.CharField(label="ntfy Password", required=False, widget=forms.PasswordInput(render_value=True))
    ntfy_token = forms.CharField(label="ntfy Bearer Token", required=False, widget=forms.PasswordInput(render_value=True))

    # Apprise
    apprise_default_url = forms.CharField(
        label="Apprise URL(s)", required=False, widget=forms.Textarea(attrs={"rows": 3, "class": "input-wide"}),
        help_text="One per line. See https://github.com/caronc/apprise/wiki for URL formats."
    )
    notify_lookahead_days = forms.IntegerField(
        label="Lookahead (days)", required=False, min_value=0, max_value=30,
        help_text="Consider items up to N days in the future for notifications if file is already available."
    )

class MailSettingsForm(forms.Form):
    mail_host = forms.CharField(label="Mail Host", required=False)
    mail_port = forms.IntegerField(label="Mail Port", required=False, min_value=1, max_value=65535)
    mail_secure = forms.ChoiceField(
        label="Security", required=False,
        choices=[("", "No TLS/SSL"), ("starttls", "STARTTLS"), ("ssl", "SSL/TLS")]
    )
    mail_user = forms.CharField(label="Mail Username", required=False)
    mail_password = forms.CharField(
        label="Mail Password", required=False,
        widget=forms.PasswordInput(render_value=True)
    )
    mail_from = forms.EmailField(label="Sender (From)", required=False)

# Account form removed: local account management disabled


class ArrInstanceForm(forms.ModelForm):
    class Meta:
        model = ArrInstance
        fields = ["kind", "name", "base_url", "api_key", "enabled", "order"]
        widgets = {
            "kind": forms.Select(attrs=WIDE),
            "name": forms.TextInput(attrs=WIDE),
            "base_url": forms.URLInput(attrs=WIDE),
            "api_key": forms.PasswordInput(render_value=True, attrs=WIDE),
            "order": forms.NumberInput(attrs={"min": 0, **WIDE}),
        }

    def clean_base_url(self):
        url = (self.cleaned_data.get("base_url") or "").strip()
        # Basic parse to inspect path parts
        try:
            parsed = urlparse(url)
        except Exception:
            return url  # let URLField handle invalids
        path = (parsed.path or "").rstrip("/")
        # Disallow URLs that already include API or internal pages
        if path.endswith("/api") or path.startswith("/api/") or \
           "/api/" in path or "/settings" in path:
            raise forms.ValidationError(
                "Please enter the application root URL (e.g. http://host:7878 or http://host:8989/radarr), not an API or internal page URL."
            )
        return url

ArrInstanceFormSet = modelformset_factory(
    ArrInstance,
    form=ArrInstanceForm,
    extra=0,
    can_delete=True,
)
