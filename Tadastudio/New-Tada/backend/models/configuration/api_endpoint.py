"""API endpoint configuration models."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ApiEndpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing reusable API endpoint configurations.

    Stores HTTP endpoint configurations (URL, method, auth, headers, etc.)
    that can be referenced by HTTP Request nodes in workflows.

    Attributes:
        id: Unique endpoint identifier (UUID).
        name: Unique endpoint name.
        description: Endpoint description.
        service_type: Service type (generic, servicenow, workday, salesforce, etc.).
        url_template: URL template with optional {placeholders}.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        headers: Static headers as key-value pairs (JSON).
        query_params: Static query parameters (JSON).
        request_body_template: Default request body template.
        content_type: Content type header value.
        parameter_schema: Dynamic parameter definitions (JSON).
        auth_type: Authentication type (none, bearer, api_key, basic, etc.).
        encrypted_auth_config: Encrypted authentication configuration (JSON).
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        retry_delay: Delay between retries in seconds.
        retry_on_status: HTTP status codes to retry on (JSON list).
        response_format: Expected response format (auto, json, xml, binary).
        extract_path: JSONPath for extracting response data.
        success_status_codes: HTTP status codes indicating success (JSON list).
        verify_ssl: Whether to verify SSL certificates.
        follow_redirects: Whether to follow HTTP redirects.
        max_redirects: Maximum number of redirects to follow.
        is_active: Whether the endpoint is active.
        usage_count: Number of times the endpoint has been used.
        last_used: Last usage timestamp.
        last_connection_test: Last connection health check timestamp.
        last_connection_status: Last health check result (success, failed, timeout).
        user_id: Owner user ID.
        visible_to_groups: Group-based visibility (JSON list).
    """

    __tablename__ = "api_endpoints"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_api_endpoint_name_user"),
    )

    # Identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(
        String(50), nullable=False, default="generic", server_default="generic"
    )

    # HTTP Configuration
    url_template = Column(Text, nullable=False)
    method = Column(String(10), nullable=False, default="GET")
    headers = Column(JSON, nullable=True)
    query_params = Column(JSON, nullable=True)
    request_body_template = Column(Text, nullable=True)
    content_type = Column(String(100), nullable=True)
    parameter_schema = Column(JSON, nullable=True)

    # Authentication (encrypted)
    auth_type = Column(String(50), default="none")
    encrypted_auth_config = Column(Text, nullable=True)

    # Request behavior
    timeout_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    retry_delay = Column(Float, default=1.0)
    retry_on_status = Column(JSON, nullable=True)

    # Response handling
    response_format = Column(String(50), default="auto")
    extract_path = Column(Text, nullable=True)
    success_status_codes = Column(JSON, nullable=True)

    # SSL/Redirect
    verify_ssl = Column(Boolean, default=True)
    follow_redirects = Column(Boolean, default=True)
    max_redirects = Column(Integer, default=10)

    # Status
    is_active = Column(Boolean, default=True)

    # Usage tracking
    usage_count = Column(BigInteger, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)

    # Connection health tracking
    last_connection_test = Column(DateTime(timezone=True), nullable=True)
    last_connection_status = Column(String(20), nullable=True)

    # Owner
    user_id = Column(String(255), nullable=True, index=True)

    # Sharing / visibility
    visible_to_groups = Column(JSONB, nullable=False, server_default="[]")
