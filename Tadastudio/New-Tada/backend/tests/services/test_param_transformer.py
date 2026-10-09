"""Tests for the config-driven model parameter transformer."""

import json
from pathlib import Path

import pytest

from backend.services.llm_models.param_transformer import (
    ModelParamTransformer,
    TransformResult,
    get_param_transformer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(providers: dict, version: str = "1.0") -> dict:
    return {"version": version, "providers": providers}


def _write_config(tmp_path: Path, config: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Basic plumbing
# ---------------------------------------------------------------------------


class TestTransformResultDefaults:
    def test_defaults(self):
        r = TransformResult()
        assert r.direct_params == {}
        assert r.model_kwargs == {}
        assert r.dropped_params == []


class TestConfigLoading:
    def test_loads_from_default_path(self):
        """The singleton loads the bundled config without errors."""
        t = get_param_transformer()
        assert t._config.get("version") is not None

    def test_missing_config_falls_back_gracefully(self, tmp_path):
        t = ModelParamTransformer(config_path=tmp_path / "nonexistent.json")
        # Should still work — just no rules
        r = t.transform("openai", "gpt-4o", {"max_tokens": 100})
        assert r.direct_params == {"max_tokens": 100}
        assert r.model_kwargs == {}

    def test_invalid_json_falls_back_gracefully(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("NOT JSON", encoding="utf-8")
        t = ModelParamTransformer(config_path=bad)
        r = t.transform("openai", "gpt-4o", {"temperature": 0.5})
        assert r.direct_params == {"temperature": 0.5}

    def test_reload(self, tmp_path):
        cfg1 = _make_config({"openai": {"param_transforms": {}, "models": {}}})
        path = _write_config(tmp_path, cfg1)
        t = ModelParamTransformer(config_path=path)

        # Initially no transforms
        r = t.transform("openai", "gpt-4o", {"max_tokens": 100})
        assert r.direct_params == {"max_tokens": 100}

        # Write new config with a rename rule at provider level
        cfg2 = _make_config(
            {
                "openai": {
                    "param_transforms": {
                        "max_tokens": {
                            "rename_to": "max_completion_tokens",
                            "via": "model_kwargs",
                        },
                    },
                    "models": {},
                }
            }
        )
        _write_config(tmp_path, cfg2)
        t.reload(config_path=path)

        r = t.transform("openai", "gpt-4o", {"max_tokens": 100})
        assert r.model_kwargs == {"max_completion_tokens": 100}
        assert "max_tokens" not in r.direct_params


# ---------------------------------------------------------------------------
# Rename transforms
# ---------------------------------------------------------------------------


class TestRenameTransforms:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "models": {
                        "reasoning-*": {
                            "param_transforms": {
                                "max_tokens": {
                                    "rename_to": "max_completion_tokens",
                                    "via": "model_kwargs",
                                },
                            }
                        },
                        "direct-rename-*": {
                            "param_transforms": {
                                "old_param": {"rename_to": "new_param"},
                            }
                        },
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_rename_via_model_kwargs(self, transformer):
        r = transformer.transform("prov", "reasoning-v1", {"max_tokens": 4096})
        assert r.model_kwargs == {"max_completion_tokens": 4096}
        assert "max_tokens" not in r.direct_params

    def test_rename_direct(self, transformer):
        r = transformer.transform("prov", "direct-rename-v1", {"old_param": "hello"})
        assert r.direct_params == {"new_param": "hello"}
        assert r.model_kwargs == {}

    def test_rename_skipped_when_value_is_none(self, transformer):
        r = transformer.transform("prov", "reasoning-v1", {"max_tokens": None})
        assert r.direct_params == {"max_tokens": None}
        assert r.model_kwargs == {}

    def test_rename_skipped_when_param_absent(self, transformer):
        r = transformer.transform("prov", "reasoning-v1", {"temperature": 0.5})
        assert r.direct_params == {"temperature": 0.5}
        assert r.model_kwargs == {}

    def test_other_params_preserved(self, transformer):
        r = transformer.transform(
            "prov",
            "reasoning-v1",
            {"max_tokens": 1024, "temperature": 0.7, "top_p": 0.9},
        )
        assert r.model_kwargs == {"max_completion_tokens": 1024}
        assert r.direct_params == {"temperature": 0.7, "top_p": 0.9}


# ---------------------------------------------------------------------------
# Drop transforms
# ---------------------------------------------------------------------------


class TestDropTransforms:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "drop_params": ["always_drop"],
                    "models": {
                        "strict-*": {
                            "drop_params": ["temperature", "top_p"],
                        },
                        "lenient-*": {
                            "drop_params": [],
                        },
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_model_drops_override_provider(self, transformer):
        """Model-level drop_params fully replace provider-level."""
        r = transformer.transform(
            "prov", "strict-v1", {"temperature": 0.7, "top_p": 0.9, "always_drop": True}
        )
        assert "temperature" not in r.direct_params
        assert "top_p" not in r.direct_params
        # "always_drop" is NOT dropped because model rules replaced provider rules
        assert r.direct_params["always_drop"] is True
        assert set(r.dropped_params) == {"temperature", "top_p"}

    def test_lenient_model_drops_nothing(self, transformer):
        r = transformer.transform(
            "prov", "lenient-v1", {"temperature": 0.7, "always_drop": True}
        )
        assert r.direct_params == {"temperature": 0.7, "always_drop": True}
        assert r.dropped_params == []

    def test_provider_drops_apply_when_no_model_match(self, transformer):
        r = transformer.transform(
            "prov", "unknown-model", {"always_drop": "val", "keep": 1}
        )
        assert "always_drop" not in r.direct_params
        assert r.direct_params == {"keep": 1}
        assert r.dropped_params == ["always_drop"]

    def test_none_values_not_dropped(self, transformer):
        r = transformer.transform("prov", "strict-v1", {"temperature": None})
        assert r.direct_params == {"temperature": None}
        assert r.dropped_params == []


# ---------------------------------------------------------------------------
# Default transforms
# ---------------------------------------------------------------------------


class TestDefaultTransforms:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "defaults": {"timeout": 60},
                    "models": {
                        "custom-*": {
                            "defaults": {"timeout": 120, "retries": 3},
                        }
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_default_applied_when_missing(self, transformer):
        r = transformer.transform("prov", "custom-v1", {})
        assert r.direct_params["timeout"] == 120
        assert r.direct_params["retries"] == 3

    def test_default_applied_when_none(self, transformer):
        r = transformer.transform("prov", "custom-v1", {"timeout": None})
        assert r.direct_params["timeout"] == 120

    def test_default_not_applied_when_present(self, transformer):
        r = transformer.transform("prov", "custom-v1", {"timeout": 30})
        assert r.direct_params["timeout"] == 30

    def test_provider_defaults_when_no_model_match(self, transformer):
        r = transformer.transform("prov", "other-model", {})
        assert r.direct_params["timeout"] == 60


# ---------------------------------------------------------------------------
# Model pattern matching
# ---------------------------------------------------------------------------


class TestPatternMatching:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "models": {
                        "o1*": {
                            "drop_params": ["temperature"],
                        },
                        "o1-mini*": {
                            "drop_params": ["temperature", "top_p"],
                        },
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_longer_pattern_wins(self, transformer):
        """o1-mini matches both 'o1*' and 'o1-mini*'; longer pattern should win."""
        r = transformer.transform("prov", "o1-mini", {"temperature": 0.5, "top_p": 0.9})
        assert set(r.dropped_params) == {"temperature", "top_p"}

    def test_shorter_pattern_used_when_longer_doesnt_match(self, transformer):
        r = transformer.transform(
            "prov", "o1-preview", {"temperature": 0.5, "top_p": 0.9}
        )
        assert r.dropped_params == ["temperature"]
        assert r.direct_params["top_p"] == 0.9

    def test_case_insensitive(self, transformer):
        r = transformer.transform("prov", "O1-Mini", {"temperature": 0.5, "top_p": 0.9})
        assert set(r.dropped_params) == {"temperature", "top_p"}

    def test_no_match_returns_provider_defaults(self, transformer):
        r = transformer.transform("prov", "gpt-4o", {"temperature": 0.5})
        assert r.direct_params == {"temperature": 0.5}
        assert r.dropped_params == []


# ---------------------------------------------------------------------------
# Unknown provider
# ---------------------------------------------------------------------------


class TestUnknownProvider:
    def test_unknown_provider_passes_through(self, tmp_path):
        cfg = _make_config({"openai": {"param_transforms": {}, "models": {}}})
        t = ModelParamTransformer(config_path=_write_config(tmp_path, cfg))
        r = t.transform("bedrock", "some-model", {"max_tokens": 100})
        assert r.direct_params == {"max_tokens": 100}
        assert r.model_kwargs == {}
        assert r.dropped_params == []


# ---------------------------------------------------------------------------
# Combined: rename + drop + defaults in a single transform
# ---------------------------------------------------------------------------


class TestCombinedTransforms:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "openai": {
                    "param_transforms": {},
                    "models": {
                        "o3*": {
                            "param_transforms": {
                                "max_tokens": {
                                    "rename_to": "max_completion_tokens",
                                    "via": "model_kwargs",
                                },
                            },
                            "drop_params": ["top_p", "presence_penalty"],
                            "defaults": {"reasoning_effort": "medium"},
                        }
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_all_three_operations(self, transformer):
        r = transformer.transform(
            "openai",
            "o3-mini",
            {
                "max_tokens": 4096,
                "temperature": 0.7,
                "top_p": 0.95,
                "presence_penalty": 0.1,
            },
        )
        # Renamed
        assert r.model_kwargs == {"max_completion_tokens": 4096}
        # Dropped
        assert set(r.dropped_params) == {"top_p", "presence_penalty"}
        # Defaults applied (reasoning_effort was missing)
        assert r.direct_params["reasoning_effort"] == "medium"
        # Kept
        assert r.direct_params["temperature"] == 0.7
        # Removed from direct
        assert "max_tokens" not in r.direct_params
        assert "top_p" not in r.direct_params
        assert "presence_penalty" not in r.direct_params


# ---------------------------------------------------------------------------
# API version rules
# ---------------------------------------------------------------------------


class TestApiVersionRules:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "azure": {
                    "param_transforms": {},
                    "api_version_rules": [
                        {
                            "min_version": "2024-10-01",
                            "drop_params": ["max_tokens"],
                            "force_params": {"temperature": 1.0},
                        }
                    ],
                    "models": {
                        "o3*": {
                            "param_transforms": {
                                "max_tokens": {
                                    "rename_to": "max_completion_tokens",
                                    "via": "model_kwargs",
                                }
                            }
                        }
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_api_version_drops_max_tokens(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-10-01",
        )
        assert "max_tokens" not in r.direct_params
        assert "max_tokens" in r.dropped_params

    def test_api_version_forces_temperature(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"temperature": 0.7},
            api_version="2024-10-01",
        )
        assert r.direct_params["temperature"] == 1.0

    def test_api_version_force_skipped_when_already_correct(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"temperature": 1.0},
            api_version="2024-10-01",
        )
        assert r.direct_params["temperature"] == 1.0

    def test_old_api_version_no_changes(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-02-15",
        )
        assert r.direct_params == {"max_tokens": 4096, "temperature": 0.7}
        assert r.dropped_params == []

    def test_no_api_version_no_changes(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
        )
        assert r.direct_params == {"max_tokens": 4096, "temperature": 0.7}
        assert r.dropped_params == []

    def test_unparseable_api_version_no_changes(self, transformer):
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="preview-2025",
        )
        assert r.direct_params == {"max_tokens": 4096, "temperature": 0.7}

    def test_preview_suffix_parsed_correctly(self, transformer):
        """'2025-01-01-preview' should match rules with min_version '2024-10-01'."""
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2025-01-01-preview",
        )
        assert "max_tokens" in r.dropped_params
        assert r.direct_params["temperature"] == 1.0

    def test_old_preview_version_no_changes(self, transformer):
        """'2024-02-15-preview' is older than min_version, rules should not fire."""
        r = transformer.transform(
            "azure",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-02-15-preview",
        )
        assert r.direct_params == {"max_tokens": 4096, "temperature": 0.7}
        assert r.dropped_params == []

    def test_api_version_drop_runs_before_model_rename(self, transformer):
        """When api_version drops max_tokens, the model rename should not fire."""
        r = transformer.transform(
            "azure",
            "o3-mini",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-12-01",
        )
        # max_tokens was dropped by api_version rule before model rename could see it
        assert "max_tokens" in r.dropped_params
        assert r.model_kwargs == {}
        assert "max_tokens" not in r.direct_params

    def test_model_rename_works_with_old_api_version(self, transformer):
        """With old api_version, model rename should still apply."""
        r = transformer.transform(
            "azure",
            "o3-mini",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-02-15",
        )
        assert r.model_kwargs == {"max_completion_tokens": 4096}
        assert "max_tokens" not in r.direct_params

    def test_multiple_rules_cumulate(self, tmp_path):
        """Multiple api_version_rules can match and their effects stack."""
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "api_version_rules": [
                        {
                            "min_version": "2024-01-01",
                            "drop_params": ["param_a"],
                            "force_params": {},
                        },
                        {
                            "min_version": "2024-06-01",
                            "drop_params": ["param_b"],
                            "force_params": {"temperature": 1.0},
                        },
                    ],
                    "models": {},
                }
            }
        )
        t = ModelParamTransformer(config_path=_write_config(tmp_path, cfg))
        r = t.transform(
            "prov",
            "model",
            {"param_a": 1, "param_b": 2, "temperature": 0.5},
            api_version="2025-01-01",
        )
        assert "param_a" in r.dropped_params
        assert "param_b" in r.dropped_params
        assert r.direct_params["temperature"] == 1.0

    def test_only_first_rule_matches_when_version_between(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "api_version_rules": [
                        {
                            "min_version": "2024-01-01",
                            "drop_params": ["param_a"],
                            "force_params": {},
                        },
                        {
                            "min_version": "2025-01-01",
                            "drop_params": ["param_b"],
                            "force_params": {},
                        },
                    ],
                    "models": {},
                }
            }
        )
        t = ModelParamTransformer(config_path=_write_config(tmp_path, cfg))
        r = t.transform(
            "prov",
            "model",
            {"param_a": 1, "param_b": 2},
            api_version="2024-06-01",
        )
        assert "param_a" in r.dropped_params
        assert "param_b" not in r.dropped_params
        assert r.direct_params["param_b"] == 2


# ---------------------------------------------------------------------------
# Force params (model-level)
# ---------------------------------------------------------------------------


class TestForceParams:
    @pytest.fixture()
    def transformer(self, tmp_path):
        cfg = _make_config(
            {
                "prov": {
                    "param_transforms": {},
                    "models": {
                        "strict-*": {
                            "force_params": {"temperature": 1.0},
                        },
                    },
                }
            }
        )
        return ModelParamTransformer(config_path=_write_config(tmp_path, cfg))

    def test_force_overrides_existing_value(self, transformer):
        r = transformer.transform("prov", "strict-v1", {"temperature": 0.7})
        assert r.direct_params["temperature"] == 1.0

    def test_force_skipped_when_already_correct(self, transformer):
        r = transformer.transform("prov", "strict-v1", {"temperature": 1.0})
        assert r.direct_params["temperature"] == 1.0

    def test_force_does_not_add_missing_param(self, transformer):
        """force_params only overrides existing values, does not add new ones."""
        r = transformer.transform("prov", "strict-v1", {"max_tokens": 100})
        assert "temperature" not in r.direct_params


# ---------------------------------------------------------------------------
# Integration: test against the real bundled config
# ---------------------------------------------------------------------------


class TestBundledConfig:
    """Tests against the actual model_params_config.json shipped in the repo."""

    @pytest.fixture()
    def transformer(self):
        return get_param_transformer()

    @pytest.mark.parametrize(
        "provider,model",
        [
            ("openai", "o1"),
            ("openai", "o1-mini"),
            ("openai", "o1-preview"),
            ("openai", "o3"),
            ("openai", "o3-mini"),
            ("openai", "o4-mini"),
            ("openai", "gpt-5"),
            ("azure_openai", "o1"),
            ("azure_openai", "o3-mini"),
            ("azure_openai", "gpt-5"),
        ],
    )
    def test_max_tokens_renamed_for_reasoning_models(
        self, transformer, provider, model
    ):
        r = transformer.transform(provider, model, {"max_tokens": 2048})
        assert r.model_kwargs == {"max_completion_tokens": 2048}
        assert "max_tokens" not in r.direct_params

    @pytest.mark.parametrize(
        "provider,model",
        [
            ("openai", "gpt-4o"),
            ("openai", "gpt-4"),
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-3.5-turbo"),
            ("azure_openai", "gpt-4o"),
            ("anthropic", "claude-3-opus-20240229"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
        ],
    )
    def test_max_tokens_unchanged_for_standard_models(
        self, transformer, provider, model
    ):
        r = transformer.transform(provider, model, {"max_tokens": 2048})
        assert r.direct_params["max_tokens"] == 2048
        assert r.model_kwargs == {}

    def test_o1_drops_temperature(self, transformer):
        r = transformer.transform(
            "openai", "o1", {"temperature": 0.7, "max_tokens": 100}
        )
        assert "temperature" in r.dropped_params
        assert "temperature" not in r.direct_params

    def test_o3_keeps_temperature(self, transformer):
        r = transformer.transform(
            "openai", "o3-mini", {"temperature": 0.7, "max_tokens": 100}
        )
        assert "temperature" not in r.dropped_params
        assert r.direct_params.get("temperature") == 0.7

    def test_none_max_tokens_not_renamed(self, transformer):
        r = transformer.transform("openai", "o3-mini", {"max_tokens": None})
        assert r.model_kwargs == {}
        assert r.direct_params == {"max_tokens": None}

    def test_empty_params(self, transformer):
        r = transformer.transform("openai", "o3-mini", {})
        assert r.direct_params == {}
        assert r.model_kwargs == {}
        assert r.dropped_params == []

    # -- Azure API version rules (bundled config) --

    def test_azure_new_api_preserves_max_tokens(self, transformer):
        """No api_version_rules — max_tokens passes through for standard models."""
        r = transformer.transform(
            "azure_openai",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-10-01",
        )
        assert r.direct_params["max_tokens"] == 4096
        assert r.direct_params["temperature"] == 0.7

    def test_azure_new_api_preserves_temperature(self, transformer):
        """No api_version_rules — temperature passes through for standard models."""
        r = transformer.transform(
            "azure_openai",
            "gpt-4o",
            {"temperature": 0.5},
            api_version="2024-11-01",
        )
        assert r.direct_params["temperature"] == 0.5

    def test_azure_old_api_preserves_params(self, transformer):
        r = transformer.transform(
            "azure_openai",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-02-15",
        )
        assert r.direct_params["max_tokens"] == 4096
        assert r.direct_params["temperature"] == 0.7

    def test_azure_new_api_with_reasoning_model(self, transformer):
        """No api_version_rules — model rename fires regardless of api_version."""
        r = transformer.transform(
            "azure_openai",
            "o3-mini",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2025-01-01",
        )
        assert r.model_kwargs == {"max_completion_tokens": 4096}
        assert "max_tokens" not in r.direct_params

    def test_azure_old_api_with_reasoning_model(self, transformer):
        """Old API version: model rename fires, converting max_tokens to max_completion_tokens."""
        r = transformer.transform(
            "azure_openai",
            "o3-mini",
            {"max_tokens": 4096, "temperature": 0.7},
            api_version="2024-02-15",
        )
        assert r.model_kwargs == {"max_completion_tokens": 4096}
        assert "max_tokens" not in r.direct_params

    def test_azure_preview_api_version_preserves_params(self, transformer):
        """No api_version_rules — params pass through for standard models on preview versions."""
        r = transformer.transform(
            "azure_openai",
            "gpt-4o",
            {"max_tokens": 4096, "temperature": 0.5},
            api_version="2025-01-01-preview",
        )
        assert r.direct_params["max_tokens"] == 4096
        assert r.direct_params["temperature"] == 0.5
