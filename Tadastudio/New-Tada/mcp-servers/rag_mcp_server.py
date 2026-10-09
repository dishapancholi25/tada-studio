"""RAG MCP Server - Processes uploaded files with queries."""
import base64
import re
from fastmcp import FastMCP

mcp = FastMCP("RAG File Processor")


def log(msg: str):
    """Print log message with timestamp."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def decode_file_content(file_content: str) -> str:
    """
    Decode file content - handles both plain text and base64.

    Supports formats:
    - Plain text: returned as-is
    - Data URL: "data:application/pdf;base64,<content>"
    - Raw base64: "<base64 encoded string>"

    Returns:
        Decoded text content
    """
    if not file_content:
        return ""

    # Check for data URL format (e.g., "data:application/pdf;base64,...")
    if file_content.startswith("data:"):
        try:
            # Extract base64 part after comma
            base64_part = file_content.split(",", 1)[-1]
            decoded = base64.b64decode(base64_part).decode('utf-8', errors='ignore')
            log(f"    Decoded data URL format ({len(decoded)} chars)")
            return decoded
        except Exception as e:
            log(f"    Failed to decode data URL: {e}")
            return file_content

    # Check if it looks like raw base64 (no spaces, valid base64 chars, reasonable length)
    if len(file_content) > 100:
        # Base64 pattern: only alphanumeric, +, /, = and no newlines in content
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]+=*$')
        # Check first 1000 chars for base64 pattern (avoid checking huge strings)
        sample = file_content[:1000].replace('\n', '').replace('\r', '')
        if base64_pattern.match(sample):
            try:
                decoded = base64.b64decode(file_content).decode('utf-8', errors='ignore')
                # Sanity check - decoded should have readable content
                if decoded and len(decoded) > 0:
                    log(f"    Decoded raw base64 ({len(decoded)} chars)")
                    return decoded
            except Exception:
                pass  # Not valid base64, treat as plain text

    # Return as plain text
    return file_content


@mcp.tool()
def process_file(file_content: str, query: str, file_name: str = "uploaded_file") -> dict:
    """
    Process uploaded file content and search based on query.

    Args:
        file_content: The raw text content of the uploaded file (plain text or base64)
        query: The search query to run against the file
        file_name: Name of the file (optional)

    Returns:
        Search results from the file content
    """
    log(f">>> TOOL CALLED: process_file")
    log(f"    file_name: {file_name}")
    log(f"    query: {query}")
    log(f"    content_length: {len(file_content) if file_content else 0} chars")

    if not file_content:
        return {"status": "error", "message": "No file content provided"}

    if not query:
        return {"status": "error", "message": "No query provided"}

    # Decode content (handles both plain text and base64)
    file_content = decode_file_content(file_content)

    # Split content into lines for searching
    lines = file_content.strip().split('\n')
    query_lower = query.lower()

    # Find matching lines
    matching_lines = []
    for i, line in enumerate(lines):
        if query_lower in line.lower():
            matching_lines.append({
                "line_number": i + 1,
                "content": line.strip()
            })

    # Extract sections/records (split by ---)
    sections = file_content.split('---')
    matching_sections = []
    for section in sections:
        if query_lower in section.lower():
            matching_sections.append(section.strip())

    return {
        "status": "success",
        "file_name": file_name,
        "query": query,
        "total_lines": len(lines),
        "matching_lines_count": len(matching_lines),
        "matching_lines": matching_lines[:20],  # Return first 20 matches
        "matching_sections_count": len(matching_sections),
        "matching_sections": matching_sections[:5],  # Return first 5 matching sections
        "file_preview": file_content[:300] if len(file_content) > 300 else file_content
    }


@mcp.tool()
def extract_field(file_content: str, field_name: str) -> dict:
    """
    Extract specific field values from structured file content.

    Args:
        file_content: The raw text content of the uploaded file (plain text or base64)
        field_name: The field to extract (e.g., "Email", "Name", "Phone")

    Returns:
        All values found for the specified field
    """
    log(f">>> TOOL CALLED: extract_field")
    log(f"    field_name: {field_name}")
    log(f"    content_length: {len(file_content) if file_content else 0} chars")

    if not file_content:
        return {"status": "error", "message": "No file content provided"}

    if not field_name:
        return {"status": "error", "message": "No field name provided"}

    # Decode content (handles both plain text and base64)
    file_content = decode_file_content(file_content)

    lines = file_content.strip().split('\n')
    field_lower = field_name.lower()
    results = []

    for line in lines:
        line_lower = line.lower()
        # Check for patterns like "Field: Value" or "Field = Value"
        if field_lower + ":" in line_lower or field_lower + " :" in line_lower:
            # Extract value after colon
            parts = line.split(":", 1)
            if len(parts) == 2:
                results.append(parts[1].strip())
        elif field_lower + "=" in line_lower or field_lower + " =" in line_lower:
            parts = line.split("=", 1)
            if len(parts) == 2:
                results.append(parts[1].strip())

    return {
        "status": "success",
        "field_name": field_name,
        "values_found": len(results),
        "values": results
    }


@mcp.tool()
def summarize_file(file_content: str) -> dict:
    """
    Get a summary of the uploaded file content.

    Args:
        file_content: The raw text content of the uploaded file (plain text or base64)

    Returns:
        Summary statistics about the file
    """
    log(f">>> TOOL CALLED: summarize_file")
    log(f"    content_length: {len(file_content) if file_content else 0} chars")

    if not file_content:
        return {"status": "error", "message": "No file content provided"}

    # Decode content (handles both plain text and base64)
    file_content = decode_file_content(file_content)

    lines = file_content.strip().split('\n')
    sections = [s.strip() for s in file_content.split('---') if s.strip()]
    words = file_content.split()

    # Try to detect common fields
    common_fields = ["name", "email", "phone", "department", "role", "location", "skills"]
    detected_fields = []
    for field in common_fields:
        if field + ":" in file_content.lower():
            detected_fields.append(field.capitalize())

    return {
        "status": "success",
        "total_characters": len(file_content),
        "total_lines": len(lines),
        "total_words": len(words),
        "total_sections": len(sections),
        "detected_fields": detected_fields,
        "preview": file_content[:500] if len(file_content) > 500 else file_content
    }


if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "streamable-http"
    print(f"Starting RAG File Processor MCP Server")
    print(f"Transport: {transport}")
    print(f"Available tools: process_file, extract_field, summarize_file")
    mcp.run(transport=transport, host="0.0.0.0", port=8001)
