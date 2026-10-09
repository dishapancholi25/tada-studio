"""Response processing for HTTP request tool."""

import base64
import json
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union


logger = logging.getLogger(__name__)

_HEADER_KEYS = ("headers", "request_headers", "response_headers")


def strip_headers_key(data: Any) -> Any:
    """Recursively remove any headers-like key from response data.

    Prevents APIs that embed request/response headers in their body
    (e.g. echo-style test endpoints) from surfacing header data to the LLM.
    """
    if isinstance(data, dict):
        return {
            k: strip_headers_key(v)
            for k, v in data.items()
            if k.lower() not in _HEADER_KEYS
        }
    if isinstance(data, list):
        return [strip_headers_key(item) for item in data]
    return data


def detect_content_type(response_content: bytes, content_type_header: str) -> str:
    """Detect the actual content type of the response.

    Args:
        response_content: Raw response content
        content_type_header: Content-Type header value

    Returns:
        Detected content type (image, json, xml, text, binary)
    """
    content_type_lower = content_type_header.lower()

    # Check for images
    if (
        "image/" in content_type_lower
        or response_content[:4] == b"\x89PNG"
        or response_content[:2] == b"\xff\xd8"  # JPEG
    ):
        return "image"

    # Check for JSON
    if "application/json" in content_type_lower:
        return "json"

    # Check for XML
    if "xml" in content_type_lower:
        return "xml"

    # Check for text
    if "text/" in content_type_lower:
        return "text"

    return "binary"


def parse_json_response(response_text: str) -> Union[Dict, List, str]:
    """Parse JSON response.

    Args:
        response_text: Response text

    Returns:
        Parsed JSON or original text if parsing fails
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return response_text


def parse_xml_response(response_text: str) -> Union[Dict, str]:
    """Parse XML response.

    Args:
        response_text: Response text

    Returns:
        Simplified dict representation of XML or original text if parsing fails
    """
    try:
        root = ET.fromstring(response_text)
        # Convert XML to dict (simplified)
        return {root.tag: root.text or {child.tag: child.text for child in root}}
    except ET.ParseError:
        return response_text


def encode_binary_response(response_content: bytes) -> str:
    """Encode binary response as base64.

    Args:
        response_content: Raw binary content

    Returns:
        Base64 encoded string
    """
    return base64.b64encode(response_content).decode("ascii")


def extract_json_path(data: Any, path: str) -> Optional[Any]:
    """Extract value from JSON data using JSONPath-like syntax.

    Args:
        data: JSON data
        path: Path to extract (e.g., "data.results[0].name")

    Returns:
        Extracted value or None if path doesn't exist
    """
    if not path:
        return data

    path_parts = path.strip(".").split(".")
    extracted = data

    for part in path_parts:
        if isinstance(extracted, dict) and part in extracted:
            extracted = extracted[part]
        elif isinstance(extracted, list) and part.isdigit():
            extracted = extracted[int(part)]
        else:
            return None

    return extracted


def process_response(
    response,
    response_format: str,
    extract_path: str = "",
) -> tuple[Any, Dict[str, Any]]:
    """Process HTTP response based on format.

    Args:
        response: requests.Response object
        response_format: Desired format (auto, json, xml, binary)
        extract_path: JSONPath to extract from response

    Returns:
        Tuple of (response_data, result_metadata)
    """
    result_metadata = {}
    response_content_type = response.headers.get("content-type", "").lower()
    actual_content_type = detect_content_type(response.content, response_content_type)

    # Handle images
    if actual_content_type == "image":
        response_data = encode_binary_response(response.content)
        result_metadata["encoding"] = "base64"
        result_metadata["content_type"] = response_content_type
        result_metadata["image_size"] = len(response.content)
        return response_data, result_metadata

    # Handle explicitly requested binary format
    if response_format == "binary":
        response_data = encode_binary_response(response.content)
        result_metadata["encoding"] = "base64"
        return response_data, result_metadata

    # Handle XML
    if response_format == "xml" or (
        response_format == "auto" and actual_content_type == "xml"
    ):
        response_data = parse_xml_response(response.text)
        return strip_headers_key(response_data), result_metadata

    # Handle JSON
    if response_format == "json" or (
        response_format == "auto" and actual_content_type == "json"
    ):
        response_data = parse_json_response(response.text)

        # Apply JSONPath extraction if specified
        if extract_path and isinstance(response_data, (dict, list)):
            extracted = extract_json_path(response_data, extract_path)
            if extracted is not None:
                response_data = extracted
            else:
                result_metadata["extraction_note"] = (
                    f"Could not extract path '{extract_path}', returning full response"
                )

        return strip_headers_key(response_data), result_metadata

    # Default: return as text
    return response.text, result_metadata


def format_response_output(response_data: Any, result_metadata: Dict[str, Any]) -> str:
    """Format response data as string for output.

    Args:
        response_data: Processed response data
        result_metadata: Metadata about the response

    Returns:
        Formatted string output
    """
    # For structured data, return as formatted JSON
    if isinstance(response_data, (dict, list)):
        return json.dumps(response_data, indent=2)
    else:
        return str(response_data)


def create_error_response(status_code: int, error_text: str, error_msg: str) -> str:
    """Create formatted error response.

    Args:
        status_code: HTTP status code
        error_text: Raw error text
        error_msg: Formatted error message

    Returns:
        JSON formatted error response
    """
    return json.dumps(
        {
            "success": False,
            "status_code": status_code,
            "error": error_msg,
            "response": error_text[:1000],
        },
        indent=2,
    )


def create_success_response(
    status_code: int,
    url: str,
    elapsed: float,
    response_data: Any,
    result_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Create success response structure.

    Args:
        status_code: HTTP status code
        url: Final URL after redirects
        elapsed: Request elapsed time
        response_data: Processed response data
        result_metadata: Response metadata

    Returns:
        Success response dictionary
    """
    result = {
        "success": True,
        "status_code": status_code,
        "url": url,
        "elapsed": elapsed,
    }

    # Merge in any metadata
    result.update(result_metadata)

    return result
