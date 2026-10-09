"""
Test suite for importing agents with structured output schemas.

This test validates that the import_agent_from_json functionality
properly handles output_schema fields and converts them to structured_outputs.
"""

import json
import pytest
from pathlib import Path

from backend.api.library.import_schema import ImportAgentRequest


class TestAgentImportWithStructuredOutput:
    """Test agent import with output_schema configuration."""

    @pytest.fixture
    def global_macro_analyst_json(self):
        """Load the global macro analyst JSON configuration."""
        json_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "finance"
            / "global_macro_analyst.json"
        )
        with open(json_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def basic_structured_output_agent(self):
        """Create a minimal agent with structured_outputs in agent_config."""
        return {
            "name": "Test Structured Output Agent",
            "description": "A test agent with structured output",
            "system_prompt": "You are a test agent that produces structured output.",
            "agent_config": {
                "structured_outputs": [
                    {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "A summary of the response",
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Confidence score between 0 and 1",
                            },
                        },
                        "required": ["summary", "confidence"],
                    }
                ]
            },
        }

    def test_import_schema_accepts_structured_outputs(
        self, basic_structured_output_agent
    ):
        """Test that ImportAgentRequest accepts structured_outputs in agent_config."""
        # Should not raise validation error
        import_request = ImportAgentRequest(**basic_structured_output_agent)
        agent_config = import_request.get_effective_agent_config()

        assert len(agent_config.structured_outputs) == 1
        schema = agent_config.structured_outputs[0]
        assert schema["type"] == "object"
        assert "summary" in schema["properties"]
        assert "confidence" in schema["properties"]

    def test_global_macro_analyst_import(self, global_macro_analyst_json):
        """Test importing the actual global macro analyst JSON."""
        # Should not raise validation error
        import_request = ImportAgentRequest(**global_macro_analyst_json)

        # Verify basic fields
        assert import_request.name == "Global Macro Analyst"

        # Get agent config
        agent_config = import_request.get_effective_agent_config()
        assert len(agent_config.structured_outputs) == 1

        # Verify structured_output schema structure
        schema = agent_config.structured_outputs[0]
        assert schema["type"] == "object"
        assert "global_events_summary" in schema["properties"]
        assert "market_impact" in schema["properties"]
        assert "key_statistics" in schema["properties"]
        assert "information_scope" in schema["properties"]
        assert "relevance_explanation" in schema["properties"]

        # Verify required fields
        assert set(schema["required"]) == {
            "global_events_summary",
            "market_impact",
            "key_statistics",
            "information_scope",
            "relevance_explanation",
        }

    def test_global_macro_analyst_schema_in_structured_outputs(
        self, global_macro_analyst_json
    ):
        """Test that global macro analyst has structured outputs properly configured."""
        import_request = ImportAgentRequest(**global_macro_analyst_json)
        agent_config = import_request.get_effective_agent_config()

        # Should be in structured_outputs
        assert len(agent_config.structured_outputs) == 1
        assert agent_config.structured_outputs[0]["type"] == "object"

    def test_market_impact_nested_structure(self, global_macro_analyst_json):
        """Test the nested market_impact object structure."""
        import_request = ImportAgentRequest(**global_macro_analyst_json)
        agent_config = import_request.get_effective_agent_config()
        schema = agent_config.structured_outputs[0]

        market_impact = schema["properties"]["market_impact"]
        assert market_impact["type"] == "object"
        assert "fund_specific_impact" in market_impact["properties"]
        assert "product_type_impact" in market_impact["properties"]
        assert "asset_class_impact" in market_impact["properties"]
        assert "local_market_impact" in market_impact["properties"]

        # All should be required
        assert set(market_impact["required"]) == {
            "fund_specific_impact",
            "product_type_impact",
            "asset_class_impact",
            "local_market_impact",
        }

    def test_key_statistics_array_structure(self, global_macro_analyst_json):
        """Test the key_statistics array structure."""
        import_request = ImportAgentRequest(**global_macro_analyst_json)
        agent_config = import_request.get_effective_agent_config()
        schema = agent_config.structured_outputs[0]

        key_statistics = schema["properties"]["key_statistics"]
        assert key_statistics["type"] == "array"

        items = key_statistics["items"]
        assert items["type"] == "object"
        assert "indicator" in items["properties"]
        assert "value" in items["properties"]
        assert "context" in items["properties"]

        # All fields should be required
        assert set(items["required"]) == {"indicator", "value", "context"}

    def test_information_scope_sources_structure(self, global_macro_analyst_json):
        """Test the information_scope sources structure."""
        import_request = ImportAgentRequest(**global_macro_analyst_json)
        agent_config = import_request.get_effective_agent_config()
        schema = agent_config.structured_outputs[0]

        info_scope = schema["properties"]["information_scope"]
        assert info_scope["type"] == "object"

        # Check source arrays
        assert "fund_specific_sources" in info_scope["properties"]
        assert "product_asset_class_sources" in info_scope["properties"]
        assert "global_context_sources" in info_scope["properties"]

        # All should be arrays of strings
        for source_field in [
            "fund_specific_sources",
            "product_asset_class_sources",
            "global_context_sources",
        ]:
            field = info_scope["properties"][source_field]
            assert field["type"] == "array"
            assert field["items"]["type"] == "string"

        # All should be required
        assert set(info_scope["required"]) == {
            "fund_specific_sources",
            "product_asset_class_sources",
            "global_context_sources",
        }

    def test_agent_config_tools_are_preserved(self, global_macro_analyst_json):
        """Test that agent_config tools are properly imported."""
        import_request = ImportAgentRequest(**global_macro_analyst_json)
        agent_config = import_request.get_effective_agent_config()

        assert "document_search" in agent_config.tools
        assert "web_search" in agent_config.tools

    def test_structured_outputs_in_agent_config_takes_precedence(self):
        """Test that structured_outputs in agent_config takes precedence over output_schema."""
        agent_data = {
            "name": "Test Agent",
            "description": "Test",
            "system_prompt": "Test prompt",
            "output_schema": {
                "type": "object",
                "properties": {"field1": {"type": "string"}},
            },
            "agent_config": {
                "structured_outputs": [
                    {"type": "object", "properties": {"field2": {"type": "string"}}}
                ]
            },
        }

        import_request = ImportAgentRequest(**agent_data)
        agent_config = import_request.get_effective_agent_config()

        # Should use the one from agent_config, not output_schema
        assert len(agent_config.structured_outputs) == 1
        assert "field2" in agent_config.structured_outputs[0]["properties"]
        assert "field1" not in agent_config.structured_outputs[0]["properties"]

    def test_no_output_schema_results_in_empty_structured_outputs(self):
        """Test that agents without output_schema have empty structured_outputs."""
        agent_data = {
            "name": "Simple Agent",
            "description": "No structured output",
            "system_prompt": "You are a simple agent.",
        }

        import_request = ImportAgentRequest(**agent_data)
        agent_config = import_request.get_effective_agent_config()

        assert agent_config.structured_outputs == []

    def test_output_schema_validation_rejects_invalid_json(self):
        """Test that invalid structured_outputs format is handled properly."""
        # This is a basic test - the actual schema validation happens later in the pipeline
        agent_data = {
            "name": "Invalid Schema Agent",
            "description": "Has invalid schema",
            "system_prompt": "Test",
            "agent_config": {
                "structured_outputs": "not a list"  # Invalid - should be a list
            },
        }

        with pytest.raises(Exception):  # Pydantic will raise validation error
            ImportAgentRequest(**agent_data)


class TestAgentImportIntegration:
    """Integration tests for the full import flow."""

    def test_json_file_can_be_loaded_and_parsed(self):
        """Test that the global_macro_analyst.json file can be loaded."""
        json_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "finance"
            / "global_macro_analyst.json"
        )

        # Should be valid JSON
        with open(json_path, "r") as f:
            data = json.load(f)

        # Should be valid ImportAgentRequest
        import_request = ImportAgentRequest(**data)

        assert import_request.name == "Global Macro Analyst"

        # Check that structured_outputs is in agent_config
        agent_config = import_request.get_effective_agent_config()
        assert len(agent_config.structured_outputs) > 0

    def test_full_import_workflow_structure(self):
        """Test the complete workflow from JSON to agent config."""
        json_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "finance"
            / "global_macro_analyst.json"
        )

        with open(json_path, "r") as f:
            agent_data = json.load(f)

        # Step 1: Validate with Pydantic
        import_request = ImportAgentRequest(**agent_data)

        # Step 2: Get effective configs
        agent_config = import_request.get_effective_agent_config()
        metadata = import_request.get_effective_metadata()

        # Step 3: Verify structured outputs are set
        assert len(agent_config.structured_outputs) > 0
        structured_output = agent_config.structured_outputs[0]

        # Step 4: Verify it's a valid JSON Schema
        assert "type" in structured_output
        assert "properties" in structured_output
        assert "required" in structured_output

        # Step 5: Verify metadata
        assert "Finance" in metadata.category
        assert "Research" in metadata.category
        assert metadata.complexity == "intermediate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
