"""URL configuration utilities."""

import os


def get_api_base_url() -> str:
    """
    Get the dynamic API base URL for the backend service.

    Checks environment variables in order of preference:
    1. API_BASE_URL (explicit override)
    2. BACKEND_URL (common deployment variable)
    3. Constructed from HOST and PORT
    4. Default to localhost:8000

    Returns:
        str: The base URL for the API (e.g., 'https://nexusagent-be.azurewebsites.net' or 'http://localhost:8000')
    """
    # Check for explicit API base URL override
    base_url = os.getenv("API_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    # Check for backend URL (common in deployments)
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        return backend_url.rstrip("/")

    # Construct from host and port
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")

    # Determine protocol
    if host == "localhost" or host.startswith("127."):
        protocol = "http"
    else:
        protocol = (
            "https" if os.getenv("USE_HTTPS", "false").lower() == "true" else "http"
        )

    return f"{protocol}://{host}:{port}"


def get_endpoint_url(path: str) -> str:
    """
    Get a complete endpoint URL by combining the base URL with a path.

    Args:
        path: The API path (e.g., '/api/http-execution/trigger/my-workflow')

    Returns:
        str: Complete URL
    """
    base_url = get_api_base_url()
    if not path.startswith("/"):
        path = "/" + path
    return f"{base_url}{path}"
