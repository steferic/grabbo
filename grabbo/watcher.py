"""Clipboard watcher for supported URLs."""
import re
import subprocess
import time

# Patterns for supported sites
URL_PATTERNS = [
    # YouTube
    r"https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
    r"https?://youtu\.be/[\w-]+",
    r"https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
    r"https?://music\.youtube\.com/watch\?v=[\w-]+",
    # SoundCloud
    r"https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+",
    r"https?://(?:m\.)?soundcloud\.com/[\w-]+/[\w-]+",
    # Bandcamp
    r"https?://[\w-]+\.bandcamp\.com/track/[\w-]+",
    r"https?://[\w-]+\.bandcamp\.com/album/[\w-]+",
    # Mixcloud
    r"https?://(?:www\.)?mixcloud\.com/[\w-]+/[\w-]+",
    # Vimeo
    r"https?://(?:www\.)?vimeo\.com/\d+",
    # TikTok
    r"https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+",
    r"https?://vm\.tiktok\.com/[\w-]+",
    # Twitter/X
    r"https?://(?:www\.)?(?:twitter|x)\.com/\w+/status/\d+",
    # Instagram
    r"https?://(?:www\.)?instagram\.com/(?:p|reel)/[\w-]+",
    # Twitch
    r"https?://(?:www\.)?twitch\.tv/videos/\d+",
    r"https?://clips\.twitch\.tv/[\w-]+",
]

URL_REGEX = re.compile("|".join(URL_PATTERNS))


def get_clipboard() -> str:
    """Get current clipboard contents on macOS."""
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def extract_url(text: str) -> str | None:
    """Extract a supported URL from text if present."""
    match = URL_REGEX.search(text)
    if match:
        return match.group(0)
    return None


def watch_clipboard(callback, interval: float = 1.0):
    """Watch clipboard for supported URLs.

    Args:
        callback: Function to call with URL when detected
        interval: Seconds between clipboard checks
    """
    seen_urls = set()
    last_clipboard = ""

    while True:
        try:
            clipboard = get_clipboard()

            # Only process if clipboard changed
            if clipboard != last_clipboard:
                last_clipboard = clipboard
                url = extract_url(clipboard)

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    callback(url)

        except KeyboardInterrupt:
            break
        except Exception:
            pass

        time.sleep(interval)
