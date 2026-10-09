"""Helper orchestrations for the combined library discovery view."""

from typing import Any, Dict, List, Optional

from backend.services.library.agent_service import AgentLibraryService
from backend.services.library.service import LibraryService


class LibraryDiscoveryService:
    """Aggregate workflows and agents for a single library request."""

    @staticmethod
    def list_items(
        search: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: Optional[int] = None,
        count_only: bool = False,
    ) -> Dict[str, Any]:
        """Return parallel agent + workflow collections honoring shared filters.

        Args:
            search: Search term to filter items
            category: Category to filter by
            complexity: Complexity level to filter by
            tags: Tags to filter by
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            limit: Maximum number of results
            count_only: If True, only return counts without full item data

        Returns:
            Dictionary with workflows, agents, and counts
        """

        if count_only:
            # Use optimized COUNT queries instead of loading full data
            workflow_count = LibraryService.count_templates(
                search=search,
                category=category,
                complexity=complexity,
                tags=tags,
            )
            agent_count = AgentLibraryService.count_agents(
                search=search,
                category=category,
                complexity=complexity,
                tags=tags,
            )
            return {
                "workflows": [],
                "agents": [],
                "counts": {"workflows": workflow_count, "agents": agent_count},
            }

        workflows = LibraryService.list_templates(
            search=search,
            category=category,
            complexity=complexity,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )
        agents = AgentLibraryService.list_agents(
            search=search,
            category=category,
            complexity=complexity,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )

        return {
            "workflows": workflows,
            "agents": agents,
            "counts": {"workflows": len(workflows), "agents": len(agents)},
        }
