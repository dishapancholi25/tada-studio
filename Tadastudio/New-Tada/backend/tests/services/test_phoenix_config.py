"""Tests for resolve_phoenix_config enabled merge logic."""

from unittest.mock import patch

from backend.services.phoenix.config import resolve_phoenix_config


def _env(enabled: str = "false"):
    """Return a mock environment dict for Phoenix config."""
    return {
        "PHOENIX_ENABLED": enabled,
        "PHOENIX_ENDPOINT": "http://phoenix:6006/v1/traces",
        "PHOENIX_PROJECT_NAME": "test",
        "PHOENIX_API_KEY": "key",
        "PHOENIX_UI_URL": "http://phoenix:6006",
    }


class TestResolvePhoenixConfigEnabled:
    """Verify override-wins merge: explicit per-run override takes precedence over global."""

    @patch.dict("os.environ", _env(enabled="true"), clear=False)
    def test_global_true_override_missing(self):
        cfg = resolve_phoenix_config(override=None)
        assert cfg.enabled is True

    @patch.dict("os.environ", _env(enabled="true"), clear=False)
    def test_global_true_override_true(self):
        cfg = resolve_phoenix_config(override={"enabled": True})
        assert cfg.enabled is True

    @patch.dict("os.environ", _env(enabled="true"), clear=False)
    def test_global_true_override_false(self):
        """Explicit override false disables even when global is true."""
        cfg = resolve_phoenix_config(override={"enabled": False})
        assert cfg.enabled is False

    @patch.dict("os.environ", _env(enabled="false"), clear=False)
    def test_global_false_override_missing(self):
        cfg = resolve_phoenix_config(override=None)
        assert cfg.enabled is False

    @patch.dict("os.environ", _env(enabled="false"), clear=False)
    def test_global_false_override_true(self):
        """Override true should enable even when global is false."""
        cfg = resolve_phoenix_config(override={"enabled": True})
        assert cfg.enabled is True

    @patch.dict("os.environ", _env(enabled="false"), clear=False)
    def test_global_false_override_false(self):
        """Both sides disabled → enabled is False."""
        cfg = resolve_phoenix_config(override={"enabled": False})
        assert cfg.enabled is False

    @patch.dict("os.environ", _env(enabled="false"), clear=False)
    def test_global_false_override_none_key(self):
        """Override has enabled key but value is None → inherit global (false)."""
        cfg = resolve_phoenix_config(override={"enabled": None})
        assert cfg.enabled is False

    @patch.dict("os.environ", _env(enabled="true"), clear=False)
    def test_global_true_override_none_key(self):
        """Override has enabled key but value is None → inherit global (true)."""
        cfg = resolve_phoenix_config(override={"enabled": None})
        assert cfg.enabled is True

    @patch.dict("os.environ", _env(enabled="false"), clear=False)
    def test_global_false_empty_override(self):
        """Empty override dict → inherit global."""
        cfg = resolve_phoenix_config(override={})
        assert cfg.enabled is False
