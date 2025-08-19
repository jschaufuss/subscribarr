from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import YouTubeSubscription
from .services import get_youtube_metadata

@login_required
def index(request):
    subs = YouTubeSubscription.objects.filter(user=request.user).order_by('title')
    items = []
    for s in subs:
        meta = {}
        try:
            meta = get_youtube_metadata(s.kind, s.target_id) or {}
        except Exception:
            meta = {}
        items.append({'sub': s, 'meta': meta})
    return render(request, 'youtube/index.html', { 'subs': subs, 'sub_items': items })

@login_required
@require_POST
def subscribe(request):
    kind = (request.POST.get('kind') or '').strip()
    target_id = (request.POST.get('target_id') or '').strip()
    title = (request.POST.get('title') or '').strip() or target_id
    if kind not in ('channel','playlist') or not target_id:
        return JsonResponse({'ok': False, 'error': 'Invalid input'}, status=400)
    sub, created = YouTubeSubscription.objects.get_or_create(user=request.user, kind=kind, target_id=target_id, defaults={'title': title})
    if not created and title and sub.title != title:
        sub.title = title
        sub.save(update_fields=['title'])
    return JsonResponse({'ok': True})

@login_required
@require_POST
def unsubscribe(request):
    kind = (request.POST.get('kind') or '').strip()
    target_id = (request.POST.get('target_id') or '').strip()
    YouTubeSubscription.objects.filter(user=request.user, kind=kind, target_id=target_id).delete()
    return JsonResponse({'ok': True})
