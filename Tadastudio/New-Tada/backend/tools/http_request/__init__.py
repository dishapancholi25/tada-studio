"""HTTP Request Tool - Modular HTTP request execution for LangGraph.

This module provides a flexible HTTP request tool that can be configured with
dynamic parameters, various authentication methods, retry logic, rate limiting,
and circuit breakers.

Example:
    Basic usage:
    >>> from backend.tools.http_request import create_http_request_tool
    >>> tool = create_http_request_tool(
    ...     url_template="https://api.example.com/users/{user_id}",
    ...     method="GET",
    ...     parameter_schema={
    ...         "user_id": {
    ...             "param_type": "string",
    ...             "description": "User ID to fetch",
    ...             "required": True,
    ...             "location": "path"
    ...         }
    ...     }
    ... )

    With authentication:
    >>> tool = create_http_request_tool(
    ...     url_template="https://api.example.com/data",
    ...     auth_type="bearer",
    ...     auth_config={"token": "your-token-here"}
    ... )
"""

# Authentication handlers
from .authentication import (
    AuthenticationHandler,
    apply_api_key_header,
    apply_api_key_query,
    apply_bearer_auth,
    create_basic_auth,
    create_digest_auth,
    handle_oauth2_flow,
    sign_request,
)

# Configuration builders and validators
from .config import ArgsSchemaBuilder, ConfigValidator, ToolDescriptionBuilder

# Execution metadata retrieval functions (for backward compatibility)
from .execution import (
    get_execution_storage,
    get_http_execution_for_node,
    get_last_http_execution,
)

# Main factory function
from .factory import create_http_request_tool

# Response processing utilities
from .response import (
    detect_content_type,
    encode_binary_response,
    extract_json_path,
    format_response_output,
    parse_json_response,
    parse_xml_response,
    process_response,
)

# Schemas for configuration
from .schemas import (
    AuthConfig,
    CacheConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    HttpExecutionMetadata,
    HttpRequestArgs,
    HttpRequestConfig,
    HttpResponse,
    OAuth2Config,
    ParameterDefinition,
    ProxyConfig,
    RateLimitConfig,
    RateLimiter,
    RequestSigningConfig,
)


__all__ = [
    # Main factory
    "create_http_request_tool",
    # Execution metadata
    "get_last_http_execution",
    "get_http_execution_for_node",
    "get_execution_storage",
    # Schemas
    "HttpRequestConfig",
    "HttpRequestArgs",
    "AuthConfig",
    "OAuth2Config",
    "ProxyConfig",
    "RateLimitConfig",
    "CircuitBreakerConfig",
    "RequestSigningConfig",
    "CacheConfig",
    "ParameterDefinition",
    "HttpExecutionMetadata",
    "HttpResponse",
    "RateLimiter",
    "CircuitBreaker",
    # Configuration
    "ToolDescriptionBuilder",
    "ArgsSchemaBuilder",
    "ConfigValidator",
    # Response processing
    "detect_content_type",
    "parse_json_response",
    "parse_xml_response",
    "encode_binary_response",
    "extract_json_path",
    "process_response",
    "format_response_output",
    # Authentication
    "apply_bearer_auth",
    "apply_api_key_header",
    "apply_api_key_query",
    "create_basic_auth",
    "create_digest_auth",
    "handle_oauth2_flow",
    "sign_request",
    "AuthenticationHandler",
]
