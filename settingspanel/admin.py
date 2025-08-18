from django.contrib import admin
from .models import AppSettings, ArrInstance

@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
	list_display = ("jellyfin_server_url", "sonarr_url", "radarr_url", "updated_at")

@admin.register(ArrInstance)
class ArrInstanceAdmin(admin.ModelAdmin):
	list_display = ("kind", "name", "base_url", "enabled", "order")
	list_filter = ("kind", "enabled")
	search_fields = ("name", "base_url")
