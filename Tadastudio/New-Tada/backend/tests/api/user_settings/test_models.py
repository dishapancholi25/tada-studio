"""Tests for user settings API models."""

import pytest
from pydantic import ValidationError

from backend.api.user_settings.models import SaveExternalServiceRequest


class TestSaveExternalServiceRequest:
    """Tests for SaveExternalServiceRequest validation."""

    def test_valid_api_key(self):
        """Test valid API key."""
        request = SaveExternalServiceRequest(api_key="tvly-test-key-12345")
        assert request.api_key == "tvly-test-key-12345"

    def test_valid_api_key_with_settings(self):
        """Test valid API key with settings."""
        request = SaveExternalServiceRequest(
            api_key="tvly-test-key-12345", settings={"key": "value"}
        )
        assert request.api_key == "tvly-test-key-12345"
        assert request.settings == {"key": "value"}

    def test_api_key_with_whitespace(self):
        """Test API key with leading/trailing whitespace is trimmed."""
        request = SaveExternalServiceRequest(api_key="  tvly-test-key-12345  ")
        assert request.api_key == "tvly-test-key-12345"

    def test_empty_api_key(self):
        """Test empty API key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SaveExternalServiceRequest(api_key="")

        errors = exc_info.value.errors()
        assert any("api_key" in str(error.get("loc")) for error in errors)

    def test_whitespace_only_api_key(self):
        """Test whitespace-only API key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SaveExternalServiceRequest(api_key="   ")

        errors = exc_info.value.errors()
        assert any("api_key" in str(error.get("loc")) for error in errors)
        assert any(
            "empty or whitespace" in str(error.get("msg")).lower() for error in errors
        )

    def test_api_key_too_long(self):
        """Test API key exceeding max length raises validation error."""
        long_key = "a" * 501  # 501 characters
        with pytest.raises(ValidationError) as exc_info:
            SaveExternalServiceRequest(api_key=long_key)

        errors = exc_info.value.errors()
        assert any("api_key" in str(error.get("loc")) for error in errors)

    def test_api_key_exactly_max_length(self):
        """Test API key at exactly max length (500 chars) is valid."""
        max_length_key = "a" * 500
        request = SaveExternalServiceRequest(api_key=max_length_key)
        assert len(request.api_key) == 500

    def test_settings_optional(self):
        """Test settings field is optional."""
        request = SaveExternalServiceRequest(api_key="tvly-test-key-12345")
        assert request.settings is None

    def test_settings_empty_dict(self):
        """Test settings can be empty dict."""
        request = SaveExternalServiceRequest(api_key="tvly-test-key-12345", settings={})
        assert request.settings == {}
