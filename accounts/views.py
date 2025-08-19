from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.conf import settings
from .forms import CustomUserChangeForm, JellyfinLoginForm
from .models import User
from .utils import JellyfinClient

# Registration is disabled: Jellyfin SSO only.

@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved.')
            return redirect('accounts:profile')
    else:
        form = CustomUserChangeForm(instance=request.user)

    # Load subscriptions
    series_subs = request.user.series_subscriptions.all()
    movie_subs = request.user.movie_subscriptions.all()
    yt_subs = request.user.yt_subscriptions.all().order_by('kind', 'title')
    # Enrich with metadata (title/image/url) best-effort
    yt_items = []
    try:
        from youtube.services import get_youtube_metadata
        for s in yt_subs:
            meta = {}
            try:
                meta = get_youtube_metadata(s.kind, s.target_id) or {}
            except Exception:
                meta = {}
            yt_items.append({'sub': s, 'meta': meta})
    except Exception:
        yt_items = [{'sub': s, 'meta': {}} for s in yt_subs]

    # Best-effort Backfill fehlender Poster, damit die Profilseite Bilder zeigt
    try:
        from settingspanel.models import AppSettings, ArrInstance
        from arr_api.services import sonarr_get_series, radarr_lookup_movie_by_title
        cfg = AppSettings.current()
        # choose any enabled instance if legacy fields are not set
        sonarr_conf = None
        radarr_conf = None
        try:
            if cfg.sonarr_url and cfg.sonarr_api_key:
                sonarr_conf = (cfg.sonarr_url, cfg.sonarr_api_key)
            else:
                inst = ArrInstance.objects.filter(enabled=True, kind='sonarr').order_by('order','id').first()
                if inst:
                    sonarr_conf = (inst.base_url, inst.api_key)
        except Exception:
            sonarr_conf = None
        try:
            if cfg.radarr_url and cfg.radarr_api_key:
                radarr_conf = (cfg.radarr_url, cfg.radarr_api_key)
            else:
                inst = ArrInstance.objects.filter(enabled=True, kind='radarr').order_by('order','id').first()
                if inst:
                    radarr_conf = (inst.base_url, inst.api_key)
        except Exception:
            radarr_conf = None
    # Series
        for sub in series_subs:
            if not sub.series_poster and sub.series_id:
                details = None
                try:
                    if sonarr_conf:
                        details = sonarr_get_series(sub.series_id, base_url=sonarr_conf[0], api_key=sonarr_conf[1])
                except Exception:
                    details = None
                if details and details.get('series_poster'):
                    sub.series_poster = details['series_poster']
                    if not sub.series_overview:
                        sub.series_overview = details.get('series_overview') or ''
                    if not sub.series_genres:
                        sub.series_genres = details.get('series_genres') or []
                    sub.save(update_fields=['series_poster', 'series_overview', 'series_genres'])
    # Movies
        for sub in movie_subs:
            if not sub.poster:
                details = None
                try:
                    if radarr_conf:
                        details = radarr_lookup_movie_by_title(sub.title, base_url=radarr_conf[0], api_key=radarr_conf[1])
                except Exception:
                    details = None
                if details and details.get('poster'):
                    sub.poster = details['poster']
                    if not sub.overview:
                        sub.overview = details.get('overview') or ''
                    if not sub.genres:
                        sub.genres = details.get('genres') or []
                    sub.save(update_fields=['poster', 'overview', 'genres'])
    except Exception:
        # still show page even if lookups fail
        pass
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'series_subs': series_subs,
        'movie_subs': movie_subs,
    'yt_subs': yt_subs,
    'yt_items': yt_items,
    })

def jellyfin_login(request):
    if request.method == 'POST':
        form = JellyfinLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Jellyfin-URL aus AppSettings
            from settingspanel.models import AppSettings
            app_settings = AppSettings.current()
            server_url = app_settings.get_jellyfin_url()
            if not server_url:
                messages.error(request, 'Jellyfin server is not configured. Please complete setup.')
                return render(request, 'accounts/login.html', {'form': form})

            try:
                client = JellyfinClient()
                client.server_url = server_url
                auth_result = client.authenticate(username, password)
                
                if not auth_result:
                    messages.error(request, 'Sign in failed. Please check your credentials.')
                    return render(request, 'accounts/login.html', {'form': form})

                # Existierenden User finden oder neu erstellen
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = User.objects.create_user(
                        username=username,
                        email=f"{username}@jellyfin.local"
                    )

                # Jellyfin Daten aktualisieren
                user.jellyfin_user_id = auth_result['user_id']
                user.jellyfin_token = auth_result['access_token']
                user.jellyfin_server = server_url
                user.save()

                if auth_result['is_admin']:
                    user.is_admin = True
                    user.save()

                login(request, user)
                messages.success(request, f'Welcome, {username}!')
                return redirect('arr_api:index')
                    
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Connection error: {str(e)}')
        # invalid form or error path
        return render(request, 'accounts/login.html', {'form': form})

    else:
        form = JellyfinLoginForm()

    return render(request, 'accounts/login.html', {'form': form})
