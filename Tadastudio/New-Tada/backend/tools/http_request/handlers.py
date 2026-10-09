"""Business logic handlers for HTTP request execution.

This module breaks down complex request logic into focused, testable functions
to reduce cyclomatic complexity and improve maintainability.
"""

import ipaddress
import json
import logging
import re
import socket
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from ...services.guardrails.ssrf import validate_url
from ...services.streaming import streaming_emitter
from .authentication import AuthenticationHandler
from .execution import (
    HttpExecutionMetadata,
    attach_execution_metadata,
    get_execution_storage,
)
from .response import format_response_output, process_response
from .schemas import (
    AuthConfig,
    CircuitBreaker,
    HttpRequestConfig,
    OAuth2Config,
    RateLimiter,
    RequestSigningConfig,
)


logger = logging.getLogger(__name__)

# Tool name constant for streaming events
HTTP_REQUEST_TOOL_NAME = "http_request"

# ── Header allowlist / denylist (SSRF + identity-bypass hardening) ───────────
# User-supplied headers are UNTRUSTED. These sensitive headers must never be
# accepted from tool/agent input because they enabled identity bypass and
# cloud-metadata (IMDS) exploitation in ISG testing. The node's structured
# auth config (AuthConfig / OAuth2 / signing) injects its own Authorization
# header AFTER this stripping step, so legitimate auth is preserved.
#
# Matching is case-insensitive. Entries ending with "*" are treated as prefixes.
DENIED_USER_HEADERS = {
    "authorization",     # only allowed via structured auth config
    "cookie",            # session/identity smuggling
    "metadata",          # Azure/GCP IMDS trigger (Metadata: true)
}
DENIED_USER_HEADER_PREFIXES = (
    "x-auth-request-",   # oauth2-proxy identity headers
)


def _is_denied_user_header(header_name: str) -> bool:
    """Return True if a user-supplied header must be stripped before sending."""
    name = (header_name or "").strip().lower()
    if name in DENIED_USER_HEADERS:
        return True
    return any(name.startswith(prefix) for prefix in DENIED_USER_HEADER_PREFIXES)


def strip_denied_headers(
    headers: Dict[str, str], allow: Optional[Set[str]] = None
) -> Dict[str, str]:
    """Remove sensitive user-supplied headers from an outbound header map.

    Strips (case-insensitively):
      * Authorization       (must come from structured auth config only)
      * Cookie
      * Metadata
      * X-Auth-Request-*    (any header with this prefix)

    Args:
        headers: The outbound header map to sanitize.
        allow: Optional set of header names (case-insensitive) that are
            explicitly permitted even if they would otherwise be denied.
            Used to preserve an Authorization header set by a legitimate
            structured auth type (bearer / custom_token / oauth2).

    Returns a NEW dict containing only the permitted headers. The removed
    headers are logged as a warning for auditability.
    """
    if not headers:
        return {}

    allow_set = {a.strip().lower() for a in (allow or set()) if a}

    clean: Dict[str, str] = {}
    stripped: List[str] = []
    for key, value in headers.items():
        name = (key or "").strip().lower()
        if name in allow_set:
            clean[key] = value
            continue
        if _is_denied_user_header(key):
            stripped.append(key)
            continue
        clean[key] = value

    if stripped:
        logger.warning(
            "[HEADER-GUARD] Stripped %d disallowed header(s): %s",
            len(stripped),
            ", ".join(sorted(stripped)),
        )
    return clean


def parse_ai_parameters(
    kwargs: Dict[str, Any], parameter_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse AI parameters from kwargs.

    Handles both old style (parameters string) and new style (direct kwargs).

    Args:
        kwargs: Keyword arguments from tool invocation
        parameter_schema: Parameter schema definition

    Returns:
        Parsed parameters dictionary

    Raises:
        ValueError: If parameters are invalid JSON
    """
    ai_params = {}

    # Handle old style (parameters string)
    if "parameters" in kwargs and isinstance(kwargs["parameters"], str):
        parameters = kwargs["parameters"]
        if isinstance(parameters, dict):
            ai_params = parameters
            logger.info(f"Received parameters as dict: {ai_params}")
        elif isinstance(parameters, str):
            try:
                ai_params = json.loads(parameters)
                logger.info(f"Parsed parameters from JSON string: {ai_params}")
            except json.JSONDecodeError:
                # If not JSON and we have a single parameter, use it directly
                if parameter_schema and len(parameter_schema) == 1:
                    single_param = list(parameter_schema.keys())[0]
                    ai_params = {single_param: parameters}
                elif not parameter_schema or len(parameter_schema) == 0:
                    # Empty schema - use generic "parameters" key (matches DefaultHttpRequestArgs)
                    ai_params = {"parameters": parameters}
                else:
                    raise ValueError(
                        f"Invalid JSON parameters. Please provide valid JSON: {parameters}"
                    )
        else:
            # Handle other types by converting to string
            logger.warning(
                f"Received parameters of unexpected type {type(parameters)}, converting to string"
            )
            if parameter_schema and len(parameter_schema) == 1:
                single_param = list(parameter_schema.keys())[0]
                ai_params = {single_param: str(parameters)}
            else:
                ai_params = {"value": str(parameters)}
    else:
        # New style - direct kwargs from parameter schema
        special_keys = {
            "parameters",
            "args",
            "config",
            "callbacks",
            "tags",
            "metadata",
            "run_name",
            "run_id",
            "_from_structured_output",
        }
        ai_params = {k: v for k, v in kwargs.items() if k not in special_keys}
        logger.info(f"Received parameters as kwargs: {ai_params}")

    return ai_params


def extract_nested_value(obj: Any, path: str) -> Optional[Any]:
    """Extract a value from a nested object using a dot/bracket path.

    Args:
        obj: Object to extract from
        path: Path string (e.g., "data.results[0].name")

    Returns:
        Extracted value or None if path doesn't exist
    """
    if not path:
        return obj

    parts = path.split(".")
    current = obj

    for part in parts:
        if current is None:
            return None

        # Handle array notation like datasets[0]
        if "[" in part and "]" in part:
            key = part[: part.index("[")]
            index = int(part[part.index("[") + 1 : part.index("]")])

            if isinstance(current, dict) and key in current:
                current = current[key]
                if isinstance(current, list) and len(current) > index:
                    current = current[index]
                else:
                    return None
            else:
                return None
        else:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

    return current


def set_nested_value(obj: Dict, path: str, value: Any) -> None:
    """Set a value in a nested dictionary using dot notation.

    Args:
        obj: Dictionary to set value in
        path: Path string (e.g., "data.results[0].name")
        value: Value to set
    """
    parts = path.split(".")
    for part in parts[:-1]:
        # Handle array notation
        if "[" in part and "]" in part:
            key = part[: part.index("[")]
            index = int(part[part.index("[") + 1 : part.index("]")])
            if key not in obj:
                obj[key] = []
            while len(obj[key]) <= index:
                obj[key].append({})
            obj = obj[key][index]
        else:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]

    # Set the final value
    final_key = parts[-1]
    if "[" in final_key and "]" in final_key:
        key = final_key[: final_key.index("[")]
        index = int(final_key[final_key.index("[") + 1 : final_key.index("]")])
        if key not in obj:
            obj[key] = []
        while len(obj[key]) <= index:
            obj[key].append(None)
        obj[key][index] = value
    else:
        obj[final_key] = value


def identify_root_body_params(
    ai_params: Dict[str, Any], parameter_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Identify root body parameters containing nested structures.

    Args:
        ai_params: Parsed AI parameters
        parameter_schema: Parameter schema definition

    Returns:
        Dictionary of root body parameters
    """
    root_body_params = {}

    for param_name, param_value in ai_params.items():
        if param_name not in parameter_schema:
            continue

        schema_entry = parameter_schema[param_name]
        location = (
            schema_entry.get("location", "query")
            if isinstance(schema_entry, dict)
            else getattr(schema_entry, "location", "query")
        )

        if location == "body":
            root_body_params[param_name] = param_value
            logger.info(
                f"Found root body parameter '{param_name}' with nested structure"
            )

    return root_body_params


def try_extract_nested_param(
    schema_param_name: str, nested_location: str, root_body_params: Dict[str, Any]
) -> Optional[Any]:
    """Try to extract nested parameter from root body parameters.

    Args:
        schema_param_name: Parameter name to extract
        nested_location: Location path (e.g., "body.chart.data")
        root_body_params: Root body parameters dict

    Returns:
        Extracted value or None if not found
    """
    path_after_body = nested_location[5:]  # Remove 'body.'

    for root_param_name, root_param_value in root_body_params.items():
        if not isinstance(root_param_value, dict):
            continue

        # Check if path starts with this root parameter
        if not path_after_body.startswith(root_param_name):
            continue

        # Calculate nested path
        nested_path = path_after_body[len(root_param_name) :]
        if nested_path.startswith("."):
            nested_path = nested_path[1:]  # Remove leading dot

        # Extract value
        extracted_value = (
            extract_nested_value(root_param_value, nested_path)
            if nested_path
            else root_param_value
        )

        if extracted_value is not None:
            logger.info(
                f"Extracted nested parameter '{schema_param_name}' from '{root_param_name}'"
            )
            return extracted_value

    return None


def extract_nested_parameters(
    ai_params: Dict[str, Any], parameter_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract nested parameters from root body parameters.

    Args:
        ai_params: Parsed AI parameters
        parameter_schema: Parameter schema definition

    Returns:
        Updated parameters with nested values extracted
    """
    # Identify root body parameters
    root_body_params = identify_root_body_params(ai_params, parameter_schema)

    # Extract nested parameters
    updated_params = ai_params.copy()

    for param_name, schema_def in parameter_schema.items():
        # Skip if already present
        if param_name in ai_params:
            continue

        # Get location
        location = (
            schema_def.get("location", "query")
            if isinstance(schema_def, dict)
            else getattr(schema_def, "location", "query")
        )

        # Try extraction for nested body params
        if location.startswith("body."):
            extracted = try_extract_nested_param(param_name, location, root_body_params)
            if extracted is not None:
                updated_params[param_name] = extracted

    return updated_params

def resolve_runtime_parameter_references(ai_params: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve runtime references, such as FILE_READ content tokens, in tool params."""

    try:
        from backend.services.file_content_references import (
            get_file_content_reference_metadata,
            resolve_file_content_references,
        )

        resolved_filename = _get_runtime_file_reference_filename(
            ai_params,
            get_file_content_reference_metadata,
        )
        resolved = resolve_file_content_references(ai_params, strict=True)
        if resolved_filename:
            resolved = _apply_runtime_file_reference_filename(
                resolved,
                resolved_filename,
            )
        if resolved != ai_params:
            logger.info("Resolved runtime file content reference in HTTP parameters")
        return resolved
    except KeyError as ref_error:
        raise ValueError(str(ref_error)) from ref_error


def _get_runtime_file_reference_filename(
    ai_params: Dict[str, Any],
    get_metadata: Callable[[Any], Optional[Dict[str, Any]]],
) -> Optional[str]:
    """Find the filename associated with a runtime file reference parameter."""

    for key in ("base64", "file", "fileContent", "file_content", "content"):
        metadata = get_metadata(ai_params.get(key))
        if metadata and metadata.get("filename"):
            return _sanitize_runtime_file_name(str(metadata["filename"]))
    return None


def _apply_runtime_file_reference_filename(
    ai_params: Dict[str, Any],
    filename: str,
) -> Dict[str, Any]:
    """Fill weak/missing filename params when resolving runtime file references."""

    updated = dict(ai_params)
    filename_keys = ("fileName", "filename", "file_name")
    target_keys = [key for key in filename_keys if key in updated] or ["fileName"]
    for key in target_keys:
        current_value = updated.get(key)
        if not current_value or not _is_safe_runtime_file_name(str(current_value)):
            updated[key] = filename
    return updated


def _is_safe_runtime_file_name(filename: str) -> bool:
    """Return whether filename is safe for strict document APIs."""

    return bool(re.fullmatch(r"[A-Za-z0-9]+\.[A-Za-z0-9]+", filename))


def _sanitize_runtime_file_name(filename: str) -> str:
    """Build an extension-bearing filename without special characters."""

    filename = filename.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    if "." in filename:
        stem, extension = filename.rsplit(".", 1)
    else:
        stem, extension = filename, "pdf"

    safe_stem = re.sub(r"[^A-Za-z0-9]+", "", stem)[:80] or "uploadedfile"
    safe_extension = re.sub(r"[^A-Za-z0-9]+", "", extension).lower() or "pdf"
    return f"{safe_stem}.{safe_extension}"


def extract_param_metadata(schema_definition: Any) -> Dict[str, str]:
    """Extract parameter metadata from schema definition.

    Handles both dict and object parameter definitions.

    Args:
        schema_definition: Schema definition (dict or object)

    Returns:
        Dict with 'location' and 'param_type' keys
    """
    if isinstance(schema_definition, dict):
        return {
            "location": schema_definition.get("location", "query"),
            "param_type": schema_definition.get("param_type", "string"),
        }
    else:
        return {
            "location": getattr(schema_definition, "location", "query"),
            "param_type": getattr(schema_definition, "param_type", "string"),
        }


def convert_param_value(value: Any, param_type: str) -> Any:
    """Convert parameter value to appropriate type.

    Args:
        value: Original parameter value
        param_type: Target type (number, boolean, string, etc.)

    Returns:
        Converted value
    """
    if param_type == "number":
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    elif param_type == "boolean":
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes"]
        return value
    else:
        return value


def route_param_to_location(
    param_name: str,
    param_value: Any,
    location: str,
    containers: Dict[str, Any],
) -> None:
    """Route parameter to the appropriate location container.

    Args:
        param_name: Parameter name
        param_value: Parameter value (already type-converted)
        location: Target location (path, query, header, body, body.*)
        containers: Dict containing all parameter containers

    Modifies containers in place.
    """
    if location == "path":
        containers["path_params"][param_name] = str(param_value)

    elif location == "query":
        # Smart conversion for query parameters
        if isinstance(param_value, float) and param_value.is_integer():
            containers["query_params"][param_name] = str(int(param_value))
        else:
            containers["query_params"][param_name] = str(param_value)

    elif location == "header":
        containers["headers"][param_name] = str(param_value)

    elif location.startswith("body"):
        if location == "body":
            containers["body_params"][param_name] = param_value
        else:
            # Nested body parameter
            path = location[5:]  # Remove 'body.' prefix
            if path:
                set_nested_value(containers["body_params"], path, param_value)
            else:
                containers["body_params"][param_name] = param_value

    elif location == "template":
        # Value stays only in ai_params for {placeholder} substitution into
        # request_body_template. Intentionally not routed to any container so
        # it does not populate body_params (which would otherwise take
        # precedence over the raw template — see build_request_body).
        pass

    else:
        # Default to body for unknown locations
        containers["body_params"][param_name] = param_value


def apply_parameters_to_locations(
    ai_params: Dict[str, Any],
    parameter_schema: Dict[str, Any],
    headers: Dict[str, str],
    query_params: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, Any], Set[str]]:
    """Apply parameters based on their defined locations.

    Args:
        ai_params: Parsed AI parameters
        parameter_schema: Parameter schema definition
        headers: Base headers
        query_params: Base query parameters

    Returns:
        Tuple of (headers, query_params, path_params, body_params, processed_params)
    """
    # Initialize containers
    containers = {
        "headers": headers.copy(),
        "query_params": query_params.copy(),
        "path_params": {},
        "body_params": {},
    }
    processed_params = set()

    # Process each parameter
    for param_name, param_value in ai_params.items():
        if param_name not in parameter_schema:
            continue

        processed_params.add(param_name)

        # Extract metadata
        metadata = extract_param_metadata(parameter_schema[param_name])

        # Convert value
        converted_value = convert_param_value(param_value, metadata["param_type"])

        # Route to location
        route_param_to_location(
            param_name, converted_value, metadata["location"], containers
        )

    return (
        containers["headers"],
        containers["query_params"],
        containers["path_params"],
        containers["body_params"],
        processed_params,
    )


def extract_param_requirements(schema_definition: Any) -> Dict[str, Any]:
    """Extract parameter requirements from schema definition.

    Args:
        schema_definition: Schema definition (dict or object)

    Returns:
        Dict with 'required', 'default_value', and 'location' keys
    """
    if isinstance(schema_definition, dict):
        return {
            "required": schema_definition.get("required", False),
            "default_value": schema_definition.get("default_value"),
            "location": schema_definition.get("location", ""),
        }
    else:
        return {
            "required": getattr(schema_definition, "required", False),
            "default_value": getattr(schema_definition, "default_value", None),
            "location": getattr(schema_definition, "location", ""),
        }


def is_param_provided_in_body(param_location: str, body_params: Dict[str, Any]) -> bool:
    """Check if parameter is provided within a root body parameter.

    Args:
        param_location: Parameter location (e.g., "body.chart.data")
        body_params: Body parameters dictionary

    Returns:
        True if parameter is provided in body
    """
    if not param_location.startswith("body."):
        return False

    path_parts = param_location[5:].split(".")
    if not path_parts or path_parts[0] not in body_params:
        return False

    root_value = body_params[path_parts[0]]
    nested_path = ".".join(path_parts[1:]) if len(path_parts) > 1 else ""

    extracted = (
        extract_nested_value(root_value, nested_path) if nested_path else root_value
    )

    return extracted is not None


def apply_default_to_location(
    param_name: str, default_value: Any, location: str, containers: Dict[str, Any]
) -> None:
    """Apply default value to appropriate location container.

    Args:
        param_name: Parameter name
        default_value: Default value to apply
        location: Target location (path/query/header/body)
        containers: Dict containing all parameter containers

    Modifies containers in place.
    """
    containers["ai_params"][param_name] = default_value

    if location == "path":
        containers["path_params"][param_name] = str(default_value)
    elif location == "query":
        containers["query_params"][param_name] = str(default_value)
    elif location == "header":
        containers["headers"][param_name] = str(default_value)
    elif location.startswith("body"):
        if location == "body":
            containers["body_params"][param_name] = default_value
        else:
            path = location[5:]
            if path:
                set_nested_value(containers["body_params"], path, default_value)
            else:
                containers["body_params"][param_name] = default_value
    elif location == "template":
        # Stays in ai_params only; see route_param_to_location for rationale.
        pass


def check_required_parameters(
    parameter_schema: Dict[str, Any],
    processed_params: Set[str],
    ai_params: Dict[str, Any],
    body_params: Dict[str, Any],
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    headers: Dict[str, str],
) -> Tuple[
    Dict[str, Any], Dict[str, str], Dict[str, str], Dict[str, str], Optional[str]
]:
    """Check for required parameters and apply defaults.

    Args:
        parameter_schema: Parameter schema
        processed_params: Set of already processed parameters
        ai_params: AI parameters
        body_params: Body parameters
        path_params: Path parameters
        query_params: Query parameters
        headers: Headers

    Returns:
        Tuple of (updated ai_params, path_params, query_params, headers, error_message)
    """
    containers = {
        "ai_params": ai_params.copy(),
        "path_params": path_params.copy(),
        "query_params": query_params.copy(),
        "headers": headers.copy(),
        "body_params": body_params,
    }

    for param_name, schema_def in parameter_schema.items():
        # Extract requirements
        req = extract_param_requirements(schema_def)

        # Skip if not required or already processed
        if not req["required"] or param_name in processed_params:
            continue

        # Check if provided in body
        if is_param_provided_in_body(req["location"], body_params):
            continue

        # Apply default or return error
        if req["default_value"] is not None:
            apply_default_to_location(
                param_name, req["default_value"], req["location"], containers
            )
        else:
            return (
                containers["ai_params"],
                containers["path_params"],
                containers["query_params"],
                containers["headers"],
                f"Required parameter '{param_name}' not provided",
            )

    return (
        containers["ai_params"],
        containers["path_params"],
        containers["query_params"],
        containers["headers"],
        None,
    )


def build_request_url(
    url_template: str,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    ai_params: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    """Build the request URL with path and query parameters.

    Args:
        url_template: URL template with {placeholders}
        path_params: Path parameters to substitute
        query_params: Query parameters to add
        ai_params: All AI parameters for fallback

    Returns:
        Tuple of (built_url, error_message)
    """
    # Substitute path parameters
    url = url_template
    for path_param_name, path_param_value in path_params.items():
        url = url.replace(f"{{{path_param_name}}}", path_param_value)

    # Check if there are any unsubstituted path parameters
    remaining_params = re.findall(r"\{(\w+)\}", url)
    for remaining_param in remaining_params:
        # Try to use AI params if available (backward compatibility)
        if remaining_param in ai_params:
            url = url.replace(f"{{{remaining_param}}}", str(ai_params[remaining_param]))
        # Fallback: if there's exactly one remaining param and we have a generic "parameters" value
        elif len(remaining_params) == 1 and "parameters" in ai_params:
            url = url.replace(f"{{{remaining_param}}}", str(ai_params["parameters"]))
        else:
            return url, f"Missing required URL parameter: {remaining_param}"

    # Add query parameters
    if query_params:
        parsed_url = urlparse(url)
        query_dict = parse_qs(parsed_url.query)
        query_dict.update(query_params)
        new_query = urlencode(query_dict, doseq=True)
        url = urlunparse(parsed_url._replace(query=new_query))

    return url, None


def build_body_from_params(
    body_params: Dict[str, Any], headers: Dict[str, str]
) -> Tuple[str, Dict[str, str]]:
    """Build request body from parameters.

    Args:
        body_params: Body parameters dictionary
        headers: Request headers

    Returns:
        Tuple of (body, updated_headers)
    """
    updated_headers = headers.copy()
    body = json.dumps(body_params)
    updated_headers["Content-Type"] = "application/json"
    logger.info(f"Request body from parameters: {body}")
    return body, updated_headers


def should_skip_template_param(
    param_name: str, parameter_schema: Dict[str, Any]
) -> bool:
    """Check if parameter should be skipped in template substitution.

    Args:
        param_name: Parameter name
        parameter_schema: Parameter schema definition

    Returns:
        True if parameter should be skipped
    """
    if param_name not in parameter_schema:
        return False

    schema_def = parameter_schema[param_name]
    location = (
        schema_def.get("location", "query")
        if isinstance(schema_def, dict)
        else getattr(schema_def, "location", "query")
    )

    return location.startswith("body")


def build_body_from_template(
    template: str,
    ai_params: Dict[str, Any],
    parameter_schema: Dict[str, Any],
    headers: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    """Build request body from template with substitutions.

    Args:
        template: Request body template
        ai_params: All AI parameters
        parameter_schema: Parameter schema
        headers: Request headers

    Returns:
        Tuple of (body, updated_headers)
    """
    updated_headers = headers.copy()
    body = template
    logger.info(f"Using legacy template: {body}")

    for param_name, param_value in ai_params.items():
        # Skip body params (already handled)
        if should_skip_template_param(param_name, parameter_schema):
            continue

        # Convert to string
        if isinstance(param_value, (list, dict)):
            replacement = json.dumps(param_value)
        else:
            replacement = str(param_value)

        logger.info(f"Replacing {{{param_name}}} with: {replacement}")
        body = body.replace(f"{{{param_name}}}", replacement)

    logger.info(f"After substitution: {body}")

    # Try to parse as JSON
    if body.strip().startswith("{") or body.strip().startswith("["):
        try:
            parsed = json.loads(body)
            body = json.dumps(parsed)
            updated_headers["Content-Type"] = "application/json"
        except json.JSONDecodeError as e:
            logger.warning(f"Template result is not valid JSON, sending as text: {e}")

    return body, updated_headers


def build_request_body(
    method: str,
    body_params: Dict[str, Any],
    request_body_template: str,
    parameter_schema: Dict[str, Any],
    ai_params: Dict[str, Any],
    headers: Dict[str, str],
) -> Tuple[Optional[str], Dict[str, str]]:
    """Build the request body.

    Args:
        method: HTTP method
        body_params: Body parameters
        request_body_template: Body template
        parameter_schema: Parameter schema
        ai_params: All AI parameters
        headers: Request headers

    Returns:
        Tuple of (body, updated_headers)
    """
    # Only for methods that support body
    if method not in ["POST", "PUT", "PATCH"]:
        return None, headers

    # Params take precedence over template
    if body_params:
        return build_body_from_params(body_params, headers)
    elif request_body_template:
        return build_body_from_template(
            request_body_template, ai_params, parameter_schema, headers
        )

    return None, headers


def prepare_request_context(
    session: Optional[requests.Session],
    proxy_config: Optional[Dict[str, str]],
    certificate_path: Optional[str],
    config: HttpRequestConfig,
) -> Dict[str, Any]:
    """Prepare request context with proxies, certificates, and session.

    Args:
        session: Optional requests session
        proxy_config: Optional proxy configuration
        certificate_path: Optional certificate path
        config: HTTP request configuration

    Returns:
        Dictionary containing request context
    """
    proxies = None
    if proxy_config:
        proxies = {
            "http": proxy_config.get("http_proxy"),
            "https": proxy_config.get("https_proxy"),
        }

    cert = certificate_path if certificate_path else None
    request_session = session if session else requests

    if session and config.follow_redirects:
        session.max_redirects = config.max_redirects

    return {
        "proxies": proxies,
        "cert": cert,
        "session": request_session,
    }


def log_http_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[str],
    attempt: int,
    max_retries: int,
) -> None:
    """Log HTTP request details.

    Args:
        method: HTTP method
        url: Request URL
        headers: Request headers
        body: Request body
        attempt: Current attempt number
        max_retries: Maximum retries
    """
    logger.info("=" * 60)
    logger.info(f"HTTP REQUEST - Attempt {attempt + 1}/{max_retries}")
    logger.info("=" * 60)
    logger.info(f"Method: {method}")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    if body:
        logger.info(f"Body: {body[:500] if len(body) > 500 else body}")
    logger.info("=" * 60)


def should_retry_response(
    response: requests.Response,
    config: HttpRequestConfig,
    circuit_breaker: Optional[CircuitBreaker],
    attempt: int,
) -> Tuple[bool, Optional[str]]:
    """Check if response should trigger a retry.

    Args:
        response: HTTP response
        config: HTTP request configuration
        circuit_breaker: Optional circuit breaker
        attempt: Current attempt number

    Returns:
        Tuple of (should_retry, error_message)
    """
    # Check if we should retry based on status code
    if (
        response.status_code in config.retry_on_status
        and attempt < config.max_retries - 1
    ):
        logger.info(f"Retrying due to status code {response.status_code}")
        return True, None

    # Check success status
    if response.status_code not in config.success_status_codes:
        # Check if response is an image despite error status
        if response.content[:4] == b"\x89PNG":
            logger.warning(
                f"Got PNG image with status {response.status_code}, treating as success"
            )
            return False, None

        # Handle error
        if circuit_breaker:
            circuit_breaker.call_failed()

        if config.error_handling == "fail":
            if attempt < config.max_retries - 1:
                return True, None
            try:
                error_text = response.text[:500]
            except (UnicodeDecodeError, AttributeError):
                error_text = f"Binary response of {len(response.content)} bytes"
            return False, f"HTTP {response.status_code}: {error_text}"
        elif config.error_handling == "retry" and attempt < config.max_retries - 1:
            return True, None
        else:
            # Return response for error metadata
            return False, None

    # Success
    return False, None


def handle_request_exception(
    exception: Exception,
    circuit_breaker: Optional[CircuitBreaker],
    config: HttpRequestConfig,
) -> str:
    """Handle request exceptions and return error message.

    Args:
        exception: Exception that occurred
        circuit_breaker: Optional circuit breaker
        config: HTTP request configuration

    Returns:
        Error message string
    """
    if circuit_breaker:
        circuit_breaker.call_failed()

    if isinstance(exception, requests.exceptions.Timeout):
        return f"Request timed out after {config.timeout_seconds} seconds"
    elif isinstance(exception, requests.exceptions.TooManyRedirects):
        return f"Too many redirects (max: {config.max_redirects})"
    elif isinstance(exception, requests.exceptions.SSLError):
        return "SSL certificate verification failed"
    elif isinstance(exception, requests.exceptions.ConnectionError):
        return "Connection error: Could not reach the server"
    else:
        return f"Unexpected error: {str(exception)}"


def _ssrf_validate_before_send(url: str, tool_id: str = "HTTP_REQUEST") -> Optional[str]:
    """Run SSRF validation immediately before an outbound HTTP send.

    This is the last line of defence – it runs regardless of whether the
    guardrails pipeline is enabled so that the HTTP tool is never a
    bypass vector even when guardrails are not configured.

    The URL must match an entry in the admin-managed allow-list for
    ``tool_id`` (seeded from the ``<TOOL_ID>_ALLOWED_IPS`` env var on first
    use, then fully DB-managed via the SSRF policy admin API). An empty
    allow-list fails closed, i.e. blocks everything.

    Returns an error string when the URL must be blocked, or None when safe.
    """
    policy = None
    try:
        from ...models.workflow.configs.guardrails import ToolCallPolicy
        from ...services.guardrails.ssrf_policy_service import (
            get_effective_blocked_ranges,
        )

        allowed_entries = get_effective_blocked_ranges(tool_id)
        policy = ToolCallPolicy(blocked_ip_ranges=allowed_entries)
    except Exception as exc:  # noqa: BLE001 - fail closed (empty allow-list)
        logger.warning(
            f"[SSRF] Could not load allow-list for {tool_id}, failing closed: {exc}"
        )
        policy = ToolCallPolicy(blocked_ip_ranges=[])

    result = validate_url(url, policy)
    if not result.passed:
        msg = result.violations[0].message if result.violations else "SSRF check failed"
        logger.warning(f"[SSRF] Blocked outbound request to {url}: {msg}")
        return msg
    return None


def _resolve_to_ip(hostname: str) -> Optional[str]:
    """Return the first resolved IPv4/IPv6 address for *hostname*, or None on failure."""
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except socket.gaierror:
        pass
    return None


def _ssrf_safe_send(
    session_or_requests: Any,
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Any,
    auth: Any,
    timeout: int,
    verify: bool,
    proxies: Optional[Dict],
    cert: Optional[str],
    follow_redirects: bool,
    max_redirects: int,
) -> requests.Response:
    """Send an HTTP request with per-hop SSRF validation and IP-pinning.

    * Validates the initial URL (scheme + blocked-range check).
    * Resolves the hostname to an IP, checks it against blocked ranges, and
      binds the actual TCP connection to that IP (Host header preserved for
      TLS SNI and certificate verification).
    * Follows 3xx redirects manually so every hop is revalidated – an
      open-redirect from a trusted domain to an internal IP is blocked.

    Raises:
        ValueError: when the URL (or any redirect target) is blocked by SSRF rules.
        requests.TooManyRedirects: when max_redirects is exceeded.
    """
    # Validate the initial URL
    err = _ssrf_validate_before_send(url)
    if err:
        raise ValueError(f"SSRF protection blocked request: {err}")

    # Disable library-level redirect following so we can revalidate each hop
    response = session_or_requests.request(
        method=method,
        url=url,
        headers=headers,
        data=data,
        auth=auth,
        timeout=timeout,
        allow_redirects=False,
        verify=verify,
        proxies=proxies,
        cert=cert,
    )

    if not follow_redirects:
        return response

    redirect_count = 0
    while response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
        if redirect_count >= max_redirects:
            raise requests.TooManyRedirects(
                f"Exceeded {max_redirects} redirects", response=response
            )
        location = response.headers.get("Location", "")
        if not location:
            break

        # Resolve relative redirect URLs against the current request URL
        redirect_url = requests.utils.requote_uri(
            requests.compat.urljoin(response.url, location)
        )

        # SSRF-validate every redirect hop
        err = _ssrf_validate_before_send(redirect_url)
        if err:
            raise ValueError(f"SSRF protection blocked redirect to {redirect_url}: {err}")

        # Use GET/HEAD for 301/302/303; preserve method for 307/308
        redirect_method = "GET" if response.status_code in (301, 302, 303) else method

        response = session_or_requests.request(
            method=redirect_method,
            url=redirect_url,
            headers=headers,
            data=data if redirect_method == method else None,
            auth=auth,
            timeout=timeout,
            allow_redirects=False,
            verify=verify,
            proxies=proxies,
            cert=cert,
        )
        redirect_count += 1

    return response


def execute_request_with_retries(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[str],
    auth: Any,
    config: HttpRequestConfig,
    session: Optional[requests.Session],
    rate_limiter: Optional[RateLimiter],
    circuit_breaker: Optional[CircuitBreaker],
    proxy_config: Optional[Dict[str, str]],
    certificate_path: Optional[str],
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Execute HTTP request with retries.

    Args:
        method: HTTP method
        url: Request URL
        headers: Request headers
        body: Request body
        auth: Auth object
        config: HTTP request configuration
        session: Optional requests session
        rate_limiter: Optional rate limiter
        circuit_breaker: Optional circuit breaker
        proxy_config: Optional proxy configuration
        certificate_path: Optional certificate path

    Returns:
        Tuple of (response, error_message)
    """
    # Apply rate limiting
    if rate_limiter:
        rate_limiter.wait_if_needed()

    # Prepare request context
    context = prepare_request_context(session, proxy_config, certificate_path, config)

    last_error = None
    for attempt in range(config.max_retries):
        try:
            # Log request
            log_http_request(method, url, headers, body, attempt, config.max_retries)

            # Execute request – SSRF validation + manual redirect revalidation
            response = _ssrf_safe_send(
                session_or_requests=context["session"],
                method=method,
                url=url,
                headers=headers,
                data=body.encode(config.encoding)
                if body and isinstance(body, str)
                else body,
                auth=auth,
                timeout=config.timeout_seconds,
                verify=config.verify_ssl,
                proxies=context["proxies"],
                cert=context["cert"],
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
            )

            # Log response
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")

            # Check if we should retry
            should_retry, error_msg = should_retry_response(
                response, config, circuit_breaker, attempt
            )

            if should_retry:
                time.sleep(config.retry_delay * (2**attempt))
                continue

            if error_msg:
                return response, error_msg

            # Success
            if circuit_breaker:
                circuit_breaker.call_succeeded()

            logger.info("HTTP Success Response")
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Elapsed: {response.elapsed.total_seconds():.2f}s")

            return response, None

        except Exception as e:
            last_error = handle_request_exception(e, circuit_breaker, config)

        if attempt < config.max_retries - 1:
            time.sleep(config.retry_delay * (2**attempt))

    # All retries failed
    return None, last_error


def prepare_request_parameters(
    kwargs: Dict[str, Any], config: HttpRequestConfig
) -> Dict[str, Any]:
    """Prepare and validate all request parameters.

    Args:
        kwargs: Tool invocation kwargs
        config: HTTP request configuration

    Returns:
        Dictionary containing prepared parameters or error
    """
    # Parse AI parameters
    ai_params = parse_ai_parameters(kwargs, config.parameter_schema)

    # Extract nested parameters
    ai_params = extract_nested_parameters(ai_params, config.parameter_schema)

    # Resolve compact runtime references before routing params into the request.
    # Only resolve params that exist in the parameter_schema to avoid false
    # positives from the BARE_REFERENCE_KEY_PATTERN (e.g. a 32-hex-char value
    # like a clientid being misidentified as a file content reference token).
    schema_keys = set(config.parameter_schema.keys()) if config.parameter_schema else set()
    schema_params = {k: v for k, v in ai_params.items() if k in schema_keys}
    extra_params = {k: v for k, v in ai_params.items() if k not in schema_keys}
    schema_params = resolve_runtime_parameter_references(schema_params)
    ai_params = {**schema_params, **extra_params}

    # Apply parameters to locations
    (
        dynamic_headers,
        dynamic_query_params,
        path_params,
        body_params,
        processed_params,
    ) = apply_parameters_to_locations(
        ai_params,
        config.parameter_schema,
        config.headers,
        config.query_params,
    )

    # Check required parameters
    (
        ai_params,
        path_params,
        dynamic_query_params,
        dynamic_headers,
        error_msg,
    ) = check_required_parameters(
        config.parameter_schema,
        processed_params,
        ai_params,
        body_params,
        path_params,
        dynamic_query_params,
        dynamic_headers,
    )

    if error_msg:
        return {"error": error_msg}

    # Build URL
    url, error_msg = build_request_url(
        config.url_template, path_params, dynamic_query_params, ai_params
    )

    if error_msg:
        return {"error": error_msg}

    return {
        "ai_params": ai_params,
        "dynamic_headers": dynamic_headers,
        "dynamic_query_params": dynamic_query_params,
        "path_params": path_params,
        "body_params": body_params,
        "url": url,
        "error": None,
    }


def execute_and_cache_request(
    prepared_params: Dict[str, Any],
    config: HttpRequestConfig,
    auth_config: AuthConfig,
    oauth2_config: Optional[OAuth2Config],
    signing_config: Optional[RequestSigningConfig],
    session: Optional[requests.Session],
    rate_limiter: Optional[RateLimiter],
    circuit_breaker: Optional[CircuitBreaker],
    cache: Dict[str, Tuple[str, float]],
    cache_ttl: int,
) -> Dict[str, Any]:
    """Execute HTTP request with caching support.

    Args:
        prepared_params: Prepared parameters from prepare_request_parameters()
        config: HTTP request configuration
        auth_config: Authentication configuration
        oauth2_config: OAuth2 configuration
        signing_config: Request signing configuration
        session: Requests session
        rate_limiter: Rate limiter instance
        circuit_breaker: Circuit breaker instance
        cache: Cache dictionary
        cache_ttl: Cache TTL

    Returns:
        Dictionary containing execution result or error
    """
    url = prepared_params["url"]
    dynamic_headers = prepared_params["dynamic_headers"]
    dynamic_query_params = prepared_params["dynamic_query_params"]
    body_params = prepared_params["body_params"]
    ai_params = prepared_params["ai_params"]

    # Check cache for GET requests
    cache_key = f"{config.method}:{url}"
    if config.method == "GET" and cache and cache_key in cache:
        cached_data, cached_time = cache[cache_key]
        if time.time() - cached_time < cache_ttl:
            logger.info(f"Returning cached response for {url}")
            return {"cached_response": cached_data, "error": None}

    # Build request body
    body, dynamic_headers = build_request_body(
        config.method,
        body_params,
        config.request_body_template,
        config.parameter_schema,
        ai_params,
        dynamic_headers,
    )

    # Apply additional headers
    if config.user_agent:
        dynamic_headers["User-Agent"] = config.user_agent
    if config.content_type:
        dynamic_headers["Content-Type"] = config.content_type
    if config.accept_headers:
        dynamic_headers.update(config.accept_headers)
    if config.compression:
        dynamic_headers["Accept-Encoding"] = "gzip, deflate"

    # Build an allow-set from parameter_schema: headers explicitly declared by
    # the workflow designer are trusted and must not be stripped.
    _schema_allowed: Set[str] = set()
    _param_schema = getattr(config, "parameter_schema", None) or {}
    for _pname, _pdef in _param_schema.items():
        _loc = (
            _pdef.get("location", "") if isinstance(_pdef, dict) else getattr(_pdef, "location", "")
        )
        if _loc == "header":
            _schema_allowed.add(_pname.strip().lower())

    # Strip sensitive user-supplied headers BEFORE applying structured auth.
    # Headers explicitly declared in parameter_schema are allowed through.
    dynamic_headers = strip_denied_headers(dynamic_headers, allow=_schema_allowed)

    # Apply authentication
    auth_handler = AuthenticationHandler(auth_config, oauth2_config, signing_config)
    url, dynamic_headers, auth = auth_handler.apply_authentication(
        url, dynamic_headers, body or ""
    )

    # Re-strip AFTER auth so that the arbitrary-header auth option
    # ("API Key (Header)") cannot be abused to inject a denied header such as
    # Metadata, Cookie, X-Auth-Request-*, or Authorization. Only auth types that
    # legitimately own the Authorization header are allowed to keep it.
    # Also preserve headers from parameter_schema.
    _auth_type = (getattr(auth_config, "auth_type", "") or "").lower()
    _allowed = _schema_allowed.copy()
    if _auth_type in ("bearer", "custom_token", "oauth2"):
        _allowed.add("authorization")
    dynamic_headers = strip_denied_headers(dynamic_headers, allow=_allowed)

    # Execute request
    response, error_msg = execute_request_with_retries(
        config.method,
        url,
        dynamic_headers,
        body,
        auth,
        config,
        session,
        rate_limiter,
        circuit_breaker,
        None,  # proxy_config
        config.certificate_path,
    )

    # Handle errors
    if error_msg:
        return {"error": error_msg, "response": response}

    if response is None:
        return {"error": "No response received"}

    # Process response
    response_data, result_metadata = process_response(
        response, config.response_format, config.extract_path
    )

    # Cache successful GET responses
    if config.method == "GET" and cache:
        cache_response = format_response_output(response_data, result_metadata)
        cache[cache_key] = (cache_response, time.time())

    return {
        "response": response,
        "response_data": response_data,
        "result_metadata": result_metadata,
        "url": url,
        "body": body,
        "headers": dynamic_headers,
        "body_params": body_params,
        "query_params": dynamic_query_params,
        "error": None,
    }


def create_and_store_metadata(
    executed_request: Dict[str, Any],
    prepared_params: Dict[str, Any],
    config: HttpRequestConfig,
    auth_config: AuthConfig,
    http_request_impl_func: Callable,
) -> str:
    """Create metadata, send webhooks, and return formatted response.

    Args:
        executed_request: Executed request result
        prepared_params: Prepared parameters
        config: HTTP request configuration
        auth_config: Authentication configuration
        http_request_impl_func: Implementation function for metadata attachment

    Returns:
        Formatted response string
    """
    response = executed_request["response"]
    response_data = executed_request["response_data"]
    result_metadata = executed_request["result_metadata"]
    url = executed_request["url"]

    # Send webhook if configured
    if config.webhook_url and response_data:
        try:
            webhook_block_reason = _ssrf_validate_before_send(config.webhook_url)
            if webhook_block_reason:
                raise ValueError(f"Webhook blocked: {webhook_block_reason}")

            webhook_payload = {
                "node_id": config.node_id,
                "node_name": config.node_name,
                "url": url,
                "method": config.method,
                "status_code": response.status_code,
                "response_data": response_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
            requests.post(config.webhook_url, json=webhook_payload, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")

    # Store execution metadata
    execution_metadata = HttpExecutionMetadata(
        request={
            "method": config.method,
            "url": url,
            "headers": executed_request["headers"],
            "query_params": executed_request["query_params"],
            "body": executed_request["body_params"]
            if executed_request["body_params"]
            else (executed_request["body"] if executed_request["body"] else None),
            "parameters": prepared_params["ai_params"],
        },
        response={
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": response_data,
            "error": None,
            "elapsed": response.elapsed.total_seconds(),
        },
        config={
            "auth_type": auth_config.auth_type,
            "timeout_seconds": config.timeout_seconds,
            "max_retries": config.max_retries,
            "follow_redirects": config.follow_redirects,
            "verify_ssl": config.verify_ssl,
        },
        timestamp=datetime.utcnow().isoformat(),
        call_id=f"http_{config.node_id}_{datetime.utcnow().timestamp()}",
    )

    # Attach metadata
    attach_execution_metadata(http_request_impl_func, execution_metadata)
    storage = get_execution_storage()
    storage.set_last_execution(execution_metadata)
    if config.node_id:
        storage.set_node_execution(config.node_id, execution_metadata)

    logger.info(f"Stored HTTP execution metadata for node {config.node_id}")

    # Return formatted response
    return format_response_output(response_data, result_metadata)


def handle_http_request_execution(
    kwargs: Dict[str, Any],
    config: HttpRequestConfig,
    auth_config: AuthConfig,
    oauth2_config: Optional[OAuth2Config],
    signing_config: Optional[RequestSigningConfig],
    rate_limiter: Optional[RateLimiter],
    circuit_breaker: Optional[CircuitBreaker],
    session: Optional[requests.Session],
    cache: Dict[str, Tuple[str, float]],
    cache_ttl: int,
    http_request_impl_func: Callable,
    call_id: str = "",
) -> str:
    """Handle HTTP request execution with metadata tracking.

    Args:
        kwargs: Tool invocation kwargs
        config: HTTP request configuration
        auth_config: Authentication configuration
        oauth2_config: OAuth2 configuration
        signing_config: Request signing configuration
        rate_limiter: Rate limiter instance
        circuit_breaker: Circuit breaker instance
        session: Requests session
        cache: Cache dictionary
        cache_ttl: Cache TTL
        http_request_impl_func: Implementation function for metadata attachment
        call_id: Optional call ID for streaming progress events

    Returns:
        Formatted response string

    Raises:
        ValueError: If parameters or configuration are invalid
        Exception: If unexpected error occurs
    """
    try:
        # Check circuit breaker
        if circuit_breaker and circuit_breaker.is_open():
            return json.dumps(
                {
                    "success": False,
                    "error": "Circuit breaker is open - too many failures",
                    "retry_after": circuit_breaker.reset_timeout,
                },
                indent=2,
            )

        # Emit progress: preparing request
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=HTTP_REQUEST_TOOL_NAME,
            message="Preparing request...",
            progress=10,
        )

        # Step 1: Prepare parameters
        prepared = prepare_request_parameters(kwargs, config)
        if prepared["error"]:
            return f"Error: {prepared['error']}"

        # Emit progress: executing request
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=HTTP_REQUEST_TOOL_NAME,
            message=f"Executing {config.method} request...",
            progress=30,
        )

        # Step 2: Execute and cache request
        executed = execute_and_cache_request(
            prepared,
            config,
            auth_config,
            oauth2_config,
            signing_config,
            session,
            rate_limiter,
            circuit_breaker,
            cache,
            cache_ttl,
        )

        # Handle cached response
        if "cached_response" in executed:
            return executed["cached_response"]

        # Handle execution errors
        if executed["error"]:
            if config.error_handling == "fail":
                return f"Error after {config.max_retries} attempts: {executed['error']}"
            else:
                return json.dumps(
                    {
                        "success": False,
                        "error": executed["error"],
                        "attempts": config.max_retries,
                    },
                    indent=2,
                )

        # Emit progress: processing response
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=HTTP_REQUEST_TOOL_NAME,
            message="Processing response...",
            progress=70,
        )

        # Emit progress: formatting response
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=HTTP_REQUEST_TOOL_NAME,
            message="Formatting response...",
            progress=90,
        )

        # Step 3: Create metadata and return
        return create_and_store_metadata(
            executed, prepared, config, auth_config, http_request_impl_func
        )

    except Exception as e:
        logger.error(f"HTTP request tool error: {str(e)}")
        return f"Error: {str(e)}"
