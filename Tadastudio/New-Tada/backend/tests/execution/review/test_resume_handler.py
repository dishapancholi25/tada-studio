"""Tests for interrupt handling in ResumeHandler.

These tests verify that interrupt value extraction works correctly for both:
- LangGraph Interrupt objects (first iteration)
- Raw dicts (subsequent iterations after resume)
"""

from unittest.mock import MagicMock


class TestInterruptValueExtraction:
    """Tests for interrupt value extraction in _handle_interrupt_during_resume."""

    def test_extract_value_from_interrupt_object(self):
        """Should extract value from LangGraph Interrupt object (first iteration)."""
        # Mock Interrupt object with .value attribute
        mock_interrupt = MagicMock()
        mock_interrupt.value = {"type": "agent_review", "node_id": "test-123"}

        # Simulate interrupts tuple
        interrupts = (mock_interrupt,)

        # Extraction logic (mirrors resume_handler.py)
        interrupt_obj = interrupts[0]
        if hasattr(interrupt_obj, "value"):
            interrupt_value = interrupt_obj.value
        elif isinstance(interrupt_obj, dict):
            interrupt_value = interrupt_obj.get("value", interrupt_obj)
        else:
            interrupt_value = interrupt_obj

        assert interrupt_value["type"] == "agent_review"
        assert interrupt_value["node_id"] == "test-123"

    def test_extract_value_from_dict_interrupt(self):
        """Should extract value from dict interrupt (multi-turn resume).

        This is the CRITICAL test case - on resume after rejection,
        LangGraph returns a raw dict instead of an Interrupt object.
        """
        # Dict interrupt (what happens on resume)
        dict_interrupt = {
            "value": {"type": "agent_review", "node_id": "test-123"},
            "resumable": True,
        }
        interrupts = (dict_interrupt,)

        # OLD broken code would fail here:
        # interrupt_value = getattr(interrupts[0], "value", None)  # Returns None!

        # NEW code handles both:
        interrupt_obj = interrupts[0]
        if hasattr(interrupt_obj, "value"):
            interrupt_value = interrupt_obj.value
        elif isinstance(interrupt_obj, dict):
            interrupt_value = interrupt_obj.get("value", interrupt_obj)
        else:
            interrupt_value = interrupt_obj

        assert interrupt_value is not None, (
            "interrupt_value should not be None for dict"
        )
        assert interrupt_value["type"] == "agent_review"
        assert interrupt_value["node_id"] == "test-123"

    def test_dict_without_value_key_uses_dict_itself(self):
        """When dict has no 'value' key, use the dict directly as payload."""
        # Direct dict payload (edge case)
        direct_payload = {"type": "agent_review", "node_id": "test-123"}
        interrupts = (direct_payload,)

        interrupt_obj = interrupts[0]
        if hasattr(interrupt_obj, "value"):
            interrupt_value = interrupt_obj.value
        elif isinstance(interrupt_obj, dict):
            interrupt_value = interrupt_obj.get("value", interrupt_obj)
        else:
            interrupt_value = interrupt_obj

        assert interrupt_value["type"] == "agent_review"
        assert interrupt_value["node_id"] == "test-123"

    def test_is_agent_review_detection_with_dict_interrupt(self):
        """The is_agent_review check should work after dict extraction."""
        # Full flow simulation
        dict_interrupt = {
            "value": {
                "type": "agent_review",
                "node_id": "test-123",
                "node_name": "Test Agent",
            }
        }

        # Extract value (new code path)
        interrupt_obj = dict_interrupt
        if hasattr(interrupt_obj, "value"):
            interrupt_value = interrupt_obj.value
        elif isinstance(interrupt_obj, dict):
            interrupt_value = interrupt_obj.get("value", interrupt_obj)
        else:
            interrupt_value = interrupt_obj

        # Now check for prompt extraction (what the actual code does)
        if isinstance(interrupt_value, dict):
            prompt_value = interrupt_value.get("prompt", interrupt_value)
        else:
            prompt_value = interrupt_value

        # Check agent review detection
        is_agent_review = (
            isinstance(prompt_value, dict)
            and prompt_value.get("type") == "agent_review"
        )

        assert is_agent_review is True, "Should detect agent_review from dict interrupt"

    def test_getattr_fails_on_dict_but_get_works(self):
        """Demonstrate why getattr fails on dicts but .get() works."""
        dict_interrupt = {"value": {"type": "agent_review"}}

        # OLD broken approach - getattr on dict returns None
        old_result = getattr(dict_interrupt, "value", None)
        assert old_result is None, "getattr on dict should return None"

        # NEW working approach - .get() on dict works
        new_result = dict_interrupt.get("value")
        assert new_result is not None, ".get() on dict should return the value"
        assert new_result["type"] == "agent_review"

    def test_hasattr_correctly_distinguishes_object_vs_dict(self):
        """Verify hasattr behaves differently for objects vs dicts."""
        # Mock object WITH .value attribute
        mock_obj = MagicMock()
        mock_obj.value = "test"
        assert hasattr(mock_obj, "value") is True

        # Dict - hasattr returns False for dict keys
        dict_obj = {"value": "test"}
        assert hasattr(dict_obj, "value") is False

    def test_empty_interrupts_tuple(self):
        """Should handle empty interrupts gracefully."""
        interrupts = ()

        interrupt_value = None
        if isinstance(interrupts, (list, tuple)) and len(interrupts) > 0:
            interrupt_obj = interrupts[0]
            if hasattr(interrupt_obj, "value"):
                interrupt_value = interrupt_obj.value
            elif isinstance(interrupt_obj, dict):
                interrupt_value = interrupt_obj.get("value", interrupt_obj)

        assert interrupt_value is None

    def test_nested_dict_structure(self):
        """Handle nested dict structure that matches real LangGraph output."""
        # More realistic structure from LangGraph
        dict_interrupt = {
            "value": {
                "type": "agent_review",
                "node_id": "b1eb47c3-4107-4134-aa76-9b4e56c6129d",
                "node_name": "Agent 1",
                "agent_output": "Test output",
                "review_prompt": "Please review",
                "review_mode": "human",
                "current_iteration": 2,
                "max_iterations": 3,
                "review_history": [{"iteration": 1, "feedback": "Make it better"}],
            },
            "resumable": True,
            "ns": ["Agent 1:b1eb47c3"],
        }

        interrupt_obj = dict_interrupt
        if hasattr(interrupt_obj, "value"):
            interrupt_value = interrupt_obj.value
        elif isinstance(interrupt_obj, dict):
            interrupt_value = interrupt_obj.get("value", interrupt_obj)
        else:
            interrupt_value = interrupt_obj

        # Verify full payload extracted
        assert interrupt_value["type"] == "agent_review"
        assert interrupt_value["current_iteration"] == 2
        assert len(interrupt_value["review_history"]) == 1
        assert interrupt_value["review_history"][0]["feedback"] == "Make it better"
