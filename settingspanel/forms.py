from django import forms

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


class NotificationSettingsForm(forms.Form):
    # ntfy
    ntfy_server_url = forms.URLField(label="ntfy Server URL", required=False,
                                     widget=forms.URLInput(attrs=WIDE),
                                     help_text="e.g. https://ntfy.sh or your self-hosted URL")
    ntfy_topic_default = forms.CharField(label="Default topic", required=False,
                                         widget=forms.TextInput(attrs=WIDE))
    ntfy_user = forms.CharField(label="ntfy Username", required=False,
                                widget=forms.TextInput(attrs=WIDE))
    ntfy_password = forms.CharField(label="ntfy Password", required=False,
                                    widget=forms.PasswordInput(render_value=True, attrs=WIDE))
    ntfy_token = forms.CharField(label="ntfy Bearer token", required=False,
                                 widget=forms.PasswordInput(render_value=True, attrs=WIDE))

    # Apprise
    apprise_default_url = forms.CharField(label="Apprise URL(s)", required=False,
                                          widget=forms.Textarea(attrs={"rows": 3, **WIDE}),
                                          help_text="One URL per line. Will be used in addition to any user-provided URLs.")
