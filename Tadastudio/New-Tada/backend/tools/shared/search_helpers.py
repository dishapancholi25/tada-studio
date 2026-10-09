"""Shared search helpers for Microsoft Graph Search API.

Used by both SharePoint and OneDrive MCP servers for building KQL queries
and parsing /search/query responses.
"""

from typing import Any, Dict, Tuple


def build_kql_query(
    query: str,
    file_types: str = "",
    author: str = "",
    date_from: str = "",
    date_to: str = "",
    path: str = "",
) -> str:
    """Build a KQL query string from convenience filter parameters.

    The base ``query`` is already a valid KQL expression (callers can use raw
    KQL syntax directly).  The helper parameters append additional KQL
    predicates so callers don't need to know the syntax.
    """
    parts = [query]

    if file_types:
        type_clauses = " OR ".join(
            f"filetype:{ft.strip()}" for ft in file_types.split(",") if ft.strip()
        )
        if type_clauses:
            parts.append(f"({type_clauses})")

    if author:
        parts.append(f'author:"{author}"')

    if date_from:
        parts.append(f"lastModifiedTime>={date_from}")

    if date_to:
        parts.append(f"lastModifiedTime<={date_to}")

    if path:
        parts.append(f'path:"{path}"')

    return " ".join(parts)


def parse_search_hits(
    data: dict, *, include_summary: bool = True
) -> Tuple[list, int, bool]:
    """Parse Microsoft Graph Search API response into a flat results list.

    Returns ``(results, total, more_results_available)``.
    """
    results = []
    total = 0
    more_available = False

    for response in data.get("value", []):
        for hit_container in response.get("hitsContainers", []):
            total += hit_container.get("total", 0)
            more_available = more_available or hit_container.get(
                "moreResultsAvailable", False
            )

            for hit in hit_container.get("hits", []):
                resource = hit.get("resource", {})
                parent_ref = resource.get("parentReference", {})

                item: Dict[str, Any] = {
                    "id": resource.get("id", ""),
                    "name": resource.get("name", ""),
                    "url": resource.get("webUrl", ""),
                    "size": resource.get("size", 0),
                    "last_modified": resource.get("lastModifiedDateTime", ""),
                    "created_by": (
                        resource.get("createdBy", {})
                        .get("user", {})
                        .get("displayName", "")
                    ),
                    "site_id": parent_ref.get("siteId", ""),
                    "drive_id": parent_ref.get("driveId", ""),
                }

                if include_summary:
                    summary = hit.get("hitHighlightedSummary") or hit.get("summary", "")
                    if summary:
                        item["snippet"] = summary

                results.append(item)

    return results, total, more_available


def extract_aggregations(data: dict) -> Dict[str, Any]:
    """Extract facets/aggregations from a Graph Search API response."""
    facets: Dict[str, Any] = {}
    for response in data.get("value", []):
        for hit_container in response.get("hitsContainers", []):
            for agg in hit_container.get("aggregations", []):
                field_name = agg.get("field", "")
                buckets = [
                    {"value": b.get("key", ""), "count": b.get("count", 0)}
                    for b in agg.get("buckets", [])
                    if b.get("count", 0) > 0
                ]
                if buckets:
                    facets[field_name] = buckets
    return facets
