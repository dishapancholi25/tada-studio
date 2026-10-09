"""Pydantic schemas and data models for HTTP request tool."""

import time
from collections import deque
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParameterDefinition(BaseModel):
    """Definition of a parameter for the HTTP request tool."""

    param_type: str = Field(default="string", description="Type of parameter")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default_value: Any = Field(default=None, description="Default value")
    location: str = Field(
        default="query",
        description="Where to place parameter (query, path, header, body)",
    )
    example: str = Field(default="", description="Example value")


class AuthConfig(BaseModel):
    """Authentication configuration."""

    auth_type: str = Field(default="none", description="Type of authentication")
    token: Optional[str] = Field(default=None, description="Bearer token or API token")
    scheme: Optional[str] = Field(default=None, description="Custom token scheme")
    key: Optional[str] = Field(default=None, description="API key")
    header_name: Optional[str] = Field(
        default=None, description="Header name for API key"
    )
    param_name: Optional[str] = Field(
        default=None, description="Query param name for API key"
    )
    username: Optional[str] = Field(default=None, description="Basic auth username")
    password: Optional[str] = Field(default=None, description="Basic auth password")


class OAuth2Config(BaseModel):
    """OAuth2 configuration."""

    client_id: str = Field(description="OAuth2 client ID")
    client_secret: str = Field(description="OAuth2 client secret")
    token_url: str = Field(description="Token endpoint URL")
    scope: str = Field(default="", description="OAuth2 scopes")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates for token endpoint")


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    http_proxy: Optional[str] = Field(default=None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS proxy URL")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=False, description="Enable caching")
    ttl: int = Field(default=300, description="Cache TTL in seconds")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    requests_per_second: Optional[int] = Field(
        default=None, description="Max requests per second"
    )
    requests_per_minute: Optional[int] = Field(
        default=None, description="Max requests per minute"
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(
        default=5, description="Failures before opening circuit"
    )
    timeout: int = Field(default=60, description="Timeout in seconds")
    reset_timeout: int = Field(default=120, description="Reset timeout in seconds")


class RequestSigningConfig(BaseModel):
    """Request signing configuration."""

    algorithm: str = Field(
        description="Signing algorithm (hmac-sha256, aws-v4, custom)"
    )
    secret: Optional[str] = Field(default=None, description="Secret for HMAC")
    header_name: Optional[str] = Field(
        default="X-Signature", description="Header name for signature"
    )
    script: Optional[str] = Field(default=None, description="Custom signing script")


class HttpRequestConfig(BaseModel):
    """Main configuration for HTTP request tool."""

    url_template: str = Field(description="URL template with {placeholders}")
    method: str = Field(default="GET", description="HTTP method")
    parameter_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Dynamic parameter definitions"
    )
    headers: Dict[str, str] = Field(default_factory=dict, description="Static headers")
    query_params: Dict[str, str] = Field(
        default_factory=dict, description="Static query parameters"
    )
    request_body_template: str = Field(default="", description="Request body template")
    content_type: Optional[str] = Field(default=None, description="Content-Type header")
    user_agent: Optional[str] = Field(default=None, description="User-Agent header")
    encoding: str = Field(default="utf-8", description="Text encoding")
    compression: bool = Field(default=True, description="Enable compression")
    cookie_jar: bool = Field(default=False, description="Enable cookie persistence")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    retry_on_status: List[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="Status codes to retry on",
    )
    response_format: str = Field(
        default="auto", description="Response format (auto, json, xml, binary)"
    )
    error_handling: str = Field(default="fail", description="Error handling strategy")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    max_redirects: int = Field(default=10, description="Maximum redirects")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    extract_path: str = Field(
        default="", description="JSONPath to extract from response"
    )
    response_transform: Optional[str] = Field(
        default=None, description="Response transformation script"
    )
    success_status_codes: List[int] = Field(
        default_factory=lambda: [200, 201, 202, 204],
        description="Status codes considered successful",
    )
    certificate_path: Optional[str] = Field(
        default=None, description="Client certificate path"
    )
    pre_request_script: Optional[str] = Field(
        default=None, description="Pre-request script"
    )
    webhook_url: Optional[str] = Field(
        default=None, description="Webhook URL for results"
    )
    accept_headers: Dict[str, str] = Field(
        default_factory=dict, description="Accept headers"
    )
    node_id: str = Field(default="", description="Node ID for tracking")
    node_name: str = Field(default="HTTP Request", description="Node display name")


class HttpRequestArgs(BaseModel):
    """Base arguments for HTTP request execution."""

    parameters: Optional[str] = Field(
        default="", description="Parameters as JSON string (backward compatibility)"
    )


class HttpExecutionMetadata(BaseModel):
    """Metadata captured during HTTP request execution."""

    request: Dict[str, Any] = Field(description="Request details")
    response: Dict[str, Any] = Field(description="Response details")
    config: Dict[str, Any] = Field(description="Configuration used")
    timestamp: str = Field(description="Execution timestamp")
    call_id: str = Field(description="Unique call identifier")


class HttpResponse(BaseModel):
    """Response from HTTP request execution."""

    success: bool = Field(description="Whether request succeeded")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Optional[HttpExecutionMetadata] = Field(
        default=None, description="Execution metadata"
    )


# Rate limiting implementation
class RateLimiter:
    """Rate limiter for HTTP requests."""

    def __init__(
        self, requests_per_second: int = None, requests_per_minute: int = None
    ):
        """Initialize rate limiter."""
        self.rps = requests_per_second
        self.rpm = requests_per_minute
        self.request_times = deque()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Clean old entries
        minute_ago = now - 60
        self.request_times = deque(t for t in self.request_times if t > minute_ago)

        # Check per-second limit
        if self.rps:
            second_ago = now - 1
            recent_second = sum(1 for t in self.request_times if t > second_ago)
            if recent_second >= self.rps:
                sleep_time = 1 - (now - second_ago)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        # Check per-minute limit
        if self.rpm:
            recent_minute = len(self.request_times)
            if recent_minute >= self.rpm:
                oldest = self.request_times[0]
                sleep_time = 60 - (now - oldest)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        self.request_times.append(now)


# Circuit breaker implementation
class CircuitBreaker:
    """Circuit breaker for HTTP requests."""

    def __init__(
        self, failure_threshold: int = 5, timeout: int = 60, reset_timeout: int = 120
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call_succeeded(self):
        """Reset the circuit breaker on success."""
        self.failures = 0
        self.state = "closed"
        self.last_failure_time = None

    def call_failed(self):
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            return True
        return False

    def is_open(self):
        """Check if circuit is open (failing fast)."""
        if self.state == "closed":
            return False

        if self.state == "open" and self.last_failure_time:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                return False

        return self.state == "open"
