"""Defense-in-depth middleware that strips oauth2-proxy internal headers from responses.

ISG Finding 1.9: Access Token Exposed to Client-Side JavaScript via Response Headers.

The ``X-Auth-Request-*`` headers are internal to the oauth2-proxy → backend hop
and must never appear in responses sent to the browser. The primary mitigation is
at the Ingress layer (``proxy_hide_header``), but this middleware provides a
backend-level safety net so that even if the Ingress is misconfigured or bypassed,
the sensitive headers are scrubbed before leaving the application.

Example:
    >>> from backend.api.security.auth_header_guard import SensitiveHeaderStripMiddleware
    >>> app.add_middleware(SensitiveHeaderStripMiddleware)
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Headers that oauth2-proxy uses internally and must never reach the browser.
# Compared case-insensitively (HTTP headers are case-insensitive).
_SENSITIVE_RESPONSE_HEADERS: frozenset[str] = frozenset(
    {
        "x-auth-request-access-token",
        "x-auth-request-email",
        "x-auth-request-user",
        "x-auth-request-username",
        "x-auth-request-preferred-username",
        "x-auth-request-groups",
        "x-forwarded-access-token",
    }
)

# Paths exempt from stripping. /api/auth/nginx-check is the nginx auth_request
# endpoint: it is marked `internal` in nginx (unreachable from browsers) and its
# X-Auth-Request-* response headers ARE the mechanism by which nginx receives
# the user's identity (via auth_request_set). Stripping them breaks header-based
# authentication for every request behind nginx. nginx never forwards auth
# subrequest response headers to the client, so this exemption leaks nothing.
_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/auth/nginx-check",
        "/auth/nginx-check",  # when ROOT_PATH=/api is handled by the proxy
    }
)


class SensitiveHeaderStripMiddleware(BaseHTTPMiddleware):
    """Strip oauth2-proxy internal auth headers from every outgoing response.

    This is a defense-in-depth measure. The Ingress ``proxy_hide_header``
    directives are the primary control; this middleware catches any headers
    that slip through or are accidentally added by application code.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # The nginx auth_request endpoint must return identity headers to nginx.
        if request.url.path in _EXEMPT_PATHS:
            return response

        for header_name in list(response.headers.keys()):
            if header_name.lower() in _SENSITIVE_RESPONSE_HEADERS:
                del response.headers[header_name]
                logger.warning(
                    "[AUTH-HEADER-GUARD] Stripped sensitive header '%s' from response to %s",
                    header_name,
                    request.url.path,
                )

        return response
