"""HTTP configuration for request nodes.

This module defines configurations for HTTP request operations including
dynamic parameters, authentication, and response handling.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import Any, Dict, List, Optional


@dataclass
class ParameterDefinition:
    """Definition for a dynamic parameter that AI can populate.

    Attributes:
        name: Parameter name
        param_type: Type (string, number, boolean, object, array)
        description: Description for AI to understand what to populate
        required: Whether this parameter is required
        default_value: Default value if not provided
        location: Parameter location (query, header, path, body)
        format: Format specifier (date, email, url, uuid, etc.)
        example: Example value to help AI understand
        enum_values: Allowed values for enum types
        min_value: Minimum value for number types
        max_value: Maximum value for number types
        pattern: Regex pattern for validation
    """

    name: str
    param_type: str
    description: str
    required: bool = False
    default_value: Optional[Any] = None
    location: str = "query"
    format: Optional[str] = None
    example: Optional[str] = None
    enum_values: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None


@dataclass
class HttpRequestConfig:
    """Configuration for HTTP request tool nodes.

    Comprehensive HTTP client configuration supporting dynamic parameters,
    multiple authentication methods, and advanced features like retries,
    rate limiting, and circuit breakers.

    Attributes:
        url_template: Base URL with parameter placeholders
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
        parameter_schema: Dynamic parameters the AI can provide
        headers: Static headers (use parameter_schema for dynamic)
        query_params: Static query params (use parameter_schema for dynamic)
        auth_type: Authentication type (none, bearer, api_key_header, etc.)
        auth_config: Authentication details
        oauth2_config: OAuth2 configuration
        certificate_path: Path to client certificate for mutual TLS
        request_body_template: Request body template with placeholders
        content_type: Explicit content-type header
        user_agent: Custom User-Agent header
        encoding: Request/response encoding
        compression: Enable gzip/deflate compression
        cookie_jar: Enable cookie persistence
        timeout_seconds: Request timeout
        max_retries: Number of retry attempts
        retry_delay: Delay between retries in seconds
        retry_on_status: Status codes to retry on
        response_format: Response format (auto, json, text, xml, binary)
        error_handling: Error handling strategy (fail, continue, retry)
        follow_redirects: Whether to follow HTTP redirects
        max_redirects: Maximum number of redirects to follow
        verify_ssl: Whether to verify SSL certificates
        extract_path: JSONPath/XPath to extract specific data
        response_transform: JavaScript expression for transformation
        success_status_codes: Status codes to consider successful
        proxy_config: Proxy configuration
        rate_limit: Rate limiting config
        circuit_breaker_config: Circuit breaker config
        request_signing: Request signing config
        pre_request_script: JavaScript to run before request
        webhook_url: Webhook URL for async callbacks
        accept_headers: Accept headers for content negotiation
        cache_config: Response caching configuration
        endpoint_id: Optional reference to a saved API endpoint
        parent_agent_id: ID of the agent this tool belongs to
    """

    endpoint_id: Optional[str] = None
    url_template: str = ""
    method: str = "GET"
    parameter_schema: Dict[str, ParameterDefinition] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    auth_type: str = "none"
    auth_config: Dict[str, str] = field(default_factory=dict)
    oauth2_config: Optional[Dict[str, str]] = None
    certificate_path: Optional[str] = None
    request_body_template: str = ""
    content_type: Optional[str] = None
    user_agent: Optional[str] = None
    encoding: str = "utf-8"
    compression: bool = True
    cookie_jar: bool = False
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_on_status: List[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )
    response_format: str = "auto"
    error_handling: str = "fail"
    follow_redirects: bool = True
    max_redirects: int = 10
    verify_ssl: bool = True
    extract_path: str = ""
    response_transform: Optional[str] = None
    success_status_codes: List[int] = field(
        default_factory=lambda: [200, 201, 202, 204]
    )
    proxy_config: Optional[Dict[str, str]] = None
    rate_limit: Optional[Dict[str, int]] = None
    circuit_breaker_config: Optional[Dict[str, int]] = None
    request_signing: Optional[Dict[str, str]] = None
    pre_request_script: Optional[str] = None
    webhook_url: Optional[str] = None
    accept_headers: Optional[Dict[str, str]] = None
    cache_config: Optional[Dict[str, Any]] = None
    parent_agent_id: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None


@dataclass
class HttpRequestActionConfig:
    """Configuration for HTTP request action nodes (static, non-AI-callable).

    Simpler HTTP configuration for static workflow actions without
    AI-driven parameter population.

    Attributes:
        endpoint_id: Optional reference to a saved API endpoint configuration
        url_template: URL with template variables
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url_param_mappings: URL parameter mappings for enhanced UI
        query_param_mappings: Query parameter mappings
        header_mappings: Header mappings
        body_mappings: Body field mappings
        body_type: Body type (json, form, text, raw)
        body_template: Request body template with variables
        headers: Headers with template variables
        body: Legacy body field
        auth_type: Authentication type (none, bearer, api_key, basic, custom)
        auth_config: Authentication configuration
        timeout_seconds: Request timeout
        max_retries: Number of retry attempts
        verify_ssl: Whether to verify SSL certificates
        response_path: JSONPath to extract specific data
        success_status_codes: Status codes to consider successful
    """

    endpoint_id: Optional[str] = None
    url_template: str = ""
    method: str = "GET"
    url_param_mappings: List[Dict[str, Any]] = field(default_factory=list)
    query_param_mappings: List[Dict[str, Any]] = field(default_factory=list)
    header_mappings: List[Dict[str, Any]] = field(default_factory=list)
    body_mappings: List[Dict[str, Any]] = field(default_factory=list)
    body_type: str = "json"
    body_template: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    auth_type: str = "none"
    auth_config: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    response_path: str = ""
    success_status_codes: List[int] = field(
        default_factory=lambda: [200, 201, 202, 204]
    )
    guardrails_config: Optional["GuardrailsConfig"] = None
