from django import forms

WIDE = {"class": "input-wide"}

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
