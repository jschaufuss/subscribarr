from django.urls import path
from .views import SettingsView, test_connection, first_run, subscriptions_overview

app_name = "settingspanel"
urlpatterns = [
    path("", SettingsView.as_view(), name="index"),
    path("test-connection/", test_connection, name="test_connection"),
    path("setup/", first_run, name="setup"),
    path("subscriptions/", subscriptions_overview, name="subscriptions"),
]
