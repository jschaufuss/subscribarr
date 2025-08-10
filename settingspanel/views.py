from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils.decorators import method_decorator
from .forms import ArrSettingsForm, MailSettingsForm, AccountForm, FirstRunSetupForm, JellyfinSettingsForm
from .models import AppSettings
from django.http import JsonResponse
from accounts.utils import jellyfin_admin_required
from django.contrib.auth import get_user_model
import requests

def needs_setup():
    """Check if the app needs first-run setup"""
    settings = AppSettings.current()
    return not bool(settings.jellyfin_server_url)

def first_run(request):
    """Handle first-run setup"""
    if not needs_setup():
        return redirect('arr_api:index')
        
    if request.method == 'POST':
        form = FirstRunSetupForm(request.POST)
        if form.is_valid():
            # Save settings
            settings = AppSettings.current()
            settings.jellyfin_server_url = form.cleaned_data['jellyfin_server_url']
            settings.jellyfin_api_key = form.cleaned_data['jellyfin_api_key']
            settings.sonarr_url = form.cleaned_data['sonarr_url']
            settings.sonarr_api_key = form.cleaned_data['sonarr_api_key']
            settings.radarr_url = form.cleaned_data['radarr_url']
            settings.radarr_api_key = form.cleaned_data['radarr_api_key']
            settings.save()
            
            messages.success(request, 'Setup erfolgreich abgeschlossen!')
            return redirect('accounts:login')
    else:
        form = FirstRunSetupForm()
    
    return render(request, 'settingspanel/first_run.html', {'form': form})
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from .forms import ArrSettingsForm, MailSettingsForm, AccountForm, JellyfinSettingsForm
from .models import AppSettings
from django.http import JsonResponse
from accounts.utils import jellyfin_admin_required
import requests

@jellyfin_admin_required
def test_connection(request):
    kind = request.GET.get("kind")  # "sonarr" | "radarr"
    url = (request.GET.get("url") or "").strip()
    key = (request.GET.get("key") or "").strip()
    if kind not in ("sonarr", "radarr"):
        return JsonResponse({"ok": False, "error": "Ungültiger Typ"}, status=400)
    if not url or not key:
        return JsonResponse({"ok": False, "error": "URL und API-Key erforderlich"}, status=400)

    try:
        r = requests.get(
            f"{url.rstrip('/')}/api/v3/system/status",
            headers={"X-Api-Key": key},
            timeout=5
        )
        if r.status_code == 200:
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": f"HTTP {r.status_code}"})
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": str(e)})

@method_decorator(jellyfin_admin_required, name='dispatch')
class SettingsView(View):
    template_name = "settingspanel/settings.html"

    def get(self, request):
        cfg = AppSettings.current()
        return render(request, self.template_name, {
            "jellyfin_form": JellyfinSettingsForm(initial={
                "jellyfin_server_url": cfg.jellyfin_server_url or "",
                "jellyfin_api_key": cfg.jellyfin_api_key or "",
            }),
            "arr_form": ArrSettingsForm(initial={
                "sonarr_url": cfg.sonarr_url or "",
                "sonarr_api_key": cfg.sonarr_api_key or "",
                "radarr_url": cfg.radarr_url or "",
                "radarr_api_key": cfg.radarr_api_key or "",
            }),
            "mail_form": MailSettingsForm(initial={
                "mail_host": cfg.mail_host or "",
                "mail_port": cfg.mail_port or "",
                "mail_secure": cfg.mail_secure or "",
                "mail_user": cfg.mail_user or "",
                "mail_password": cfg.mail_password or "",
                "mail_from": cfg.mail_from or "",
            }),
            "account_form": AccountForm(initial={
                "username": cfg.acc_username or "",
                "email": cfg.acc_email or "",
            }),
        })

    def post(self, request):
        jellyfin_form = JellyfinSettingsForm(request.POST)
        arr_form = ArrSettingsForm(request.POST)
        mail_form = MailSettingsForm(request.POST)
        acc_form = AccountForm(request.POST)
        
        if not (jellyfin_form.is_valid() and arr_form.is_valid() and mail_form.is_valid() and acc_form.is_valid()):
            return render(request, self.template_name, {
                "jellyfin_form": jellyfin_form,
                "arr_form": arr_form,
                "mail_form": mail_form,
                "account_form": acc_form
            })

        cfg = AppSettings.current()
        
        # Update Jellyfin settings
        cfg.jellyfin_server_url = jellyfin_form.cleaned_data["jellyfin_server_url"] or None
        cfg.jellyfin_api_key = jellyfin_form.cleaned_data["jellyfin_api_key"] or None
        cfg.sonarr_url     = arr_form.cleaned_data["sonarr_url"] or None
        cfg.sonarr_api_key = arr_form.cleaned_data["sonarr_api_key"] or None
        cfg.radarr_url     = arr_form.cleaned_data["radarr_url"] or None
        cfg.radarr_api_key = arr_form.cleaned_data["radarr_api_key"] or None

        cfg.mail_host     = mail_form.cleaned_data["mail_host"] or None
        cfg.mail_port     = mail_form.cleaned_data["mail_port"] or None
        cfg.mail_secure   = mail_form.cleaned_data["mail_secure"] or ""
        cfg.mail_user     = mail_form.cleaned_data["mail_user"] or None
        cfg.mail_password = mail_form.cleaned_data["mail_password"] or None
        cfg.mail_from     = mail_form.cleaned_data["mail_from"] or None

        cfg.acc_username = acc_form.cleaned_data["username"] or None
        cfg.acc_email    = acc_form.cleaned_data["email"] or None

        cfg.save()
        messages.success(request, "Einstellungen gespeichert (DB).")
        return redirect("settingspanel:index")
