"""
Wiki content sanitizer service.

This module provides server-side HTML sanitization for wiki content
to prevent stored XSS attacks. It uses the bleach library with a
strict allowlist of safe tags and attributes.

Security Note:
    This sanitizer is a defense-in-depth measure. Client-side sanitization
    via rehype-sanitize also applies, but server-side sanitization ensures
    that malicious content cannot be stored regardless of how it's submitted.

Blocked tags:
    - script: JavaScript execution
    - iframe: Frame injection, srcdoc XSS
    - object: Plugin/embedded content
    - embed: Plugin/embedded content
    - style: CSS injection
    - form: Credential phishing
    - input: Form-based attacks
    - meta: Redirect injection
    - base: Base URL hijacking
    - link: Resource injection

Blocked attributes:
    - on*: All event handlers (onclick, onerror, onload, etc.)
    - srcdoc: Iframe content injection
    - formaction: Form action override
    - xlink:href: SVG link injection
"""

import re
from typing import List, Optional, Set

import bleach
from bleach.css_sanitizer import CSSSanitizer

from backend.services.config import get_logger

logger = get_logger(__name__)

# Tags that are explicitly allowed in wiki content
# These are safe HTML tags commonly used in markdown rendering
ALLOWED_TAGS: List[str] = [
    # Text formatting
    "p",
    "br",
    "span",
    "div",
    # Headings
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # Lists
    "ul",
    "ol",
    "li",
    # Tables
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "colgroup",
    "col",
    # Text styling
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "del",
    "ins",
    "mark",
    "small",
    "sub",
    "sup",
    # Links and media (with attribute restrictions)
    "a",
    "img",
    # Code
    "pre",
    "code",
    "kbd",
    "samp",
    "var",
    # Semantic
    "blockquote",
    "q",
    "cite",
    "abbr",
    "dfn",
    # Structural
    "hr",
    "details",
    "summary",
    "figure",
    "figcaption",
    # Definition lists
    "dl",
    "dt",
    "dd",
]

# Attributes allowed on specific tags
# Note: We do NOT allow any on* event handlers
ALLOWED_ATTRIBUTES: dict = {
    # Global safe attributes (no event handlers)
    "*": ["class", "id", "title", "lang", "dir"],
    # Links - href is sanitized separately, no javascript: or data:
    "a": ["href", "target", "rel", "download"],
    # Images - src is sanitized, no event handlers
    "img": ["src", "alt", "width", "height", "loading", "decoding"],
    # Tables
    "th": ["scope", "colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "col": ["span"],
    "colgroup": ["span"],
    # Abbreviations
    "abbr": ["title"],
    # Lists (for task lists)
    "li": ["data-task"],
    # Code blocks
    "code": ["class"],  # For language-* classes from syntax highlighting
    "pre": ["class"],
}

# Dangerous URL schemes that should never be allowed
DANGEROUS_PROTOCOLS: Set[str] = {
    "javascript",
    "vbscript",
    "data",  # Can contain scripts via data:text/html
    "blob",  # Can reference dangerous content
}

# Allowed URL protocols
ALLOWED_PROTOCOLS: List[str] = [
    "http",
    "https",
    "mailto",
    "tel",
    "ftp",
]

# Pattern to detect event handler attributes (on*)
EVENT_HANDLER_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)

# Pattern to detect srcdoc attribute
SRCDOC_PATTERN = re.compile(r"\bsrcdoc\s*=", re.IGNORECASE)


class WikiSanitizer:
    """
    Sanitizes wiki content to prevent XSS attacks.

    This class provides a clean() method that removes dangerous HTML
    elements and attributes while preserving safe markdown-generated content.

    Usage:
        sanitizer = WikiSanitizer()
        safe_content = sanitizer.clean(user_content)
    """

    def __init__(self):
        """Initialize the sanitizer with default configuration."""
        # CSS sanitizer for inline styles (very restrictive)
        self._css_sanitizer = CSSSanitizer(
            allowed_css_properties=["color", "background-color", "text-align"]
        )

    def clean(self, content: str) -> str:
        """
        Sanitize HTML content to remove XSS vectors.

        Args:
            content: Raw HTML/markdown content that may contain malicious code

        Returns:
            Sanitized content with dangerous elements removed

        Example:
            >>> sanitizer = WikiSanitizer()
            >>> sanitizer.clean('<script>alert("XSS")</script>')
            ''
            >>> sanitizer.clean('<iframe srcdoc="<script>alert(1)</script>">')
            ''
            >>> sanitizer.clean('<p onclick="alert(1)">Hello</p>')
            '<p>Hello</p>'
        """
        if not content:
            return content

        # Pre-filter: Remove event handlers that might slip through
        # This catches cases like <div onclick="..."> before bleach processes
        content = self._remove_event_handlers(content)

        # Main sanitization pass using bleach
        clean_content = bleach.clean(
            content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,  # Remove disallowed tags entirely (don't escape)
            strip_comments=True,  # Remove HTML comments
        )

        # Post-filter: Double-check no dangerous patterns remain
        clean_content = self._post_sanitize(clean_content)

        return clean_content

    def _remove_event_handlers(self, content: str) -> str:
        """
        Remove event handler attributes from content.

        This is a pre-filter to catch event handlers before bleach processing.
        Bleach should handle this, but this adds defense in depth.
        """
        # Remove onclick, onerror, onload, etc.
        if EVENT_HANDLER_PATTERN.search(content):
            logger.warning(
                "[WIKI-SANITIZE] Event handler detected and will be removed"
            )
            # Remove entire attribute including value
            content = re.sub(
                r'\s*on\w+\s*=\s*["\'][^"\']*["\']',
                "",
                content,
                flags=re.IGNORECASE,
            )
            content = re.sub(
                r"\s*on\w+\s*=\s*[^\s>]+",
                "",
                content,
                flags=re.IGNORECASE,
            )

        # Remove srcdoc attribute specifically (iframe XSS vector)
        if SRCDOC_PATTERN.search(content):
            logger.warning(
                "[WIKI-SANITIZE] srcdoc attribute detected and will be removed"
            )
            content = re.sub(
                r'\s*srcdoc\s*=\s*["\'][^"\']*["\']',
                "",
                content,
                flags=re.IGNORECASE,
            )

        return content

    def _post_sanitize(self, content: str) -> str:
        """
        Post-sanitization checks for any remaining dangerous patterns.

        This catches edge cases that might slip through bleach.
        """
        # Verify no script/iframe/object tags remain (they shouldn't after bleach)
        dangerous_tags = ["<script", "<iframe", "<object", "<embed", "<form", "<input"]
        for tag in dangerous_tags:
            if tag in content.lower():
                logger.error(
                    f"[WIKI-SANITIZE] Dangerous tag {tag} found after sanitization"
                )
                content = re.sub(
                    rf"<{tag[1:]}\b[^>]*>.*?</{tag[1:]}>",
                    "",
                    content,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                content = re.sub(
                    rf"<{tag[1:]}\b[^>]*/?>",
                    "",
                    content,
                    flags=re.IGNORECASE,
                )

        return content

    def is_safe(self, content: str) -> bool:
        """
        Check if content is safe without modifying it.

        Args:
            content: Content to check

        Returns:
            True if content is safe, False if it would be modified by clean()
        """
        if not content:
            return True

        return self.clean(content) == content


# Singleton instance for convenience
_sanitizer_instance: Optional[WikiSanitizer] = None


def get_wiki_sanitizer() -> WikiSanitizer:
    """Get the wiki sanitizer singleton instance."""
    global _sanitizer_instance
    if _sanitizer_instance is None:
        _sanitizer_instance = WikiSanitizer()
    return _sanitizer_instance


def sanitize_wiki_content(content: str) -> str:
    """
    Convenience function to sanitize wiki content.

    Args:
        content: Raw wiki content

    Returns:
        Sanitized content
    """
    return get_wiki_sanitizer().clean(content)
