"""Factory functions for creating HTTP request tools.

Simplified factory that delegates complexity to handlers and config modules.
"""

from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import StructuredTool

from .config import ArgsSchemaBuilder, ToolDescriptionBuilder
from .handlers import handle_http_request_execution
from .schemas import (
    AuthConfig,
    CircuitBreaker,
    HttpRequestConfig,
    OAuth2Config,
    RateLimiter,
    RequestSigningConfig,
)


def set_default_parameters(
    headers: Dict[str, str],
    query_params: Dict[str, str],
    parameter_schema: Dict[str, Any],
    auth_config: Dict[str, str],
    success_status_codes: List[int],
    retry_on_status: List[int],
) -> Dict[str, Any]:
    """Set default parameters for configuration.

    Args:
        headers: Static headers
        query_params: Static query parameters
        parameter_schema: Dynamic parameter definitions
        auth_config: Authentication configuration
        success_status_codes: Status codes considered successful
        retry_on_status: Status codes to retry on

    Returns:
        Dictionary with default values applied
    """
    return {
        "headers": headers or {},
        "query_params": query_params or {},
        "parameter_schema": parameter_schema or {},
        "auth_config": auth_config or {},
        "success_status_codes": success_status_codes or [200, 201, 202, 204],
        "retry_on_status": retry_on_status or [429, 500, 502, 503, 504],
    }


def build_config_objects(
    auth_type: str,
    auth_config: Dict[str, str],
    oauth2_config: Dict[str, str],
    request_signing: Dict[str, str],
    verify_ssl: bool = True,
) -> tuple[AuthConfig, Optional[OAuth2Config], Optional[RequestSigningConfig]]:
    """Build authentication and signing configuration objects.

    Args:
        auth_type: Authentication type
        auth_config: Authentication configuration
        oauth2_config: OAuth2 configuration
        request_signing: Request signing configuration

    Returns:
        Tuple of (auth_cfg, oauth2_cfg, signing_cfg)
    """
    # Build auth config
    auth_cfg = AuthConfig(
        auth_type=auth_type,
        token=auth_config.get("token") if auth_config else None,
        scheme=auth_config.get("scheme") if auth_config else None,
        key=auth_config.get("key") if auth_config else None,
        header_name=auth_config.get("header_name") if auth_config else None,
        param_name=auth_config.get("param_name") if auth_config else None,
        username=auth_config.get("username") if auth_config else None,
        password=auth_config.get("password") if auth_config else None,
    )

    # Build OAuth2 config
    oauth2_cfg = None
    if oauth2_config:
        oauth2_cfg = OAuth2Config(
            client_id=oauth2_config.get("client_id"),
            client_secret=oauth2_config.get("client_secret"),
            token_url=oauth2_config.get("token_url"),
            scope=oauth2_config.get("scope", ""),
            verify_ssl=oauth2_config.get("verify_ssl", verify_ssl),
        )

    # Build signing config
    signing_cfg = None
    if request_signing:
        signing_cfg = RequestSigningConfig(
            algorithm=request_signing.get("algorithm"),
            secret=request_signing.get("secret"),
            header_name=request_signing.get("header_name", "X-Signature"),
            script=request_signing.get("script"),
        )

    return auth_cfg, oauth2_cfg, signing_cfg


def build_infrastructure(
    rate_limit: Dict[str, int],
    circuit_breaker_config: Dict[str, int],
    cookie_jar: bool,
    cache_config: Dict[str, Any],
) -> tuple[
    Optional[RateLimiter],
    Optional[CircuitBreaker],
    Optional[requests.Session],
    Dict,
    int,
]:
    """Build rate limiter, circuit breaker, session, and cache.

    Args:
        rate_limit: Rate limiting configuration
        circuit_breaker_config: Circuit breaker configuration
        cookie_jar: Enable cookie persistence
        cache_config: Cache configuration

    Returns:
        Tuple of (rate_limiter, circuit_breaker, session, cache, cache_ttl)
    """
    # Rate limiter
    rate_limiter = None
    if rate_limit:
        rate_limiter = RateLimiter(
            requests_per_second=rate_limit.get("requests_per_second"),
            requests_per_minute=rate_limit.get("requests_per_minute"),
        )

    # Circuit breaker
    circuit_breaker = None
    if circuit_breaker_config:
        circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_config.get("failure_threshold", 5),
            timeout=circuit_breaker_config.get("timeout", 60),
            reset_timeout=circuit_breaker_config.get("reset_timeout", 120),
        )

    # Session
    session = requests.Session() if cookie_jar else None

    # Cache
    cache = {}
    cache_ttl = cache_config.get("ttl", 300) if cache_config else 0

    return rate_limiter, circuit_breaker, session, cache, cache_ttl


def create_http_request_tool(
    url_template: str,
    method: str = "GET",
    parameter_schema: Dict[str, Any] = None,
    headers: Dict[str, str] = None,
    query_params: Dict[str, str] = None,
    auth_type: str = "none",
    auth_config: Dict[str, str] = None,
    oauth2_config: Dict[str, str] = None,
    certificate_path: str = None,
    request_body_template: str = "",
    content_type: str = None,
    user_agent: str = None,
    encoding: str = "utf-8",
    compression: bool = True,
    cookie_jar: bool = False,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retry_on_status: List[int] = None,
    response_format: str = "auto",
    error_handling: str = "fail",
    follow_redirects: bool = True,
    max_redirects: int = 10,
    verify_ssl: bool = True,
    extract_path: str = "",
    response_transform: str = None,
    success_status_codes: List[int] = None,
    proxy_config: Dict[str, str] = None,
    rate_limit: Dict[str, int] = None,
    circuit_breaker_config: Dict[str, int] = None,
    request_signing: Dict[str, str] = None,
    pre_request_script: str = None,
    webhook_url: str = None,
    accept_headers: Dict[str, str] = None,
    cache_config: Dict[str, Any] = None,
    node_id: str = "",
    node_name: str = "HTTP Request",
    tool_name: str = None,
    description_prefix: str = None,
):
    """Create an HTTP request tool with dynamic parameter support.

    Args:
        url_template: URL template with {placeholders}
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        parameter_schema: Dynamic parameter definitions
        headers: Static headers
        query_params: Static query parameters
        auth_type: Authentication type (none, bearer, basic, oauth2, etc.)
        auth_config: Authentication configuration
        oauth2_config: OAuth2 configuration
        certificate_path: Path to client certificate
        request_body_template: Request body template
        content_type: Content-Type header
        user_agent: User-Agent header
        encoding: Text encoding
        compression: Enable compression
        cookie_jar: Enable cookie persistence
        timeout_seconds: Request timeout
        max_retries: Maximum retry attempts
        retry_delay: Retry delay in seconds
        retry_on_status: Status codes to retry on
        response_format: Response format (auto, json, xml, binary)
        error_handling: Error handling strategy
        follow_redirects: Follow HTTP redirects
        max_redirects: Maximum redirects
        verify_ssl: Verify SSL certificates
        extract_path: JSONPath to extract from response
        response_transform: Response transformation script
        success_status_codes: Status codes considered successful
        proxy_config: Proxy configuration
        rate_limit: Rate limiting configuration
        circuit_breaker_config: Circuit breaker configuration
        request_signing: Request signing configuration
        pre_request_script: Pre-request script
        webhook_url: Webhook URL for results
        accept_headers: Accept headers
        cache_config: Cache configuration
        node_id: Node ID for tracking
        node_name: Node display name
        tool_name: Optional custom tool name
        description_prefix: Optional prefix for the tool description

    Returns:
        StructuredTool instance for HTTP requests
    """
    # Set defaults
    defaults = set_default_parameters(
        headers,
        query_params,
        parameter_schema,
        auth_config,
        success_status_codes,
        retry_on_status,
    )

    # Build main configuration
    config = HttpRequestConfig(
        url_template=url_template,
        method=method,
        parameter_schema=defaults["parameter_schema"],
        headers=defaults["headers"],
        query_params=defaults["query_params"],
        request_body_template=request_body_template,
        content_type=content_type,
        user_agent=user_agent,
        encoding=encoding,
        compression=compression,
        cookie_jar=cookie_jar,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_on_status=defaults["retry_on_status"],
        response_format=response_format,
        error_handling=error_handling,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
        verify_ssl=verify_ssl,
        extract_path=extract_path,
        response_transform=response_transform,
        success_status_codes=defaults["success_status_codes"],
        certificate_path=certificate_path,
        pre_request_script=pre_request_script,
        webhook_url=webhook_url,
        accept_headers=accept_headers or {},
        node_id=node_id,
        node_name=node_name,
    )

    # Build auth/signing configs
    auth_cfg, oauth2_cfg, signing_cfg = build_config_objects(
        auth_type, defaults["auth_config"], oauth2_config, request_signing, verify_ssl
    )

    # Build infrastructure
    rate_limiter, circuit_breaker, session, cache, cache_ttl = build_infrastructure(
        rate_limit, circuit_breaker_config, cookie_jar, cache_config
    )

    # Build tool description and args schema
    tool_description = ToolDescriptionBuilder.build_description(config)
    if description_prefix:
        tool_description = f"{description_prefix}. {tool_description}"
    HttpRequestArgs = ArgsSchemaBuilder.build_args_schema(
        defaults["parameter_schema"], url_template
    )

    # Create the actual tool function
    def http_request(**kwargs) -> str:
        """Execute HTTP request with given parameters."""
        return handle_http_request_execution(
            kwargs,
            config,
            auth_cfg,
            oauth2_cfg,
            signing_cfg,
            rate_limiter,
            circuit_breaker,
            session,
            cache,
            cache_ttl,
            http_request,  # Pass self for metadata attachment
        )

    # Generate final tool name
    final_tool_name = tool_name or (
        f"http_request_{node_id}" if node_id else "http_request"
    )

    # Create the tool with proper schema
    http_tool = StructuredTool(
        name=final_tool_name,
        description=tool_description,
        func=http_request,
        args_schema=HttpRequestArgs,
    )

    # Attach node_id for metadata lookup (used by async agent)
    # Use object.__setattr__ to bypass Pydantic's field validation
    object.__setattr__(http_tool, "node_id", node_id)

    return http_tool
