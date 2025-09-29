"""
Blog-related functions to get latest posts.
"""

from bs4 import BeautifulSoup
from dateutil import parser
from urllib.error import HTTPError
import urllib.request
import xml.etree.ElementTree as ET


def remove_emojis(text):
    """Remove common emoji characters and zero-width joiners from text."""
    if not text:
        return ''

    emoji_ranges = [
        (0x1F600, 0x1F64F),
        (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF),
        (0x1F900, 0x1F9FF),
        (0x2600,  0x26FF),
        (0x2700,  0x27BF),
    ]

    # remove emoji's zero-width joiner: \u200d
    res = ''.join(
        c for c in text
        if c != '\u200d' and not any(start <= ord(c) <= end for start, end in emoji_ranges)
    )
    return res

def fetch_xml(rss_url):
    """
    Fetch raw XML data from the given RSS feed URL.
    Returns bytes or None if fetching fails.
    """
    try:
        with urllib.request.urlopen(rss_url) as response:
            return response.read()
    except HTTPError:
        return None

def parse_feed(xml_data, n=3):
    """
    Parse RSS feed XML and extract up to n items.
    Returns a list of post dictionaries.
    """
    root = ET.fromstring(xml_data)
    ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
    posts = []

    for item in root.findall('./channel/item')[:n]:
        posts.append(extract_item(item, ns))

    return posts

def extract_item(item, ns):
    """
    Extract relevant fields from a single RSS <item>.
    Returns a dictionary with title, link, date, tags, items, and image.
    """
    title = remove_emojis(item.find('title').text)
    link = item.find('link').text
    date = parser.parse(item.find('pubDate').text)
    tags = [tag.text for tag in item.findall('category')]

    content_encoded = item.find('content:encoded', ns)
    body_html = content_encoded.text if content_encoded is not None else ''
    items = parse_content(body_html)

    media_content = item.find('{http://search.yahoo.com/mrss/}content')
    image = media_content.attrib.get('url') if media_content is not None else None

    return {
        "title": title,
        "link": link,
        "date": date,
        "items": items,
        "image": image,
        "tags": tags
    }

def parse_content(body_html):
    """
    Parse the HTML body of a post to extract key-value pairs
    defined in <b> tags inside kg-card blocks.

    Returns a dictionary of extracted items.
    """
    soup = BeautifulSoup(body_html, 'html.parser')
    items = {}

    for card in soup.find_all('div', class_='kg-card'):
        for p in card.find_all('p'):
            for b_tag in p.find_all('b'):
                key = remove_emojis(b_tag.get_text()).strip().rstrip(':').lower()
                if not key:
                    continue

                text_parts = []
                for sibling in b_tag.next_siblings:
                    if sibling.name == 'br':
                        break
                    elif isinstance(sibling, str):
                        text_parts.append(sibling)
                    else:
                        text_parts.append(sibling.get_text())
                items[key] = ''.join(text_parts).strip()

    return items

def get_latest_posts(n=3, tag=None):
    """
    Fetch and parse posts from an RSS feed.
    If a tag is provided, fetch posts only from that tag's feed.

    Args:
        n (int): Number of posts to fetch.
        tag (str | None): Optional tag to filter by.

    Returns:
        list[dict] | None: List of post dictionaries, or None if fetch fails.
    """
    url = "https://biodiversitycellatlas.org/blog"
    if tag:
        url = f"{url}/tag/{tag}"

    url = f"{url}/rss/"

    xml = fetch_xml(url)
    if not xml:
        return None
    return parse_feed(xml, n)
