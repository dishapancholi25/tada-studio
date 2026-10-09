"""Phoenix dataset and experiment synchronisation.

Mirrors evaluation datasets and run results into Phoenix datasets /
experiments so they can be explored via the Phoenix UI.  All operations
are best-effort and non-fatal.
"""

from typing import Any, Dict, List, Optional

from backend.services.config import get_logger
from backend.services.phoenix.config import PhoenixConfig

logger = get_logger("phoenix.dataset_sync")


class PhoenixDatasetSync:
    """Sync evaluation data to Phoenix datasets and experiments."""

    def sync_run_to_experiment(
        self,
        run_id: str,
        dataset_id: str,
        run_snapshot: Dict[str, Any],
        test_cases: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        effective_config: PhoenixConfig,
        existing_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mirror an evaluation run as a Phoenix experiment.

        Args:
            run_id: The evaluation run UUID.
            dataset_id: The evaluation dataset UUID.
            run_snapshot: Snapshotted run configuration.
            test_cases: Snapshotted test case dicts.
            results: Per-case result dicts with score fields.
            effective_config: Resolved Phoenix configuration.
            existing_summary: Previously persisted external_eval_summary.

        Returns:
            Dict with sync status and Phoenix identifiers.
        """
        if not effective_config.enabled or not effective_config.api_base_url:
            return {"status": "skipped"}

        # Idempotency: skip if already synced
        if existing_summary and existing_summary.get("phoenix_experiment_name"):
            return {"status": "already_synced", **existing_summary}

        try:
            from phoenix.client import Client  # type: ignore[import-untyped]
        except ImportError:
            return {"status": "not_installed"}

        api_base_url = effective_config.api_base_url
        client_base_url = effective_config.client_base_url

        try:
            import pandas as pd  # type: ignore[import-untyped]

            from backend.services.phoenix.config import _client_headers

            client = Client(
                base_url=api_base_url, headers=_client_headers(effective_config)
            )
            dataset_name = f"agentic-eval-{dataset_id}"
            experiment_name = f"eval-run-{run_id[:8]}"

            dataset_ok = False
            dataset_obj = None

            # --- Build dataset dataframe ---
            rows = []
            for tc in test_cases:
                rows.append(
                    {
                        "input": str(tc.get("input_data", "")),
                        "expected_output": str(tc.get("expected_output", "")),
                        "test_case_id": tc.get("id", ""),
                        "dataset_id": dataset_id,
                        "workflow_id": run_snapshot.get("workflow_id", ""),
                    }
                )
            df = pd.DataFrame(rows) if rows else pd.DataFrame()

            # --- Create or fetch dataset using dataset-object flow ---
            try:
                dataset_obj = client.datasets.get_dataset(dataset=dataset_name)
                logger.debug("Fetched existing Phoenix dataset: %s", dataset_name)
                dataset_ok = True
            except Exception:
                try:
                    dataset_obj = client.datasets.create_dataset(
                        name=dataset_name,
                        dataframe=df,
                        input_keys=["input"],
                        output_keys=["expected_output"],
                    )
                    logger.info("Created Phoenix dataset: %s", dataset_name)
                    dataset_ok = True
                except Exception as create_exc:
                    logger.warning(
                        "Phoenix dataset creation failed (non-fatal): %s", create_exc
                    )

            # --- Mirror results as experiment ---
            experiment_ok = False
            try:
                results_by_tc = {r.get("test_case_id", ""): r for r in results}

                def task_fn(example: Dict[str, Any]) -> str:
                    tc_id = example.get("test_case_id", "")
                    result = results_by_tc.get(tc_id, {})
                    return f"composite_score={result.get('composite_score', 'N/A')}"

                def composite_eval(example: Dict[str, Any], output: str) -> float:
                    tc_id = example.get("test_case_id", "")
                    result = results_by_tc.get(tc_id, {})
                    return float(result.get("composite_score", 0) or 0)

                def quality_eval(example: Dict[str, Any], output: str) -> float:
                    tc_id = example.get("test_case_id", "")
                    result = results_by_tc.get(tc_id, {})
                    return float(result.get("quality_score", 0) or 0)

                client.experiments.run_experiment(
                    dataset=dataset_obj,
                    task=task_fn,
                    experiment_name=experiment_name,
                    evaluators=[composite_eval, quality_eval],
                )
                logger.info(
                    "Created Phoenix experiment: %s for dataset %s",
                    experiment_name,
                    dataset_name,
                )
                experiment_ok = True
            except Exception as exp_exc:
                logger.warning(
                    "Phoenix experiment creation failed (non-fatal): %s", exp_exc
                )

            # Only return success when experiment actually succeeded
            if experiment_ok:
                return {
                    "status": "ok",
                    "phoenix_dataset_name": dataset_name,
                    "phoenix_experiment_name": experiment_name,
                    "dataset_url": f"{client_base_url}/datasets/{dataset_name}",
                }
            else:
                # Dataset may exist but experiment failed — remain retryable
                result: Dict[str, Any] = {
                    "status": "experiment_failed",
                    "phoenix_dataset_name": dataset_name,
                }
                if dataset_ok:
                    result["dataset_url"] = f"{client_base_url}/datasets/{dataset_name}"
                return result

        except Exception as exc:
            logger.warning(
                "Phoenix dataset sync failed for run %s (non-fatal): %s", run_id, exc
            )
            return {"status": "error", "error": str(exc)}
