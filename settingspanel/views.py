from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils.decorators import method_decorator
from .forms import (
    ArrSettingsForm,
    MailSettingsForm,
    FirstRunSetupForm,
    JellyfinSettingsForm,
    NotificationSettingsForm,
    ArrInstanceFormSet,
)
from .models import AppSettings, ArrInstance
from django.http import JsonResponse
from accounts.utils import jellyfin_admin_required
from arr_api.models import SeriesSubscription, MovieSubscription, Movie4KSubscription, SentNotification
from youtube.models import YouTubeSubscription
from django.db.models import Count
import requests
from django.core.mail import send_mail
from django.conf import settings as dj_settings
from django.utils import timezone

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

            # Create initial ArrInstance rows so they appear in admin settings
            try:
                if settings.sonarr_url and settings.sonarr_api_key:
                    ArrInstance.objects.get_or_create(
                        kind="sonarr",
                        name="Default",
                        defaults={
                            "base_url": settings.sonarr_url,
                            "api_key": settings.sonarr_api_key,
                            "enabled": True,
                            "order": 0,
                        }
                    )
                if settings.radarr_url and settings.radarr_api_key:
                    ArrInstance.objects.get_or_create(
                        kind="radarr",
                        name="Default",
                        defaults={
                            "base_url": settings.radarr_url,
                            "api_key": settings.radarr_api_key,
                            "enabled": True,
                            "order": 0,
                        }
                    )
            except Exception:
                # Non-fatal if creation fails; user can add later in settings
                pass
            
            messages.success(request, 'Setup completed successfully!')
            return redirect('accounts:login')
    else:
        form = FirstRunSetupForm()
    
    return render(request, 'settingspanel/first_run.html', {'form': form})


def test_setup_connection(request):
    """Test connections during setup - no auth required"""
    if not needs_setup():
        return JsonResponse({"ok": False, "error": "Setup already completed"}, status=403)
        
    kind = request.GET.get("kind", "").strip().lower()  # "sonarr" | "radarr" | "jellyfin"
    url = (request.GET.get("url") or "").strip()
    key = (request.GET.get("key") or "").strip()
    
    if kind not in ("sonarr", "radarr", "jellyfin"):
        return JsonResponse({"ok": False, "error": "Invalid type"}, status=400)
    if not url or not key:
        return JsonResponse({"ok": False, "error": "URL and API key required"}, status=400)

    try:
        if kind == "jellyfin":
            # Test Jellyfin connection
            r = requests.get(
                f"{url.rstrip('/')}/System/Info",
                headers={"X-Emby-Token": key},
                timeout=8
            )
        else:
            # Test Sonarr/Radarr connection
            r = requests.get(
                f"{url.rstrip('/')}/api/v3/system/status",
                headers={"X-Api-Key": key},
                timeout=5
            )
            
        if r.status_code == 200:
            if kind == "jellyfin":
                try:
                    data = r.json()
                    server_name = data.get("ServerName", "Jellyfin Server")
                    return JsonResponse({"ok": True, "message": f"Connected to {server_name}"})
                except:
                    return JsonResponse({"ok": True, "message": "Connected to Jellyfin server"})
            else:
                return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": f"HTTP {r.status_code}"})
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": str(e)})


@jellyfin_admin_required
def test_connection(request):
    kind = request.GET.get("kind")  # "sonarr" | "radarr" | "jellyfin"
    url = (request.GET.get("url") or "").strip()
    key = (request.GET.get("key") or "").strip()
    
    # Allow jellyfin test during setup without auth
    if kind == "jellyfin" and needs_setup():
        # Skip auth requirement during setup for jellyfin test
        pass
    elif kind not in ("sonarr", "radarr", "jellyfin"):
        return JsonResponse({"ok": False, "error": "Invalid type"}, status=400)
        
    if not url or not key:
        return JsonResponse({"ok": False, "error": "URL and API key required"}, status=400)

    try:
        if kind == "jellyfin":
            # Test Jellyfin connection
            r = requests.get(
                f"{url.rstrip('/')}/System/Info",
                headers={"X-Emby-Token": key},
                timeout=8
            )
        else:
            # Test Sonarr/Radarr connection
            r = requests.get(
                f"{url.rstrip('/')}/api/v3/system/status",
                headers={"X-Api-Key": key},
                timeout=5
            )
            
        if r.status_code == 200:
            if kind == "jellyfin":
                try:
                    data = r.json()
                    server_name = data.get("ServerName", "Jellyfin Server")
                    return JsonResponse({"ok": True, "message": f"Connected to {server_name}"})
                except:
                    return JsonResponse({"ok": True, "message": "Connected to Jellyfin server"})
            else:
                return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": f"HTTP {r.status_code}"})
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": str(e)})
def test_connection(request):
    kind = request.GET.get("kind")  # "sonarr" | "radarr" | "jellyfin"
    url = (request.GET.get("url") or "").strip()
    key = (request.GET.get("key") or "").strip()
    
    # Allow jellyfin test during setup without auth
    if kind == "jellyfin" and needs_setup():
        # Skip auth requirement during setup for jellyfin test
        pass
    elif kind not in ("sonarr", "radarr", "jellyfin"):
        return JsonResponse({"ok": False, "error": "Invalid type"}, status=400)
        
    if not url or not key:
        return JsonResponse({"ok": False, "error": "URL and API key required"}, status=400)

    try:
        if kind == "jellyfin":
            # Test Jellyfin connection
            r = requests.get(
                f"{url.rstrip('/')}/System/Info",
                headers={"X-Emby-Token": key},
                timeout=8
            )
        else:
            # Test Sonarr/Radarr connection
            r = requests.get(
                f"{url.rstrip('/')}/api/v3/system/status",
                headers={"X-Api-Key": key},
                timeout=5
            )
            
        if r.status_code == 200:
            if kind == "jellyfin":
                try:
                    data = r.json()
                    server_name = data.get("ServerName", "Jellyfin Server")
                    return JsonResponse({"ok": True, "message": f"Connected to {server_name}"})
                except:
                    return JsonResponse({"ok": True, "message": "Connected to Jellyfin server"})
            else:
                return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": f"HTTP {r.status_code}"})
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": str(e)})


@jellyfin_admin_required
def test_notify(request):
    """Send a test notification via email/ntfy/apprise.
    Query params: channel=email|ntfy|apprise (default: email)
    For email: uses current user's email; for ntfy/apprise: uses user's overrides plus app defaults.
    """
    channel = (request.GET.get("channel") or "email").strip().lower()
    user = request.user
    title = "Subscribarr test notification"
    body = "This is a test notification from Subscribarr settings."
    from arr_api.notifications import _dispatch_user_notification, _set_runtime_email_settings

    # Force user's channel for this test if requested; otherwise dispatch to chosen channel explicitly
    if channel in ("ntfy", "apprise"):
        # Temporarily override user's preferred channel for this dispatch
        orig = getattr(user, 'notification_channel', 'email')
        try:
            setattr(user, 'notification_channel', channel)
            ok = _dispatch_user_notification(user, subject=title, body_text=body, html_message=None)
            return JsonResponse({"ok": bool(ok)})
        finally:
            setattr(user, 'notification_channel', orig)
    else:
        # email
        try:
            _set_runtime_email_settings()
            to = [user.email] if getattr(user, 'email', None) else []
            if not to:
                return JsonResponse({"ok": False, "error": "User has no email address set"}, status=400)
            send_mail(title, body, dj_settings.DEFAULT_FROM_EMAIL, to, fail_silently=False)
            return JsonResponse({"ok": True})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)


@jellyfin_admin_required
def reset_notify_tokens(request):
    """Delete SentNotification tokens for testing.
    Removes entries with air_date in [today .. today+lookahead_days].
    Optional query param: scope=me|all (default: me)
    """
    scope = (request.GET.get('scope') or 'me').strip().lower()
    today = timezone.now().date()
    try:
        la = max(0, int(getattr(AppSettings.current(), 'notify_lookahead_days', 1) or 0))
    except Exception:
        la = 0
    end_date = today + timezone.timedelta(days=la)
    qs = SentNotification.objects.filter(air_date__gte=today, air_date__lte=end_date)
    if scope != 'all':
        qs = qs.filter(user=request.user)
    deleted, _ = qs.delete()
    return JsonResponse({"ok": True, "deleted": deleted})

@method_decorator(jellyfin_admin_required, name='dispatch')
class SettingsView(View):
    template_name = "settingspanel/settings.html"

    def get(self, request):
        cfg = AppSettings.current()
        # If no ArrInstance rows exist yet, but legacy fields are present, seed them once
        try:
            if not ArrInstance.objects.exists():
                created_any = False
                if cfg.sonarr_url and cfg.sonarr_api_key:
                    ArrInstance.objects.get_or_create(
                        kind="sonarr",
                        name="Default",
                        defaults={
                            "base_url": cfg.sonarr_url,
                            "api_key": cfg.sonarr_api_key,
                            "enabled": True,
                            "order": 0,
                        },
                    )
                    created_any = True
                if cfg.radarr_url and cfg.radarr_api_key:
                    ArrInstance.objects.get_or_create(
                        kind="radarr",
                        name="Default",
                        defaults={
                            "base_url": cfg.radarr_url,
                            "api_key": cfg.radarr_api_key,
                            "enabled": True,
                            "order": 0,
                        },
                    )
                    created_any = True
                if created_any:
                    messages.info(request, "Imported legacy Sonarr/Radarr settings as instances.")
        except Exception:
            pass
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
            "arr_instances": ArrInstanceFormSet(queryset=ArrInstance.objects.all().order_by("order", "id")),
            "mail_form": MailSettingsForm(initial={
                "mail_host": cfg.mail_host or "",
                "mail_port": cfg.mail_port or "",
                "mail_secure": cfg.mail_secure or "",
                "mail_user": cfg.mail_user or "",
                "mail_password": cfg.mail_password or "",
                "mail_from": cfg.mail_from or "",
            }),
            "notify_form": NotificationSettingsForm(initial={
                "ntfy_server_url": cfg.ntfy_server_url or "",
                "ntfy_topic_default": cfg.ntfy_topic_default or "",
                "ntfy_user": cfg.ntfy_user or "",
                "ntfy_password": cfg.ntfy_password or "",
                "ntfy_token": cfg.ntfy_token or "",
                "apprise_default_url": cfg.apprise_default_url or "",
                "notify_lookahead_days": cfg.notify_lookahead_days or 1,
            }),
        })

    def post(self, request):
        jellyfin_form = JellyfinSettingsForm(request.POST)
        arr_form = ArrSettingsForm(request.POST)
        mail_form = MailSettingsForm(request.POST)
        notify_form = NotificationSettingsForm(request.POST)
        inst_formset = ArrInstanceFormSet(request.POST, queryset=ArrInstance.objects.all().order_by("order", "id"))
        if not (jellyfin_form.is_valid() and arr_form.is_valid() and mail_form.is_valid() and notify_form.is_valid() and inst_formset.is_valid()):
            return render(
                request,
                self.template_name,
                {
                    "jellyfin_form": jellyfin_form,
                    "arr_form": arr_form,
                    "mail_form": mail_form,
                    "notify_form": notify_form,
                    "arr_instances": inst_formset,
                },
            )

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

        # Update Notification settings
        cfg.ntfy_server_url    = notify_form.cleaned_data.get("ntfy_server_url") or None
        cfg.ntfy_topic_default = notify_form.cleaned_data.get("ntfy_topic_default") or None
        cfg.ntfy_user          = notify_form.cleaned_data.get("ntfy_user") or None
        cfg.ntfy_password      = notify_form.cleaned_data.get("ntfy_password") or None
        cfg.ntfy_token         = notify_form.cleaned_data.get("ntfy_token") or None
        cfg.apprise_default_url = notify_form.cleaned_data.get("apprise_default_url") or None
        # Notification behavior
        nad = notify_form.cleaned_data.get("notify_lookahead_days")
        try:
            cfg.notify_lookahead_days = max(0, min(30, int(nad))) if nad is not None else cfg.notify_lookahead_days
        except Exception:
            pass

        cfg.save()
        # Save instances with minor normalization
        objs = inst_formset.save(commit=False)
        for obj in objs:
            if obj.base_url:
                obj.base_url = obj.base_url.strip().rstrip('/')
            obj.save()
        for obj in inst_formset.deleted_objects:
            obj.delete()
        messages.success(request, "Settings saved (DB).")
        return redirect("settingspanel:index")

@jellyfin_admin_required
def subscriptions_overview(request):
    series = SeriesSubscription.objects.select_related('user').order_by('user__username', 'series_title')
    movies = MovieSubscription.objects.select_related('user').order_by('user__username', 'title')
    movies_4k = Movie4KSubscription.objects.select_related('user').order_by('user__username', 'title')
    youtube_subs = YouTubeSubscription.objects.select_related('user').order_by('user__username', 'title')

    # Aggregate counts per user
    s_counts = SeriesSubscription.objects.values('user_id', 'user__username').annotate(series_count=Count('id'))
    m_counts = MovieSubscription.objects.values('user_id', 'user__username').annotate(movie_count=Count('id'))
    m4k_counts = Movie4KSubscription.objects.values('user_id', 'user__username').annotate(movie4k_count=Count('id'))
    yt_counts = YouTubeSubscription.objects.values('user_id', 'user__username').annotate(youtube_count=Count('id'))

    user_map = {}
    for row in s_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
            'movie4k_count': 0,
            'youtube_count': 0,
        })
        user_map[key]['series_count'] = row['series_count']
    for row in m_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
            'movie4k_count': 0,
            'youtube_count': 0,
        })
        user_map[key]['movie_count'] = row['movie_count']
    for row in m4k_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
            'movie4k_count': 0,
            'youtube_count': 0,
        })
        user_map[key]['movie4k_count'] = row['movie4k_count']
    for row in yt_counts:
        key = row['user_id']
        user_map.setdefault(key, {
            'user_id': key,
            'username': row['user__username'],
            'series_count': 0,
            'movie_count': 0,
            'movie4k_count': 0,
            'youtube_count': 0,
        })
        user_map[key]['youtube_count'] = row['youtube_count']

    user_stats = []
    for key, val in user_map.items():
        total = (val.get('series_count') or 0) + (val.get('movie_count') or 0) + (val.get('movie4k_count') or 0) + (val.get('youtube_count') or 0)
        user_stats.append({
            'user_id': val['user_id'],
            'username': val['username'],
            'username_lower': (val['username'] or '').lower(),
            'series_count': val.get('series_count') or 0,
            'movie_count': val.get('movie_count') or 0,
            'movie4k_count': val.get('movie4k_count') or 0,
            'youtube_count': val.get('youtube_count') or 0,
            'total_count': total,
        })
    user_stats.sort(key=lambda x: (-x['total_count'], x['username'].lower()))

    return render(request, 'settingspanel/subscriptions.html', {
        'series': series,
        'movies': movies,
        'movies_4k': movies_4k,
        'youtube_subs': youtube_subs,
        'user_stats': user_stats,
    })
