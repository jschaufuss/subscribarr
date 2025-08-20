from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .views import needs_setup

class SetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if needs_setup():
            # URLs, die auch ohne Setup erlaubt sind
            allowed_urls = [
                reverse('settingspanel:setup'),
                reverse('settingspanel:test_setup_connection'),
                '/static/',  # Für CSS/JS
            ]
            
            # Prüfe, ob die aktuelle URL erlaubt ist
            if not any(request.path.startswith(url) for url in allowed_urls):
                return redirect('settingspanel:setup')
        
        response = self.get_response(request)
        return response
