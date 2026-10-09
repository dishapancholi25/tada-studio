"""API routes for node output schemas."""

from fastapi import APIRouter, HTTPException

from backend.services.io.schemas import get_all_schemas, get_output_schema

router = APIRouter(prefix="/api/schemas", tags=["schemas"])


@router.get("/outputs")
def list_output_schemas() -> dict:
    """Return all node output schemas for frontend consumption."""
    return {
        node_type: schema.model_dump()
        for node_type, schema in get_all_schemas().items()
    }


@router.get("/outputs/{node_type}")
def get_node_output_schema(node_type: str) -> dict:
    """Return output schema for a specific node type."""
    schema = get_output_schema(node_type)
    if not schema:
        raise HTTPException(
            status_code=404, detail=f"No schema registered for {node_type}"
        )
    return schema.model_dump()
