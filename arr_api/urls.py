from django.urls import path
from .views import SonarrAiringView, RadarrUpcomingMoviesView

urlpatterns = [
    path("sonarr/airing", SonarrAiringView.as_view(), name="sonarr-airing"),
    path("radarr/upcoming", RadarrUpcomingMoviesView.as_view(), name="radarr-upcoming"),
]