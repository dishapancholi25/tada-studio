"""Tests for agent tools utility functions.

This module tests the utility functions used by agent tool creators,
particularly collision detection in tool naming.
"""

from backend.services.graph.agent_tools.utils import (
    build_tool_name,
    is_default_node_name,
    sanitize_tool_name,
)


class TestSanitizeToolName:
    """Tests for sanitize_tool_name function."""

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        assert sanitize_tool_name("Amex Fraud Hub API") == "amex_fraud_hub_api"
        assert sanitize_tool_name("Customer Support Docs") == "customer_support_docs"

    def test_special_characters(self):
        """Test handling of special characters."""
        assert sanitize_tool_name("API-v2 Endpoint") == "api_v2_endpoint"
        assert sanitize_tool_name("Special!@#$%Characters") == "specialcharacters"
        assert sanitize_tool_name("Test_With-Dashes") == "test_with_dashes"

    def test_multiple_separators(self):
        """Test collapsing multiple separators."""
        assert sanitize_tool_name("Multiple---Dashes") == "multiple_dashes"
        assert sanitize_tool_name("Many   Spaces") == "many_spaces"
        assert sanitize_tool_name("Mixed- -Separators") == "mixed_separators"

    def test_leading_trailing_underscores(self):
        """Test removal of leading/trailing underscores."""
        assert sanitize_tool_name("  Leading Spaces") == "leading_spaces"
        assert sanitize_tool_name("Trailing Spaces  ") == "trailing_spaces"
        assert sanitize_tool_name("-Leading Dash") == "leading_dash"

    def test_starts_with_number(self):
        """Test handling names that start with a number."""
        assert sanitize_tool_name("123 Start With Number") == "_123_start_with_number"
        assert sanitize_tool_name("2024 Report") == "_2024_report"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert sanitize_tool_name("") == "tool"
        assert sanitize_tool_name("!!!") == "tool"  # All special chars removed

    def test_collision_cases(self):
        """Test cases that would cause collisions."""
        # These should sanitize to the same value
        assert sanitize_tool_name("API v1") == "api_v1"
        assert sanitize_tool_name("API-v1") == "api_v1"
        assert sanitize_tool_name("API_v1") == "api_v1"


class TestIsDefaultNodeName:
    """Tests for is_default_node_name function."""

    def test_default_names(self):
        """Test recognition of default node names."""
        assert is_default_node_name("Document Search") is True
        assert is_default_node_name("Web Search") is True
        assert is_default_node_name("HTTP Request") is True
        assert is_default_node_name("Database Query") is True

    def test_custom_names(self):
        """Test that custom names are not recognized as defaults."""
        assert is_default_node_name("Regulations RAG") is False
        assert is_default_node_name("Amex API") is False
        assert is_default_node_name("Custom Search") is False


class TestBuildToolName:
    """Tests for build_tool_name function."""

    def test_semantic_naming(self):
        """Test semantic naming with custom node names."""
        result = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Amex Fraud Hub API",
            node_id="f70424aa-1234-5678-9abc-def012345678",
        )
        assert result == "document_search_amex_fraud_hub_api"

    def test_default_name_fallback(self):
        """Test fallback to ID-based naming for default names."""
        result = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Document Search",
            node_id="f70424aa-1234-5678-9abc-def012345678",
        )
        assert result == "document_search_f70424aa"

    def test_custom_default_name(self):
        """Test using custom default name parameter."""
        result = build_tool_name(
            tool_type_prefix="http_request",
            node_name="HTTP Request",
            node_id="abc12345-1234-5678-9abc-def012345678",
            default_name="HTTP Request",
        )
        assert result == "http_request_abc12345"

    def test_empty_node_name(self):
        """Test handling of empty node name."""
        result = build_tool_name(
            tool_type_prefix="web_search",
            node_name="",
            node_id="xyz98765-1234-5678-9abc-def012345678",
        )
        assert result == "web_search_xyz98765"

    def test_collision_detection_no_collision(self):
        """Test that unique names are tracked without collision."""
        used_names = set()

        # First tool
        name1 = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Regulations RAG",
            node_id="abc12345-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "document_search_regulations_rag"
        assert name1 in used_names

        # Second tool with different name
        name2 = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Policies RAG",
            node_id="def67890-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name2 == "document_search_policies_rag"
        assert name2 in used_names

        # Both names should be tracked
        assert len(used_names) == 2

    def test_collision_detection_with_collision(self):
        """Test that collisions are detected and ID suffix is added."""
        used_names = set()

        # First tool - "API v1"
        name1 = build_tool_name(
            tool_type_prefix="http_request",
            node_name="API v1",
            node_id="abc12345-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "http_request_api_v1"
        assert name1 in used_names

        # Second tool - "API-v1" (sanitizes to same name)
        name2 = build_tool_name(
            tool_type_prefix="http_request",
            node_name="API-v1",
            node_id="def67890-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        # Should have ID suffix appended due to collision
        assert name2 == "http_request_api_v1_def678"
        assert name2 in used_names

        # Both names should be tracked
        assert len(used_names) == 2
        assert name1 != name2

    def test_multiple_collisions(self):
        """Test handling of multiple collisions."""
        used_names = set()

        # Create three tools that would all collide
        name1 = build_tool_name(
            tool_type_prefix="database_query",
            node_name="Customer DB",
            node_id="id1_aaaa-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "database_query_customer_db"

        name2 = build_tool_name(
            tool_type_prefix="database_query",
            node_name="Customer-DB",
            node_id="id2_bbbb-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name2 == "database_query_customer_db_id2_bb"

        name3 = build_tool_name(
            tool_type_prefix="database_query",
            node_name="Customer_DB",
            node_id="id3_cccc-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name3 == "database_query_customer_db_id3_cc"

        # All three should be unique
        assert len(used_names) == 3
        assert len({name1, name2, name3}) == 3

    def test_no_collision_tracking_without_parameter(self):
        """Test that collision tracking is optional."""
        # Without used_names parameter, should work as before
        name1 = build_tool_name(
            tool_type_prefix="web_search",
            node_name="Search Tool",
            node_id="abc12345-1234-5678-9abc-def012345678",
        )
        name2 = build_tool_name(
            tool_type_prefix="web_search",
            node_name="Search Tool",
            node_id="def67890-1234-5678-9abc-def012345678",
        )
        # Without tracking, both will have the same name
        assert name1 == name2 == "web_search_search_tool"

    def test_collision_with_default_name(self):
        """Test that default names don't trigger collision detection."""
        used_names = set()

        # Default names should always use ID-based naming
        name1 = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Document Search",
            node_id="abc12345-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "document_search_abc12345"

        name2 = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Document Search",
            node_id="def67890-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name2 == "document_search_def67890"

        # Both should be unique (ID-based)
        assert name1 != name2
        assert len(used_names) == 2

    def test_mixed_default_and_custom_names(self):
        """Test mixing default and custom names."""
        used_names = set()

        # Custom name
        name1 = build_tool_name(
            tool_type_prefix="http_request",
            node_name="Payment API",
            node_id="abc12345-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "http_request_payment_api"

        # Default name
        name2 = build_tool_name(
            tool_type_prefix="http_request",
            node_name="HTTP Request",
            node_id="def67890-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name2 == "http_request_def67890"

        # Another custom name
        name3 = build_tool_name(
            tool_type_prefix="http_request",
            node_name="Analytics API",
            node_id="ghi13579-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name3 == "http_request_analytics_api"

        assert len(used_names) == 3

    def test_different_tool_types_same_name(self):
        """Test that different tool types can have same node names without collision."""
        used_names = set()

        # Document search with "Customer Data"
        name1 = build_tool_name(
            tool_type_prefix="document_search",
            node_name="Customer Data",
            node_id="abc12345-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name1 == "document_search_customer_data"

        # Database query with "Customer Data"
        name2 = build_tool_name(
            tool_type_prefix="database_query",
            node_name="Customer Data",
            node_id="def67890-1234-5678-9abc-def012345678",
            used_names=used_names,
        )
        assert name2 == "database_query_customer_data"

        # No collision because different prefixes
        assert name1 != name2
        assert len(used_names) == 2
