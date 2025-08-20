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


def _http_get(url: str, timeout: int = 10) -> str | None:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        # Try with different user agent if first request fails
        try:
            headers['User-Agent'] = 'Subscribarr/YouTube (+https://github.com/subscribarr)'
            r = requests.get(url, timeout=timeout//2, headers=headers, allow_redirects=True)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            return None


def _parse_og(html: str) -> dict:
    # Enhanced OG parser with better YouTube-specific extraction
    meta = {}
    if not html:
        return meta
    
    # Standard OG tags
    for prop in ("og:title", "og:image", "og:url", "og:description"):
        # Try both property and name attributes
        patterns = [
            r'<meta[^>]+property=["\']%s["\'][^>]+content=["\']([^"\']+)["\']' % re.escape(prop),
            r'<meta[^>]+name=["\']%s["\'][^>]+content=["\']([^"\']+)["\']' % re.escape(prop),
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']%s["\']' % re.escape(prop),
        ]
        for pattern in patterns:
            m = re.search(pattern, html, flags=re.I)
            if m:
                meta[prop] = m.group(1)
                break
    
    # Twitter card fallbacks
    if 'og:title' not in meta:
        m = re.search(r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            meta['og:title'] = m.group(1)
    
    if 'og:image' not in meta:
        m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            meta['og:image'] = m.group(1)
    
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
    
    # Page title fallback
    if 'og:title' not in meta:
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, flags=re.I)
        if m:
            title = m.group(1).strip()
            # Clean up YouTube title suffixes
            title = re.sub(r'\s*-\s*YouTube\s*$', '', title, flags=re.I)
            meta['og:title'] = title
    
    # YouTube-specific JSON data extraction
    if 'og:image' not in meta or 'og:title' not in meta:
        # Try to extract from ytInitialData or similar
        json_patterns = [
            r'var ytInitialData = ({.+?});',
            r'"ytInitialData"\s*:\s*({.+?}),',
            r'window\["ytInitialData"\]\s*=\s*({.+?});'
        ]
        
        for pattern in json_patterns:
            m = re.search(pattern, html, flags=re.S)
            if m:
                try:
                    import json
                    data = json.loads(m.group(1))
                    
                    # Extract channel/playlist title and avatar
                    if 'og:title' not in meta:
                        # Try various paths for title
                        title_paths = [
                            ['metadata', 'channelMetadataRenderer', 'title'],
                            ['header', 'c4TabbedHeaderRenderer', 'title'],
                            ['header', 'pageHeaderRenderer', 'pageTitle'],
                            ['microformat', 'microformatDataRenderer', 'title'],
                        ]
                        for path in title_paths:
                            try:
                                temp = data
                                for key in path:
                                    temp = temp[key]
                                if isinstance(temp, str) and temp.strip():
                                    meta['og:title'] = temp.strip()
                                    break
                            except (KeyError, TypeError):
                                continue
                    
                    # Extract avatar/thumbnail
                    if 'og:image' not in meta:
                        thumbnail_paths = [
                            ['metadata', 'channelMetadataRenderer', 'avatar', 'thumbnails'],
                            ['header', 'c4TabbedHeaderRenderer', 'avatar', 'thumbnails'],
                            ['microformat', 'microformatDataRenderer', 'thumbnail', 'thumbnails'],
                        ]
                        for path in thumbnail_paths:
                            try:
                                temp = data
                                for key in path:
                                    temp = temp[key]
                                if isinstance(temp, list) and temp:
                                    # Get highest resolution thumbnail
                                    best_thumb = max(temp, key=lambda x: x.get('width', 0) * x.get('height', 0))
                                    if 'url' in best_thumb:
                                        meta['og:image'] = best_thumb['url']
                                        break
                            except (KeyError, TypeError):
                                continue
                    
                    if 'og:title' in meta and 'og:image' in meta:
                        break
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    
    # Attempt to find avatar thumbnails array in inline JSON (legacy method)
    if 'og:image' not in meta:
        # c4TabbedHeaderRenderer path (channel pages)
        m = re.search(r'c4TabbedHeaderRenderer"\s*:\s*\{.*?"avatar"\s*:\s*\{\s*"thumbnails"\s*:\s*\[(.*?)\]', html, flags=re.I|re.S)
        if m:
            # find highest resolution url in thumbnails list
            urls = re.findall(r'"url"\s*:\s*"(https:[^"\\]+)"', m.group(1))
            if urls:
                meta['og:image'] = urls[-1]  # Usually highest res is last
    
    # Fallback: any yt3.ggpht.com url on page (prefer largest)
    if 'og:image' not in meta:
        urls = re.findall(r'(https://yt3\.ggpht\.com/[a-zA-Z0-9_\-~=%\.]+)', html)
        if urls:
            # Heuristic: pick the longest url (often higher res variants)
            urls_sorted = sorted(set(urls), key=len, reverse=True)
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
    
    # Resolve handle to channel ID if needed
    original_tid = tid
    if kind == 'channel' and (tid.startswith('@') or tid.startswith('/@')):
        cid = _resolve_handle_to_channel_id(tid)
        if cid:
            tid = cid
    
    # Try multiple URL formats for better success rate
    urls_to_try = []
    if kind == 'channel':
        if tid.startswith('UC'):
            urls_to_try = [
                f'https://www.youtube.com/channel/{tid}',
                f'https://www.youtube.com/c/{tid}',
                f'https://www.youtube.com/{tid}'
            ]
        elif tid.startswith('@'):
            urls_to_try = [
                f'https://www.youtube.com/{tid}',
                f'https://www.youtube.com/c/{tid.lstrip("@")}',
                f'https://www.youtube.com/user/{tid.lstrip("@")}'
            ]
        else:
            urls_to_try = [
                f'https://www.youtube.com/{tid.lstrip("/")}',
                f'https://www.youtube.com/c/{tid}',
                f'https://www.youtube.com/user/{tid}',
                f'https://www.youtube.com/channel/{tid}'
            ]
    else:  # playlist
        urls_to_try = [
            f'https://www.youtube.com/playlist?list={tid}'
        ]
    
    # Try each URL until we get good metadata
    best_meta = {}
    for base_url in urls_to_try:
        # Add language parameter for consistent markup
        page_url = base_url + ('&hl=en' if '?' in base_url else '?hl=en')
        
        html = _http_get(page_url)
        if not html:
            continue
            
        og = _parse_og(html)
        title = og.get('og:title')
        image = og.get('og:image')
        url = og.get('og:url') or base_url
        
        # Score this result (prefer results with both title and image)
        score = 0
        if title and title.strip() and title.lower() not in ['youtube', 'youtube.com']:
            score += 2
        if image and image.strip():
            score += 2
        
        # Keep best result so far
        current_score = 0
        if best_meta.get('title'):
            current_score += 2
        if best_meta.get('image'):
            current_score += 2
            
        if score > current_score:
            best_meta = {
                'title': title,
                'image': image,
                'url': url,
            }
            
        # If we have both title and image, we're good
        if score >= 4:
            break
    
    # Fallback: try getting image from feed if we still don't have one
    if not best_meta.get('image'):
        try:
            feed = build_feed_url(kind, tid)
            entries = fetch_feed_entries(feed) if feed else []
            if entries:
                # For playlist: first entry thumb approximates cover
                # For channel: use channel avatar from feed metadata or first video thumb
                feed_image = entries[0].get('thumb')
                if feed_image:
                    best_meta['image'] = feed_image
        except Exception:
            pass
    
    # Final fallback: use a generic image based on type
    if not best_meta.get('image'):
        if kind == 'channel':
            best_meta['image'] = 'https://via.placeholder.com/88x88/ff0000/ffffff?text=📺'
        else:
            best_meta['image'] = 'https://via.placeholder.com/88x88/cc0000/ffffff?text=📋'
    
    # Fallback title if none found
    if not best_meta.get('title'):
        best_meta['title'] = f"{kind.title()}: {original_tid}"
    
    # Fallback URL
    if not best_meta.get('url'):
        best_meta['url'] = urls_to_try[0] if urls_to_try else f'https://www.youtube.com/{original_tid}'
    
    return best_meta
