"""Output extraction utilities for HTTP execution API.

This module provides functions to extract and format execution outputs from
completed workflow executions, handling different node types and output formats.
"""

import json
import re
from typing import Any, Dict, List, Optional

from backend.services.config import get_logger


logger = get_logger(__name__)


def _resolve_document_file_url(
    item: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Resolve a user-facing file URL for document search results.

    Priority:
    1. Construct a stable PAT-authenticated view URL from document_id
       (``/api/pat/documents/{document_id}/view``). This route bypasses the
       OAuth2-Proxy session requirement at the Ingress level and is validated
       by the backend via the caller's PAT (Personal Access Token), so
       external/HTTP-triggered clients holding a PAT can open it directly.
       Requesting this endpoint returns a JSON payload containing a
       freshly-minted, short-lived blob URL (default 60m TTL); a new URL is
       generated on each request so expired links can be refreshed by simply
       re-requesting this endpoint.
    2. Explicit file_url already provided by upstream output.
    3. Fallback to source_location.
    """
    item = item or {}
    metadata = metadata or {}

    document_id = item.get("document_id") or metadata.get("document_id")
    if document_id:
        return f"/api/pat/documents/{document_id}/view"

    explicit = item.get("file_url") or metadata.get("file_url")
    if explicit:
        return explicit

    return item.get("source_location") or metadata.get("source_location")


def _extract_page_field(metadata: Dict[str, Any]) -> Optional[Any]:
    """Extract page number(s) from document chunk metadata.

    Chunks that fit entirely within one page carry a single integer ``page``.
    Chunks produced by :class:`PageBoundaryTracker` that span a page boundary
    additionally carry ``spans_pages=True`` plus a ``pages`` list (and/or
    ``page_start``/``page_end``) identifying every page the chunk overlaps.
    For those chunks we surface the full list of page numbers instead of
    silently dropping the information.

    Args:
        metadata: Document chunk metadata dictionary

    Returns:
        - int: single page number for single-page chunks
        - List[int]: page numbers for chunks spanning multiple pages
        - None: no valid page information available
    """
    if metadata.get("spans_pages"):
        pages_value = metadata.get("pages", metadata.get("Pages"))
        if isinstance(pages_value, list):
            pages_list = [p for p in pages_value if isinstance(p, int)]
            if pages_list:
                return pages_list

        # Fall back to reconstructing the range from page_start/page_end
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        if isinstance(page_start, int) and isinstance(page_end, int):
            return list(range(page_start, page_end + 1))

    page_value = metadata.get("page", metadata.get("Page"))
    return page_value if isinstance(page_value, int) else None


def _parse_json_document_results(payload: Any) -> List[Dict[str, Any]]:
    """Parse document search results from JSON/list payloads.

    Supports list payloads containing either:
    - {content, metadata}
    - {text, metadata}
    """
    if payload is None:
        return []

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return []

    if not isinstance(payload, list):
        return []

    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            continue

        metadata = item.get("metadata", {}) or {}
        page_num = _extract_page_field(metadata)

        relevance = metadata.get("relevance")
        if relevance is None:
            relevance = metadata.get("score", metadata.get("Relevance"))

        results.append(
            {
                "content": item.get("content") or item.get("text") or "",
                "metadata": {
                    "page": page_num,
                    "relevance": relevance,
                    "confidence": metadata.get("confidence"),
                    "source": item.get("source")
                    or metadata.get("source")
                    or f"Document {idx + 1}",
                    "file_url": _resolve_document_file_url(item, metadata),
                },
                "isStructured": True,
            }
        )

    return [r for r in results if r.get("content")]


def _parse_page_token(token: Optional[str]) -> Optional[Any]:
    """Parse a "Page"/"Pages" reference token into an int or list of ints.

    Args:
        token: Raw captured token, e.g. ``"3"`` (single page) or ``"1-2"``
            (range emitted for chunks spanning multiple pages).

    Returns:
        - int for a single page number
        - List[int] for a page range (e.g. "1-2" -> [1, 2])
        - None if token is empty/unparsable
    """
    if not token:
        return None

    if "-" in token:
        start_str, _, end_str = token.partition("-")
        try:
            start, end = int(start_str), int(end_str)
        except ValueError:
            return None
        if end < start:
            return [start]
        return list(range(start, end + 1))

    try:
        return int(token)
    except ValueError:
        return None


def _parse_formatted_document_results(text: str) -> List[Dict[str, Any]]:
    """Parse document search results from structured markdown output."""
    if not isinstance(text, str):
        return []

    context_match = re.search(
        r"## Retrieved Context\n+([\s\S]*?)(?=\n## References|$)",
        text,
    )
    if not context_match:
        return []

    references_match = re.search(r"## References\n+([\s\S]*?)(?=\n## |$)", text)
    references: Dict[str, Dict[str, Any]] = {}

    if references_match:
        for line in references_match.group(1).strip().split("\n"):
            # "Page N" is used for single-page chunks; "Pages N-M" is used for
            # chunks whose text spans multiple pages (see
            # StructuredFormatter._build_references / format_page_info_structured).
            # Match both and capture the full "N" or "N-M" token so multi-page
            # spans aren't silently dropped.
            ref_match = re.match(
                r"\[(\d+)\]\s+([^,]+)(?:,\s*Pages?\s+([\d]+(?:-[\d]+)?))?(?:,\s*Chunk\s+\d+)?(?:,\s*Score:\s*([\d.]+))?(?:,\s*(?:URL|Source Location):\s*(\S+))?",
                line,
            )
            if not ref_match:
                continue
            references[ref_match.group(1)] = {
                "source": ref_match.group(2).strip(),
                "page": _parse_page_token(ref_match.group(3)),
                "score": float(ref_match.group(4)) if ref_match.group(4) else None,
                "source_location": ref_match.group(5) if ref_match.group(5) else None,
            }

    chunks = re.split(r"(?=\[\d+(?:\.\d+)?\])", context_match.group(1))
    results: List[Dict[str, Any]] = []

    for chunk in chunks:
        if not chunk.strip():
            continue

        chunk_match = re.match(r"^\[(\d+)(?:\.(\d+))?\]\s*([\s\S]+)$", chunk.strip())
        if not chunk_match:
            continue

        ref_num = chunk_match.group(1)
        content = chunk_match.group(3).strip()

        confidence = None
        confidence_match = re.search(r"\s*\*Confidence:\s*(\d+)%\*", content)
        if confidence_match:
            confidence = int(confidence_match.group(1)) / 100
            content = content.replace(confidence_match.group(0), "").strip()

        ref = references.get(ref_num, {})
        results.append(
            {
                "content": content,
                "metadata": {
                    "page": ref.get("page"),
                    "relevance": ref.get("score") if ref.get("score") is not None else confidence,
                    "confidence": confidence,
                    "source": ref.get("source"),
                    "file_url": _resolve_document_file_url({}, ref),
                },
                "isStructured": True,
            }
        )

    return [r for r in results if r.get("content")]


def _extract_document_search_results(
    node_executions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Extract normalized document search results from DOCUMENT_SEARCH nodes."""
    normalized_results: List[Dict[str, Any]] = []

    for node_exec in node_executions:
        if node_exec.get("node_type") != "DOCUMENT_SEARCH":
            continue

        output_data = node_exec.get("output_data")
        if not output_data:
            continue

        candidates: List[Any] = []
        if isinstance(output_data, dict):
            for key in ("result", "results", "output", "response"):
                if key in output_data:
                    candidates.append(output_data.get(key))
            candidates.append(output_data)
        else:
            candidates.append(output_data)

        for candidate in candidates:
            parsed = _parse_json_document_results(candidate)
            logger.info("[HTTP-EXEC] Parsed %d document search results from node %s", len(parsed), node_exec.get("node_id"))
            if not parsed and isinstance(candidate, str):
                parsed = _parse_formatted_document_results(candidate)
                logger.info("[HTTP-EXEC] Parsed %d document search results from formatted text in node %s", len(parsed), node_exec.get("node_id"))

            if parsed:
                normalized_results.extend(parsed)
                break

    return normalized_results


def _attach_document_search_results(
    output: Any,
    document_search_results: List[Dict[str, Any]],
) -> Any:
    """Attach document search results to output while preserving compatibility."""
    if not document_search_results:
        return output

    if isinstance(output, dict):
        if "document_search_results" not in output:
            enriched_output = dict(output)
            enriched_output["document_search_results"] = document_search_results
            return enriched_output
        return output

    return {
        "result": output,
        "document_search_results": document_search_results,
    }


def extract_end_node_output(node_executions: list[Dict[str, Any]]) -> Optional[Any]:
    """Extract output from the END node if present.

    The END node contains the final structured output configured by the user.
    This function finds the END node and extracts its output data.

    Args:
        node_executions: List of node execution dictionaries from ExecutionHistoryService

    Returns:
        END node output if found, None otherwise

    Example:
        >>> executions = [
        ...     {"node_type": "START", "output_data": {"message": "start"}},
        ...     {"node_type": "END", "output_data": {"result": "success"}}
        ... ]
        >>> output = extract_end_node_output(executions)
        >>> print(output)  # {"result": "success"}
    """
    for node_exec in node_executions:
        if node_exec.get("node_type") == "END" and node_exec.get("output_data"):
            output = node_exec["output_data"]
            logger.debug(f"[HTTP-EXEC] Found END node output: {type(output)}")

            # Check if this is a configured END node output
            if isinstance(output, dict):
                # If it has execution_id, data, or outputs, it's a configured output
                if any(key in output for key in ["execution_id", "data", "outputs"]):
                    logger.info(
                        "[HTTP-EXEC] Returning configured END node output structure"
                    )
                    return output
                # Legacy format with 'results' key
                elif "results" in output:
                    logger.info("[HTTP-EXEC] Returning legacy END node results")
                    return output["results"]

            # Return raw output if not in expected format
            return output

    logger.debug("[HTTP-EXEC] No END node found in execution")
    return None


def extract_last_completed_output(
    node_executions: list[Dict[str, Any]],
) -> Optional[Any]:
    """Extract output from the last completed node.

    When no END node is present, this function finds the most recent completed node
    and extracts its output. This is a fallback mechanism for workflows without
    explicit END nodes.

    Args:
        node_executions: List of node execution dictionaries from ExecutionHistoryService

    Returns:
        Last completed node output if found, None otherwise

    Example:
        >>> executions = [
        ...     {"node_type": "AGENT", "status": "completed", "output_data": {...}, "end_time": "2024-01-01T10:00:00"},
        ...     {"node_type": "TOOL", "status": "completed", "output_data": {...}, "end_time": "2024-01-01T10:01:00"}
        ... ]
        >>> output = extract_last_completed_output(executions)
        >>> # Returns output from TOOL node (latest)
    """
    # Filter to completed nodes with output
    completed_nodes = [
        node
        for node in node_executions
        if node.get("status") == "completed" and node.get("output_data")
    ]

    if not completed_nodes:
        logger.debug("[HTTP-EXEC] No completed nodes with output found")
        return None

    # Sort by end_time to get the latest
    try:
        last_node = sorted(completed_nodes, key=lambda x: x.get("end_time", ""))[-1]
        output = last_node["output_data"]

        logger.debug(
            f"[HTTP-EXEC] Found last completed node: {last_node.get('node_type')}"
        )

        # Extract response if it's an agent node
        if isinstance(output, dict) and "response" in output:
            logger.info("[HTTP-EXEC] Extracting response from agent node")
            return {"result": output["response"]}

        return output
    except (IndexError, KeyError) as e:
        logger.warning(f"[HTTP-EXEC] Failed to extract last completed output: {e}")
        return None


def extract_execution_output(execution_data: Optional[Dict[str, Any]]) -> Optional[Any]:
    """Extract execution output from execution data.

    This is the main entry point for output extraction. It tries to find output
    from the END node first, then falls back to the last completed node.

    Args:
        execution_data: Execution data dictionary from ExecutionHistoryService.get_graph_execution_dict()

    Returns:
        Extracted output if found, None otherwise

    Example:
        >>> from backend.services.execution.history import ExecutionHistoryService
        >>> execution_data = ExecutionHistoryService.get_graph_execution_dict(123)
        >>> output = extract_execution_output(execution_data)
        >>> if output:
        ...     print(f"Execution result: {output}")
    """
    if not execution_data:
        logger.warning("[HTTP-EXEC] No execution data provided for output extraction")
        return None

    node_executions = execution_data.get("node_executions")
    if not node_executions:
        logger.warning("[HTTP-EXEC] No node executions found in execution data")
        return None

    logger.debug(
        f"[HTTP-EXEC] Extracting output from {len(node_executions)} node executions"
    )

    document_search_results = _extract_document_search_results(node_executions)

    # Try END node first
    end_output = extract_end_node_output(node_executions)
    if end_output is not None:
        return _attach_document_search_results(end_output, document_search_results)

    # Fall back to last completed node
    last_output = extract_last_completed_output(node_executions)
    if last_output is not None:
        return _attach_document_search_results(last_output, document_search_results)

    # As a final fallback, return only normalized document search results when available.
    if document_search_results:
        return {"document_search_results": document_search_results}

    logger.warning("[HTTP-EXEC] Could not extract any output from execution")
    return None


def format_execution_response(
    execution_id: str,
    status: str,
    output: Optional[Any] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Format a standardized execution response.

    Args:
        execution_id: Execution identifier
        status: Execution status (completed, failed, etc.)
        output: Optional execution output
        message: Optional status message

    Returns:
        Formatted response dictionary

    Example:
        >>> response = format_execution_response(
        ...     execution_id="exec_123",
        ...     status="completed",
        ...     output={"result": "success"}
        ... )
        >>> print(response)
        {'success': True, 'execution_id': 'exec_123', 'status': 'completed', 'output': {...}}
    """
    response = {
        "success": status != "failed",
        "execution_id": execution_id,
        "status": status,
    }

    if output is not None:
        response["output"] = output

    if message is not None:
        response["message"] = message

    return response
