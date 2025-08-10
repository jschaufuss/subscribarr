from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.conf import settings
from .forms import CustomUserCreationForm, CustomUserChangeForm, JellyfinLoginForm
from .models import User
from .utils import JellyfinClient

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Registrierung erfolgreich! Sie können sich jetzt anmelden.')
        return response

@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'E-Mail gespeichert.')
            return redirect('accounts:profile')
    else:
        form = CustomUserChangeForm(instance=request.user)

    # Lade Abonnements
    series_subs = request.user.series_subscriptions.all()
    movie_subs = request.user.movie_subscriptions.all()

    # Best-effort Backfill fehlender Poster, damit die Profilseite Bilder zeigt
    try:
        from settingspanel.models import AppSettings
        from arr_api.services import sonarr_get_series, radarr_lookup_movie_by_title
        cfg = AppSettings.current()
        # Serien
        for sub in series_subs:
            if not sub.series_poster and sub.series_id:
                details = sonarr_get_series(sub.series_id, base_url=cfg.sonarr_url, api_key=cfg.sonarr_api_key)
                if details and details.get('series_poster'):
                    sub.series_poster = details['series_poster']
                    if not sub.series_overview:
                        sub.series_overview = details.get('series_overview') or ''
                    if not sub.series_genres:
                        sub.series_genres = details.get('series_genres') or []
                    sub.save(update_fields=['series_poster', 'series_overview', 'series_genres'])
        # Filme
        for sub in movie_subs:
            if not sub.poster:
                details = radarr_lookup_movie_by_title(sub.title, base_url=cfg.radarr_url, api_key=cfg.radarr_api_key)
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
                messages.error(request, 'Jellyfin Server ist nicht konfiguriert. Bitte Setup abschließen.')
                return render(request, 'accounts/login.html', {'form': form})

            try:
                client = JellyfinClient()
                client.server_url = server_url
                auth_result = client.authenticate(username, password)
                
                if not auth_result:
                    messages.error(request, 'Anmeldung fehlgeschlagen. Bitte überprüfen Sie Ihre Anmeldedaten.')
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
                messages.success(request, f'Willkommen, {username}!')
                return redirect('arr_api:index')
                    
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Verbindungsfehler: {str(e)}')
        # invalid form or error path
        return render(request, 'accounts/login.html', {'form': form})

    else:
        form = JellyfinLoginForm()

    return render(request, 'accounts/login.html', {'form': form})
