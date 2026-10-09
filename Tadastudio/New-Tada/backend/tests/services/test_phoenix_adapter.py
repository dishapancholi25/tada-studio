"""Tests for PhoenixTraceAdapter."""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.phoenix.config import PhoenixConfig


@pytest.fixture
def enabled_config():
    return PhoenixConfig(
        enabled=True,
        endpoint="http://phoenix:6006/v1/traces",
        project_name="test-project",
        api_key="test-key",
        ui_url="http://phoenix:6006",
    )


@pytest.fixture
def disabled_config():
    return PhoenixConfig(
        enabled=False,
        endpoint="",
        project_name="test-project",
        api_key=None,
        ui_url="",
    )


@pytest.fixture
def sample_result_summaries():
    return [
        {
            "result_id": "result-1",
            "test_case_id": "tc-1",
            "evaluation_execution_id": "eval_run1_tc1_abc12345",
            "composite_score": 85.0,
            "quality_score": 90.0,
            "cost_score": 80.0,
            "reliability_score": 95.0,
            "latency_score": 75.0,
            "quality_raw": {"reasoning": "Good output"},
            "guardrail_signals": {},
        },
        {
            "result_id": "result-2",
            "test_case_id": "tc-2",
            "evaluation_execution_id": "eval_run1_tc2_def67890",
            "composite_score": 60.0,
            "quality_score": 55.0,
            "cost_score": 70.0,
            "reliability_score": 65.0,
            "latency_score": 50.0,
            "quality_raw": {},
            "guardrail_signals": {},
        },
    ]


@pytest.mark.asyncio
async def test_export_returns_empty_when_no_base_url(
    disabled_config, sample_result_summaries
):
    import backend.services.evaluation.phoenix_adapter as adapter_mod

    adapter = adapter_mod.PhoenixTraceAdapter(disabled_config)
    result = await adapter.export_run_traces(
        run_id="run-1",
        run_scores={},
        result_summaries=sample_result_summaries,
        project_name="test",
    )
    assert result == {"run_summary": {}, "result_trace_references": {}}


@pytest.mark.asyncio
async def test_export_correlates_spans_with_stable_kwargs(
    enabled_config, sample_result_summaries
):
    """Verify get_spans_dataframe is called with query= and project_identifier=
    and log_span_annotations_dataframe uses dataframe=, annotation_name=, annotator_kind=."""
    import pandas as pd
    import sys
    import importlib

    mock_df = pd.DataFrame(
        [{"context.trace_id": "trace-abc", "context.span_id": "span-123"}]
    )

    mock_client = MagicMock()
    mock_client.spans.get_spans_dataframe.return_value = mock_df
    mock_client.spans.log_span_annotations_dataframe.return_value = None

    mock_client_module = MagicMock()
    mock_client_module.Client = MagicMock(return_value=mock_client)

    mock_span_query = MagicMock()
    mock_span_query_instance = MagicMock()
    mock_span_query_instance.where.return_value = mock_span_query_instance
    mock_span_query.return_value = mock_span_query_instance

    mock_spans_module = MagicMock()
    mock_spans_module.SpanQuery = mock_span_query

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "phoenix.client.types": MagicMock(),
            "phoenix.client.types.spans": mock_spans_module,
        },
    ):
        import backend.services.evaluation.phoenix_adapter as adapter_mod

        importlib.reload(adapter_mod)

        adapter = adapter_mod.PhoenixTraceAdapter(enabled_config)
        result = await adapter.export_run_traces(
            run_id="run-1",
            run_scores={"composite_score": 72.5},
            result_summaries=sample_result_summaries,
            project_name="test-project",
        )

        assert "result_trace_references" in result
        assert "run_summary" in result

        # Assert get_spans_dataframe called with explicit keyword args
        calls = mock_client.spans.get_spans_dataframe.call_args_list
        assert len(calls) >= 1
        for call in calls:
            kwargs = call.kwargs
            assert "query" in kwargs, (
                "get_spans_dataframe must be called with query= kwarg"
            )
            assert "project_identifier" in kwargs, (
                "get_spans_dataframe must be called with project_identifier= kwarg"
            )

        # Assert log_span_annotations_dataframe called with correct kwargs
        ann_calls = mock_client.spans.log_span_annotations_dataframe.call_args_list
        assert len(ann_calls) > 0, "Annotations should have been logged"
        for ann_call in ann_calls:
            kwargs = ann_call.kwargs
            assert "dataframe" in kwargs, (
                "log_span_annotations_dataframe must be called with dataframe= kwarg"
            )
            assert "annotation_name" in kwargs, (
                "log_span_annotations_dataframe must be called with annotation_name= kwarg"
            )
            assert kwargs.get("annotator_kind") == "CODE", (
                "log_span_annotations_dataframe must be called with annotator_kind='CODE'"
            )


@pytest.mark.asyncio
async def test_export_empty_dataframe_no_trace_ref(enabled_config):
    import pandas as pd
    import sys

    empty_df = pd.DataFrame()

    mock_client = MagicMock()
    mock_client.spans.get_spans_dataframe.return_value = empty_df

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": MagicMock(Client=MagicMock(return_value=mock_client)),
        },
    ):
        import importlib
        import backend.services.evaluation.phoenix_adapter as adapter_mod

        importlib.reload(adapter_mod)

        adapter = adapter_mod.PhoenixTraceAdapter(enabled_config)
        result = await adapter.export_run_traces(
            run_id="run-1",
            run_scores={},
            result_summaries=[
                {
                    "result_id": "r1",
                    "evaluation_execution_id": "eval_run1_tc1_abc",
                    "composite_score": 50.0,
                }
            ],
            project_name="test",
        )
        assert result["result_trace_references"] == {}


@pytest.mark.asyncio
async def test_export_catches_all_exceptions(enabled_config, sample_result_summaries):
    """All Phoenix failures are caught and an empty structure is returned."""
    import sys

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": MagicMock(
                Client=MagicMock(side_effect=RuntimeError("connection failed"))
            ),
        },
    ):
        import importlib
        import backend.services.evaluation.phoenix_adapter as adapter_mod

        importlib.reload(adapter_mod)

        adapter = adapter_mod.PhoenixTraceAdapter(enabled_config)
        result = await adapter.export_run_traces(
            run_id="run-1",
            run_scores={},
            result_summaries=sample_result_summaries,
            project_name="test",
        )
        assert result == {"run_summary": {}, "result_trace_references": {}}
