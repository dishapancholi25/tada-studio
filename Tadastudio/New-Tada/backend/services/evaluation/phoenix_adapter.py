"""Phoenix trace adapter for evaluation telemetry export.

Correlates evaluation execution spans in Phoenix, annotates them with
pillar scores, and returns trace references for persistence.  All
operations are best-effort -- errors are logged and never propagate.
"""

from typing import Any, Dict, List

from backend.services.config import get_logger
from backend.services.phoenix.config import PhoenixConfig

logger = get_logger("evaluation.phoenix_adapter")


def _score_label(score: float) -> str:
    """Map a 0-100 score to a human-readable label bucket."""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"


class PhoenixTraceAdapter:
    """Adapter for exporting evaluation run traces to Phoenix.

    Queries Phoenix for spans emitted during evaluation execution,
    annotates them with pillar scores, and returns per-result trace
    references so the orchestrator can persist them.
    """

    def __init__(self, effective_config: PhoenixConfig):
        self._config = effective_config

    async def export_run_traces(
        self,
        run_id: str,
        run_scores: Dict[str, Any],
        result_summaries: List[Dict[str, Any]],
        project_name: str,
    ) -> Dict[str, Any]:
        """Export evaluation run traces to Phoenix.

        Args:
            run_id: The evaluation run UUID.
            run_scores: Aggregated run-level scores.
            result_summaries: Per-case result summaries with score fields.
            project_name: Phoenix project name.

        Returns:
            Dict with ``run_summary`` and ``result_trace_references``.
        """
        empty_result: Dict[str, Any] = {
            "run_summary": {},
            "result_trace_references": {},
        }
        api_base = self._config.api_base_url
        if not api_base:
            logger.debug("Phoenix api_base_url not configured, skipping trace export")
            return empty_result

        try:
            from phoenix.client import Client  # type: ignore[import-untyped]
        except ImportError:
            logger.debug("Phoenix client SDK not installed, skipping trace export")
            return empty_result

        try:
            # Force-flush the OTel span exporter so all evaluation spans
            # are available in Phoenix before we query for them.
            try:
                from opentelemetry.trace import get_tracer_provider

                provider = get_tracer_provider()
                if hasattr(provider, "force_flush"):
                    provider.force_flush(timeout_millis=10_000)
            except Exception as flush_exc:
                logger.debug(
                    "OTel flush before Phoenix query failed (non-fatal): %s", flush_exc
                )

            from backend.services.phoenix.config import _client_headers

            client = Client(base_url=api_base, headers=_client_headers(self._config))
            result_trace_references: Dict[str, Dict[str, Any]] = {}
            correlated_count = 0
            annotated_count = 0

            # Resolve the Relay global ID for the project so the Phoenix
            # client doesn't try (and fail) to base64-decode the name.
            from backend.services.phoenix.config import resolve_project_id

            project_identifier = (
                resolve_project_id(project_name, self._config) or project_name
            )

            for summary in result_summaries:
                result_id = summary.get("result_id", "")
                eval_exec_id = summary.get("evaluation_execution_id", "")
                if not eval_exec_id:
                    continue

                try:
                    # Build a SpanQuery filter to find spans by execution_id.
                    # We query agentic_studio.execution_id (set reliably by
                    # phoenix_workflow_context) rather than evaluation_execution_id
                    # (which depends on fragile metadata merging across OI contexts).
                    from phoenix.client.types.spans import SpanQuery

                    span_query = SpanQuery().where(
                        f"metadata['agentic_studio.execution_id'] == '{eval_exec_id}'"
                    )
                    df = client.spans.get_spans_dataframe(
                        query=span_query,
                        project_identifier=project_identifier,
                        root_spans_only=True,
                    )

                    if df is None or df.empty:
                        continue

                    trace_id = None
                    span_id = None
                    if "context.trace_id" in df.columns:
                        trace_id = str(df["context.trace_id"].iloc[0])
                    if "context.span_id" in df.columns:
                        span_id = str(df["context.span_id"].iloc[0])

                    if not trace_id or not span_id:
                        continue

                    from backend.services.phoenix.config import build_trace_path

                    trace_path = build_trace_path(project_name, trace_id, self._config)
                    trace_ref: Dict[str, Any] = {
                        "project": project_name,
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "execution_id": eval_exec_id,
                        "path": trace_path,
                    }
                    result_trace_references[result_id] = trace_ref
                    correlated_count += 1

                    # Annotate span with pillar scores
                    try:
                        import pandas as pd  # type: ignore[import-untyped]

                        pillar_fields = [
                            ("composite_score", "Composite"),
                            ("quality_score", "Quality"),
                            ("cost_score", "Cost"),
                            ("reliability_score", "Reliability"),
                            ("latency_score", "Latency"),
                        ]
                        for field_key, annotation_name in pillar_fields:
                            score_val = summary.get(field_key)
                            if score_val is None:
                                continue

                            score_float = float(score_val)
                            explanation = ""
                            if field_key == "quality_score":
                                quality_raw = summary.get("quality_raw") or {}
                                explanation = quality_raw.get("reasoning", "")

                            ann_df = pd.DataFrame(
                                [
                                    {
                                        "span_id": span_id,
                                        "score": score_float,
                                        "label": _score_label(score_float),
                                        "explanation": explanation,
                                        "metadata": {"field_key": field_key},
                                    }
                                ]
                            )
                            client.spans.log_span_annotations_dataframe(
                                dataframe=ann_df,
                                annotation_name=annotation_name,
                                annotator_kind="CODE",
                            )
                            annotated_count += 1
                    except Exception as ann_exc:
                        logger.warning(
                            "Failed to annotate span %s (non-fatal): %s",
                            span_id,
                            ann_exc,
                        )

                except Exception as span_exc:
                    logger.warning(
                        "Failed to correlate spans for result %s (non-fatal): %s",
                        result_id,
                        span_exc,
                    )

            from backend.services.phoenix.config import build_project_path

            project_path = build_project_path(project_name, self._config)
            run_summary: Dict[str, Any] = {
                "project": project_name,
                "annotated_count": annotated_count,
                "correlated_count": correlated_count,
                "project_path": project_path,
            }

            logger.info(
                "Phoenix trace export completed for run %s: correlated=%d, annotated=%d",
                run_id,
                correlated_count,
                annotated_count,
            )

            return {
                "run_summary": run_summary,
                "result_trace_references": result_trace_references,
            }

        except Exception as exc:
            logger.warning(
                "Phoenix trace export failed for run %s (non-fatal): %s", run_id, exc
            )
            return empty_result
