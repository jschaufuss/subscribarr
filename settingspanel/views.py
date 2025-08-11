from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils.decorators import method_decorator
from .forms import ArrSettingsForm, MailSettingsForm, AccountForm, FirstRunSetupForm, JellyfinSettingsForm
from .models import AppSettings
from django.http import JsonResponse
from accounts.utils import jellyfin_admin_required
from django.contrib.auth import get_user_model
from arr_api.models import SeriesSubscription, MovieSubscription
from django.db.models import Count
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
            
            messages.success(request, 'Setup completed successfully!')
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
        return JsonResponse({"ok": False, "error": "Invalid type"}, status=400)
    if not url or not key:
        return JsonResponse({"ok": False, "error": "URL and API key required"}, status=400)

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
                "account_form": acc_form,
            })

        cfg = AppSettings.current()

        # Update Jellyfin settings
        cfg.jellyfin_server_url = jellyfin_form.cleaned_data.get("jellyfin_server_url") or None
        cfg.jellyfin_api_key    = jellyfin_form.cleaned_data.get("jellyfin_api_key") or None

        # Update Sonarr/Radarr settings
        cfg.sonarr_url     = arr_form.cleaned_data.get("sonarr_url") or None
        cfg.sonarr_api_key = arr_form.cleaned_data.get("sonarr_api_key") or None
        cfg.radarr_url     = arr_form.cleaned_data.get("radarr_url") or None
        cfg.radarr_api_key = arr_form.cleaned_data.get("radarr_api_key") or None

        # Update Mail settings
        cfg.mail_host     = mail_form.cleaned_data.get("mail_host") or None
        cfg.mail_port     = mail_form.cleaned_data.get("mail_port") or None
        cfg.mail_secure   = mail_form.cleaned_data.get("mail_secure") or ""
        cfg.mail_user     = mail_form.cleaned_data.get("mail_user") or None
        cfg.mail_password = mail_form.cleaned_data.get("mail_password") or None
        cfg.mail_from     = mail_form.cleaned_data.get("mail_from") or None

        # Update account settings
        cfg.acc_username = acc_form.cleaned_data.get("username") or None
        cfg.acc_email    = acc_form.cleaned_data.get("email") or None

        cfg.save()
        messages.success(request, "Settings saved (DB).")
        return redirect("settingspanel:index")

@jellyfin_admin_required
def subscriptions_overview(request):
    series = SeriesSubscription.objects.select_related('user').order_by('user__username', 'series_title')
    movies = MovieSubscription.objects.select_related('user').order_by('user__username', 'title')

    # Aggregate counts per user
    s_counts = SeriesSubscription.objects.values('user_id', 'user__username').annotate(series_count=Count('id'))
    m_counts = MovieSubscription.objects.values('user_id', 'user__username').annotate(movie_count=Count('id'))

    user_map = {}
    for row in s_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
        })
        user_map[key]['series_count'] = row['series_count']
    for row in m_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
        })
        user_map[key]['movie_count'] = row['movie_count']

    user_stats = []
    for key, val in user_map.items():
        total = (val.get('series_count') or 0) + (val.get('movie_count') or 0)
        user_stats.append({
            'user_id': val['user_id'],
            'username': val['username'],
            'username_lower': (val['username'] or '').lower(),
            'series_count': val.get('series_count') or 0,
            'movie_count': val.get('movie_count') or 0,
            'total_count': total,
        })
    user_stats.sort(key=lambda x: (-x['total_count'], x['username'].lower()))

    return render(request, 'settingspanel/subscriptions.html', {
        'series': series,
        'movies': movies,
        'user_stats': user_stats,
    })
