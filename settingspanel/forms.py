from django import forms

WIDE = {"class": "input-wide"}

class FirstRunSetupForm(forms.Form):
    # Jellyfin (Required)
    jellyfin_server_url = forms.URLField(
        label="Jellyfin Server URL",
        required=True,
        help_text="Die URL deines Jellyfin-Servers"
    )
    jellyfin_api_key = forms.CharField(
        label="Jellyfin API Key",
        required=True,
        widget=forms.PasswordInput(render_value=True),
        help_text="Der API-Key aus den Jellyfin-Einstellungen"
    )
    
    # Sonarr (Optional)
    sonarr_url = forms.URLField(
        label="Sonarr URL",
        required=False,
        help_text="Die URL deines Sonarr-Servers"
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
        help_text="Die URL deines Radarr-Servers"
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
        help_text="z.B. http://localhost:8096"
    )
    jellyfin_api_key = forms.CharField(
        label="Jellyfin API Key",
        required=False,
        widget=forms.PasswordInput(render_value=True, attrs=WIDE),
        help_text="Admin API Key aus den Jellyfin Einstellungen"
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

class MailSettingsForm(forms.Form):
    mail_host = forms.CharField(label="Mail Host", required=False)
    mail_port = forms.IntegerField(label="Mail Port", required=False, min_value=1, max_value=65535)
    mail_secure = forms.ChoiceField(
        label="Sicherheit", required=False,
        choices=[("", "Kein TLS/SSL"), ("starttls", "STARTTLS"), ("ssl", "SSL/TLS")]
    )
    mail_user = forms.CharField(label="Mail Benutzer", required=False)
    mail_password = forms.CharField(
        label="Mail Passwort", required=False,
        widget=forms.PasswordInput(render_value=True)
    )
    mail_from = forms.EmailField(label="Absender (From)", required=False)

class AccountForm(forms.Form):
    username = forms.CharField(label="Benutzername", required=False)
    email = forms.EmailField(label="E-Mail", required=False)
    new_password = forms.CharField(label="Neues Passwort", required=False, widget=forms.PasswordInput)
    repeat_password = forms.CharField(label="Passwort wiederholen", required=False, widget=forms.PasswordInput)
