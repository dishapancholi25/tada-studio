"""Security middleware module.

Provides security-related middleware including Content Security Policy (CSP)
headers for XSS protection and auth header stripping for token leakage prevention.
"""

from .auth_header_guard import SensitiveHeaderStripMiddleware
from .csp_middleware import CSPMiddleware, get_csp_policy

__all__ = ["CSPMiddleware", "SensitiveHeaderStripMiddleware", "get_csp_policy"]
