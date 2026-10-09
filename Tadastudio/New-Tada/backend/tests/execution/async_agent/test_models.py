"""Tests for async agent execution models."""

from backend.services.execution.async_agent.models import ToolExecutionRecord


class TestToolExecutionRecordWasStreamed:
    """Tests for was_streamed field in ToolExecutionRecord."""

    def test_was_streamed_defaults_to_false(self):
        """Verify was_streamed defaults to False."""
        record = ToolExecutionRecord(tool_name="test_tool")
        assert record.was_streamed is False

    def test_was_streamed_can_be_set_to_true(self):
        """Verify was_streamed can be set to True at creation."""
        record = ToolExecutionRecord(tool_name="test_tool", was_streamed=True)
        assert record.was_streamed is True

    def test_was_streamed_included_in_to_dict_when_true(self):
        """Verify was_streamed appears in to_dict() when True."""
        record = ToolExecutionRecord(tool_name="test_tool", was_streamed=True)
        result = record.to_dict()
        assert result["was_streamed"] is True

    def test_was_streamed_included_in_to_dict_when_false(self):
        """Verify was_streamed appears in to_dict() when False."""
        record = ToolExecutionRecord(tool_name="test_tool", was_streamed=False)
        result = record.to_dict()
        assert result["was_streamed"] is False

    def test_was_streamed_can_be_mutated(self):
        """Verify was_streamed can be changed after creation."""
        record = ToolExecutionRecord(tool_name="test_tool")
        assert record.was_streamed is False

        record.was_streamed = True
        assert record.was_streamed is True

        result = record.to_dict()
        assert result["was_streamed"] is True
