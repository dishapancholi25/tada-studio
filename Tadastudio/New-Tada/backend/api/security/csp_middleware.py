"""Content Security Policy (CSP) Middleware.

This middleware adds CSP headers to all responses as part of XSS mitigation
(Observation #5 - Stored Cross-Site Scripting in Wiki Pages).

CSP provides a browser-side defense layer that blocks inline scripts,
frames, and unsafe objects even if sanitization is bypassed.

References:
- https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
- https://csp.withgoogle.com/docs/index.html
"""

import logging
import os
import re
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# CSP directives for XSS protection
# These are deliberately strict to provide maximum protection
DEFAULT_CSP_DIRECTIVES = {
    # Default fallback for all resource types
    "default-src": "'self'",
    # Scripts must come from same origin only - blocks inline scripts
    "script-src": "'self'",
    # Styles from same origin - may need 'unsafe-inline' for some UI frameworks
    "style-src": "'self' 'unsafe-inline'",
    # Images from same origin and data URIs (for embedded images)
    "img-src": "'self' data: blob:",
    # Fonts from same origin
    "font-src": "'self' data:",
    # Block all frame embedding - prevents iframe-based XSS
    "frame-src": "'none'",
    # Block all plugin content (Flash, Java, etc.)
    "object-src": "'none'",
    # Restrict form submissions to same origin
    "form-action": "'self'",
    # Restrict base URI to prevent base tag hijacking
    "base-uri": "'self'",
    # Connect (fetch, XHR, WebSocket) to same origin
    "connect-src": "'self' wss: ws:",
    # Block embedding this site in frames on other sites
    "frame-ancestors": "'self'",
}

# Swagger/ReDoc pages served by FastAPI load third-party static assets and inline scripts.
# Keep this policy scoped to docs routes only to avoid weakening global CSP.
DOCS_CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "img-src": "'self' data: blob: https://fastapi.tiangolo.com",
    "font-src": "'self' data:",
    "frame-src": "'none'",
    "object-src": "'none'",
    "form-action": "'self'",
    "base-uri": "'self'",
    "connect-src": "'self' wss: ws:",
    "frame-ancestors": "'self'",
}


_DOCS_PATH_PATTERN = re.compile(r"/(?:docs|redoc)(?:/|$)")


def get_csp_policy(
    report_uri: Optional[str] = None,
    report_only: bool = False,
    directives: Optional[dict[str, str]] = None,
) -> str:
    """Build the CSP policy string from directives.

    Args:
        report_uri: Optional URI to send CSP violation reports to.
                    Used for monitoring before enforcing strict policies.
        report_only: If True, use Content-Security-Policy-Report-Only header
                     which reports violations without blocking them.

    Returns:
        CSP policy string ready to be used as header value.
    """
    directives = (directives or DEFAULT_CSP_DIRECTIVES).copy()

    # Add report-uri if configured
    if report_uri:
        directives["report-uri"] = report_uri

    # Build policy string
    policy_parts = [f"{key} {value}" for key, value in directives.items()]
    return "; ".join(policy_parts)


class CSPMiddleware(BaseHTTPMiddleware):
    """Middleware that adds Content-Security-Policy headers to responses.

    This middleware is part of the XSS mitigation strategy and provides
    browser-side protection as a defense-in-depth measure.

    Attributes:
        report_uri: Optional URI for CSP violation reports
        report_only: If True, only report violations without blocking
    """

    def __init__(
        self,
        app,
        report_uri: Optional[str] = None,
        report_only: bool = False,
    ):
        """Initialize CSP middleware.

        Args:
            app: The ASGI application
            report_uri: Optional URI to send CSP violation reports
            report_only: If True, use Report-Only mode (monitoring only)
        """
        super().__init__(app)
        self.report_uri = report_uri or os.getenv("CSP_REPORT_URI")
        report_only_env = os.getenv("CSP_REPORT_ONLY", "").lower() == "true"
        self.report_only = report_only or report_only_env
        self.policy = get_csp_policy(
            report_uri=self.report_uri,
            report_only=self.report_only,
        )
        self.docs_policy = get_csp_policy(
            report_uri=self.report_uri,
            report_only=self.report_only,
            directives=DOCS_CSP_DIRECTIVES,
        )

        # Determine header name based on mode
        if self.report_only:
            self.header_name = "Content-Security-Policy-Report-Only"
            logger.info(
                "[CSP] Initialized in REPORT-ONLY mode (violations logged, not blocked)"
            )
        else:
            self.header_name = "Content-Security-Policy"
            logger.info("[CSP] Initialized in ENFORCE mode (violations blocked)")

        if self.report_uri:
            logger.info("[CSP] Violation reports will be sent to: %s", self.report_uri)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add CSP header to response.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response with CSP header added
        """
        response = await call_next(request)

        # Apply a route-specific policy for FastAPI docs pages (Swagger/ReDoc),
        # and keep strict defaults for the rest of the application.
        response.headers[self.header_name] = (
            self.docs_policy if _DOCS_PATH_PATTERN.search(request.url.path) else self.policy
        )

        # Add additional security headers
        # X-Content-Type-Options prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options provides legacy browser support for frame blocking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # X-XSS-Protection for legacy browsers (deprecated but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
 