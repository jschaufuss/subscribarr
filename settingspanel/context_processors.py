from .models import AppSettings

def feature_flags(request):
    try:
        cfg = AppSettings.current()
        youtube_enabled = bool(getattr(cfg, 'youtube_enabled', True))
    except Exception:
        youtube_enabled = True
    hide_user = False
    try:
        if request.user.is_authenticated and getattr(request.user, 'hide_youtube', False):
            hide_user = True
    except Exception:
        hide_user = False
    return {
        'YOUTUBE_GLOBAL_ENABLED': youtube_enabled,
        'YOUTUBE_USER_HIDDEN': hide_user,
        'SHOW_YOUTUBE_UI': youtube_enabled and not hide_user,
    }
