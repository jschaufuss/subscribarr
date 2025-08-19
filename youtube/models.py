from django.db import models
from django.conf import settings

class YouTubeSubscription(models.Model):
    CHANNEL = 'channel'
    PLAYLIST = 'playlist'
    KIND_CHOICES = [(CHANNEL, 'Channel'), (PLAYLIST, 'Playlist')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='yt_subscriptions')
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    target_id = models.CharField(max_length=128)  # channelId or playlistId
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'kind', 'target_id')]
        indexes = [models.Index(fields=['kind', 'target_id'])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"

class YTSentNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video_id = models.CharField(max_length=64)
    published_date = models.DateField()
    title = models.CharField(max_length=300)
    channel_title = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'video_id')]
        indexes = [models.Index(fields=['video_id'])]
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.video_id} -> {self.user}"
