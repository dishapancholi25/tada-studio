"""Tests for EnhancedNodeData deserialization.

These tests ensure that node data can be correctly deserialized from dictionaries,
including handling the 'node_type' to 'type' field aliasing used by the frontend.
"""

from backend.models.workflow.enums import NodeType
from backend.models.workflow.node import EnhancedNodeData


class TestEnhancedNodeDataFromDict:
    """Test suite for EnhancedNodeData.from_dict() method."""

    def test_from_dict_with_type_field(self):
        """Test deserialization with standard 'type' field."""
        data = {
            "uniq_id": "node-123",
            "name": "Test Agent",
            "type": "AGENT",
            "position": {"x": 100, "y": 200},
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.uniq_id == "node-123"
        assert node.name == "Test Agent"
        assert node.type == NodeType.AGENT
        assert node.position.x == 100
        assert node.position.y == 200

    def test_from_dict_with_node_type_field(self):
        """Test deserialization with 'node_type' field (frontend sends this)."""
        data = {
            "uniq_id": "node-456",
            "name": "Another Agent",
            "node_type": "AGENT",
            "position": {"x": 300, "y": 400},
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.uniq_id == "node-456"
        assert node.name == "Another Agent"
        assert node.type == NodeType.AGENT
        assert node.position.x == 300
        assert node.position.y == 400

    def test_from_dict_with_both_type_and_node_type(self):
        """Test that node_type takes precedence when both fields are present."""
        data = {
            "uniq_id": "node-789",
            "name": "Condition Node",
            "type": "AGENT",  # This should be overwritten
            "node_type": "CONDITION",  # This should win
            "position": {"x": 500, "y": 600},
        }

        node = EnhancedNodeData.from_dict(data)

        # node_type should overwrite type
        assert node.type == NodeType.CONDITION

    def test_from_dict_with_start_node(self):
        """Test deserialization of START node."""
        data = {
            "uniq_id": "start-1",
            "name": "Start",
            "node_type": "START",
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.type == NodeType.START

    def test_from_dict_with_end_node(self):
        """Test deserialization of END node."""
        data = {
            "uniq_id": "end-1",
            "name": "End",
            "node_type": "END",
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.type == NodeType.END

    def test_from_dict_with_condition_node(self):
        """Test deserialization of CONDITION node with config."""
        data = {
            "uniq_id": "cond-1",
            "name": "Route Decision",
            "node_type": "CONDITION",
            "condition_config": {
                "condition_type": "llm",
                "branches": [
                    {"label": "Yes", "color": "#10b981", "handle_id": "yes"},
                    {"label": "No", "color": "#ef4444", "handle_id": "no"},
                ],
            },
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.type == NodeType.CONDITION
        assert node.condition_config is not None
        assert len(node.condition_config.branches) == 2

    def test_from_dict_minimal_data(self):
        """Test deserialization with minimal required data."""
        data = {
            "uniq_id": "min-1",
            "name": "Minimal",
            "type": "AGENT",
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.uniq_id == "min-1"
        assert node.name == "Minimal"
        assert node.type == NodeType.AGENT
        # Should have defaults for optional fields
        assert node.position is not None

    def test_from_dict_with_agent_config(self):
        """Test deserialization with agent configuration."""
        data = {
            "uniq_id": "agent-1",
            "name": "Configured Agent",
            "node_type": "AGENT",
            "agent_config": {
                "system_prompt": "You are a helpful assistant.",
                "llm_config": {
                    "model_name": "gpt-4",
                    "temperature": 0.7,
                },
            },
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.type == NodeType.AGENT
        assert node.agent_config is not None
        assert node.agent_config.system_prompt == "You are a helpful assistant."
        assert node.agent_config.llm_config is not None
        assert node.agent_config.llm_config.model_name == "gpt-4"

    def test_from_dict_preserves_node_type_enum(self):
        """Test that NodeType enum is preserved if already converted."""
        data = {
            "uniq_id": "enum-1",
            "name": "Enum Node",
            "type": NodeType.AGENT,  # Already a NodeType enum
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.type == NodeType.AGENT
        assert isinstance(node.type, NodeType)

    def test_from_dict_with_id_field(self):
        """Test deserialization with 'id' field instead of 'uniq_id' (frontend format)."""
        data = {
            "id": "frontend-node-1",
            "name": "Frontend Node",
            "type": "AGENT",
            "position": {"x": 100, "y": 100},
        }

        node = EnhancedNodeData.from_dict(data)

        assert node.uniq_id == "frontend-node-1"
        assert node.name == "Frontend Node"
        assert node.type == NodeType.AGENT

    def test_from_dict_with_both_id_and_uniq_id(self):
        """Test that uniq_id takes precedence when both fields are present."""
        data = {
            "id": "should-be-ignored",
            "uniq_id": "should-be-used",
            "name": "Priority Test",
            "type": "AGENT",
        }

        node = EnhancedNodeData.from_dict(data)

        # uniq_id should take precedence, id should be ignored
        assert node.uniq_id == "should-be-used"
