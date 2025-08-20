from django.urls import path
from .views import SettingsView, test_connection, first_run, subscriptions_overview, test_notify, reset_notify_tokens, test_setup_connection

app_name = "settingspanel"
urlpatterns = [
    path("", SettingsView.as_view(), name="index"),
    path("test-connection/", test_connection, name="test_connection"),
    path("test-setup-connection/", test_setup_connection, name="test_setup_connection"),
    path("test-notify/", test_notify, name="test_notify"),
    path("reset-notify-tokens/", reset_notify_tokens, name="reset_notify_tokens"),
    path("setup/", first_run, name="setup"),
    path("subscriptions/", subscriptions_overview, name="subscriptions"),
]
