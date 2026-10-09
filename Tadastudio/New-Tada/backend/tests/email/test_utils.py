"""Tests for email utility functions.

Covers _extract_json_from_text (ReDoS fix) and extract_email_content.
"""

from backend.services.email.utils import (
    _extract_json_from_text,
    extract_email_content,
)
from backend.services.email.config import (
    EXTRACT_MODE_FULL_BODY,
    EXTRACT_MODE_JSON,
    EXTRACT_MODE_REGEX,
    EXTRACT_MODE_STRIPPED_TEXT,
)


# ---------------------------------------------------------------------------
# _extract_json_from_text
# ---------------------------------------------------------------------------


class TestExtractJsonFromText:
    """Tests for the string-indexing based JSON extraction."""

    # --- Happy-path: objects ---

    def test_plain_json_object(self):
        result = _extract_json_from_text('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_object_with_surrounding_text(self):
        text = 'Here is the result: {"status": "ok", "count": 3} -- end'
        result = _extract_json_from_text(text)
        assert result == {"status": "ok", "count": 3}

    def test_nested_json_object(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_json_from_text(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    # --- Happy-path: arrays ---

    def test_plain_json_array(self):
        result = _extract_json_from_text("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_json_array_with_surrounding_text(self):
        text = 'Results: [{"id": 1}, {"id": 2}] done'
        result = _extract_json_from_text(text)
        assert result == [{"id": 1}, {"id": 2}]

    # --- Object preferred over array ---

    def test_object_preferred_when_both_present(self):
        """When text contains both {} and [], the object should be tried first."""
        text = '{"items": [1, 2]}'
        result = _extract_json_from_text(text)
        assert result == {"items": [1, 2]}

    # --- Fallback to array when object fails ---

    def test_falls_through_to_array_when_braces_invalid(self):
        """If first/last braces don't form valid JSON, fall through to array."""
        # first { with no matching } means obj_end == -1 -> skip to array
        text = "not json { broken [1, 2, 3]"
        # { is at index 9, there is no }, so obj_end == -1 -> skip to array
        result = _extract_json_from_text(text)
        assert result == [1, 2, 3]

    # --- No JSON found ---

    def test_no_json_returns_original_text(self):
        text = "This is just plain text with no JSON"
        result = _extract_json_from_text(text)
        assert result == text

    def test_empty_string_returns_original(self):
        result = _extract_json_from_text("")
        assert result == ""

    # --- Invalid JSON within braces ---

    def test_invalid_json_in_braces_returns_original(self):
        text = "{not valid json}"
        result = _extract_json_from_text(text)
        assert result == text

    def test_invalid_json_in_brackets_returns_original(self):
        text = "[not valid json]"
        result = _extract_json_from_text(text)
        assert result == text

    # --- Multiple objects: first-to-last brace behavior ---

    def test_multiple_objects_greedy_span(self):
        """first { to last } may span multiple objects -- json.loads decides validity."""
        text = '{"a": 1} {"b": 2}'
        result = _extract_json_from_text(text)
        # first { to last } is '{"a": 1} {"b": 2}' which is invalid JSON,
        # so it should fall through. No valid array either -> return original.
        assert result == text

    # --- Multiline JSON ---

    def test_multiline_json(self):
        text = """Some preamble
{
    "name": "test",
    "values": [10, 20]
}
Some epilogue"""
        result = _extract_json_from_text(text)
        assert result == {"name": "test", "values": [10, 20]}

    # --- Performance: no ReDoS on adversarial input ---

    def test_no_redos_on_nested_braces(self):
        """Large input with many braces should complete quickly (no regex backtracking)."""
        # This would cause catastrophic backtracking with r"\{.*\}" + re.DOTALL
        # on certain pathological inputs. String indexing is O(n).
        text = "{" * 5000 + "x" * 5000 + "}" * 5000
        result = _extract_json_from_text(text)
        # Invalid JSON, should return original text
        assert result == text


# ---------------------------------------------------------------------------
# extract_email_content integration with _extract_json_from_text
# ---------------------------------------------------------------------------


class TestExtractEmailContent:
    """Tests for extract_email_content covering all extract modes."""

    def test_full_body_mode(self):
        body = "Hello, this is the email body."
        result = extract_email_content(body, extract_mode=EXTRACT_MODE_FULL_BODY)
        assert result == body

    def test_stripped_text_mode(self):
        stripped = "Just the main text"
        result = extract_email_content(
            "full body with signature",
            extract_mode=EXTRACT_MODE_STRIPPED_TEXT,
            stripped_text=stripped,
        )
        assert result == stripped

    def test_stripped_text_mode_falls_back_to_body(self):
        body = "full body"
        result = extract_email_content(
            body,
            extract_mode=EXTRACT_MODE_STRIPPED_TEXT,
            stripped_text=None,
        )
        # stripped_text is None -> falls through to default which returns body
        assert result == body

    def test_regex_mode_with_group(self):
        body = "Order ID: 12345, Status: shipped"
        result = extract_email_content(
            body,
            extract_mode=EXTRACT_MODE_REGEX,
            extraction_pattern=r"Order ID: (\d+)",
        )
        assert result == "12345"

    def test_regex_mode_no_match_returns_body(self):
        body = "No match here"
        result = extract_email_content(
            body,
            extract_mode=EXTRACT_MODE_REGEX,
            extraction_pattern=r"Order ID: (\d+)",
        )
        assert result == body

    def test_json_mode_extracts_object(self):
        body = 'Response: {"approved": true, "amount": 500}'
        result = extract_email_content(body, extract_mode=EXTRACT_MODE_JSON)
        assert result == {"approved": True, "amount": 500}

    def test_json_mode_no_json_returns_body(self):
        body = "No json here"
        result = extract_email_content(body, extract_mode=EXTRACT_MODE_JSON)
        assert result == body

    def test_default_mode_prefers_stripped_text(self):
        """Default/unknown mode returns stripped_text if available."""
        result = extract_email_content(
            "full body",
            extract_mode="unknown_mode",
            stripped_text="stripped",
        )
        assert result == "stripped"
