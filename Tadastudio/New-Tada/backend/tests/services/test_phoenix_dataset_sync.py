"""Tests for PhoenixDatasetSync."""

import sys
from unittest.mock import MagicMock, patch

from backend.services.phoenix.config import PhoenixConfig
from backend.services.phoenix.dataset_sync import PhoenixDatasetSync


def _make_config(
    enabled: bool = True, ui_url: str = "http://phoenix:6006"
) -> PhoenixConfig:
    return PhoenixConfig(
        enabled=enabled,
        endpoint="http://phoenix:6006/v1/traces",
        project_name="test",
        api_key="key",
        ui_url=ui_url,
    )


def test_skipped_when_disabled():
    sync = PhoenixDatasetSync()
    result = sync.sync_run_to_experiment(
        run_id="run-1",
        dataset_id="ds-1",
        run_snapshot={},
        test_cases=[],
        results=[],
        effective_config=_make_config(enabled=False),
    )
    assert result["status"] == "skipped"


def test_already_synced():
    sync = PhoenixDatasetSync()
    result = sync.sync_run_to_experiment(
        run_id="run-1",
        dataset_id="ds-1",
        run_snapshot={},
        test_cases=[],
        results=[],
        effective_config=_make_config(),
        existing_summary={
            "phoenix_experiment_name": "eval-run-abc",
            "phoenix_dataset_name": "agentic-eval-ds-1",
        },
    )
    assert result["status"] == "already_synced"
    assert result["phoenix_experiment_name"] == "eval-run-abc"


def test_not_installed_when_import_fails():
    with patch.dict(sys.modules, {"phoenix.client": None}):
        sync = PhoenixDatasetSync()
        result = sync.sync_run_to_experiment(
            run_id="run-1",
            dataset_id="ds-1",
            run_snapshot={},
            test_cases=[],
            results=[],
            effective_config=_make_config(),
        )
    assert result["status"] == "not_installed"


def test_skipped_when_no_base_url():
    config = PhoenixConfig(
        enabled=True,
        endpoint="",
        project_name="test",
        api_key=None,
        ui_url="",
    )
    sync = PhoenixDatasetSync()
    result = sync.sync_run_to_experiment(
        run_id="run-1",
        dataset_id="ds-1",
        run_snapshot={},
        test_cases=[],
        results=[],
        effective_config=config,
    )
    assert result["status"] == "skipped"


def test_uses_dataset_object_flow():
    """Verify datasets.get_dataset and datasets.create_dataset are used
    instead of upload_dataset, and run_experiment receives dataset=dataset_obj."""
    mock_dataset_obj = MagicMock(name="dataset_object")

    mock_client_instance = MagicMock()
    # get_dataset raises to simulate new dataset
    mock_client_instance.datasets.get_dataset.side_effect = RuntimeError("not found")
    mock_client_instance.datasets.create_dataset.return_value = mock_dataset_obj
    mock_client_instance.experiments.run_experiment.return_value = None

    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_client_module = MagicMock()
    mock_client_module.Client = mock_client_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "pandas": MagicMock(),
        },
    ):
        sync = PhoenixDatasetSync()
        result = sync.sync_run_to_experiment(
            run_id="run-12345678",
            dataset_id="ds-1",
            run_snapshot={"workflow_id": "wf-1"},
            test_cases=[{"id": "tc-1", "input_data": "hi", "expected_output": "hello"}],
            results=[{"test_case_id": "tc-1", "composite_score": 80}],
            effective_config=_make_config(),
        )

    assert result["status"] == "ok"

    # Assert get_dataset was called first
    mock_client_instance.datasets.get_dataset.assert_called_once_with(
        dataset="agentic-eval-ds-1"
    )

    # Assert create_dataset was called with name=, dataframe=, input_keys=, output_keys=
    create_call = mock_client_instance.datasets.create_dataset.call_args
    assert create_call.kwargs.get("name") == "agentic-eval-ds-1"
    assert "dataframe" in create_call.kwargs
    assert create_call.kwargs.get("input_keys") == ["input"]
    assert create_call.kwargs.get("output_keys") == ["expected_output"]

    # Assert upload_dataset was NOT called
    mock_client_instance.datasets.upload_dataset.assert_not_called()

    # Assert run_experiment receives dataset=dataset_obj
    exp_call = mock_client_instance.experiments.run_experiment.call_args
    assert exp_call.kwargs.get("dataset") is mock_dataset_obj


def test_fetches_existing_dataset():
    """When get_dataset succeeds, create_dataset should not be called."""
    mock_dataset_obj = MagicMock(name="existing_dataset")

    mock_client_instance = MagicMock()
    mock_client_instance.datasets.get_dataset.return_value = mock_dataset_obj
    mock_client_instance.experiments.run_experiment.return_value = None

    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_client_module = MagicMock()
    mock_client_module.Client = mock_client_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "pandas": MagicMock(),
        },
    ):
        sync = PhoenixDatasetSync()
        result = sync.sync_run_to_experiment(
            run_id="run-12345678",
            dataset_id="ds-1",
            run_snapshot={},
            test_cases=[],
            results=[],
            effective_config=_make_config(),
        )

    assert result["status"] == "ok"
    mock_client_instance.datasets.get_dataset.assert_called_once()
    mock_client_instance.datasets.create_dataset.assert_not_called()

    # run_experiment should receive dataset=dataset_obj
    exp_call = mock_client_instance.experiments.run_experiment.call_args
    assert exp_call.kwargs.get("dataset") is mock_dataset_obj


def test_experiment_failure_returns_non_ok_status():
    """When experiment creation fails, status should NOT be 'ok' and
    phoenix_experiment_name should NOT be present."""
    mock_dataset_obj = MagicMock(name="dataset_object")

    mock_client_instance = MagicMock()
    mock_client_instance.datasets.get_dataset.side_effect = RuntimeError("not found")
    mock_client_instance.datasets.create_dataset.return_value = mock_dataset_obj
    mock_client_instance.experiments.run_experiment.side_effect = RuntimeError(
        "experiment failed"
    )

    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_client_module = MagicMock()
    mock_client_module.Client = mock_client_cls

    mock_pd = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "pandas": mock_pd,
        },
    ):
        sync = PhoenixDatasetSync()
        result = sync.sync_run_to_experiment(
            run_id="run-12345678",
            dataset_id="ds-1",
            run_snapshot={"workflow_id": "wf-1"},
            test_cases=[{"id": "tc-1", "input_data": "hi", "expected_output": "hello"}],
            results=[{"test_case_id": "tc-1", "composite_score": 80}],
            effective_config=_make_config(),
        )

    assert result["status"] == "experiment_failed"
    assert "phoenix_experiment_name" not in result
    assert "phoenix_dataset_name" in result


def test_experiment_failure_remains_retryable():
    """A failed experiment attempt should not block future retries
    (no phoenix_experiment_name marker emitted)."""
    mock_dataset_obj = MagicMock(name="dataset_object")

    mock_client_instance = MagicMock()
    mock_client_instance.datasets.get_dataset.side_effect = RuntimeError("not found")
    mock_client_instance.datasets.create_dataset.return_value = mock_dataset_obj
    mock_client_instance.experiments.run_experiment.side_effect = RuntimeError("boom")

    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_client_module = MagicMock()
    mock_client_module.Client = mock_client_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "pandas": MagicMock(),
        },
    ):
        sync = PhoenixDatasetSync()

        # First attempt — fails
        result1 = sync.sync_run_to_experiment(
            run_id="run-aabbccdd",
            dataset_id="ds-2",
            run_snapshot={},
            test_cases=[],
            results=[],
            effective_config=_make_config(),
        )
        assert result1["status"] == "experiment_failed"
        assert "phoenix_experiment_name" not in result1

        # Simulate retry: existing_summary does NOT have phoenix_experiment_name
        # so idempotency guard should NOT block the retry
        result2 = sync.sync_run_to_experiment(
            run_id="run-aabbccdd",
            dataset_id="ds-2",
            run_snapshot={},
            test_cases=[],
            results=[],
            effective_config=_make_config(),
            existing_summary=result1,  # no phoenix_experiment_name
        )
        # Should attempt again (not blocked by already_synced)
        assert result2["status"] != "already_synced"


def test_successful_sync_returns_ok_with_experiment_name():
    """When both dataset and experiment succeed, return ok with all markers."""
    mock_dataset_obj = MagicMock(name="dataset_object")

    mock_client_instance = MagicMock()
    mock_client_instance.datasets.get_dataset.return_value = mock_dataset_obj
    mock_client_instance.experiments.run_experiment.return_value = None

    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_client_module = MagicMock()
    mock_client_module.Client = mock_client_cls

    with patch.dict(
        sys.modules,
        {
            "phoenix": MagicMock(),
            "phoenix.client": mock_client_module,
            "pandas": MagicMock(),
        },
    ):
        sync = PhoenixDatasetSync()
        result = sync.sync_run_to_experiment(
            run_id="run-12345678",
            dataset_id="ds-1",
            run_snapshot={},
            test_cases=[],
            results=[],
            effective_config=_make_config(),
        )

    assert result["status"] == "ok"
    assert result["phoenix_experiment_name"] == "eval-run-run-1234"
    assert result["phoenix_dataset_name"] == "agentic-eval-ds-1"
    assert "dataset_url" in result
