from django.urls import path
from .views import (
    ArrIndexView, SeriesSubscribeView, SeriesUnsubscribeView,
    MovieSubscribeView, MovieUnsubscribeView,
    ListSeriesSubscriptionsView, ListMovieSubscriptionsView,
    CalendarView, CalendarEventsApi,
    FourKIndexView, Movie4KSubscribeView, Movie4KUnsubscribeView,
)

app_name = 'arr_api'

urlpatterns = [
    path('', ArrIndexView.as_view(), name='index'),
    # Calendar
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('api/calendar/events/', CalendarEventsApi.as_view(), name='calendar-events'),

    # 4K section
    path('movies-4k/', FourKIndexView.as_view(), name='movies-4k'),
    path('api/movies4k/subscribe/<int:tmdb_id>/', Movie4KSubscribeView.as_view(), name='subscribe-movie4k'),
    path('api/movies4k/unsubscribe/<int:tmdb_id>/', Movie4KUnsubscribeView.as_view(), name='unsubscribe-movie4k'),
    
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