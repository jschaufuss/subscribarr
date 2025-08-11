import requests
from django.conf import settings
from django.core.cache import cache
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

class JellyfinClient:
    def __init__(self):
    # Base settings from Django settings
        self.client = settings.JELLYFIN_CLIENT
        self.version = settings.JELLYFIN_VERSION
        self.device = settings.JELLYFIN_DEVICE
        self.device_id = settings.JELLYFIN_DEVICE_ID
        self.server_url = None  # Wird später gesetzt
        self.api_key = None     # Optional, wird aus den AppSettings geholt wenn nötig

    def authenticate(self, username, password):
        """Authenticate with Jellyfin and return user info if successful"""
        if not self.server_url:
            raise ValueError("No server URL provided")

    # Ensure the URL has a protocol
        if not self.server_url.startswith(('http://', 'https://')):
            self.server_url = f'http://{self.server_url}'
        
    # Remove trailing slashes
        self.server_url = self.server_url.rstrip('/')

        headers = {
            'X-Emby-Authorization': (
                f'MediaBrowser Client="{self.client}", '
                f'Device="{self.device}", '
                f'DeviceId="{self.device_id}", '
                f'Version="{self.version}"'
            )
        }

        auth_data = {
            'Username': username,
            'Pw': password
        }

        try:
            response = requests.post(
                f'{self.server_url}/Users/AuthenticateByName',
                json=auth_data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'user_id': data['User']['Id'],
                'access_token': data['AccessToken'],
                'is_admin': data['User'].get('Policy', {}).get('IsAdministrator', False)
            }
        except requests.exceptions.ConnectionError:
            raise ValueError("Unable to connect to the server. Please check the server URL.")
        except requests.exceptions.Timeout:
            raise ValueError("Connection to the server timed out.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return None  # Authentifizierung fehlgeschlagen
            raise ValueError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            return None

    def is_admin(self, user_id, token):
        """Check if user is admin in Jellyfin"""
        cache_key = f'jellyfin_admin_{user_id}'
        
    # Check cache first
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {
            'X-Emby-Authorization': (
                f'MediaBrowser Client="{self.client}", '
                f'Device="{self.device}", '
                f'DeviceId="{self.device_id}", '
                f'Version="{self.version}", '
                f'Token="{token}"'
            )
        }

        try:
            response = requests.get(
                f'{self.server_url}/Users/{user_id}',
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            is_admin = data.get('Policy', {}).get('IsAdministrator', False)
            
            # Cache result for 5 minutes
            cache.set(cache_key, is_admin, 300)
            
            return is_admin
        except:
            return False

def jellyfin_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to view this page.')
            return redirect('accounts:login')
        
        if not request.user.is_jellyfin_admin:
            messages.error(request, 'You need admin rights to view this page.')
            return redirect('index')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view
