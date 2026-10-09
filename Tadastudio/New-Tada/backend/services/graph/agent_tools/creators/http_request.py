"""HTTP request tool creator for agents.

This module creates HTTP request tool instances that agents can use
to make HTTP calls to external APIs.
"""

from typing import Any, Dict, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.api_endpoint.resolver import (
    resolve_endpoint_config as _resolve_endpoint_config,
)
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def _extract_http_config_from_dict(http_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract HTTP configuration from a dictionary.

    Args:
        http_config: HTTP configuration dictionary

    Returns:
        Dictionary of configuration parameters
    """
    return {
        "url_template": http_config.get("url_template", ""),
        "method": http_config.get("method", "GET"),
        "parameter_schema": http_config.get("parameter_schema", {}),
        "headers": http_config.get("headers", {}),
        "query_params": http_config.get("query_params", {}),
        "auth_type": http_config.get("auth_type", "none"),
        "auth_config": http_config.get("auth_config", {}),
        "oauth2_config": http_config.get("oauth2_config", {}),
        "certificate_path": http_config.get("certificate_path", None),
        "request_body_template": http_config.get("request_body_template", ""),
        "content_type": http_config.get("content_type", None),
        "user_agent": http_config.get("user_agent", None),
        "encoding": http_config.get("encoding", "utf-8"),
        "compression": http_config.get("compression", True),
        "cookie_jar": http_config.get("cookie_jar", False),
        "timeout_seconds": http_config.get("timeout_seconds", 30),
        "max_retries": http_config.get("max_retries", 3),
        "retry_delay": http_config.get("retry_delay", 1.0),
        "retry_on_status": http_config.get(
            "retry_on_status", [429, 500, 502, 503, 504]
        ),
        "response_format": http_config.get("response_format", "auto"),
        "error_handling": http_config.get("error_handling", "fail"),
        "follow_redirects": http_config.get("follow_redirects", True),
        "max_redirects": http_config.get("max_redirects", 10),
        "verify_ssl": http_config.get("verify_ssl", True),
        "extract_path": http_config.get("extract_path", ""),
        "response_transform": http_config.get("response_transform", None),
        "success_status_codes": http_config.get(
            "success_status_codes", [200, 201, 202, 204]
        ),
        "proxy_config": http_config.get("proxy_config", None),
        "rate_limit": http_config.get("rate_limit", None),
        "circuit_breaker_config": http_config.get("circuit_breaker_config", None),
        "request_signing": http_config.get("request_signing", None),
        "pre_request_script": http_config.get("pre_request_script", None),
        "webhook_url": http_config.get("webhook_url", None),
        "accept_headers": http_config.get("accept_headers", None),
        "cache_config": http_config.get("cache_config", None),
    }


def _extract_http_config_from_object(http_config: Any) -> Dict[str, Any]:
    """
    Extract HTTP configuration from a config object.

    Args:
        http_config: HTTP configuration object

    Returns:
        Dictionary of configuration parameters
    """
    return {
        "url_template": http_config.url_template,
        "method": http_config.method,
        "parameter_schema": getattr(http_config, "parameter_schema", {}),
        "headers": http_config.headers,
        "query_params": (
            http_config.query_params if hasattr(http_config, "query_params") else {}
        ),
        "auth_type": http_config.auth_type,
        "auth_config": http_config.auth_config,
        "oauth2_config": getattr(http_config, "oauth2_config", None),
        "certificate_path": getattr(http_config, "certificate_path", None),
        "request_body_template": http_config.request_body_template,
        "content_type": getattr(http_config, "content_type", None),
        "user_agent": getattr(http_config, "user_agent", None),
        "encoding": getattr(http_config, "encoding", "utf-8"),
        "compression": getattr(http_config, "compression", True),
        "cookie_jar": getattr(http_config, "cookie_jar", False),
        "timeout_seconds": http_config.timeout_seconds,
        "max_retries": http_config.max_retries,
        "retry_delay": http_config.retry_delay,
        "retry_on_status": getattr(
            http_config, "retry_on_status", [429, 500, 502, 503, 504]
        ),
        "response_format": http_config.response_format,
        "error_handling": http_config.error_handling,
        "follow_redirects": http_config.follow_redirects,
        "max_redirects": getattr(http_config, "max_redirects", 10),
        "verify_ssl": http_config.verify_ssl,
        "extract_path": http_config.extract_path,
        "response_transform": getattr(http_config, "response_transform", None),
        "success_status_codes": http_config.success_status_codes,
        "proxy_config": getattr(http_config, "proxy_config", None),
        "rate_limit": getattr(http_config, "rate_limit", None),
        "circuit_breaker_config": getattr(http_config, "circuit_breaker_config", None),
        "request_signing": getattr(http_config, "request_signing", None),
        "pre_request_script": getattr(http_config, "pre_request_script", None),
        "webhook_url": getattr(http_config, "webhook_url", None),
        "accept_headers": getattr(http_config, "accept_headers", None),
        "cache_config": getattr(http_config, "cache_config", None),
    }


def create_http_request_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
    user_id: Optional[str] = None,
) -> Optional[Any]:
    """
    Create an HTTP request tool from an HTTP_REQUEST node.

    Args:
        target_node: The HTTP_REQUEST node configuration
        used_tool_names: Optional set to track used tool names for collision detection
        user_id: The executing user's ID for endpoint visibility checks

    Returns:
        HTTP request tool instance, or None if configuration is invalid

    Raises:
        ImportError: If HTTP request tool module is not available
    """
    if not target_node.http_request_config:
        logger.warning(f"Node {target_node.name} missing http_request_config")
        return None

    logger.info(f"Creating HTTP request tool from node: {target_node.name}")

    from backend.tools.http_request import create_http_request_tool

    http_config = target_node.http_request_config

    # Resolve saved API endpoint reference if present
    if isinstance(http_config, dict) and http_config.get("endpoint_id"):
        http_config = _resolve_endpoint_config(http_config, user_id=user_id)

    # Handle both dict and HttpRequestConfig object
    if isinstance(http_config, dict):
        config_params = _extract_http_config_from_dict(http_config)
    else:
        config_params = _extract_http_config_from_object(http_config)

    if not config_params["url_template"]:
        logger.warning(f"HTTP request node {target_node.name} missing url_template")
        return None

    # Add node identification
    config_params["node_id"] = target_node.uniq_id
    config_params["node_name"] = target_node.name

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="http_request",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="HTTP Request",
        used_names=used_tool_names,
    )
    config_params["tool_name"] = tool_name

    # Build description prefix from node name if not default
    if target_node.name and target_node.name != "HTTP Request":
        description_prefix = f"HTTP request '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"
        config_params["description_prefix"] = description_prefix

    http_request_tool = create_http_request_tool(**config_params)

    logger.info(f"Created HTTP request tool: {tool_name}")
    return http_request_tool
