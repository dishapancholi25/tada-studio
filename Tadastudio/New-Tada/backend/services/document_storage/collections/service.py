"""Collection management service."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from ..config import LOG_PREFIX
from ..models import CollectionInfo
from .repository import CollectionRepository
from ...groups.service import GroupService


logger = logging.getLogger(__name__)


def _get_default_embedding_deployment_id() -> Optional[str]:
    """Return the default embedding deployment ID from the model deployments table.

    Queries for the deployment marked ``is_default=True`` with ``model_type='embedding'``.
    Returns ``None`` if no default is configured or the lookup fails.
    """
    try:
        from ...model_deployment.service import ModelDeploymentService

        default = ModelDeploymentService().get_default_deployment("embedding")
        if default:
            logger.debug(
                "%s Default embedding deployment resolved: %s (%s)",
                LOG_PREFIX,
                default["id"],
                default.get("name", ""),
            )
            return default["id"]
    except Exception as exc:
        logger.warning(
            "%s Failed to resolve default embedding deployment: %s", LOG_PREFIX, exc
        )
    return None


def _apply_default_embedding(
    collection: CollectionInfo, default_id: Optional[str]
) -> CollectionInfo:
    """Return *collection* with ``embedding_deployment_id`` set to *default_id* if not already set."""
    if not collection.embedding_deployment_id and default_id:
        collection.embedding_deployment_id = default_id
    return collection


class CollectionService:
    """Service for managing document collections."""

    def __init__(self):
        """Initialize collection service."""
        self.repository = CollectionRepository()
        self.group_service = GroupService()

    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        visible_to_groups: Optional[List[str]] = None,
    ) -> CollectionInfo:
        """Create a new document collection.

        Args:
            name: Collection name
            description: Optional description
            user_id: Optional user ID
            visible_to_groups: List of group names that can access this collection

        Returns:
            CollectionInfo for the created collection
        """
        collection_id = str(uuid.uuid4())

        if visible_to_groups is None:
            visible_to_groups = []

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            self.group_service.validate_groups_exist(groups_to_validate)

        logger.info(
            f"{LOG_PREFIX} Creating collection: {name} (ID: {collection_id}) "
            f"with visibility {visible_to_groups} by user {user_id}"
        )

        collection = self.repository.create_collection(
            collection_id=collection_id,
            name=name,
            description=description,
            user_id=user_id,
            visible_to_groups=visible_to_groups,
        )

        return collection

    def get_collections(
        self,
        user_id: str,
        filter_type: str = "owned",
    ) -> List[CollectionInfo]:
        """Get collections with group-based access filtering.

        Args:
            user_id: Current user ID
            filter_type: 'owned', 'shared', or 'all'

        Returns:
            List of CollectionInfo objects with visibility and access info
        """
        logger.debug(
            f"{LOG_PREFIX} Getting collections for user {user_id}"
            f" with filter_type={filter_type}"
        )

        # Get user groups for access filtering
        user_groups = self.group_service.get_user_groups(user_id)

        results = self.repository.get_collections(
            user_id=user_id,
            user_groups=user_groups,
            filter_type=filter_type,
        )

        # is_read_only is already set by the repository based on ownership
        # For 'owned' filter, force is_read_only=False
        if filter_type == "owned":
            for col in results:
                col.is_read_only = False

        # Enrich any collection that has no stored embedding with the system default.
        # Fetch the default once to avoid N redundant DB calls.
        if any(not col.embedding_deployment_id for col in results):
            default_id = _get_default_embedding_deployment_id()
            if default_id:
                for col in results:
                    _apply_default_embedding(col, default_id)

        logger.info(f"{LOG_PREFIX} Retrieved {len(results)} collections")

        return results

    def get_collection(self, collection_id: str) -> Optional[CollectionInfo]:
        """Get a specific collection.

        Args:
            collection_id: Collection ID

        Returns:
            CollectionInfo or None if not found.  ``embedding_deployment_id`` is
            always populated: if the collection has no stored value the system
            default embedding deployment (``is_default=True``) is substituted.
        """
        collection = self.repository.get_collection(collection_id)
        if collection and not collection.embedding_deployment_id:
            _apply_default_embedding(collection, _get_default_embedding_deployment_id())
        return collection

    def set_embedding_deployment_id(
        self, collection_id: str, embedding_deployment_id: str
    ) -> bool:
        """Set the embedding deployment for a collection (called on first upload).

        Args:
            collection_id: Collection ID
            embedding_deployment_id: Deployment ID from model_deployments table

        Returns:
            True if updated
        """
        return self.repository.set_embedding_deployment_id(
            collection_id, embedding_deployment_id
        )

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and all its documents.

        Args:
            collection_id: Collection ID to delete

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"{LOG_PREFIX} Deleting collection: {collection_id}")

        success = self.repository.delete_collection(collection_id)

        if success:
            logger.info(f"{LOG_PREFIX} Collection {collection_id} deleted successfully")
        else:
            logger.warning(f"{LOG_PREFIX} Collection {collection_id} not found")

        return success

    def update_collection(
        self,
        collection_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        embedding_deployment_id: Optional[str] = None,
    ) -> "CollectionInfo":
        """Update collection name, description, and/or embedding model.

        Args:
            collection_id: Collection ID
            user_id: ID of user making the change (must be owner)
            name: New name (if provided)
            description: New description (if provided)
            embedding_deployment_id: New embedding deployment ID (if provided)

        Returns:
            Updated CollectionInfo

        Raises:
            PermissionError: If user is not the collection owner
            ValueError: If collection not found or name conflict
        """
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection not found: {collection_id}")

        if collection.user_id != user_id:
            raise PermissionError("Only the creator can edit this collection")

        updated = self.repository.update_collection(
            collection_id,
            user_id,
            name=name,
            description=description,
            embedding_deployment_id=embedding_deployment_id,
        )

        if not updated:
            raise ValueError(f"Failed to update collection: {collection_id}")

        logger.info(
            f"{LOG_PREFIX} Collection '{collection_id}' updated by user {user_id}"
        )

        return updated

    def update_visibility(
        self,
        collection_id: str,
        visible_to_groups: List[str],
        user_id: str,
    ) -> CollectionInfo:
        """Update collection visibility groups.

        Args:
            collection_id: Collection ID
            visible_to_groups: New list of group names
            user_id: ID of user making the change

        Returns:
            Updated CollectionInfo

        Raises:
            PermissionError: If user is not the collection owner
            ValueError: If groups don't exist
        """
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection not found: {collection_id}")

        if collection.user_id != user_id:
            raise PermissionError("Only the creator can change visibility")

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            self.group_service.validate_groups_exist(groups_to_validate)

        success = self.repository.update_collection_visibility(
            collection_id, visible_to_groups, user_id
        )

        if not success:
            raise ValueError(
                f"Failed to update visibility for collection: {collection_id}"
            )

        logger.info(
            f"{LOG_PREFIX} Collection '{collection.name}' visibility changed to "
            f"{visible_to_groups} by user {user_id}"
        )

        # Return updated collection info
        updated = self.repository.get_collection(collection_id)
        if not updated:
            raise ValueError(f"Collection not found after update: {collection_id}")
        return updated

    def check_collection_access(self, collection_id: str, user_id: str) -> bool:
        """Check if a user has access to a collection.

        Args:
            collection_id: Collection ID
            user_id: User ID to check

        Returns:
            True if user has access
        """
        user_groups = self.group_service.get_user_groups(user_id)
        return self.repository.check_collection_access(
            collection_id, user_id, user_groups
        )

    def check_collection_references(self, collection_id: str) -> Dict[str, Any]:
        """Check documents, chunks, and workflows referencing a collection.

        Args:
            collection_id: Collection ID

        Returns:
            Dict with document_count, chunk_count, documents, workflow_count, workflows
        """
        try:
            result = self.repository.get_collection_references(collection_id)
            # Ensure we're returning a dict
            if not isinstance(result, dict):
                logger.error(
                    f"Repository returned non-dict: {type(result)}, value: {result}"
                )
                return {
                    "document_count": 0,
                    "chunk_count": 0,
                    "documents": [],
                    "workflow_count": 0,
                    "workflows": [],
                }
            return result
        except Exception as e:
            logger.error(f"Error checking collection references: {e}", exc_info=True)
            # Return empty references on error
            return {
                "document_count": 0,
                "chunk_count": 0,
                "documents": [],
                "workflow_count": 0,
                "workflows": [],
            }
