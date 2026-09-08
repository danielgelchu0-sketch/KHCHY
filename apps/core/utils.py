import re
import bleach
from django.utils.html import escape
from django.utils.safestring import mark_safe

ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u",
    "ul", "ol", "li", "blockquote", "code", "pre", "a"
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_user_input(text: str) -> str:
    """
    Sanitize untrusted user-submitted text using bleach.
    Enforces strict tag whitelist, attributes, safe link protocols,
    and automatic rel='nofollow noopener noreferrer' on links.
    """
    if not text:
        return ""

    # Replace windows line endings
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip script and style elements along with their contents completely
    cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<\s*style[^>]*>.*?<\s*/\s*style\s*>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # If input doesn't contain HTML tags, convert newlines to paragraphs/breaks
    if not re.search(r"<[a-zA-Z\/][^>]*>", cleaned):
        paragraphs = cleaned.split("\n\n")
        escaped_paras = [
            f"<p>{escape(para).replace(chr(10), '<br>')}</p>"
            for para in paragraphs
            if para.strip()
        ]
        cleaned = "".join(escaped_paras)

    # Sanitize with bleach
    sanitized = bleach.clean(
        cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # Linkify plain URLs safely
    linkified = bleach.linkify(
        sanitized,
        callbacks=[
            lambda attrs, new: {
                **attrs,
                (None, "rel"): "nofollow noopener noreferrer",
                (None, "target"): "_blank",
            }
        ],
    )

    return mark_safe(linkified)
