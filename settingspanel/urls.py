from django.urls import path
from .views import SettingsView, test_connection

app_name = "settingspanel"
urlpatterns = [
    path("", SettingsView.as_view(), name="index"),
    path("test-connection/", test_connection, name="test_connection"),
]
