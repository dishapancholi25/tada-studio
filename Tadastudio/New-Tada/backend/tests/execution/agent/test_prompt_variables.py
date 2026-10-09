"""Tests for prompt variable replacement functionality."""

from datetime import datetime, timezone

from backend.services.execution.agent.prompt_variables import (
    get_variable_replacements,
    replace_prompt_variables,
)


class TestGetVariableReplacements:
    """Tests for get_variable_replacements function."""

    def test_returns_dictionary(self):
        """Test that function returns a dictionary."""
        replacements = get_variable_replacements()
        assert isinstance(replacements, dict)

    def test_contains_required_variables(self):
        """Test that all required variables are present."""
        replacements = get_variable_replacements()
        assert "{{$today}}" in replacements
        assert "{{$now}}" in replacements

    def test_today_is_midnight(self):
        """Test that {{$today}} represents midnight (00:00:00) in UTC."""
        replacements = get_variable_replacements()
        today_value = replacements["{{$today}}"]

        # Parse ISO format and check time components
        # Format: YYYY-MM-DDTHH:MM:SSZ (UTC)
        assert "T00:00:00Z" in today_value

    def test_now_includes_time(self):
        """Test that {{$now}} includes current time in UTC."""
        replacements = get_variable_replacements()
        now_value = replacements["{{$now}}"]

        # Should be in ISO format with UTC timezone (Z suffix)
        assert "T" in now_value
        assert now_value.endswith("Z")
        # Parse to ensure it's a valid datetime (replace Z with +00:00 for parsing)
        parsed_dt = datetime.fromisoformat(now_value.replace("Z", "+00:00"))
        # Verify it's timezone-aware and in UTC
        assert parsed_dt.tzinfo is not None
        assert parsed_dt.tzinfo == timezone.utc

    def test_values_are_iso_format(self):
        """Test that both variables use ISO format."""
        replacements = get_variable_replacements()

        # Both should be parseable as ISO datetime (replace Z with +00:00 for parsing)
        datetime.fromisoformat(replacements["{{$today}}"].replace("Z", "+00:00"))
        datetime.fromisoformat(replacements["{{$now}}"].replace("Z", "+00:00"))


class TestReplacePromptVariables:
    """Tests for replace_prompt_variables function."""

    def test_empty_prompt_returns_empty(self):
        """Test that empty prompt returns empty string."""
        result = replace_prompt_variables("")
        assert result == ""

    def test_none_prompt_returns_none(self):
        """Test that None prompt returns None."""
        result = replace_prompt_variables(None)
        assert result is None

    def test_prompt_without_variables_unchanged(self):
        """Test that prompt without variables is unchanged."""
        prompt = "This is a simple prompt without variables."
        result = replace_prompt_variables(prompt)
        assert result == prompt

    def test_replaces_today_variable(self):
        """Test that {{$today}} is replaced with UTC timezone."""
        prompt = "Today's date is {{$today}}"
        result = replace_prompt_variables(prompt)

        assert "{{$today}}" not in result
        assert "T00:00:00Z" in result

    def test_replaces_now_variable(self):
        """Test that {{$now}} is replaced with UTC timezone."""
        prompt = "Current time is {{$now}}"
        result = replace_prompt_variables(prompt)

        assert "{{$now}}" not in result
        assert "T" in result  # Should contain time separator
        assert result.endswith("Z")

    def test_replaces_multiple_variables(self):
        """Test that multiple variables are replaced."""
        prompt = "Date: {{$today}}, Time: {{$now}}"
        result = replace_prompt_variables(prompt)

        assert "{{$today}}" not in result
        assert "{{$now}}" not in result
        assert result.startswith("Date: ")
        assert ", Time: " in result

    def test_replaces_duplicate_variables(self):
        """Test that duplicate variables are all replaced."""
        prompt = "Start: {{$now}}, End: {{$now}}"
        result = replace_prompt_variables(prompt)

        # Count occurrences of the variable placeholder
        assert result.count("{{$now}}") == 0
        assert result.count("Start: ") == 1
        assert result.count("End: ") == 1

    def test_preserves_surrounding_text(self):
        """Test that text around variables is preserved."""
        prompt = "Before {{$today}} middle {{$now}} after"
        result = replace_prompt_variables(prompt)

        assert result.startswith("Before ")
        assert " middle " in result
        assert " after" in result

    def test_case_sensitive_replacement(self):
        """Test that variable names are case sensitive."""
        prompt = "{{$TODAY}} and {{$NOW}} should not be replaced"
        result = replace_prompt_variables(prompt)

        # These should not be replaced (case doesn't match)
        assert "{{$TODAY}}" in result
        assert "{{$NOW}}" in result

    def test_partial_variable_names_not_replaced(self):
        """Test that partial matches are not replaced."""
        prompt = "{{$tod}} and {{$no}} are not variables"
        result = replace_prompt_variables(prompt)

        assert result == prompt

    def test_real_world_prompt_example(self):
        """Test with a realistic agent system prompt."""
        prompt = """You are a helpful assistant.

Today's date is {{$today}}.
Current timestamp: {{$now}}

Please use this information when answering questions about dates and times."""

        result = replace_prompt_variables(prompt)

        assert "{{$today}}" not in result
        assert "{{$now}}" not in result
        assert "You are a helpful assistant." in result
        assert "Today's date is" in result
        assert "Current timestamp:" in result

    def test_multiline_prompt_with_variables(self):
        """Test that variables work correctly in multiline prompts."""
        prompt = """Line 1: {{$today}}
Line 2: Some text
Line 3: {{$now}}"""

        result = replace_prompt_variables(prompt)
        lines = result.split("\n")

        assert len(lines) == 3
        assert "{{$today}}" not in lines[0]
        assert lines[1] == "Line 2: Some text"
        assert "{{$now}}" not in lines[2]
