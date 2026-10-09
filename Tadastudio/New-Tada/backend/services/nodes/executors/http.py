"""
HTTP Node Executor.

This module handles execution of HTTP_REQUEST_ACTION nodes, including:
- URL, query param, header, and body mapping from state
- Authentication (Bearer, API Key, Basic Auth)
- Request execution with retry logic
- Response parsing and path extraction
- Database tracking and WebSocket notifications
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import requests
from requests.auth import HTTPBasicAuth
from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


http_executor_logger = get_logger("nodes.executors.http")


class HttpNodeExecutor(BaseNodeExecutor):
    """
    Executor for HTTP_REQUEST_ACTION nodes.

    Handles HTTP requests with comprehensive configuration including:
    - Dynamic URL/query/header/body parameter mapping
    - Authentication (Bearer, API Key, Basic)
    - Retry logic with exponential backoff
    - Response path extraction
    - Success status code validation
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize HTTP node executor."""
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request node.

        Args:
            node: The HTTP request node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with HTTP response data
        """
        http_executor_logger.info(f"Executing HTTP_REQUEST_ACTION node: {node.name}")
        execution_start_time = time.time()

        # Create tracking record
        node_exec_id = await self._create_tracking_record(node, state, graph)

        try:
            # Validate and extract configuration
            config = self._validate_config(node)

            # Resolve saved API endpoint if referenced
            config = self._resolve_endpoint(config, user_id)

            # Parse configuration into HttpRequestConfig
            http_config = self._parse_config(config)

            # Build the complete request
            request_spec = self._build_request(http_config, state, graph)

            # Execute the request with retries
            response_data = await self._execute_request(
                request_spec,
                http_config.max_retries,
                http_config.timeout_seconds,
                http_config.verify_ssl,
            )

            # Process the response
            node_output = self._handle_response(
                response_data,
                http_config.response_path,
                http_config.success_status_codes,
            )

            # Complete tracking
            execution_duration = time.time() - execution_start_time
            await self._complete_tracking(
                node, state, node_exec_id, node_output, execution_duration, graph
            )

            # Return state update
            return self._build_state_update(node_output, state)

        except Exception as e:
            http_executor_logger.error(
                f"HTTP request error for {node.name}: {e}", exc_info=True
            )
            return await self._handle_error(node, state, node_exec_id, str(e))

    def _validate_config(self, node: EnhancedNodeData) -> Union[Dict, Any]:
        """
        Validate HTTP configuration exists.

        Args:
            node: The HTTP request node

        Returns:
            HTTP configuration object

        Raises:
            ValueError: If configuration is missing
        """
        config = node.http_request_action_config
        if not config:
            raise ValueError("HTTP request action configuration is missing")
        return config

    def _resolve_endpoint(
        self, config: Union[Dict, Any], user_id: Optional[str] = None
    ) -> Union[Dict, Any]:
        """Resolve a saved API endpoint reference if present in the config.

        Converts the config to a dict, merges saved endpoint defaults with
        node-level overrides (node values take precedence), and returns
        the merged dict for parsing.

        Args:
            config: Configuration as dict or dataclass
            user_id: Optional user identifier for visibility checks

        Returns:
            Merged config dict if endpoint_id was resolved, original config otherwise
        """
        # Extract endpoint_id from config
        if isinstance(config, dict):
            endpoint_id = config.get("endpoint_id")
        else:
            endpoint_id = getattr(config, "endpoint_id", None)

        if not endpoint_id:
            return config

        # Convert dataclass to dict for merging
        if not isinstance(config, dict):
            config_dict = {
                "endpoint_id": endpoint_id,
                "url_template": getattr(config, "url_template", ""),
                "method": getattr(config, "method", "GET"),
                "headers": dict(config.headers)
                if getattr(config, "headers", None)
                else {},
                "body_template": getattr(config, "body_template", ""),
                "body_type": getattr(config, "body_type", "json"),
                "auth_type": getattr(config, "auth_type", "none"),
                "auth_config": dict(config.auth_config)
                if getattr(config, "auth_config", None)
                else {},
                "timeout_seconds": getattr(config, "timeout_seconds", 30),
                "max_retries": getattr(config, "max_retries", 3),
                "verify_ssl": getattr(config, "verify_ssl", True),
                "response_path": getattr(config, "response_path", ""),
                "success_status_codes": (
                    list(config.success_status_codes)
                    if getattr(config, "success_status_codes", None)
                    else [200, 201, 202, 204]
                ),
                "url_param_mappings": list(config.url_param_mappings)
                if getattr(config, "url_param_mappings", None)
                else [],
                "query_param_mappings": list(config.query_param_mappings)
                if getattr(config, "query_param_mappings", None)
                else [],
                "header_mappings": list(config.header_mappings)
                if getattr(config, "header_mappings", None)
                else [],
                "body_mappings": list(config.body_mappings)
                if getattr(config, "body_mappings", None)
                else [],
            }
        else:
            config_dict = config

        from backend.services.api_endpoint.resolver import resolve_endpoint_config

        return resolve_endpoint_config(config_dict, user_id)

    def _parse_config(self, config: Union[Dict, Any]) -> "HttpRequestConfig":
        """
        Parse configuration from dict or dataclass into standard format.

        Args:
            config: Configuration as dict or dataclass

        Returns:
            HttpRequestConfig with normalized values
        """
        if isinstance(config, dict):
            return HttpRequestConfig(
                url_template=config.get("url_template", ""),
                method=config.get("method", "GET"),
                headers=config.get("headers", {}),
                body_template=config.get("body_template", ""),
                body_type=config.get("body_type", "json"),
                auth_type=config.get("auth_type", "none"),
                auth_config=config.get("auth_config", {}),
                timeout_seconds=config.get("timeout_seconds", 30),
                max_retries=config.get("max_retries", 3),
                verify_ssl=config.get("verify_ssl", True),
                response_path=config.get("response_path", ""),
                success_status_codes=config.get(
                    "success_status_codes", [200, 201, 202, 204]
                ),
                url_param_mappings=config.get("url_param_mappings", []),
                query_param_mappings=config.get("query_param_mappings", []),
                header_mappings=config.get("header_mappings", []),
                body_mappings=config.get("body_mappings", []),
            )
        else:
            return HttpRequestConfig(
                url_template=config.url_template,
                method=config.method,
                headers=dict(config.headers) if config.headers else {},
                body_template=config.body_template,
                body_type=getattr(config, "body_type", "json"),
                auth_type=config.auth_type,
                auth_config=dict(config.auth_config) if config.auth_config else {},
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
                verify_ssl=getattr(config, "verify_ssl", True),
                response_path=config.response_path,
                success_status_codes=(
                    list(config.success_status_codes)
                    if config.success_status_codes
                    else [200, 201, 202, 204]
                ),
                url_param_mappings=(
                    list(config.url_param_mappings)
                    if hasattr(config, "url_param_mappings")
                    else []
                ),
                query_param_mappings=(
                    list(config.query_param_mappings)
                    if hasattr(config, "query_param_mappings")
                    else []
                ),
                header_mappings=(
                    list(config.header_mappings)
                    if hasattr(config, "header_mappings")
                    else []
                ),
                body_mappings=(
                    list(config.body_mappings)
                    if hasattr(config, "body_mappings")
                    else []
                ),
            )

    def _build_request(
        self, config: "HttpRequestConfig", state: WorkflowState, graph: Any
    ) -> "HttpRequestSpec":
        """
        Build complete HTTP request specification from config and state.

        Args:
            config: HTTP request configuration
            state: Current workflow state
            graph: The graph definition

        Returns:
            HttpRequestSpec with fully resolved URL, headers, body, auth
        """
        # Start with base URL
        url = config.url_template

        # Process URL parameters (path variables)
        url = self._process_url_parameters(url, config.url_param_mappings, state)

        # Process query parameters
        query_params = self._process_query_parameters(
            config.query_param_mappings, state
        )
        url = self._append_query_params(url, query_params)

        # Process headers
        headers = self._process_headers(config.headers, config.header_mappings, state)

        # Strip sensitive user-supplied headers BEFORE applying structured auth.
        # Prevents smuggling of Authorization, Cookie, Metadata, X-Auth-Request-*
        # (identity bypass / IMDS). The node's own auth config (applied below) can
        # still legitimately set the Authorization header.
        from backend.tools.http_request.handlers import strip_denied_headers

        headers = strip_denied_headers(headers)

        # Process body
        body = self._process_body(
            config.method,
            config.body_template,
            config.body_mappings,
            state,
            headers,
            config.body_type,
        )

        # Setup authentication. Auth config values support {{variable}}
        # templates (e.g. a bearer token produced by a previous HTTP node),
        # matching the "Enter token or {{variable}}" hint in the panel.
        auth_config = self._resolve_auth_config_templates(config.auth_config, state)
        auth = self._setup_auth(config.auth_type, auth_config, headers)

        # Re-strip AFTER auth so the arbitrary-header auth option ("API Key
        # (Header)") cannot inject a denied header name. Only bearer auth
        # legitimately owns the Authorization header on this path.
        _auth_type = (config.auth_type or "").lower()
        _allowed = {"authorization"} if _auth_type == "bearer" else set()
        headers = strip_denied_headers(headers, allow=_allowed)

        return HttpRequestSpec(
            url=url,
            method=config.method,
            headers=headers,
            body=body,
            auth=auth,
        )

    def _process_url_parameters(
        self, url: str, url_param_mappings: List, state: WorkflowState
    ) -> str:
        """
        Process URL path parameters and substitute into URL template.

        Args:
            url: URL template with {param} placeholders
            url_param_mappings: List of parameter mappings
            state: Current workflow state

        Returns:
            URL with substituted parameters
        """
        for param_mapping in url_param_mappings:
            param_name, value = self._extract_mapping_value(param_mapping, state)
            if param_name:
                url = url.replace(f"{{{param_name}}}", str(value))
        return url

    def _process_query_parameters(
        self, query_param_mappings: List, state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Process query parameters from mappings.

        Args:
            query_param_mappings: List of query parameter mappings
            state: Current workflow state

        Returns:
            Dictionary of query parameters
        """
        query_params = {}
        for param_mapping in query_param_mappings:
            param_name, value = self._extract_mapping_value(param_mapping, state)
            if param_name:
                query_params[param_name] = value
        return query_params

    def _append_query_params(self, url: str, query_params: Dict[str, Any]) -> str:
        """
        Append query parameters to URL.

        Args:
            url: Base URL
            query_params: Dictionary of query parameters

        Returns:
            URL with query string appended
        """
        if query_params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(query_params)}"
        return url

    def _process_headers(
        self, base_headers: Dict, header_mappings: List, state: WorkflowState
    ) -> Dict[str, str]:
        """
        Process headers from base configuration and mappings.

        Args:
            base_headers: Base headers from configuration
            header_mappings: List of header mappings
            state: Current workflow state

        Returns:
            Complete headers dictionary
        """
        headers = dict(base_headers)
        for header_mapping in header_mappings:
            header_name, value = self._extract_header_mapping_value(
                header_mapping, state
            )
            if header_name:
                headers[header_name] = str(value)
        return headers

    def _process_body(
        self,
        method: str,
        body_template: str,
        body_mappings: List,
        state: WorkflowState,
        headers: Dict[str, str],
        body_type: str = "json",
    ) -> Optional[str]:
        """
        Process request body for POST/PUT/PATCH requests.

        Args:
            method: HTTP method
            body_template: Body template string
            body_mappings: List of body field mappings
            state: Current workflow state
            headers: Headers dictionary (will be updated with Content-Type)
            body_type: Body encoding (json, form, text, raw)

        Returns:
            Request body as string, or None for GET/DELETE
        """
        if method not in ["POST", "PUT", "PATCH"]:
            return None

        if body_mappings:
            body_data = {}
            for body_mapping in body_mappings:
                field_name, value = self._extract_body_mapping_value(
                    body_mapping, state
                )
                if field_name:
                    body_data[field_name] = value

            if body_type == "form":
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                return urlencode(
                    {k: "" if v is None else str(v) for k, v in body_data.items()}
                )

            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            return json.dumps(body_data)

        elif body_template:
            # Use template string - delegate to template processor
            from backend.services.io import TemplateProcessor

            template_processor = TemplateProcessor()
            rendered = template_processor.process(body_template, state)

            # Default the Content-Type the same way the mapping branch does.
            # Only for types whose encoding is unambiguous — a raw/text body
            # may be XML, CSV or anything else, so it is left to the caller.
            if "Content-Type" not in headers:
                if body_type == "form":
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                elif body_type == "json":
                    headers["Content-Type"] = "application/json"

            return rendered

        return None

    def _resolve_auth_config_templates(
        self, auth_config: Optional[Dict], state: WorkflowState
    ) -> Dict:
        """
        Resolve {{variable}} templates inside auth config values.

        Lets a node authenticate with a value produced upstream, e.g. a
        bearer token from a preceding OAuth token request:
        ``{"token": "{{access_token}}"}``.

        Args:
            auth_config: Raw auth configuration (values may contain templates)
            state: Current workflow state

        Returns:
            Auth configuration with templates replaced by state values
        """
        if not auth_config:
            return {}

        from backend.services.io import TemplateProcessor

        template_processor = TemplateProcessor()
        resolved: Dict[str, Any] = {}
        for key, value in auth_config.items():
            if isinstance(value, str) and "{{" in value:
                resolved[key] = template_processor.process(value, state)
            else:
                resolved[key] = value
        return resolved

    def _setup_auth(
        self, auth_type: str, auth_config: Dict, headers: Dict[str, str]
    ) -> Optional[HTTPBasicAuth]:
        """
        Set up authentication for the request.

        Args:
            auth_type: Type of authentication (bearer, api_key, basic, none)
            auth_config: Authentication configuration
            headers: Headers dictionary (will be updated for bearer/api_key)

        Returns:
            HTTPBasicAuth object for basic auth, None otherwise
        """
        if auth_type == "bearer" and auth_config.get("token"):
            headers["Authorization"] = f"Bearer {auth_config['token']}"
            return None

        elif auth_type == "api_key":
            # The properties panel saves header_name/api_key; header/key are
            # kept as legacy fallbacks.
            header_name = auth_config.get("header_name") or auth_config.get("header")
            api_key = auth_config.get("api_key") or auth_config.get("key")
            if header_name and api_key:
                headers[header_name] = api_key
            return None

        elif auth_type == "basic":
            if "username" in auth_config and "password" in auth_config:
                return HTTPBasicAuth(auth_config["username"], auth_config["password"])
            return None

        return None

    def _extract_mapping_value(
        self, param_mapping: Union[Dict, Any], state: WorkflowState
    ) -> tuple:
        """
        Extract parameter name and value from a mapping.

        Args:
            param_mapping: Parameter mapping as dict or dataclass
            state: Current workflow state

        Returns:
            Tuple of (parameter_name, value)
        """
        if isinstance(param_mapping, dict):
            param_name = param_mapping.get("parameter_name")
            source_node_id = param_mapping.get("source_node_id")
            source_field_path = param_mapping.get("source_field_path")
            source_mode = param_mapping.get("source_mode", "specific")
            static_value = param_mapping.get("static_value", "")
            default_value = param_mapping.get("default_value", "")
            custom_template = param_mapping.get("custom_template")
        else:
            param_name = getattr(param_mapping, "parameter_name", None)
            source_node_id = getattr(param_mapping, "source_node_id", None)
            source_field_path = getattr(param_mapping, "source_field_path", None)
            source_mode = getattr(param_mapping, "source_mode", "specific")
            static_value = getattr(param_mapping, "static_value", "")
            default_value = getattr(param_mapping, "default_value", "")
            custom_template = getattr(param_mapping, "custom_template", None)

        if not param_name:
            return None, None

        # Delegate to mapping value extractor
        from backend.services.io import MappingValueExtractor

        mapping_extractor = MappingValueExtractor()
        value = mapping_extractor.extract(
            source_mode=source_mode,
            state=state,
            static_value=static_value,
            default_value=default_value,
            source_node_id=source_node_id,
            source_field_path=source_field_path,
            idx=0,
            sql_expressions=[],
            custom_template=custom_template,
        )

        return param_name, value

    def _extract_header_mapping_value(
        self, header_mapping: Union[Dict, Any], state: WorkflowState
    ) -> tuple:
        """
        Extract header name and value from a mapping.

        Args:
            header_mapping: Header mapping as dict or dataclass
            state: Current workflow state

        Returns:
            Tuple of (header_name, value)
        """
        if isinstance(header_mapping, dict):
            # The properties panel saves "parameter_name" (HttpParameterMapping);
            # "header_name" is kept as a legacy fallback.
            header_name = header_mapping.get("header_name") or header_mapping.get(
                "parameter_name"
            )
            source_node_id = header_mapping.get("source_node_id")
            source_field_path = header_mapping.get("source_field_path")
            source_mode = header_mapping.get("source_mode", "static")
            static_value = header_mapping.get("static_value", "")
            default_value = header_mapping.get("default_value", "")
            custom_template = header_mapping.get("custom_template")
        else:
            header_name = getattr(header_mapping, "header_name", None) or getattr(
                header_mapping, "parameter_name", None
            )
            source_node_id = getattr(header_mapping, "source_node_id", None)
            source_field_path = getattr(header_mapping, "source_field_path", None)
            source_mode = getattr(header_mapping, "source_mode", "static")
            static_value = getattr(header_mapping, "static_value", "")
            default_value = getattr(header_mapping, "default_value", "")
            custom_template = getattr(header_mapping, "custom_template", None)

        if not header_name:
            return None, None

        from backend.services.io import MappingValueExtractor

        mapping_extractor = MappingValueExtractor()
        value = mapping_extractor.extract(
            source_mode=source_mode,
            state=state,
            static_value=static_value,
            default_value=default_value,
            source_node_id=source_node_id,
            source_field_path=source_field_path,
            idx=0,
            sql_expressions=[],
            custom_template=custom_template,
        )

        return header_name, value

    def _extract_body_mapping_value(
        self, body_mapping: Union[Dict, Any], state: WorkflowState
    ) -> tuple:
        """
        Extract body field name and value from a mapping.

        Args:
            body_mapping: Body field mapping as dict or dataclass
            state: Current workflow state

        Returns:
            Tuple of (field_name, value)
        """
        if isinstance(body_mapping, dict):
            # The properties panel saves "parameter_name" (HttpParameterMapping);
            # "field_name" is kept as a legacy fallback.
            field_name = body_mapping.get("field_name") or body_mapping.get(
                "parameter_name"
            )
            source_node_id = body_mapping.get("source_node_id")
            source_field_path = body_mapping.get("source_field_path")
            source_mode = body_mapping.get("source_mode", "specific")
            static_value = body_mapping.get("static_value", "")
            default_value = body_mapping.get("default_value", "")
            custom_template = body_mapping.get("custom_template")
        else:
            field_name = getattr(body_mapping, "field_name", None) or getattr(
                body_mapping, "parameter_name", None
            )
            source_node_id = getattr(body_mapping, "source_node_id", None)
            source_field_path = getattr(body_mapping, "source_field_path", None)
            source_mode = getattr(body_mapping, "source_mode", "specific")
            static_value = getattr(body_mapping, "static_value", "")
            default_value = getattr(body_mapping, "default_value", "")
            custom_template = getattr(body_mapping, "custom_template", None)

        if not field_name:
            return None, None

        from backend.services.io import MappingValueExtractor

        mapping_extractor = MappingValueExtractor()
        value = mapping_extractor.extract(
            source_mode=source_mode,
            state=state,
            static_value=static_value,
            default_value=default_value,
            source_node_id=source_node_id,
            source_field_path=source_field_path,
            idx=0,
            sql_expressions=[],
            custom_template=custom_template,
        )

        return field_name, value

    async def _execute_request(
        self,
        request_spec: "HttpRequestSpec",
        max_retries: int,
        timeout_seconds: int,
        verify_ssl: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic.

        Args:
            request_spec: Complete request specification
            max_retries: Maximum number of retry attempts
            timeout_seconds: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Response data dictionary with success, status_code, and data

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        response_obj = None

        # Reuse the tool path's SSRF-safe sender so standalone HTTP nodes get the
        # same protection: validate/resolve the target before sending, block
        # loopback/link-local/private ranges, and re-validate every redirect hop.
        from backend.tools.http_request.handlers import _ssrf_safe_send

        for attempt in range(max_retries):
            try:
                http_executor_logger.info(
                    f"HTTP {request_spec.method} request to {request_spec.url} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                response_obj = _ssrf_safe_send(
                    session_or_requests=requests,
                    method=request_spec.method,
                    url=request_spec.url,
                    headers=request_spec.headers,
                    data=request_spec.body,
                    auth=request_spec.auth,
                    timeout=timeout_seconds,
                    verify=verify_ssl,
                    proxies=None,
                    cert=None,
                    follow_redirects=True,
                    max_redirects=10,
                )

                # Request completed - will validate status code later
                return {
                    "response": response_obj,
                    "success": True,
                }

            except ValueError as ssrf_error:
                # SSRF validation blocked this destination (or a redirect hop).
                # This is a security block, not a transient error — fail fast,
                # do not retry.
                http_executor_logger.warning(
                    f"HTTP request blocked by SSRF protection: {ssrf_error}"
                )
                raise Exception(f"Blocked by SSRF protection: {ssrf_error}") from ssrf_error

            except requests.exceptions.Timeout:
                last_error = f"Request timeout after {timeout_seconds} seconds"
                http_executor_logger.warning(
                    f"HTTP request timeout (attempt {attempt + 1})"
                )

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                http_executor_logger.warning(f"HTTP request error: {e}")

            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries failed
        raise Exception(
            f"HTTP request failed after {max_retries} attempts: {last_error}"
        )

    def _handle_response(
        self,
        response_data: Dict[str, Any],
        response_path: str,
        success_status_codes: List[int],
    ) -> Dict[str, Any]:
        """
        Process HTTP response and extract data.

        Args:
            response_data: Response data from _execute_request
            response_path: Optional path to extract from response JSON
            success_status_codes: List of successful status codes

        Returns:
            Node output dictionary with success, status_code, and data

        Raises:
            Exception: If status code is not in success_status_codes
        """
        response = response_data["response"]

        # Check if status code is successful
        if response.status_code not in success_status_codes:
            error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
            http_executor_logger.warning(f"HTTP request failed: {error_msg}")
            raise Exception(error_msg)

        # Parse response
        try:
            parsed_data = response.json()
        except (ValueError, TypeError):
            parsed_data = response.text

        # Strip any headers-like key so downstream agent nodes never see it
        from backend.tools.http_request.response import strip_headers_key

        parsed_data = strip_headers_key(parsed_data)

        # Extract specific path if configured
        if response_path and isinstance(parsed_data, dict):
            path_parts = response_path.split(".")
            extracted = parsed_data
            for part in path_parts:
                if isinstance(extracted, dict) and part in extracted:
                    extracted = extracted[part]
                else:
                    break
            parsed_data = extracted

        http_executor_logger.info(
            f"HTTP_REQUEST_ACTION completed successfully: status={response.status_code}"
        )

        return {
            "success": True,
            "status_code": response.status_code,
            "data": parsed_data,
        }

    async def _create_tracking_record(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> Optional[int]:
        """
        Create database tracking record and send start notification.

        Args:
            node: The HTTP request node
            state: Current workflow state
            graph: The graph definition

        Returns:
            Node execution ID, or None if tracking disabled
        """
        # Build input for tracking using InputBuilder
        from backend.services.io import InputBuilder

        input_builder = InputBuilder()
        input_message = input_builder.build(node, state, graph)

        # Get review iteration from state (set by upstream agent nodes)
        # This tracks which agent review iteration triggered this HTTP request
        review_iteration = state.get("current_review_iteration")

        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "HTTP_REQUEST_ACTION",
            {"message": input_message},
            review_iteration=review_iteration,
        )

        # Send start notification
        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_start(
                node,
                state,
                "HTTP_REQUEST_ACTION",
                node_exec_id=node_exec_id,
                execution_order=current_order,
            )

        return node_exec_id

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        node_output: Dict[str, Any],
        duration_seconds: float,
        graph: Any,
    ) -> None:
        """
        Complete database tracking and send completion notification.

        Args:
            node: The HTTP request node
            state: Current workflow state
            node_exec_id: Database node execution ID
            node_output: Output data from HTTP request
            duration_seconds: Execution duration
            graph: The graph definition
        """
        # Complete database record
        await self.database_tracker.complete_node_execution(
            node_exec_id, node_output, None
        )

        # Send completion notification
        if node_exec_id:
            from backend.services.io import InputBuilder

            input_builder = InputBuilder()
            input_message = input_builder.build(node, state, graph)

            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_complete(
                node,
                state,
                node_output,
                "HTTP_REQUEST_ACTION",
                node_exec_id=node_exec_id,
                duration_seconds=duration_seconds,
                input_data={"message": input_message},
                execution_order=current_order,
            )

    def _build_state_update(
        self, node_output: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Args:
            node_output: Output from HTTP request
            state: Current workflow state

        Returns:
            State update dictionary
        """
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": json.dumps(node_output),
                "structured": node_output,
                "fields": node_output,
            },
            **order_update,
        }

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Handle HTTP request error.

        Args:
            node: The HTTP request node
            state: Current workflow state
            node_exec_id: Database node execution ID
            error_message: Error message

        Returns:
            Error state update
        """
        error_output = {"error": error_message, "success": False}

        # Update database if tracking was started
        if node_exec_id:
            await self.database_tracker.complete_node_execution(
                node_exec_id, error_output, None
            )

        # Send error notification
        await self.notification_handler.notify_error(
            node, state, error_message, "HTTP_REQUEST_ACTION"
        )

        # Build error state update
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": json.dumps(error_output),
                "structured": error_output,
                "fields": error_output,
            },
            **order_update,
        }


# Helper data classes for internal use
class HttpRequestConfig:
    """Configuration for HTTP request."""

    def __init__(
        self,
        url_template: str,
        method: str,
        headers: Dict,
        body_template: str,
        body_type: str,
        auth_type: str,
        auth_config: Dict,
        timeout_seconds: int,
        max_retries: int,
        response_path: str,
        success_status_codes: List[int],
        url_param_mappings: List,
        query_param_mappings: List,
        header_mappings: List,
        body_mappings: List,
        verify_ssl: bool = True,
    ):
        """Initialize HTTP request configuration."""
        self.url_template = url_template
        self.method = method
        self.headers = headers
        self.body_template = body_template
        self.body_type = body_type
        self.auth_type = auth_type
        self.auth_config = auth_config
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.response_path = response_path
        self.success_status_codes = success_status_codes
        self.url_param_mappings = url_param_mappings
        self.query_param_mappings = query_param_mappings
        self.header_mappings = header_mappings
        self.body_mappings = body_mappings


class HttpRequestSpec:
    """Specification for a complete HTTP request."""

    def __init__(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[str],
        auth: Optional[HTTPBasicAuth],
    ):
        """Initialize HTTP request specification."""
        self.url = url
        self.method = method
        self.headers = headers
        self.body = body
        self.auth = auth
