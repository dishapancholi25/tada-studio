"""Node versioning service.

Computes per-node config hashes and maintains the node_version_index table
so that feedback and evaluation results can be associated with specific
node configurations.
"""

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.models.workflows.node_version_index import NodeVersionIndex
from backend.services.database import get_db

logger = logging.getLogger(__name__)
LOG_PREFIX = "[NODE-VERSIONING]"


class NodeVersioningService:
    """Manages node-level version tracking across graph definition versions."""

    @staticmethod
    def compute_node_hash(node_config: Dict[str, Any]) -> str:
        """Compute a stable SHA256 hash of a node's configuration.

        The hash is computed from a canonicalised JSON representation
        (sorted keys, no whitespace) so that semantically identical
        configs always produce the same hash.

        Args:
            node_config: The node configuration dict from the graph definition.

        Returns:
            64-character hex SHA256 digest.
        """
        canonical = json.dumps(node_config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_nodes_from_definition(
        definition_json: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract the list of node dicts from a graph definition JSON blob.

        Args:
            definition_json: The full graph definition JSON.

        Returns:
            List of node configuration dicts.
        """
        nodes = definition_json.get("nodes", [])
        if isinstance(nodes, list):
            return nodes
        return []

    def index_graph_definition(
        self,
        graph_definition_id: str,
        workflow_id: Optional[str],
        definition_json: Dict[str, Any],
        parent_graph_definition_id: Optional[str] = None,
    ) -> List[NodeVersionIndex]:
        """Compute node hashes for a graph definition and persist them.

        For each node in the definition, if the parent graph definition had
        the same node_id with the same config_hash, the node_version is
        carried forward. If the hash changed (or the node is new), the
        node_version is incremented.

        Args:
            graph_definition_id: ID of the new graph definition.
            workflow_id: Parent workflow ID.
            definition_json: The graph definition JSON blob.
            parent_graph_definition_id: ID of the previous graph definition
                version (used to determine version increments).

        Returns:
            List of created NodeVersionIndex entries.
        """
        nodes = self.extract_nodes_from_definition(definition_json)
        if not nodes:
            return []

        # Load parent version's node hashes for comparison
        parent_index: Dict[str, Dict[str, Any]] = {}
        if parent_graph_definition_id:
            parent_index = self._load_parent_index(parent_graph_definition_id)

        created: List[NodeVersionIndex] = []
        with get_db() as db:
            for node in nodes:
                node_id = node.get("id")
                if not node_id:
                    continue

                node_type = node.get("type", "UNKNOWN")
                node_name = node.get("name", node_id)
                config_hash = self.compute_node_hash(node)

                # Determine version number
                parent_entry = parent_index.get(node_id)
                if parent_entry and parent_entry["config_hash"] == config_hash:
                    # Config unchanged — carry forward version
                    node_version = parent_entry["node_version"]
                elif parent_entry:
                    # Config changed — increment version
                    node_version = parent_entry["node_version"] + 1
                else:
                    # New node — start at version 1
                    node_version = 1

                entry = NodeVersionIndex(
                    id=str(uuid.uuid4()),
                    graph_definition_id=graph_definition_id,
                    workflow_id=workflow_id,
                    node_id=node_id,
                    node_type=node_type,
                    node_name=node_name,
                    config_hash=config_hash,
                    config_json=node,
                    node_version=node_version,
                )
                db.add(entry)
                created.append(entry)

            db.commit()
            logger.info(
                "%s Indexed %d nodes for graph definition %s",
                LOG_PREFIX,
                len(created),
                graph_definition_id,
            )

        return created

    def get_node_hash(
        self,
        graph_definition_id: str,
        node_id: str,
    ) -> Optional[str]:
        """Look up the config_hash for a specific node in a graph definition.

        Args:
            graph_definition_id: The graph definition to look in.
            node_id: The node ID within the graph.

        Returns:
            The config_hash string, or None if not found.
        """
        with get_db() as db:
            entry = (
                db.query(NodeVersionIndex)
                .filter(
                    NodeVersionIndex.graph_definition_id == graph_definition_id,
                    NodeVersionIndex.node_id == node_id,
                )
                .first()
            )
            return entry.config_hash if entry else None

    def get_node_history(
        self,
        workflow_id: str,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """Get the version history for a specific node across all graph versions.

        Args:
            workflow_id: The parent workflow ID.
            node_id: The node ID to get history for.

        Returns:
            List of version entries ordered by graph definition creation time.
        """
        with get_db() as db:
            entries = (
                db.query(NodeVersionIndex)
                .filter(
                    NodeVersionIndex.workflow_id == workflow_id,
                    NodeVersionIndex.node_id == node_id,
                )
                .order_by(NodeVersionIndex.created_at.asc())
                .all()
            )
            return [
                {
                    "id": str(e.id),
                    "graph_definition_id": str(e.graph_definition_id),
                    "node_id": e.node_id,
                    "node_type": e.node_type,
                    "node_name": e.node_name,
                    "config_hash": e.config_hash,
                    "node_version": e.node_version,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ]

    def get_changed_nodes(
        self,
        graph_definition_id_a: str,
        graph_definition_id_b: str,
    ) -> Dict[str, Any]:
        """Compare two graph definition versions and return changed nodes.

        Args:
            graph_definition_id_a: First (older) graph definition.
            graph_definition_id_b: Second (newer) graph definition.

        Returns:
            Dict with 'added', 'removed', and 'modified' node lists.
        """
        index_a = self._load_parent_index(graph_definition_id_a)
        index_b = self._load_parent_index(graph_definition_id_b)

        ids_a = set(index_a.keys())
        ids_b = set(index_b.keys())

        added = [index_b[nid] for nid in (ids_b - ids_a)]
        removed = [index_a[nid] for nid in (ids_a - ids_b)]
        modified = [
            {
                "node_id": nid,
                "old_version": index_a[nid]["node_version"],
                "new_version": index_b[nid]["node_version"],
                "old_hash": index_a[nid]["config_hash"],
                "new_hash": index_b[nid]["config_hash"],
            }
            for nid in (ids_a & ids_b)
            if index_a[nid]["config_hash"] != index_b[nid]["config_hash"]
        ]

        return {"added": added, "removed": removed, "modified": modified}

    def _load_parent_index(self, graph_definition_id: str) -> Dict[str, Dict[str, Any]]:
        """Load node version index entries for a graph definition, keyed by node_id."""
        with get_db() as db:
            entries = (
                db.query(NodeVersionIndex)
                .filter(NodeVersionIndex.graph_definition_id == graph_definition_id)
                .all()
            )
            return {
                e.node_id: {
                    "config_hash": e.config_hash,
                    "node_version": e.node_version,
                    "node_type": e.node_type,
                    "node_name": e.node_name,
                }
                for e in entries
            }
