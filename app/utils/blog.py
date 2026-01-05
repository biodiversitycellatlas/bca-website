"""
Blog-related functions to get latest posts.
"""

from bs4 import BeautifulSoup
from dateutil import parser
import feedparser
from django.conf import settings


def remove_emojis(text):
    """Remove common emoji characters and zero-width joiners from text."""
    if not text:
        return ""

    emoji_ranges = [
        (0x1F600, 0x1F64F),
        (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF),
        (0x1F900, 0x1F9FF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]

    return "".join(c for c in text if c != "\u200d" and not any(start <= ord(c) <= end for start, end in emoji_ranges))


def parse_content(body_html):
    """
    Parse the HTML body of a post to extract key-value pairs
    defined in the information blocks of the content.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    items = {}

    for card in soup.find_all("div", class_="kg-card"):
        for p in card.find_all("p"):
            for b_tag in p.find_all("b"):
                key = remove_emojis(b_tag.get_text()).strip().rstrip(":").lower()
                if not key:
                    continue

                text_parts = []
                for sibling in b_tag.next_siblings:
                    if getattr(sibling, "name", None) == "br":
                        break

                    if isinstance(sibling, str):
                        text_parts.append(sibling)
                    else:
                        text_parts.append(sibling.get_text())
                items[key] = "".join(text_parts).strip()
    return items


def extract_image(entry):
    """Extract the main image URL from blog entry."""
    image = None

    media = entry.get("media_content", [])
    if media and isinstance(media, list):
        image = media[0].get("url")

    return image


def get_latest_posts(n=3, tag=None):
    """
    Fetch and parse posts from the internal Ghost container
    using the RSS feed (optionally filtered by tag).
    Bypasses VPN/Public DNS by using the Podman bridge network.
    """
    posts = []  # Define an empty list for posts

    # 1. Use internal container name and port
    # Get the base from .env and append the path
    internal_host = getattr(settings, "GHOST_INTERNAL_URL").rstrip("/")
    public_domain = getattr(settings, "BCA_DOMAIN", "localhost")
    base_url = f"{internal_host}/blog"
    tag_path = f"tag/{tag}/" if tag else ""
    # Ensure the trailing slash is present to avoid Ghost's internal redirects
    feed_url = f"{base_url}/{tag_path}rss/"

    # 2. Detect if the app is in "Secure" mode
    # We check if SECURE_SSL_REDIRECT is True (common in prod)
    is_secure = getattr(settings, "SECURE_SSL_REDIRECT", False)

    request_headers = {}
    if is_secure:
        request_headers = {"Host": public_domain, "X-Forwarded-Proto": "https", "User-Agent": "BCA-Django-Internal/1.0"}

    try:
        # feedparser.parse can take headers directly
        feed = feedparser.parse(feed_url, request_headers=request_headers)

        # Check for successful fetch
        if hasattr(feed, "status") and feed.status >= 400:
            print(f"get_latest_posts - Ghost RSS Fetch Failed: Status {feed.status} for {feed_url}")
            return []

        if not feed.entries:
            return []

        for entry in feed.entries[:n]:
            # Extract content from feed
            body_html = entry.get("content", [{}])[0].get("value")
            items = parse_content(body_html)

            date = None
            if entry.get("published"):
                date = parser.parse(entry.get("published"))

            post = {
                "title": entry.title,
                "link": entry.link,
                "date": date,
                "tags": [tag.term for tag in entry.get("tags", [])],
                "items": items,
                "image": extract_image(entry),
            }
            posts.append(post)

        return posts

    except Exception as e:
        print(f"get_latest_posts - Ghost RSS Internal Error: {e}")
        return []
