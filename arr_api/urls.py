from django.urls import path
from .views import (
    ArrIndexView, SeriesSubscribeView, SeriesUnsubscribeView,
    MovieSubscribeView, MovieUnsubscribeView,
    ListSeriesSubscriptionsView, ListMovieSubscriptionsView
)

app_name = 'arr_api'

urlpatterns = [
    path('', ArrIndexView.as_view(), name='index'),
    
    # Series URLs
    path('api/series/subscribe/<int:series_id>/', SeriesSubscribeView.as_view(), name='subscribe-series'),
    path('api/series/unsubscribe/<int:series_id>/', SeriesUnsubscribeView.as_view(), name='unsubscribe-series'),
    path('api/series/subscriptions/', ListSeriesSubscriptionsView.as_view(), name='list-series-subscriptions'),
    
    # Movie URLs
    path('api/movies/subscribe/<str:title>/', MovieSubscribeView.as_view(), name='subscribe-movie'),
    path('api/movies/unsubscribe/<str:title>/', MovieUnsubscribeView.as_view(), name='unsubscribe-movie'),
    path('api/movies/subscriptions/', ListMovieSubscriptionsView.as_view(), name='list-movie-subscriptions'),
    
    # Get all subscriptions

]