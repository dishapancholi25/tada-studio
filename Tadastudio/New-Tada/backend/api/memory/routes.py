"""FastAPI routes for memory management.

This module defines all API endpoints for memory operations including
creating, retrieving, updating, and deleting agent memories.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import (
    require_execution_access,
    require_workflow_access_by_id,
)
from backend.services.config import get_logger
from backend.services.memory import MemoryError

from .dependencies import MemoryService
from .models import (
    AgentProfileResponse,
    ConversationHistoryResponse,
    MemoryClearResponse,
    MemoryCreateRequest,
    MemoryPruneResponse,
    MemoryResponse,
)

logger = get_logger("memory_api")

# Create router
router = APIRouter(
    prefix="/api/memory", tags=["memory"], dependencies=[Depends(require_active_user)]
)


async def _get_existing_agent_profile(
    agent_id: str,
    memory_service: MemoryService,
) -> Optional[dict]:
    """Load an existing profile for authorization checks."""
    return await memory_service.get_agent_profile(agent_id)


async def _require_agent_profile_workflow_access(
    current_user: Dict[str, Any],
    agent_id: str,
    memory_service: MemoryService,
) -> Optional[dict]:
    """Authorize profile-scoped memory access when no execution scope is supplied.

    Admins are allowed without requiring a profile lookup. Non-admin callers
    must be authorized against the workflow recorded on the stored profile.
    """
    if current_user.get("is_admin"):
        return None

    profile = await _get_existing_agent_profile(agent_id, memory_service)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent memory profile not found")

    require_workflow_access_by_id(current_user, profile["graph_id"])
    return profile


@router.post("/memories", response_model=MemoryResponse, dependencies=[Depends(require_scope("memory:*:write"))])
async def create_memory(
    memory: MemoryCreateRequest,
    memory_service: MemoryService,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new memory entry.

    Args:
        memory: Memory creation request
        memory_service: Injected memory service
        current_user: Authenticated user (injected)

    Returns:
        Created memory entry

    Raises:
        HTTPException: If memory creation fails or user lacks access to the
            referenced execution
    """
    try:
        # If the memory is tied to a workflow execution, verify the
        # authenticated user has access to that execution before storing.
        if memory.graph_execution_id:
            require_execution_access(current_user, memory.graph_execution_id)
        else:
            await _require_agent_profile_workflow_access(
                current_user, memory.agent_id, memory_service
            )

        created_memory = await memory_service.create_memory(
            agent_id=memory.agent_id,
            agent_name=memory.agent_name,
            memory_type=memory.memory_type,
            content=memory.content,
            graph_execution_id=memory.graph_execution_id,
            node_execution_id=memory.node_execution_id,
            importance_score=memory.importance_score,
        )

        return MemoryResponse(
            id=str(created_memory.id),
            agent_id=created_memory.agent_id,
            agent_name=created_memory.agent_name,
            memory_type=created_memory.memory_type,
            content=created_memory.content,
            importance_score=created_memory.importance_score,
            access_count=created_memory.access_count,
            is_active=created_memory.is_active,
            created_at=created_memory.created_at.isoformat(),
            last_accessed=created_memory.last_accessed.isoformat()
            if created_memory.last_accessed
            else None,
        )
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to create memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/memories", response_model=list[MemoryResponse], dependencies=[Depends(require_scope("memory:*:read"))])
async def get_agent_memories(
    agent_id: str,
    memory_service: MemoryService,
    memory_types: Optional[str] = Query(
        None, description="Comma-separated list of memory types to filter"
    ),
    limit: int = Query(10, ge=1, le=100, description="Maximum memories to return"),
    only_active: bool = Query(True, description="Only return active memories"),
    graph_execution_id: Optional[str] = Query(
        None, description="Filter by graph execution ID"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get memories for a specific agent.

    Args:
        agent_id: Agent identifier
        memory_service: Injected memory service
        memory_types: Optional comma-separated memory types
        limit: Maximum number of memories to return
        only_active: Whether to only return active memories
        graph_execution_id: Optional execution ID filter
        current_user: Authenticated user (injected)

    Returns:
        List of memory entries

    Raises:
        HTTPException: If retrieval fails or user lacks access to the
            referenced execution
    """
    try:
        if graph_execution_id:
            require_execution_access(current_user, graph_execution_id)
        else:
            await _require_agent_profile_workflow_access(
                current_user, agent_id, memory_service
            )

        memory_type_list = memory_types.split(",") if memory_types else None

        memories = await memory_service.get_agent_memories(
            agent_id=agent_id,
            memory_types=memory_type_list,
            limit=limit,
            only_active=only_active,
            graph_execution_id=graph_execution_id,
        )

        return [
            MemoryResponse(
                id=str(memory["id"]),
                agent_id=memory["agent_id"],
                agent_name=memory["agent_name"],
                memory_type=memory["memory_type"],
                content=memory["content"],
                importance_score=memory["importance_score"],
                access_count=memory["access_count"],
                is_active=memory["is_active"],
                created_at=memory["created_at"].isoformat()
                if hasattr(memory["created_at"], "isoformat")
                else str(memory["created_at"]),
                last_accessed=memory["last_accessed"].isoformat()
                if memory.get("last_accessed")
                and hasattr(memory["last_accessed"], "isoformat")
                else None,
            )
            for memory in memories
        ]
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to get agent memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/agents/{agent_id}/conversation-history",
    response_model=ConversationHistoryResponse,
    dependencies=[Depends(require_scope("memory:*:read"))],
)
async def get_conversation_history(
    agent_id: str,
    memory_service: MemoryService,
    graph_execution_id: Optional[str] = Query(
        None, description="Filter by graph execution ID"
    ),
    limit: int = Query(10, ge=1, le=100, description="Maximum history entries"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get conversation history for an agent.

    Args:
        agent_id: Agent identifier
        memory_service: Injected memory service
        graph_execution_id: Optional execution ID filter
        limit: Maximum number of history entries
        current_user: Authenticated user (injected)

    Returns:
        Conversation history

    Raises:
        HTTPException: If retrieval fails or user lacks access to the
            referenced execution
    """
    try:
        if graph_execution_id:
            require_execution_access(current_user, graph_execution_id)
        else:
            await _require_agent_profile_workflow_access(
                current_user, agent_id, memory_service
            )

        history = await memory_service.get_conversation_history(
            agent_id=agent_id, graph_execution_id=graph_execution_id, limit=limit
        )
        return ConversationHistoryResponse(agent_id=agent_id, history=history)
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/profile", response_model=AgentProfileResponse, dependencies=[Depends(require_scope("memory:*:read"))])
async def get_agent_profile(
    agent_id: str,
    agent_name: str,
    graph_id: str,
    memory_service: MemoryService,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get or create agent memory profile.

    Args:
        agent_id: Agent identifier
        agent_name: Agent name
        graph_id: Graph identifier
        memory_service: Injected memory service

    Returns:
        Agent memory profile

    Raises:
        HTTPException: If profile retrieval fails
    """
    try:
        existing_profile = await _get_existing_agent_profile(agent_id, memory_service)
        if existing_profile:
            stored_graph_id = existing_profile["graph_id"]
            if graph_id != stored_graph_id:
                raise HTTPException(
                    status_code=403,
                    detail="Caller-supplied graph_id does not match stored agent profile",
                )
            require_workflow_access_by_id(current_user, stored_graph_id)
        else:
            require_workflow_access_by_id(current_user, graph_id)

        profile = await memory_service.get_or_create_agent_profile(
            agent_id=agent_id, agent_name=agent_name, graph_id=graph_id
        )
        if profile["graph_id"] != graph_id:
            raise HTTPException(
                status_code=403,
                detail="Caller-supplied graph_id does not match stored agent profile",
            )

        return AgentProfileResponse(
            id=str(profile["id"]),
            agent_id=profile["agent_id"],
            agent_name=profile["agent_name"],
            graph_id=profile["graph_id"],
            memory_window_size=profile["memory_window_size"],
            summarization_threshold=profile["summarization_threshold"],
            memory_retention_days=profile["memory_retention_days"],
            total_conversations=profile["total_conversations"],
            total_messages=profile["total_messages"],
            last_interaction=profile["last_interaction"].isoformat()
            if profile.get("last_interaction")
            else None,
        )
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to get agent profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/prune-memories", response_model=MemoryPruneResponse, dependencies=[Depends(require_scope("memory:*:write"))])
async def prune_agent_memories(
    agent_id: str,
    memory_service: MemoryService,
    retention_days: int = Query(30, ge=1, description="Days to retain memories"),
    graph_execution_id: str = Query(
        ..., description="Execution scope for authorization"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Prune old memories for an agent.

    Args:
        agent_id: Agent identifier
        memory_service: Injected memory service
        retention_days: Number of days to retain memories

    Returns:
        Pruning result

    Raises:
        HTTPException: If pruning fails
    """
    try:
        require_execution_access(current_user, graph_execution_id)

        count = await memory_service.prune_old_memories(
            agent_id,
            retention_days,
            graph_execution_id,
        )
        return MemoryPruneResponse(
            message=f"Successfully pruned {count} old memories for agent {agent_id}",
            count=count,
        )
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to prune memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}/memories", response_model=MemoryClearResponse, dependencies=[Depends(require_scope("memory:*:write"))])
async def clear_agent_memory(
    agent_id: str,
    memory_service: MemoryService,
    graph_execution_id: Optional[str] = Query(
        None, description="Filter by graph execution ID"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Clear all memories for an agent.

    Args:
        agent_id: Agent identifier
        memory_service: Injected memory service
        graph_execution_id: Optional execution ID filter

    Returns:
        Clearing result

    Raises:
        HTTPException: If clearing fails
    """
    try:
        if graph_execution_id:
            require_execution_access(current_user, graph_execution_id)
        else:
            await _require_agent_profile_workflow_access(
                current_user, agent_id, memory_service
            )

        count = await memory_service.clear_agent_memory(agent_id, graph_execution_id)
        return MemoryClearResponse(
            message=f"Successfully cleared {count} memories for agent {agent_id}",
            count=count,
        )
    except MemoryError as e:
        logger.error(f"[MEMORY-API] Memory error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MEMORY-API] Failed to clear memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
