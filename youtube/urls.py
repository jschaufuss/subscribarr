from django.urls import path
from .views import index, subscribe, unsubscribe

app_name = 'youtube'

urlpatterns = [
    path('', index, name='index'),
    path('subscribe/', subscribe, name='subscribe'),
    path('unsubscribe/', unsubscribe, name='unsubscribe'),
]
