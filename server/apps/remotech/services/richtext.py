import re
from urllib.parse import urlsplit

import nh3
from django.conf import settings

ALLOWED_TAGS = {
    "p",
    "div",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "a",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "code",
    "img",
    "figure",
    "figcaption",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "sub",
    "sup",
    "mark",
    "span",
    "iframe",
}

ALIGNABLE_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "span"}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target", "download"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "iframe": {
        "src",
        "width",
        "height",
        "frameborder",
        "allowfullscreen",
        "allow",
        "title",
        "referrerpolicy",
    },
    "*": {"class"},
}
for _tag in ALIGNABLE_TAGS:
    ALLOWED_ATTRIBUTES.setdefault(_tag, set()).add("style")

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

STRIP_CONTENT_TAGS = {
    "script",
    "style",
    "object",
    "embed",
    "noscript",
    "template",
}

# Domain host embed video yang diizinkan di dalam <iframe> module teks.
# Pencocokan memakai dot-boundary: "youtube.com" juga menyetujui "www.youtube.com",
# tetapi tidak "evil-youtube.com".
EMBED_HOSTS = {
    "youtube.com",
    "youtube-nocookie.com",
    "drive.google.com",
    "docs.google.com",
    "player.vimeo.com",
    "www.loom.com",
    "player.twitch.tv",
    "clips.twitch.tv",
}

MEDIA_URL_PATTERN = re.compile(
    r"""(?:src|href)\s*=\s*["'](/?media/[^"']+)["']""", re.IGNORECASE
)
MEDIA_ATTR_PATTERN = re.compile(
    r"""((?:src|href)\s*=\s*["'])(/?media/[^"']+)(["'])""", re.IGNORECASE
)
IFRAME_TAG_PATTERN = re.compile(
    r"<iframe\b([^>]*)>(?:.*?</iframe\s*>)?", re.IGNORECASE | re.DOTALL
)
IFRAME_SRC_PATTERN = re.compile(r"""src\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def is_embed_host(value: str) -> bool:
    """True bila URL http(s) menuju host di EMBED_HOSTS (dot-boundary match)."""
    if not isinstance(value, str) or not value:
        return False
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    if not host:
        return False
    return any(host == entry or host.endswith(f".{entry}") for entry in EMBED_HOSTS)


def _strip_disallowed_iframes(html: str) -> str:
    """Buang <iframe> (beserta isinya) yang src-nya bukan host embed yang diizinkan."""

    def _keep(match: re.Match) -> str:
        src = IFRAME_SRC_PATTERN.search(match.group(1))
        if src and is_embed_host(src.group(1)):
            return match.group(0)
        return ""

    return IFRAME_TAG_PATTERN.sub(_keep, html)


def normalize_media_url(value):
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("/media/"):
        return value
    if value.startswith("media/"):
        return f"/{value}"

    parts = urlsplit(value)
    if parts.scheme in ("http", "https") and parts.path.startswith("/media/"):
        base = urlsplit(settings.BASE_URL)
        if base.netloc and parts.netloc == base.netloc:
            path = parts.path
            if parts.query:
                path = f"{path}?{parts.query}"
            return path
    return value


def absolutize_media_url(value):
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("media/"):
        value = f"/{value}"
    index = value.find("/media/")
    if index == -1:
        return value
    return f"{settings.BASE_URL.rstrip('/')}{value[index:]}"


def absolutize_media_urls(html):
    if not html:
        return html
    base = settings.BASE_URL.rstrip("/")
    return MEDIA_ATTR_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}{base}/{match.group(2).lstrip('/')}{match.group(3)}"
        ),
        html,
    )


def _attribute_filter(tag, attr, value):
    if tag == "iframe" and attr == "src":
        # Lapis kedua setelah _strip_disallowed_iframes: src iframe harus host embed.
        return value if is_embed_host(value) else None
    if attr in ("src", "href"):
        return normalize_media_url(value)
    return value


_cleaner = nh3.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    attribute_filter=_attribute_filter,
    url_schemes=ALLOWED_URL_SCHEMES,
    url_relative="pass_through",
    filter_style_properties={"text-align"},
    clean_content_tags=STRIP_CONTENT_TAGS,
)


def sanitize_richtext(html: str) -> str:
    if not html:
        return ""
    return _cleaner.clean(_strip_disallowed_iframes(html))


def extract_media_urls(html: str) -> set[str]:
    if not html:
        return set()
    return {match for match in MEDIA_URL_PATTERN.findall(html)}
