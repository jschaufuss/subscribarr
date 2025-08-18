from django.db import models
from django.conf import settings

class SeriesSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='series_subscriptions')
    series_id = models.IntegerField()
    series_title = models.CharField(max_length=255)
    series_poster = models.URLField(null=True, blank=True)
    series_overview = models.TextField(blank=True)
    series_genres = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'series_id']  # A user can subscribe to a series only once

    def __str__(self):
        return self.series_title

class MovieSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='movie_subscriptions')
    movie_id = models.IntegerField()
    title = models.CharField(max_length=255)
    poster = models.URLField(null=True, blank=True)
    overview = models.TextField(blank=True)
    genres = models.JSONField(default=list)
    release_date = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'movie_id']  # A user can subscribe to a movie only once

    def __str__(self):
        return self.title

class SentNotification(models.Model):
    """Store sent notifications to avoid duplicates"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    media_id = models.IntegerField()
    media_type = models.CharField(max_length=10)  # 'series' or 'movie'
    media_title = models.CharField(max_length=255)
    air_date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # We dedupe per user + media (episodeId/movieId) + type + date
        unique_together = ['user', 'media_id', 'media_type', 'air_date']
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.media_type}: {self.media_title} for {self.user.username} on {self.air_date}"
