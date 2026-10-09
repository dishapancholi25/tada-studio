"""Prompt variable replacement utilities.

This module provides functionality to replace template variables in agent system prompts
with dynamic values such as current date and time.
"""

from datetime import datetime, timezone
from typing import Dict


def get_variable_replacements() -> Dict[str, str]:
    """Get current values for all supported template variables.

    Returns:
        Dictionary mapping variable names to their current values
    """
    now = datetime.now(timezone.utc)

    # {{$today}} - current date at midnight (date only)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # {{$now}} - current date and time
    current_time = now

    return {
        "{{$today}}": today.isoformat().replace("+00:00", "Z"),
        "{{$now}}": current_time.isoformat().replace("+00:00", "Z"),
    }


def replace_prompt_variables(prompt: str) -> str:
    """Replace template variables in a prompt with their current values.

    Supported variables:
    - {{$today}}: Current date at midnight (ISO format)
    - {{$now}}: Current date and time (ISO format)

    Args:
        prompt: The prompt text containing template variables

    Returns:
        Prompt with variables replaced by their current values

    Examples:
        >>> prompt = "Today is {{$today}}, current time is {{$now}}"
        >>> replace_prompt_variables(prompt)
        "Today is 2025-12-11T00:00:00Z, current time is 2025-12-11T12:05:30.123456Z"
    """
    if not prompt:
        return prompt

    # Get current variable values
    replacements = get_variable_replacements()

    # Replace all variables
    result = prompt
    for variable, value in replacements.items():
        result = result.replace(variable, value)

    return result
