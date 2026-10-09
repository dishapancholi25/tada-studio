"""Tests for TemplateProcessor variable resolution.

Covers chaining values between nodes, e.g. using an OAuth access token
produced by one HTTP node in a downstream node's Authorization header.
"""

import pytest

from backend.services.io.template_processor import TemplateProcessor


@pytest.fixture
def processor():
    """TemplateProcessor instance."""
    return TemplateProcessor()


@pytest.fixture
def token_state():
    """State containing a typical OAuth token response from an HTTP node.

    The response payload is nested under ``data``, matching what
    HttpNodeExecutor writes into node_outputs.
    """
    payload = {
        "success": True,
        "status_code": 200,
        "data": {
            "token_type": "Bearer",
            "access_token": "tok_abc123",
            "scope": "CRM",
            "expires_in": 86490,
        },
    }
    return {
        "messages": [],
        "node_outputs": {
            "token_node": {
                "raw": "{}",
                "structured": payload,
                "fields": payload,
            }
        },
    }


class TestNestedVariableResolution:
    """Bare and dotted variable names both resolve nested response fields."""

    def test_bare_name_finds_nested_field(self, processor, token_state):
        """{{access_token}} resolves even though the value is under data."""
        assert processor.process("{{access_token}}", token_state) == "tok_abc123"

    def test_dotted_path_resolves(self, processor, token_state):
        """Dots are allowed in template variables."""
        assert processor.process("{{data.access_token}}", token_state) == "tok_abc123"

    def test_template_inside_surrounding_text(self, processor, token_state):
        """Variables can be embedded in a larger string."""
        assert (
            processor.process("Bearer {{access_token}}", token_state)
            == "Bearer tok_abc123"
        )

    def test_non_string_value_is_stringified(self, processor, token_state):
        """Numeric fields render as strings."""
        assert processor.process("{{expires_in}}", token_state) == "86490"

    def test_missing_variable_renders_empty(self, processor, token_state):
        """Unknown variables resolve to an empty string, not the literal."""
        assert processor.process("{{nonexistent}}", token_state) == ""

    def test_multiple_variables_in_one_template(self, processor, token_state):
        """Several variables resolve independently."""
        result = processor.process("{{token_type}} {{access_token}}", token_state)
        assert result == "Bearer tok_abc123"

    def test_empty_template_returns_input(self, processor, token_state):
        """Empty templates are returned unchanged."""
        assert processor.process("", token_state) == ""

    def test_text_without_variables_is_unchanged(self, processor, token_state):
        """Plain strings pass through untouched."""
        assert processor.process("literal_token", token_state) == "literal_token"


class TestNestedSearch:
    """Depth-first search only returns scalars."""

    def test_search_skips_dict_values(self, processor):
        """A key holding a dict is not returned as a value."""
        state = {
            "messages": [],
            "node_outputs": {
                "n1": {"structured": {"data": {"nested": {"access_token": "deep"}}}}
            },
        }
        assert processor.process("{{access_token}}", state) == "deep"

    def test_search_traverses_lists(self, processor):
        """Values inside lists are found."""
        state = {
            "messages": [],
            "node_outputs": {
                "n1": {"structured": {"items": [{"id": 1}, {"access_token": "in_list"}]}}
            },
        }
        assert processor.process("{{access_token}}", state) == "in_list"
