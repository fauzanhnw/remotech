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
}

ALIGNABLE_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "span"}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target", "download"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "*": {"class"},
}
for _tag in ALIGNABLE_TAGS:
    ALLOWED_ATTRIBUTES.setdefault(_tag, set()).add("style")

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

STRIP_CONTENT_TAGS = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "noscript",
    "template",
}

MEDIA_URL_PATTERN = re.compile(
    r"""(?:src|href)\s*=\s*["'](/?media/[^"']+)["']""", re.IGNORECASE
)
MEDIA_ATTR_PATTERN = re.compile(
    r"""((?:src|href)\s*=\s*["'])(/?media/[^"']+)(["'])""", re.IGNORECASE
)


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
    return _cleaner.clean(html)


def extract_media_urls(html: str) -> set[str]:
    if not html:
        return set()
    return {match for match in MEDIA_URL_PATTERN.findall(html)}
