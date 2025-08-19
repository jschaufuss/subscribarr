import re
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from functools import lru_cache


ATOM_NS = '{http://www.w3.org/2005/Atom}'
YT_NS = '{http://www.youtube.com/xml/schemas/2015}'
MEDIA_NS = '{http://search.yahoo.com/mrss/}'


def _resolve_handle_to_channel_id(handle: str, timeout: int = 6) -> str | None:
    h = handle.strip()
    if h.startswith('/'):
        h = h[1:]
    if not h.startswith('@'):
        return None
    url = f"https://www.youtube.com/{h}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        m = re.search(r'"channelId"\s*:\s*"(UC[^"]+?)"', r.text)
        if m:
            return m.group(1)
    except requests.RequestException:
        return None
    return None


def build_feed_url(kind: str, target_id: str) -> str | None:
    tid = (target_id or '').strip()
    if not tid:
        return None
    if tid.startswith('/@') or tid.startswith('@'):
        cid = _resolve_handle_to_channel_id(tid)
        if not cid:
            return None
        tid = cid
    # Channel IDs start with UC, Playlists start with PL or UU (uploads)
    if kind == 'channel' or tid.startswith('UC'):
        if not tid.startswith('UC'):
            return None
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={tid}"
    # playlist
    if tid.startswith('PL') or tid.startswith('UU') or kind == 'playlist':
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={tid}"
    return None


def _parse_dt(s: str) -> datetime | None:
    try:
        # Atom published like 2025-08-18T17:22:46+00:00
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch_feed_entries(feed_url: str, timeout: int = 10) -> list[dict]:
    if not feed_url:
        return []
    try:
        r = requests.get(feed_url, timeout=timeout, headers={'User-Agent': 'Subscribarr/YouTube'})
        r.raise_for_status()
    except requests.RequestException:
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    entries = []
    for e in root.findall(f'{ATOM_NS}entry'):
        title_el = e.find(f'{ATOM_NS}title')
        title = title_el.text if title_el is not None else ''
        link_el = e.find(f'{ATOM_NS}link')
        href = link_el.get('href') if link_el is not None else ''
        pub_el = e.find(f'{ATOM_NS}published')
        published = _parse_dt(pub_el.text) if pub_el is not None else None
        vid_el = e.find(f'{YT_NS}videoId')
        video_id = vid_el.text if vid_el is not None else None
        # media thumbnail (video still)
        thumb_url = None
        mt = e.find(f'{MEDIA_NS}thumbnail')
        if mt is not None and mt.get('url'):
            thumb_url = mt.get('url')
        else:
            mg = e.find(f'{MEDIA_NS}group')
            if mg is not None:
                mthumb = mg.find(f'{MEDIA_NS}thumbnail')
                if mthumb is not None and mthumb.get('url'):
                    thumb_url = mthumb.get('url')
        if not video_id and href:
            q = parse_qs(urlparse(href).query)
            video_id = (q.get('v') or [None])[0]
        author_name = ''
        author_el = e.find(f'{ATOM_NS}author')
        if author_el is not None:
            name_el = author_el.find(f'{ATOM_NS}name')
            author_name = name_el.text if name_el is not None else ''
        if not video_id:
            continue
        entries.append({
            'video_id': video_id,
            'title': title,
            'url': href or f'https://www.youtube.com/watch?v={video_id}',
            'published': published,
            'channel_title': author_name,
            'thumb': thumb_url,
        })
    return entries


def _http_get(url: str, timeout: int = 8) -> str | None:
    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'Subscribarr/YouTube',
                'Accept-Language': 'en-US,en;q=0.8',
            }
        )
        r.raise_for_status()
        return r.text
    except requests.RequestException:
        return None


def _parse_og(html: str) -> dict:
    # Very small regex-based OG parser
    meta = {}
    if not html:
        return meta
    # property="og:*"
    for prop in ("og:title", "og:image", "og:url"):
        m = re.search(r'<meta[^>]+property=["\']%s["\'][^>]+content=["\']([^"\']+)["\']' % re.escape(prop), html, flags=re.I)
        if m:
            meta[prop] = m.group(1)
    # itemprop="image"
    if 'og:image' not in meta:
        m = re.search(r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            meta['og:image'] = m.group(1)
    # <link rel="image_src" href="...">
    if 'og:image' not in meta:
        m = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            meta['og:image'] = m.group(1)
    # Attempt to find avatar thumbnails array in inline JSON
    if 'og:image' not in meta:
        # c4TabbedHeaderRenderer path (channel pages)
        m = re.search(r'c4TabbedHeaderRenderer"\s*:\s*\{.*?"avatar"\s*:\s*\{\s*"thumbnails"\s*:\s*\[(.*?)\]', html, flags=re.I|re.S)
        if m:
            # find last url in thumbnails list
            urls = re.findall(r'"url"\s*:\s*"(https:[^"\\]+)"', m.group(1))
            if urls:
                meta['og:image'] = urls[-1]
    # Fallback: any yt3.ggpht.com url on page (prefer largest sN)
    if 'og:image' not in meta:
        urls = re.findall(r'(https://yt3\.ggpht\.com/[a-zA-Z0-9_\-~=%\.]+)', html)
        if urls:
            # Heuristic: pick the longest url (often higher res variants)
            urls_sorted = sorted(urls, key=len, reverse=True)
            meta['og:image'] = urls_sorted[0]
    return meta


@lru_cache(maxsize=256)
def get_youtube_metadata(kind: str, target_id: str) -> dict:
    """
    Return minimal metadata for a channel or playlist without API key using OG tags.
    { 'title': str|None, 'image': str|None, 'url': str|None }
    """
    tid = (target_id or '').strip()
    if not tid:
        return {}
    if kind == 'channel' and (tid.startswith('@') or tid.startswith('/@')):
        cid = _resolve_handle_to_channel_id(tid)
        if cid:
            tid = cid
    if kind == 'channel':
        page_url = f'https://www.youtube.com/channel/{tid}' if tid.startswith('UC') else f'https://www.youtube.com/{tid.lstrip("/")}'
    else:
        page_url = f'https://www.youtube.com/playlist?list={tid}'
    # stabilize markup language
    if '?' in page_url:
        page_url = page_url + '&hl=en'
    else:
        page_url = page_url + '?hl=en'
    html = _http_get(page_url)
    og = _parse_og(html or '')
    title = og.get('og:title')
    image = og.get('og:image')
    url = og.get('og:url') or page_url
    # Fallback: try first feed thumbnail if no image
    if not image:
        feed = build_feed_url(kind, tid)
        entries = fetch_feed_entries(feed) if feed else []
        if entries:
            # If playlist: first entry thumb approximates cover; for channel: also acceptable fallback
            image = entries[0].get('thumb') or image
    return {
        'title': title,
        'image': image,
        'url': url,
    }
