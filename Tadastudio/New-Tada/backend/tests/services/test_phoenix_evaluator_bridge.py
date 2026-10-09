"""Tests for PhoenixEvaluatorBridge."""

import json
import sys
from unittest.mock import MagicMock, patch

from backend.services.phoenix.config import PhoenixConfig
from backend.services.phoenix.evaluators import (
    PhoenixEvaluatorBridge,
    _create_phoenix_model_from_deployment,
    _create_quality_judge_evaluator,
    _extract_context,
    _extract_tool_calls,
    _extract_user_input,
    _resolve_deployment,
    _score_from_result,
)


def _make_config(
    enabled: bool = True,
    eval_penalty_enabled: bool = False,
    eval_model_deployment_id: str | None = None,
) -> PhoenixConfig:
    return PhoenixConfig(
        enabled=enabled,
        endpoint="http://phoenix:6006/v1/traces",
        project_name="test",
        api_key="key",
        ui_url="http://phoenix:6006",
        eval_penalty_enabled=eval_penalty_enabled,
        eval_model_deployment_id=eval_model_deployment_id,
    )


def _mock_score(score=None, label=None, explanation=None):
    """Create a mock phoenix Score object."""
    s = MagicMock()
    s.score = score
    s.label = label
    s.explanation = explanation
    return s


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_extract_tool_calls_from_message_structure():
    """Tool calls are extracted from message_structure.messages."""
    node_execs = [
        {
            "message_structure": {
                "messages": [
                    {"role": "user", "content": "hello"},
                    {
                        "role": "assistant",
                        "content": "let me search",
                        "tool_calls": [
                            {"name": "web_search"},
                            {"name": "document_search"},
                        ],
                    },
                ]
            },
            "node_metadata": {},
        }
    ]
    calls = _extract_tool_calls(node_execs)
    names = [c["name"] for c in calls]
    assert "web_search" in names
    assert "document_search" in names


def test_extract_tool_calls_from_tool_node_types():
    """Tool-type node executions are collected."""
    node_execs = [
        {"node_type": "DOCUMENT_SEARCH", "node_name": "Search KB", "node_metadata": {}},
        {"node_type": "HTTP_REQUEST", "node_name": "Call API", "node_metadata": {}},
    ]
    calls = _extract_tool_calls(node_execs)
    names = [c["name"] for c in calls]
    assert "Search KB" in names
    assert "Call API" in names


def test_extract_tool_calls_from_node_metadata_legacy():
    """Legacy tool_calls in node_metadata are still collected."""
    node_execs = [
        {"node_metadata": {"tool_calls": [{"name": "calc"}]}},
    ]
    calls = _extract_tool_calls(node_execs)
    assert len(calls) == 1
    assert calls[0]["name"] == "calc"


def test_extract_context_from_document_search_output():
    """Context is extracted from DOCUMENT_SEARCH node output_data."""
    node_execs = [
        {"node_type": "AGENT", "output_data": "some agent output", "node_metadata": {}},
        {
            "node_type": "DOCUMENT_SEARCH",
            "output_data": "Retrieved: doc content here",
            "node_metadata": {},
        },
    ]
    ctx = _extract_context(node_execs)
    assert ctx is not None
    assert "doc content here" in ctx


def test_extract_context_returns_none_when_no_docs():
    """No context when no DOCUMENT_SEARCH nodes exist."""
    node_execs = [
        {"node_type": "AGENT", "output_data": "output", "node_metadata": {}},
    ]
    assert _extract_context(node_execs) is None


def test_extract_user_input_from_input_data():
    """User input extracted from node input_data."""
    node_execs = [
        {"input_data": {"message": "What is the unlock procedure?"}},
    ]
    assert _extract_user_input(node_execs) == "What is the unlock procedure?"


def test_extract_user_input_from_message_structure():
    """User input extracted from message_structure user messages."""
    node_execs = [
        {
            "input_data": None,
            "message_structure": {
                "messages": [
                    {"role": "user", "content": "Help me unlock"},
                    {"role": "assistant", "content": "Sure"},
                ]
            },
        },
    ]
    assert _extract_user_input(node_execs) == "Help me unlock"


def test_score_from_result_list_with_score():
    """Score extracted from List[Score] with numeric score."""
    scores = [_mock_score(score=0.85)]
    assert _score_from_result(scores) == 0.85


def test_score_from_result_list_with_label():
    """Binary label mapped to raw evaluator score when numeric score is None.

    For HallucinationEvaluator: "hallucinated" → 1.0, "factual" → 0.0
    (the caller inverts to faithfulness).
    """
    scores = [_mock_score(score=None, label="factual")]
    assert _score_from_result(scores) == 0.0
    scores2 = [_mock_score(score=None, label="hallucinated")]
    assert _score_from_result(scores2) == 1.0
    scores3 = [_mock_score(score=None, label="correct")]
    assert _score_from_result(scores3) == 1.0


def test_score_from_result_empty():
    assert _score_from_result([]) is None
    assert _score_from_result(None) is None


# ---------------------------------------------------------------------------
# Bridge integration tests
# ---------------------------------------------------------------------------


def test_skipped_when_disabled():
    result = PhoenixEvaluatorBridge.run_supplementary_evals(
        actual_output="hello",
        context="some context",
        target_type="workflow",
        node_executions=[],
        phoenix_config=_make_config(enabled=False),
    )
    assert result["status"] == "skipped"
    assert result["quality_penalty"] == 0.0


def test_not_installed_when_import_fails():
    with patch.dict(sys.modules, {"phoenix.evals": None}):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="hello",
            context="some context",
            target_type="agent",
            node_executions=[],
            phoenix_config=_make_config(),
        )
    assert result["status"] == "not_installed"
    assert result["quality_penalty"] == 0.0


def test_skipped_when_no_context_and_no_tools():
    """When context is None (hallucination skipped) and no tool calls, result is skipped."""
    mock_evals = MagicMock()
    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="hello",
            context=None,
            target_type="model",
            node_executions=[],
            phoenix_config=_make_config(),
        )
    assert result["status"] == "skipped"
    assert result["quality_penalty"] == 0.0
    assert result["evaluations"] == {}


def test_hallucination_evaluator_called_with_dict():
    """HallucinationEvaluator is called with a dict (not DataFrame)."""
    # Phoenix HallucinationEvaluator: score=0.15 means 15% hallucinated
    mock_score = _mock_score(
        score=0.15, label="factual", explanation="Grounded in context"
    )

    mock_hallu_cls = MagicMock()
    mock_hallu_instance = MagicMock()
    mock_hallu_instance.evaluate.return_value = [mock_score]
    mock_hallu_cls.return_value = mock_hallu_instance
    mock_hallu_cls.__name__ = "HallucinationEvaluator"

    mock_llm_cls = MagicMock()

    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls

    mock_metrics = MagicMock()
    mock_metrics.HallucinationEvaluator = mock_hallu_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="some output",
            context="some context",
            target_type="workflow",
            node_executions=[],
            phoenix_config=_make_config(),
        )

    assert result["status"] == "ok"
    faith = result["evaluations"]["faithfulness"]
    assert faith["status"] == "ok"
    assert faith["score"] == 0.85  # 1.0 - 0.15 (hallucination inverted to faithfulness)
    assert faith["label"] == "factual"
    assert faith["evaluator"] == "HallucinationEvaluator"

    # Verify evaluate was called with a dict, not a DataFrame
    call_args = mock_hallu_instance.evaluate.call_args
    eval_input = call_args[0][0]
    assert isinstance(eval_input, dict)
    assert "input" in eval_input
    assert "output" in eval_input
    assert "context" in eval_input


def test_hallucination_penalty_applied_when_enabled():
    """Quality penalty applied when faithfulness < 0.3 and penalty enabled."""
    # Phoenix score=0.9 means 90% hallucinated → faithfulness=0.1 → penalty triggered
    mock_score = _mock_score(score=0.9, label="hallucinated")

    mock_hallu_cls = MagicMock()
    mock_hallu_instance = MagicMock()
    mock_hallu_instance.evaluate.return_value = [mock_score]
    mock_hallu_cls.return_value = mock_hallu_instance
    mock_hallu_cls.__name__ = "HallucinationEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    mock_metrics = MagicMock()
    mock_metrics.HallucinationEvaluator = mock_hallu_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="made up stuff",
            context="actual facts",
            target_type="workflow",
            node_executions=[],
            phoenix_config=_make_config(eval_penalty_enabled=True),
        )

    assert result["quality_penalty"] == 10.0


def test_hallucination_penalty_not_applied_when_disabled():
    """Quality penalty NOT applied when eval_penalty_enabled is False."""
    # Phoenix score=0.9 means 90% hallucinated → faithfulness=0.1, but penalty disabled
    mock_score = _mock_score(score=0.9, label="hallucinated")

    mock_hallu_cls = MagicMock()
    mock_hallu_instance = MagicMock()
    mock_hallu_instance.evaluate.return_value = [mock_score]
    mock_hallu_cls.return_value = mock_hallu_instance
    mock_hallu_cls.__name__ = "HallucinationEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    mock_metrics = MagicMock()
    mock_metrics.HallucinationEvaluator = mock_hallu_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="made up stuff",
            context="actual facts",
            target_type="workflow",
            node_executions=[],
            phoenix_config=_make_config(eval_penalty_enabled=False),
        )

    assert result["quality_penalty"] == 0.0


def test_tool_selection_evaluator_called_with_dict():
    """ToolSelectionEvaluator is called with a dict containing input, available_tools, tool_selection."""
    mock_score = _mock_score(score=1.0, label="correct", explanation="Good tool choice")

    mock_tool_cls = MagicMock()
    mock_tool_instance = MagicMock()
    mock_tool_instance.evaluate.return_value = [mock_score]
    mock_tool_cls.return_value = mock_tool_instance
    mock_tool_cls.__name__ = "ToolSelectionEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    mock_metrics = MagicMock()
    mock_metrics.ToolSelectionEvaluator = mock_tool_cls

    node_execs = [
        {
            "node_type": "AGENT",
            "node_name": "Investigator",
            "input_data": {"message": "Check account status"},
            "message_structure": {
                "messages": [
                    {"role": "user", "content": "Check account status"},
                    {
                        "role": "assistant",
                        "content": "Searching...",
                        "tool_calls": [{"name": "document_search"}],
                    },
                ]
            },
            "node_metadata": {},
        }
    ]

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="Account is locked due to...",
            context=None,
            target_type="agent",
            node_executions=node_execs,
            phoenix_config=_make_config(),
        )

    assert result["status"] == "ok"
    tool = result["evaluations"]["tool_selection"]
    assert tool["status"] == "ok"
    assert tool["evaluator"] == "ToolSelectionEvaluator"
    assert tool["score"] == 1.0
    assert tool["tool_call_count"] == 1
    assert "document_search" in tool["tools_used"]

    # Verify evaluate was called with a dict, not a DataFrame
    call_args = mock_tool_instance.evaluate.call_args
    eval_input = call_args[0][0]
    assert isinstance(eval_input, dict)
    assert "input" in eval_input
    assert "available_tools" in eval_input
    assert "tool_selection" in eval_input


def test_tool_selection_falls_back_to_invocation_evaluator():
    """When ToolSelectionEvaluator is unavailable, falls back to ToolInvocationEvaluator."""
    mock_score = _mock_score(score=0.75, label="correct")

    mock_invocation_cls = MagicMock()
    mock_invocation_instance = MagicMock()
    mock_invocation_instance.evaluate.return_value = [mock_score]
    mock_invocation_cls.return_value = mock_invocation_instance
    mock_invocation_cls.__name__ = "ToolInvocationEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    del mock_evals.ToolSelectionEvaluator

    mock_metrics = MagicMock()
    del mock_metrics.ToolSelectionEvaluator
    mock_metrics.ToolInvocationEvaluator = mock_invocation_cls

    node_execs = [
        {
            "node_type": "DOCUMENT_SEARCH",
            "node_name": "Search KB",
            "node_metadata": {},
        }
    ]

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="output",
            context=None,
            target_type="agent",
            node_executions=node_execs,
            phoenix_config=_make_config(),
        )

    assert result["status"] == "ok"
    tool = result["evaluations"]["tool_selection"]
    assert tool["status"] == "ok"
    assert tool["evaluator"] == "ToolInvocationEvaluator"
    assert tool["score"] == 0.75


def test_no_tool_evaluator_available():
    """When neither evaluator is available, tool metadata is still recorded."""
    mock_llm_cls = MagicMock()

    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    del mock_evals.ToolSelectionEvaluator
    del mock_evals.ToolInvocationEvaluator
    del mock_evals.HallucinationEvaluator

    mock_metrics = MagicMock()
    del mock_metrics.ToolSelectionEvaluator
    del mock_metrics.ToolInvocationEvaluator
    del mock_metrics.HallucinationEvaluator

    node_execs = [
        {
            "node_type": "AGENT",
            "node_name": "Agent",
            "node_metadata": {"tool_calls": [{"name": "calc"}]},
        }
    ]

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="output",
            context=None,
            target_type="agent",
            node_executions=node_execs,
            phoenix_config=_make_config(),
        )

    assert result["status"] == "ok"
    tool = result["evaluations"]["tool_selection"]
    assert tool["status"] == "no_evaluator"
    assert tool["tool_call_count"] == 1


def test_phoenix_results_merged_into_quality_diagnostics():
    """Verify result format is compatible with scoring.py quality diagnostics merge."""
    # Phoenix score=0.05 means 5% hallucinated → faithfulness=0.95
    mock_score = _mock_score(score=0.05, label="factual")

    mock_hallu_cls = MagicMock()
    mock_hallu_instance = MagicMock()
    mock_hallu_instance.evaluate.return_value = [mock_score]
    mock_hallu_cls.return_value = mock_hallu_instance
    mock_hallu_cls.__name__ = "HallucinationEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    mock_metrics = MagicMock()
    mock_metrics.HallucinationEvaluator = mock_hallu_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="some output",
            context="some context",
            target_type="workflow",
            node_executions=[],
            phoenix_config=_make_config(),
        )

    # scoring.py checks: phoenix_eval_result.get("status") == "ok"
    # then sets quality_diag["phoenix"] = phoenix_eval_result
    assert result["status"] == "ok"
    assert "evaluations" in result
    assert (
        result["evaluations"]["faithfulness"]["evaluator"] == "HallucinationEvaluator"
    )
    assert result["evaluations"]["faithfulness"]["score"] == 0.95
    assert "quality_penalty" in result


def test_context_auto_extracted_from_document_search_nodes():
    """When context=None, bridge extracts from DOCUMENT_SEARCH output_data."""
    # Phoenix score=0.1 means 10% hallucinated → faithfulness=0.9
    mock_score = _mock_score(score=0.1, label="factual")

    mock_hallu_cls = MagicMock()
    mock_hallu_instance = MagicMock()
    mock_hallu_instance.evaluate.return_value = [mock_score]
    mock_hallu_cls.return_value = mock_hallu_instance
    mock_hallu_cls.__name__ = "HallucinationEvaluator"

    mock_llm_cls = MagicMock()
    mock_evals = MagicMock()
    mock_evals.LLM = mock_llm_cls
    mock_metrics = MagicMock()
    mock_metrics.HallucinationEvaluator = mock_hallu_cls

    node_execs = [
        {
            "node_type": "DOCUMENT_SEARCH",
            "node_name": "Search KB",
            "output_data": "Account unlock procedure: Step 1...",
            "node_metadata": {},
        },
        {
            "node_type": "AGENT",
            "node_name": "Investigator",
            "input_data": {"message": "How to unlock?"},
            "output_data": {"result": "Follow the procedure"},
            "node_metadata": {},
        },
    ]

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="Follow the unlock procedure...",
            context=None,  # Should auto-extract from DOCUMENT_SEARCH
            target_type="workflow",
            node_executions=node_execs,
            phoenix_config=_make_config(),
        )

    assert result["status"] == "ok"
    assert "faithfulness" in result["evaluations"]
    # Verify the evaluator was called (context was extracted)
    mock_hallu_instance.evaluate.assert_called_once()
    eval_input = mock_hallu_instance.evaluate.call_args[0][0]
    assert "Account unlock procedure" in eval_input["context"]


# ---------------------------------------------------------------------------
# Model deployment resolution tests
# ---------------------------------------------------------------------------


def test_resolve_deployment_uses_explicit_id():
    """When eval_model_deployment_id is set, it resolves that specific deployment."""
    mock_dep = {
        "id": "dep-123",
        "provider": "openai",
        "model_name": "gpt-4o",
        "credentials": {"api_key": "sk-test"},
        "settings": {},
    }

    with patch("backend.services.model_deployment.ModelDeploymentService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_deployment.return_value = mock_dep

        config = _make_config(eval_model_deployment_id="dep-123")
        result = _resolve_deployment(config)

    assert result is not None
    assert result["id"] == "dep-123"
    instance.get_deployment.assert_called_once_with("dep-123", include_credentials=True)


def test_resolve_deployment_falls_back_to_default():
    """When no explicit ID, falls back to default LLM deployment with credentials."""
    mock_dep = {
        "id": "default-dep",
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "credentials": {"api_key": "sk-default"},
        "settings": {},
    }

    with patch("backend.services.model_deployment.ModelDeploymentService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_default_deployment.return_value = mock_dep
        instance.get_deployment.return_value = mock_dep

        config = _make_config()
        result = _resolve_deployment(config)

    assert result is not None
    assert result["id"] == "default-dep"
    instance.get_default_deployment.assert_called_once_with(model_type="llm")
    # Should also fetch with credentials
    instance.get_deployment.assert_called_once_with(
        "default-dep", include_credentials=True
    )


def test_resolve_deployment_returns_none_on_failure():
    """Returns None when deployment service raises."""
    with patch(
        "backend.services.model_deployment.ModelDeploymentService",
        side_effect=Exception("DB down"),
    ):
        config = _make_config()
        result = _resolve_deployment(config)

    assert result is None


def test_create_phoenix_model_from_openai_deployment():
    """OpenAI deployment creates a Phoenix LLM with correct params."""
    deployment = {
        "id": "dep-1",
        "provider": "openai",
        "model_name": "gpt-4o",
        "credentials": {"api_key": "sk-test123"},
        "settings": {},
    }

    mock_llm_cls = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "phoenix.evals": MagicMock(LLM=mock_llm_cls),
        },
    ):
        result = _create_phoenix_model_from_deployment(deployment)

    assert result is not None
    mock_llm_cls.assert_called_once()
    call_kwargs = mock_llm_cls.call_args[1]
    assert call_kwargs["provider"] == "openai"
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["api_key"] == "sk-test123"


def test_create_phoenix_model_from_azure_deployment():
    """Azure OpenAI deployment passes azure_endpoint and azure_deployment."""
    deployment = {
        "id": "dep-2",
        "provider": "azure_openai",
        "model_name": "gpt-4o",
        "credentials": {"api_key": "az-key"},
        "settings": {
            "azure_endpoint": "https://myresource.openai.azure.com",
            "deployment_name": "my-gpt4o",
            "api_version": "2024-06-01",
        },
    }

    mock_llm_cls = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "phoenix.evals": MagicMock(LLM=mock_llm_cls),
        },
    ):
        result = _create_phoenix_model_from_deployment(deployment)

    assert result is not None
    call_kwargs = mock_llm_cls.call_args[1]
    assert call_kwargs["provider"] == "azure"
    assert call_kwargs["azure_endpoint"] == "https://myresource.openai.azure.com"
    assert call_kwargs["azure_deployment"] == "my-gpt4o"
    assert call_kwargs["api_version"] == "2024-06-01"


def test_create_phoenix_model_from_azure_managed_identity():
    """Azure OpenAI deployment without api_key uses managed identity token provider."""
    deployment = {
        "id": "dep-mi",
        "provider": "azure_openai",
        "model_name": "gpt-4o",
        "credentials": {},  # No API key — managed identity
        "settings": {
            "azure_endpoint": "https://myresource.openai.azure.com",
            "deployment_name": "my-gpt4o",
            "api_version": "2024-06-01",
            "use_managed_identity": True,
        },
    }

    mock_llm_cls = MagicMock()
    mock_token_provider = MagicMock()

    with (
        patch.dict(
            sys.modules,
            {
                "phoenix.evals": MagicMock(LLM=mock_llm_cls),
            },
        ),
        patch(
            "backend.services.phoenix.evaluators._get_azure_token_provider",
            return_value=mock_token_provider,
        ),
    ):
        result = _create_phoenix_model_from_deployment(deployment)

    assert result is not None
    call_kwargs = mock_llm_cls.call_args[1]
    assert call_kwargs["provider"] == "azure"
    assert call_kwargs["azure_ad_token_provider"] is mock_token_provider
    assert "api_key" not in call_kwargs


def test_create_phoenix_model_from_anthropic_deployment():
    """Anthropic deployment creates a Phoenix LLM with correct params."""
    deployment = {
        "id": "dep-3",
        "provider": "anthropic",
        "model_name": "claude-sonnet-4-20250514",
        "credentials": {"api_key": "sk-ant-test"},
        "settings": {},
    }

    mock_llm_cls = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "phoenix.evals": MagicMock(LLM=mock_llm_cls),
        },
    ):
        result = _create_phoenix_model_from_deployment(deployment)

    assert result is not None
    mock_llm_cls.assert_called_once()
    call_kwargs = mock_llm_cls.call_args[1]
    assert call_kwargs["provider"] == "anthropic"
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"
    assert call_kwargs["api_key"] == "sk-ant-test"


# ---------------------------------------------------------------------------
# LLM Judge evaluator tests
# ---------------------------------------------------------------------------


def test_quality_judge_evaluator_returns_score():
    """QualityJudgeEvaluator calls llm.generate_text and returns normalised score."""

    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 82,
            "reasoning": "Well structured response",
            "criteria_scores": {
                "Coherence": 85,
                "Relevance": 80,
                "Instruction-following": 81,
            },
        }
    )

    evaluator = _create_quality_judge_evaluator(mock_llm, has_expected=False)

    result = evaluator._evaluate(
        {
            "actual_output": "Quantum computing uses qubits...",
        }
    )

    assert len(result) == 1
    score = result[0]
    assert score.score == 0.82  # 82 / 100
    assert score.label == "good"
    assert score.explanation == "Well structured response"
    assert score.metadata["quality_score_raw"] == 82
    assert score.metadata["criteria_scores"] == {
        "Coherence": 85.0,
        "Relevance": 80.0,
        "Instruction-following": 81.0,
    }

    # Verify generate_text was called (free-text JSON, not structured output)
    mock_llm.generate_text.assert_called_once()


def test_quality_judge_evaluator_with_expected():
    """QualityJudgeEvaluator includes expected_output placeholder when has_expected=True."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 95,
            "reasoning": "Matches expected output",
            "criteria_scores": {
                "Correctness": 96,
                "Completeness": 94,
                "Coherence": 95,
                "Relevance": 95,
            },
        }
    )

    evaluator = _create_quality_judge_evaluator(mock_llm, has_expected=True)

    # The prompt template should contain expected_output variable
    assert "expected_output" in evaluator.prompt_template.variables

    result = evaluator._evaluate(
        {
            "actual_output": "The answer is correct",
            "expected_output": "The correct answer",
        }
    )

    assert result[0].score == 0.95
    assert result[0].label == "excellent"
    assert result[0].metadata["criteria_scores"]["Correctness"] == 96.0


def test_quality_judge_evaluator_with_custom_criteria():
    """QualityJudgeEvaluator uses custom judge_criteria in the prompt."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 70,
            "reasoning": "Meets custom criteria",
            "criteria_scores": {
                "Accuracy": 75,
                "Tone": 65,
            },
        }
    )

    custom_criteria = {
        "Accuracy": "Must be factually correct",
        "Tone": "Must be professional",
    }
    evaluator = _create_quality_judge_evaluator(
        mock_llm, has_expected=False, judge_criteria=custom_criteria
    )

    result = evaluator._evaluate(
        {
            "actual_output": "Some output text",
        }
    )

    assert result[0].score == 0.70
    assert result[0].metadata["criteria_scores"] == {"Accuracy": 75.0, "Tone": 65.0}

    # Verify the prompt contains custom criteria text
    prompt_arg = mock_llm.generate_text.call_args[1]["prompt"]
    user_content = prompt_arg[1]["content"]
    assert "Accuracy" in user_content
    assert "Must be factually correct" in user_content
    assert "Tone" in user_content


def test_llm_judge_bridge_integration():
    """LLM judge evaluation runs end-to-end via the bridge with expected_output and criteria_scores."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 75,
            "reasoning": "Good but minor issues",
            "criteria_scores": {"Accuracy": 80},
        }
    )

    config = _make_config()
    config.eval_llm_judge_enabled = True
    config.eval_faithfulness_enabled = False
    config.eval_tool_selection_enabled = False

    with patch(
        "backend.services.phoenix.evaluators._create_llm_model",
        return_value=mock_llm,
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="Quantum computing uses qubits...",
            context=None,
            target_type="workflow",
            node_executions=[{"input_data": {"message": "Explain quantum computing"}}],
            phoenix_config=config,
            expected_output="Quantum computing leverages qubits for parallel computation.",
            judge_criteria={"Accuracy": "Must be factually correct"},
        )

    assert result["status"] == "ok"
    judge = result["evaluations"]["llm_judge"]
    assert judge["status"] == "ok"
    assert judge["score"] == 0.75
    assert judge["quality_score_raw"] == 75
    assert judge["label"] == "good"
    assert judge["evaluator"] == "QualityJudgeEvaluator"
    assert judge["criteria_scores"] == {"Accuracy": 80.0}

    # Verify expected_output was passed to generate_text prompt
    prompt_arg = mock_llm.generate_text.call_args[1]["prompt"]
    user_content = prompt_arg[1]["content"]
    assert "Quantum computing leverages qubits" in user_content
    assert "Accuracy" in user_content


def test_llm_judge_skipped_when_disabled():
    """LLM judge block is not executed when eval_llm_judge_enabled is False."""
    mock_evals = MagicMock()

    mock_metrics = MagicMock()
    del mock_metrics.HallucinationEvaluator
    del mock_metrics.ToolSelectionEvaluator
    del mock_metrics.ToolInvocationEvaluator

    config = _make_config()
    config.eval_llm_judge_enabled = False
    config.eval_faithfulness_enabled = False
    config.eval_tool_selection_enabled = False

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.evals": mock_evals,
            "phoenix.evals.metrics": mock_metrics,
        },
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="some output",
            context=None,
            target_type="workflow",
            node_executions=[{"input_data": {"message": "hello"}}],
            phoenix_config=config,
        )

    assert result["status"] == "skipped"
    assert "llm_judge" not in result["evaluations"]


def test_quality_judge_evaluator_with_context_description():
    """QualityJudgeEvaluator includes context_description in prompt when provided."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 85,
            "reasoning": "Well aligned with context",
        }
    )

    evaluator = _create_quality_judge_evaluator(
        mock_llm, has_expected=False, has_context_description=True
    )

    result = evaluator._evaluate(
        {
            "actual_output": "Some output text",
            "context_description": "This workflow answers customer FAQ questions",
        }
    )

    assert result[0].score == 0.85

    # Verify the prompt contains the context section
    prompt_arg = mock_llm.generate_text.call_args[1]["prompt"]
    user_content = prompt_arg[1]["content"]
    assert "## Context" in user_content
    assert "customer FAQ questions" in user_content


def test_quality_judge_evaluator_without_context_description():
    """QualityJudgeEvaluator omits ## Context section when has_context_description=False."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 60,
            "reasoning": "Fair output",
        }
    )

    evaluator = _create_quality_judge_evaluator(
        mock_llm, has_expected=False, has_context_description=False
    )

    result = evaluator._evaluate(
        {
            "actual_output": "Some output text",
        }
    )

    assert result[0].score == 0.60

    # Verify the prompt does NOT contain the context section
    prompt_arg = mock_llm.generate_text.call_args[1]["prompt"]
    user_content = prompt_arg[1]["content"]
    assert "## Context" not in user_content


def test_llm_judge_bridge_with_context_description():
    """LLM judge evaluation passes context_description through the bridge."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.return_value = json.dumps(
        {
            "quality_score": 80,
            "reasoning": "Good with context",
        }
    )

    config = _make_config()
    config.eval_llm_judge_enabled = True
    config.eval_faithfulness_enabled = False
    config.eval_tool_selection_enabled = False

    with patch(
        "backend.services.phoenix.evaluators._create_llm_model",
        return_value=mock_llm,
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="The answer is 42",
            context=None,
            target_type="workflow",
            node_executions=[{"input_data": {"message": "What is the answer?"}}],
            phoenix_config=config,
            context_description="A workflow that answers trivia questions",
        )

    assert result["status"] == "ok"
    judge = result["evaluations"]["llm_judge"]
    assert judge["status"] == "ok"
    assert judge["score"] == 0.80

    # Verify context_description was passed into the prompt
    prompt_arg = mock_llm.generate_text.call_args[1]["prompt"]
    user_content = prompt_arg[1]["content"]
    assert "## Context" in user_content
    assert "trivia questions" in user_content


def test_llm_judge_error_is_non_fatal():
    """LLM judge errors are caught and recorded without crashing."""
    mock_llm = MagicMock()
    mock_llm.model = "gpt-4o"
    mock_llm.generate_text.side_effect = RuntimeError("LLM timeout")

    config = _make_config()
    config.eval_llm_judge_enabled = True
    config.eval_faithfulness_enabled = False
    config.eval_tool_selection_enabled = False

    with patch(
        "backend.services.phoenix.evaluators._create_llm_model",
        return_value=mock_llm,
    ):
        result = PhoenixEvaluatorBridge.run_supplementary_evals(
            actual_output="some output",
            context=None,
            target_type="workflow",
            node_executions=[{"input_data": {"message": "hello"}}],
            phoenix_config=config,
        )

    assert result["evaluations"]["llm_judge"]["status"] == "error"
    assert "LLM timeout" in result["evaluations"]["llm_judge"]["error"]
