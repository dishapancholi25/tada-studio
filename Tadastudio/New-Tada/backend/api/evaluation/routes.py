"""Evaluation REST API – datasets, runs, recommendations, auto-eval config."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from fastapi.responses import Response, StreamingResponse

from backend.api.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_feature_access,
)
from backend.models.evaluation import (
    EvaluationDataset,
    EvaluationRecommendation,
    EvaluationResult,
    EvaluationRun,
    EvaluationTestCase,
    TestCaseFile,
)
from backend.models.execution.execution_feedback import ExecutionFeedback
from backend.models.execution.graph_execution import GraphExecution
from backend.models.execution.node_execution import NodeExecution
from backend.models.workflows import Workflow
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import require_workflow_access_by_id
from backend.services.database import get_db
from backend.services.evaluation import (
    EvaluationDatasetRepository,
    EvaluationOrchestrator,
    EvaluationRecommendationRepository,
    EvaluationResultRepository,
    EvaluationRunRepository,
    RecommendationEngine,
    TargetContextService,
)
from backend.services.evaluation.dataset_generation import DatasetGenerationService

from .schemas import (
    AddTestCasesRequest,
    AIGenerateRequest,
    ApplyRecommendationRequest,
    AutoEvalConfig,
    CreateDatasetRequest,
    CreateRunRequest,
    DatasetListResponse,
    DatasetResponse,
    ImportDatasetRequest,
    ImportFromExecutionsRequest,
    RecommendationActionResponse,
    RecommendationListResponse,
    RecommendationPreviewResponse,
    ResultDetailResponse,
    RunCompareResponse,
    RunListResponse,
    RunResponse,
    TargetContextResponse,
    TestCaseListResponse,
    TestCaseResponse,
    UpdateDatasetRequest,
    UpdateDatasetVisibilityRequest,
    UpdateTestCaseRequest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level service singletons (stateless, safe to reuse)
# ---------------------------------------------------------------------------
_dataset_repo = EvaluationDatasetRepository()
_run_repo = EvaluationRunRepository()
_result_repo = EvaluationResultRepository()
_rec_repo = EvaluationRecommendationRepository()
_rec_engine = RecommendationEngine()
_dataset_service = DatasetGenerationService()
_target_context_service = TargetContextService()

router = APIRouter(
    prefix="/api/evaluation",
    tags=["evaluation"],
    dependencies=[
        Depends(require_active_user),
        Depends(require_feature_access("nav.evaluations")),
        Depends(require_scope("evaluation:*:read")),
    ],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_orchestration(run_id: str) -> None:
    """Launch async orchestration as a background task on the main event loop.

    Running on the main loop (instead of ``asyncio.run()`` in a thread) avoids
    cross-loop issues with the singleton ``EvaluationLLMDispatchQueue`` whose
    worker tasks would die when the temporary loop closed, causing subsequent
    ``ainvoke`` calls through the dispatch queue to deadlock.
    """
    await EvaluationOrchestrator().start_run(run_id)


def _resolve_node_name_from_graphs(node_id: str, db) -> Optional[str]:
    """Search latest graph definitions for a node matching *node_id* and return its name."""
    from backend.models.workflows.graph_definition import GraphDefinition

    latest_defs = (
        db.query(GraphDefinition.definition_json)
        .filter(GraphDefinition.is_latest.is_(True))
        .all()
    )
    for (defn_json,) in latest_defs:
        if not isinstance(defn_json, dict):
            continue
        for node in defn_json.get("nodes", []):
            nid = node.get("uniq_id") or node.get("id")
            if nid == node_id:
                return (
                    node.get("name")
                    or node.get("label")
                    or node.get("data", {}).get("label")
                    or node.get("data", {}).get("name")
                    or None
                )
    return None


def _resolve_workflow_name(workflow_id: Optional[str]) -> Optional[str]:
    """Best-effort resolve workflow name from its ID."""
    if not workflow_id:
        return None
    try:
        with get_db() as db:
            from backend.models.workflows import Workflow as WfModel

            wf = db.query(WfModel).filter(WfModel.id == workflow_id).first()
            return wf.name if wf else None
    except Exception:
        return None


def _resolve_target_name(
    target_type: Optional[str], target_id: Optional[str]
) -> Optional[str]:
    """Best-effort resolve a human-readable name for a target.

    Returns None when the target cannot be resolved (missing ID, not found, etc.).
    """
    if not target_id or not target_type:
        return None
    try:
        with get_db() as db:
            if target_type == "workflow":
                from backend.models.workflows import Workflow as WfModel

                wf = db.query(WfModel).filter(WfModel.id == target_id).first()
                return wf.name if wf else None
            if target_type == "model":
                from backend.models.configuration.model_deployment import (
                    ModelDeployment,
                )

                dep = (
                    db.query(ModelDeployment)
                    .filter(ModelDeployment.id == target_id)
                    .first()
                )
                if dep:
                    return (
                        dep.display_name
                        if hasattr(dep, "display_name") and dep.display_name
                        else dep.name
                    )
                return None
            if target_type in ("agent", "tool"):
                return _resolve_node_name_from_graphs(target_id, db)
            return None
    except Exception:
        return None


def _serialize_dataset(
    ds: EvaluationDataset,
    creator_name: Optional[str] = None,
    creator_email: Optional[str] = None,
    is_read_only: bool = False,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert an EvaluationDataset ORM instance to a response dict."""
    with get_db() as db:
        case_count = _dataset_repo.count_test_cases(str(ds.id), db)
        run_q = db.query(EvaluationRun).filter(EvaluationRun.dataset_id == str(ds.id))
        if user_id:
            run_q = run_q.filter(EvaluationRun.triggered_by_user_id == user_id)
        run_count = run_q.count()
    target_id_str = str(ds.target_id) if ds.target_id else None
    return {
        "id": str(ds.id),
        "name": ds.name,
        "description": ds.description,
        "target_type": ds.target_type,
        "target_id": target_id_str,
        "target_name": _resolve_target_name(ds.target_type, target_id_str),
        "workflow_id": str(ds.workflow_id) if ds.workflow_id else None,
        "workflow_name": _resolve_workflow_name(
            str(ds.workflow_id) if ds.workflow_id else None
        ),
        "tags": ds.tags,
        "test_case_count": case_count,
        "run_count": run_count,
        "baseline_run_id": str(ds.baseline_run_id) if ds.baseline_run_id else None,
        "created_by_user_id": str(ds.created_by_user_id)
        if ds.created_by_user_id
        else None,
        "created_by_name": creator_name,
        "created_by_email": creator_email,
        "visible_to_groups": ds.visible_to_groups
        if hasattr(ds, "visible_to_groups")
        else [],
        "is_read_only": is_read_only,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
    }


def _serialize_run(run: EvaluationRun, include_results: bool = False) -> Dict[str, Any]:
    """Convert an EvaluationRun ORM instance to a response dict."""
    # Resolve graph definition version number if linked
    graph_version = None
    gd_id = run.graph_definition_id
    if gd_id:
        try:
            with get_db() as db:
                from backend.models.workflows import GraphDefinition

                gd = (
                    db.query(GraphDefinition)
                    .filter(GraphDefinition.id == gd_id)
                    .first()
                )
                if gd:
                    graph_version = gd.version
        except Exception:
            pass

    # Resolve dataset name
    dataset_name = None
    if run.dataset_id:
        try:
            with get_db() as db:
                ds = (
                    db.query(EvaluationDataset)
                    .filter(EvaluationDataset.id == run.dataset_id)
                    .first()
                )
                if ds:
                    dataset_name = ds.name
        except Exception:
            pass

    # Resolve triggered-by user name/email
    triggered_by_name = None
    triggered_by_email = None
    if run.triggered_by_user_id:
        try:
            from backend.models.auth.user import User

            with get_db() as db:
                user = (
                    db.query(User)
                    .filter(User.id == str(run.triggered_by_user_id))
                    .first()
                )
                if user:
                    triggered_by_name = user.name
                    triggered_by_email = user.email
        except Exception:
            pass

    # Resolve workflow name
    workflow_name = _resolve_workflow_name(
        str(run.workflow_id) if run.workflow_id else None
    )

    data: Dict[str, Any] = {
        "id": str(run.id),
        "name": run.name,
        "workflow_id": str(run.workflow_id) if run.workflow_id else None,
        "workflow_name": workflow_name,
        "graph_definition_id": str(gd_id) if gd_id else None,
        "graph_version": graph_version,
        "dataset_id": str(run.dataset_id) if run.dataset_id else None,
        "dataset_name": dataset_name,
        "target_id": str(run.target_id) if run.target_id else None,
        "target_type": run.target_type,
        "status": run.status,
        "trigger": run.trigger,
        "environment": run.environment,
        "composite_score": run.composite_score,
        "cost_score": run.cost_score,
        "quality_score": run.quality_score,
        "reliability_score": run.reliability_score,
        "latency_score": run.latency_score,
        "total_cases": run.total_cases or 0,
        "completed_cases": run.completed_cases or 0,
        "failed_cases": run.failed_cases or 0,
        "regression_flag": bool(run.regression_flag)
        if run.regression_flag is not None
        else False,
        "regression_severity": run.regression_severity,
        "regression_ack_required": bool(run.regression_ack_required),
        "triggered_by_user_id": str(run.triggered_by_user_id)
        if run.triggered_by_user_id
        else None,
        "triggered_by_name": triggered_by_name,
        "triggered_by_email": triggered_by_email,
        "external_eval_summary": run.external_eval_summary,
        "pillar_weights": run.pillar_weights,
        "concurrency_limit": run.concurrency_limit,
        "judge_model_config": run.judge_model_config,
        "judge_output_policy": run.judge_output_policy,
        "external_integration_config": run.external_integration_config,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }

    if include_results:
        results = _result_repo.list_by_run(str(run.id))
        data["results"] = [_serialize_result(r) for r in results]

    return data


def _serialize_result(result) -> Dict[str, Any]:
    """Convert an EvaluationResult ORM instance to a response dict."""
    gs = result.guardrail_signals or {}
    signals = gs.get("signals", [])
    return {
        "id": str(result.id),
        "test_case_id": str(result.test_case_id) if result.test_case_id else None,
        "graph_execution_id": str(result.graph_execution_id)
        if result.graph_execution_id
        else None,
        "composite_score": result.composite_score,
        "cost_score": result.cost_score,
        "quality_score": result.quality_score,
        "reliability_score": result.reliability_score,
        "latency_score": result.latency_score,
        "trace_reference": result.trace_reference,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "guardrail_violation_count": len(signals),
        "guardrail_status": (
            "blocked" if any(
                s.get("action_taken") == "blocked" or s.get("severity") == "block"
                for s in signals
            )
            else "warned" if signals
            else None
        ),
    }


def _serialize_result_detail(result, db) -> Dict[str, Any]:
    """Convert an EvaluationResult ORM instance to a rich detail dict.

    Includes raw pillar JSON columns, the linked test case, and an execution summary.
    Expects to be called within an active ``db`` session so lazy relationships resolve.
    """
    data = _serialize_result(result)
    data["run_id"] = str(result.run_id)
    data["quality_raw"] = result.quality_raw
    data["cost_raw"] = result.cost_raw
    data["reliability_raw"] = result.reliability_raw
    data["latency_raw"] = result.latency_raw
    data["guardrail_signals"] = result.guardrail_signals
    data["external_eval_raw"] = result.external_eval_raw
    data["trace_reference"] = result.trace_reference

    # Inline linked test case
    tc = result.test_case
    if tc is not None:
        data["test_case"] = _serialize_test_case(tc)
    else:
        data["test_case"] = None

    # Load the parent run's judge_output_policy for output filtering
    run = db.query(EvaluationRun).filter(EvaluationRun.id == result.run_id).first()
    judge_output_policy = (run.judge_output_policy if run else None) or {}

    # Inline execution summary
    exe = (
        db.query(GraphExecution)
        .filter(GraphExecution.id == result.graph_execution_id)
        .first()
        if result.graph_execution_id
        else None
    )
    if exe is not None:
        # Apply the same extraction logic the judge uses so the UI shows
        # what the judge actually evaluated, not the full execution dump.
        from backend.services.evaluation.scoring import _extract_judge_output

        judge_output = (
            _extract_judge_output(exe.output_data, judge_output_policy)
            if exe.output_data
            else None
        )
        data["execution_summary"] = {
            "id": str(exe.id),
            "status": exe.status,
            "duration_seconds": exe.duration_seconds,
            "input_data": exe.input_data,
            "output_data": judge_output,
            "error_message": exe.error_message,
            "start_time": exe.start_time.isoformat() if exe.start_time else None,
            "end_time": exe.end_time.isoformat() if exe.end_time else None,
        }
    else:
        data["execution_summary"] = None

    return data


def _serialize_recommendation(rec: EvaluationRecommendation) -> Dict[str, Any]:
    """Convert an EvaluationRecommendation ORM instance to a response dict."""
    return {
        "id": str(rec.id),
        "run_id": str(rec.run_id),
        "recommendation_type": rec.recommendation_type,
        "target_node_id": str(rec.target_node_id) if rec.target_node_id else None,
        "title": rec.title,
        "rationale": rec.rationale,
        "risk_tier": rec.risk_tier,
        "status": rec.status,
        "proposed_change": rec.proposed_change,
        "expected_impact": rec.expected_impact,
        "applied_by_user_id": str(rec.applied_by_user_id)
        if rec.applied_by_user_id
        else None,
        "applied_version": rec.applied_version,
        "applied_graph_definition_id": rec.applied_graph_definition_id,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


def _serialize_test_case(tc: EvaluationTestCase) -> Dict[str, Any]:
    """Convert an EvaluationTestCase ORM instance to a response dict.

    Backward compat: old test cases may store dicts for input_data /
    expected_output — normalise them to plain strings.
    """
    raw_input = tc.input_data
    if isinstance(raw_input, dict):
        input_str = raw_input.get("message", "") or json.dumps(raw_input)
    else:
        input_str = raw_input or ""

    raw_expected = tc.expected_output
    if isinstance(raw_expected, dict):
        expected_str = raw_expected.get("message", "") or json.dumps(raw_expected)
    elif raw_expected:
        expected_str = str(raw_expected)
    else:
        expected_str = None

    # Attach file metadata (without binary content)
    files_list = None
    try:
        if tc.files:
            files_list = [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "mime_type": f.mime_type,
                    "file_size": f.file_size,
                }
                for f in tc.files
            ]
    except Exception:
        pass  # Detached instance or lazy-load failure

    # judge_criteria / tags may be stored as JSON-encoded strings if the
    # LLM double-serialised them during generation.  Deserialise so the
    # Pydantic response model (Dict / List) validates correctly.
    judge_criteria = tc.judge_criteria
    if isinstance(judge_criteria, str):
        try:
            judge_criteria = json.loads(judge_criteria)
        except (json.JSONDecodeError, ValueError):
            judge_criteria = None

    tags = tc.tags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, ValueError):
            tags = None

    return {
        "id": str(tc.id),
        "input_data": input_str,
        "expected_output": expected_str,
        "judge_criteria": judge_criteria,
        "tags": tags,
        "files": files_list,
    }


def _get_user_id(current_user: Dict[str, Any]) -> Optional[str]:
    """Extract user identifier from the auth claims dict."""
    return current_user.get("sub") or current_user.get("email")


def _verify_dataset_read_access(
    ds: EvaluationDataset, current_user: Dict[str, Any]
) -> None:
    """Verify the authenticated user may read a dataset.

    Access is granted to admins, the dataset owner, and users whose group
    membership matches the dataset's ``visible_to_groups`` (or the
    ``__all__`` sentinel). Prevents cross-tenant disclosure of datasets
    (ISG Finding 6430).

    Raises:
        HTTPException: 403 if the user has no read access to the dataset.
    """
    if current_user.get("is_admin"):
        return

    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id == user_id:
        return

    visible_to_groups = ds.visible_to_groups or []
    if "__all__" in visible_to_groups:
        return

    if visible_to_groups and user_id:
        try:
            from backend.services.groups.service import GroupService

            user_groups = GroupService().get_user_groups(user_id)
            if any(g in visible_to_groups for g in user_groups):
                return
        except Exception:
            pass

    raise HTTPException(status_code=403, detail="Not authorized to access this dataset")


def _verify_dataset_write_access(
    ds: EvaluationDataset, current_user: Dict[str, Any]
) -> None:
    """Verify the authenticated user may modify a dataset (owner or admin only)."""
    if current_user.get("is_admin"):
        return
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )


# ═══════════════════════════════════════════════════════════════════════
# Dataset endpoints
# ═══════════════════════════════════════════════════════════════════════


@router.post("/datasets", response_model=DatasetResponse, status_code=201, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def create_dataset(
    body: CreateDatasetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new evaluation dataset."""
    user_id = _get_user_id(current_user)
    # For workflow target type, ensure workflow_id is set to target_id
    workflow_id = body.workflow_id
    if body.target_type == "workflow" and not workflow_id and body.target_id:
        workflow_id = body.target_id
    ds = _dataset_repo.create(
        {
            "name": body.name,
            "description": body.description,
            "target_type": body.target_type,
            "target_id": body.target_id,
            "workflow_id": workflow_id,
            "tags": body.tags,
            "created_by_user_id": user_id,
            "visible_to_groups": body.visible_to_groups or [],
        }
    )
    return _serialize_dataset(ds, user_id=user_id)


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    target_type: Optional[str] = Query(None, pattern="^(workflow|agent|model|tool)$"),
    target_id: Optional[str] = Query(None),
    filter_type: Optional[str] = Query("all", pattern="^(all|my|shared)$"),
    show_all: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List evaluation datasets, optionally filtered by target_type, target_id, and ownership."""
    user_id = _get_user_id(current_user)
    is_admin = current_user.get("is_admin", False)

    # Admin with show_all bypasses user/group filtering
    effective_user_id = None if (show_all and is_admin) else user_id

    user_groups: List[str] = []
    if effective_user_id:
        try:
            from backend.services.groups.service import GroupService

            user_groups = GroupService().get_user_groups(effective_user_id)
        except Exception:
            pass

    rows = _dataset_repo.list(
        target_type=target_type,
        target_id=target_id,
        user_id=effective_user_id,
        user_groups=user_groups,
        filter_type=filter_type or "all",
    )
    return {
        "datasets": [
            _serialize_dataset(
                r["dataset"],
                creator_name=r["creator_name"],
                creator_email=r["creator_email"],
                is_read_only=r["is_read_only"],
                user_id=effective_user_id,
            )
            for r in rows
        ]
    }


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single dataset with its test case count."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(ds, current_user)
    return _serialize_dataset(ds, user_id=_get_user_id(current_user))


@router.patch("/datasets/{dataset_id}", response_model=DatasetResponse, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def update_dataset(
    dataset_id: str,
    body: UpdateDatasetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a dataset's mutable fields (name, description)."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    # Check ownership before allowing mutation
    user_id = _get_user_id(current_user)
    existing = _dataset_repo.get(dataset_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if (
        existing.created_by_user_id
        and user_id
        and existing.created_by_user_id != user_id
    ):
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )
    ds = _dataset_repo.update(dataset_id, updates)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _serialize_dataset(ds, user_id=user_id)


@router.delete("/datasets/{dataset_id}", status_code=204, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def delete_dataset(
    dataset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> None:
    """Soft-delete a dataset."""
    user_id = _get_user_id(current_user)
    existing = _dataset_repo.get(dataset_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if (
        existing.created_by_user_id
        and user_id
        and existing.created_by_user_id != user_id
    ):
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )
    ok = _dataset_repo.soft_delete(dataset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Dataset not found")


@router.patch("/datasets/{dataset_id}/visibility", response_model=DatasetResponse, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def update_dataset_visibility(
    dataset_id: str,
    body: UpdateDatasetVisibilityRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update dataset visibility groups. Only the dataset creator can change visibility."""
    user_id = _get_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate groups exist (skip __all__ special token)
    groups_to_validate = [g for g in body.visible_to_groups if g != "__all__"]
    if groups_to_validate:
        try:
            from backend.services.groups.service import GroupService

            GroupService().validate_groups_exist(groups_to_validate)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    try:
        ds = _dataset_repo.update_visibility(
            dataset_id, body.visible_to_groups, user_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return _serialize_dataset(ds, user_id=user_id)


@router.post("/datasets/{dataset_id}/clone", response_model=DatasetResponse, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def clone_dataset(
    dataset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Clone a dataset and all its test cases."""
    source = _dataset_repo.get(dataset_id)
    if not source:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(source, current_user)
    user_id = _get_user_id(current_user)

    # Create the new dataset
    new_ds = _dataset_repo.create(
        {
            "name": f"{source.name} (clone)",
            "description": source.description,
            "target_type": source.target_type,
            "target_id": source.target_id,
            "workflow_id": source.workflow_id,
            "tags": source.tags,
            "created_by_user_id": user_id,
            "visible_to_groups": [],
        }
    )

    # Copy all test cases and their file attachments
    with get_db() as db:
        cases = (
            db.query(EvaluationTestCase)
            .filter(EvaluationTestCase.dataset_id == dataset_id)
            .order_by(EvaluationTestCase.created_at.asc())
            .all()
        )
        for tc in cases:
            clone = EvaluationTestCase(
                dataset_id=new_ds.id,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                judge_criteria=tc.judge_criteria,
                tags=tc.tags,
            )
            db.add(clone)
            db.flush()  # assign clone.id so file FKs resolve

            # Copy file attachments
            files = (
                db.query(TestCaseFile).filter(TestCaseFile.test_case_id == tc.id).all()
            )
            for f in files:
                db.add(
                    TestCaseFile(
                        test_case_id=clone.id,
                        filename=f.filename,
                        mime_type=f.mime_type,
                        file_size=f.file_size,
                        content=f.content,
                    )
                )
        db.commit()

    # Re-fetch to get updated test_case_count
    new_ds = _dataset_repo.get(new_ds.id)
    return _serialize_dataset(new_ds, user_id=user_id)


# ── Dataset export / import ────────────────────────────────────────────


@router.get("/datasets/{dataset_id}/export")
async def export_dataset(
    dataset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Export a dataset and all its test cases as a JSON-serialisable dict.

    File attachments are included as base64-encoded ``file_info`` dicts so
    that the exported payload is fully self-contained and can be re-imported
    via ``POST /datasets/import``.
    """
    import base64 as _b64

    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(ds, current_user)

    with get_db() as db:
        cases = (
            db.query(EvaluationTestCase)
            .filter(EvaluationTestCase.dataset_id == dataset_id)
            .order_by(EvaluationTestCase.created_at.asc())
            .all()
        )

        exported_cases = []
        for tc in cases:
            ser = _serialize_test_case(tc)
            case_out: Dict[str, Any] = {
                "input_data": ser["input_data"],
                "expected_output": ser["expected_output"],
                "judge_criteria": ser["judge_criteria"],
                "tags": ser["tags"],
            }
            # Include file attachments as base64-encoded file_info
            if tc.files:
                for f in tc.files:
                    case_out["file_info"] = {
                        "name": f.filename,
                        "type": f.mime_type,
                        "size": f.file_size,
                        "base64": _b64.b64encode(bytes(f.content)).decode("ascii"),
                    }
                    break  # one file per test case
            exported_cases.append(case_out)

    target_id_str = str(ds.target_id) if ds.target_id else None
    return {
        "format": "nexus-dataset-v1",
        "dataset": {
            "name": ds.name,
            "description": ds.description,
            "target_type": ds.target_type,
            "target_id": target_id_str,
            "target_name": _resolve_target_name(ds.target_type, target_id_str),
            "workflow_id": str(ds.workflow_id) if ds.workflow_id else None,
            "workflow_name": _resolve_workflow_name(
                str(ds.workflow_id) if ds.workflow_id else None
            ),
            "tags": ds.tags,
        },
        "test_cases": exported_cases,
    }


@router.post("/datasets/import", response_model=DatasetResponse, status_code=201, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def import_dataset(
    body: ImportDatasetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Import a dataset from a previously-exported JSON payload.

    Creates a new dataset and populates it with the test cases from the
    export payload.  If test cases contain ``file_info`` with base64-encoded
    content, file attachments are recreated automatically.
    """
    import base64 as _b64

    user_id = _get_user_id(current_user)

    if body.format != "nexus-dataset-v1":
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported format: {body.format}. Expected 'nexus-dataset-v1'.",
        )

    ds_meta = body.dataset

    # Validate that target_id / workflow_id exist in this environment;
    # drop them if they don't (cross-instance imports).
    # When IDs are missing, fall back to resolving by workflow_name.
    target_id = ds_meta.target_id
    workflow_id = ds_meta.workflow_id
    if workflow_id:
        with get_db() as db:
            exists = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not exists:
                logger.info(
                    "Import: workflow_id %s not found in this environment, trying name lookup",
                    workflow_id,
                )
                workflow_id = None
                # If target_id was the workflow, drop it too
                if (
                    ds_meta.target_type == "workflow"
                    and target_id == ds_meta.workflow_id
                ):
                    target_id = None
    # Fall back: resolve workflow by name when IDs were dropped
    if ds_meta.target_type == "workflow" and not workflow_id and ds_meta.workflow_name:
        with get_db() as db:
            wf_by_name = (
                db.query(Workflow)
                .filter(Workflow.name == ds_meta.workflow_name)
                .first()
            )
            if wf_by_name:
                logger.info(
                    "Import: resolved workflow by name '%s' -> %s",
                    ds_meta.workflow_name,
                    wf_by_name.id,
                )
                workflow_id = str(wf_by_name.id)
                target_id = workflow_id
    if ds_meta.target_type == "workflow" and not workflow_id and target_id:
        workflow_id = target_id

    # De-duplicate name: if the user already owns a dataset with this name,
    # append a numeric suffix like "dataset name (1)", "dataset name (2)", etc.
    desired_name = ds_meta.name
    with get_db() as db:
        existing_names = {
            row[0]
            for row in db.query(EvaluationDataset.name)
            .filter(
                EvaluationDataset.created_by_user_id == user_id,
                EvaluationDataset.is_deleted == False,  # noqa: E712
            )
            .all()
        }
    if desired_name in existing_names:
        counter = 1
        while f"{desired_name} ({counter})" in existing_names:
            counter += 1
        desired_name = f"{desired_name} ({counter})"

    ds = _dataset_repo.create(
        {
            "name": desired_name,
            "description": ds_meta.description,
            "target_type": ds_meta.target_type,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "tags": ds_meta.tags,
            "created_by_user_id": user_id,
            "visible_to_groups": [],
        }
    )

    if body.test_cases:
        cases_to_add = [
            {
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "judge_criteria": tc.judge_criteria,
                "tags": tc.tags,
            }
            for tc in body.test_cases
        ]
        try:
            saved = _dataset_service.add_manual_test_cases(str(ds.id), cases_to_add)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # Recreate file attachments from file_info
        has_files = False
        with get_db() as db:
            for i, case_dict in enumerate(saved):
                tc_body = body.test_cases[i] if i < len(body.test_cases) else None
                fi = tc_body.file_info if tc_body else None
                if not fi or not isinstance(fi, dict):
                    continue
                b64_data = fi.get("base64")
                if not b64_data:
                    continue
                try:
                    content = _b64.b64decode(b64_data)
                except Exception:
                    continue
                filename = fi.get("name") or fi.get("filename") or "uploaded_file"
                mime_type = fi.get("type", "application/octet-stream")
                file_size = fi.get("size") or len(content)
                if file_size > _MAX_TEST_CASE_FILE_SIZE:
                    continue

                tcf = TestCaseFile(
                    test_case_id=case_dict["id"],
                    filename=filename,
                    mime_type=mime_type,
                    file_size=file_size,
                    content=content,
                )
                db.add(tcf)
                has_files = True
            if has_files:
                db.commit()

    # Re-fetch to get updated test_case_count
    ds = _dataset_repo.get(ds.id)
    return _serialize_dataset(ds, user_id=user_id)


# ── Test cases ────────────────────────────────────────────────────────


@router.get(
    "/datasets/{dataset_id}/test-cases",
    response_model=TestCaseListResponse,
)
async def list_test_cases(
    dataset_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all test cases for a dataset."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(ds, current_user)
    with get_db() as db:
        cases = (
            db.query(EvaluationTestCase)
            .filter(EvaluationTestCase.dataset_id == dataset_id)
            .order_by(EvaluationTestCase.created_at.asc())
            .all()
        )
        return {"test_cases": [_serialize_test_case(tc) for tc in cases]}


@router.delete("/datasets/{dataset_id}/test-cases/{test_case_id}", status_code=204, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def delete_test_case(
    dataset_id: str,
    test_case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a single test case from a dataset."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )
    with get_db() as db:
        tc = (
            db.query(EvaluationTestCase)
            .filter(
                EvaluationTestCase.id == test_case_id,
                EvaluationTestCase.dataset_id == dataset_id,
            )
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")
        db.delete(tc)
        db.commit()


# ── Test case files ────────────────────────────────────────────────

_MAX_TEST_CASE_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    ".csv",
    ".xls",
    ".xlsx",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    ".py",
    ".js",
    ".html",
    ".css",
    ".md",
    ".zip",
    ".tar",
    ".gz",
}


@router.post(
    "/datasets/{dataset_id}/test-cases/{test_case_id}/files",
    status_code=201,
)
async def upload_test_case_file(
    dataset_id: str,
    test_case_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Upload a file attachment for a test case."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_write_access(ds, current_user)

    with get_db() as db:
        tc = (
            db.query(EvaluationTestCase)
            .filter(
                EvaluationTestCase.id == test_case_id,
                EvaluationTestCase.dataset_id == dataset_id,
            )
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")

        # Validate filename & extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")
        import os

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not allowed. Supported: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
            )

        content = await file.read()
        if len(content) > _MAX_TEST_CASE_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum size of {_MAX_TEST_CASE_FILE_SIZE // (1024 * 1024)} MB",
            )

        # Remove existing file for this test case (one file per case)
        existing = (
            db.query(TestCaseFile)
            .filter(TestCaseFile.test_case_id == test_case_id)
            .all()
        )
        for ef in existing:
            db.delete(ef)

        tcf = TestCaseFile(
            test_case_id=test_case_id,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(content),
            content=content,
        )
        db.add(tcf)
        db.commit()
        db.refresh(tcf)

        return {
            "id": str(tcf.id),
            "filename": tcf.filename,
            "mime_type": tcf.mime_type,
            "file_size": tcf.file_size,
        }


@router.get("/datasets/{dataset_id}/test-cases/{test_case_id}/files")
async def list_test_case_files(
    dataset_id: str,
    test_case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List files attached to a test case."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(ds, current_user)

    with get_db() as db:
        tc = (
            db.query(EvaluationTestCase)
            .filter(
                EvaluationTestCase.id == test_case_id,
                EvaluationTestCase.dataset_id == dataset_id,
            )
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")

        files = (
            db.query(TestCaseFile)
            .filter(TestCaseFile.test_case_id == test_case_id)
            .all()
        )
        return {
            "files": [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "mime_type": f.mime_type,
                    "file_size": f.file_size,
                }
                for f in files
            ]
        }


@router.get("/datasets/{dataset_id}/test-cases/{test_case_id}/files/{file_id}")
async def download_test_case_file(
    dataset_id: str,
    test_case_id: str,
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Download a test case file attachment."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_read_access(ds, current_user)

    with get_db() as db:
        tcf = (
            db.query(TestCaseFile)
            .filter(
                TestCaseFile.id == file_id,
                TestCaseFile.test_case_id == test_case_id,
            )
            .first()
        )
        if not tcf:
            raise HTTPException(status_code=404, detail="File not found")

        return Response(
            content=bytes(tcf.content),
            media_type=tcf.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{tcf.filename}"',
            },
        )


@router.delete(
    "/datasets/{dataset_id}/test-cases/{test_case_id}/files/{file_id}",
    status_code=204,
)
async def delete_test_case_file(
    dataset_id: str,
    test_case_id: str,
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a file attachment from a test case."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _verify_dataset_write_access(ds, current_user)

    with get_db() as db:
        tcf = (
            db.query(TestCaseFile)
            .filter(
                TestCaseFile.id == file_id,
                TestCaseFile.test_case_id == test_case_id,
            )
            .first()
        )
        if not tcf:
            raise HTTPException(status_code=404, detail="File not found")
        db.delete(tcf)
        db.commit()


@router.patch(
    "/datasets/{dataset_id}/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
)
async def update_test_case(
    dataset_id: str,
    test_case_id: str,
    body: UpdateTestCaseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a single test case."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )
    with get_db() as db:
        tc = (
            db.query(EvaluationTestCase)
            .filter(
                EvaluationTestCase.id == test_case_id,
                EvaluationTestCase.dataset_id == dataset_id,
            )
            .first()
        )
        if not tc:
            raise HTTPException(status_code=404, detail="Test case not found")
        updates = body.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(tc, key, value)
        db.commit()
        db.refresh(tc)
        return _serialize_test_case(tc)


@router.post(
    "/datasets/{dataset_id}/test-cases",
    response_model=List[TestCaseResponse],
    status_code=201,
)
async def add_test_cases(
    dataset_id: str,
    body: AddTestCasesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Add manual or AI-generated test cases to a dataset."""
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )

    results: List[Dict[str, Any]] = []

    # Manual test cases (synchronous service method)
    if body.manual:
        cases = [tc.model_dump() for tc in body.manual]
        try:
            added = _dataset_service.add_manual_test_cases(dataset_id, cases)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        results.extend(added)

    # AI-generated test cases
    if body.ai_generate:
        ai = body.ai_generate
        try:
            generated = await _dataset_service.generate_ai_test_cases(
                dataset_id=dataset_id,
                seed_prompt=ai.seed_prompt,
                count=ai.count,
                include_edge_cases=ai.include_edge_cases,
                include_adversarial=ai.include_adversarial,
                generator_model=ai.generator_model,
                target_type=ds.target_type,
                example_execution_ids=ai.example_execution_ids,
                target_node_id=ds.target_id
                if ds.target_type in ("agent", "tool")
                else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        results.extend(generated)

    return results


@router.post("/datasets/{dataset_id}/test-cases/generate-stream")
async def generate_test_cases_stream(
    dataset_id: str,
    body: AIGenerateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """Generate AI test cases with SSE streaming progress.

    Each batch is persisted immediately so that already-generated cases
    survive even if a later batch fails.
    """
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )

    async def event_stream():
        try:
            async for progress in _dataset_service.generate_ai_test_cases_streaming(
                dataset_id=dataset_id,
                seed_prompt=body.seed_prompt,
                count=body.count,
                include_edge_cases=body.include_edge_cases,
                include_adversarial=body.include_adversarial,
                generator_model=body.generator_model,
                target_type=ds.target_type,
                example_execution_ids=body.example_execution_ids,
                target_node_id=ds.target_id
                if ds.target_type in ("agent", "tool")
                else None,
            ):
                yield f"data: {json.dumps(progress)}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'event': 'error', 'message': str(exc), 'saved_count': 0, 'total': body.count})}\n\n"
        except Exception as exc:
            logger.error(
                "Unexpected error in test-case generation stream for dataset %s: %s",
                dataset_id,
                exc,
            )
            yield f"data: {json.dumps({'event': 'error', 'message': 'An unexpected error occurred during test case generation.', 'saved_count': 0, 'total': body.count})}\n\n"
        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Import from executions ────────────────────────────────────────────


@router.post(
    "/datasets/{dataset_id}/import-from-executions",
    response_model=List[TestCaseResponse],
    status_code=201,
)
async def import_from_executions(
    dataset_id: str,
    body: ImportFromExecutionsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Import positively-rated execution runs as test cases.

    Only executions with positive feedback are eligible for import.
    The execution's input_data becomes the test case input, and optionally
    the output_data becomes the expected_output.
    """
    ds = _dataset_repo.get(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    user_id = _get_user_id(current_user)
    if ds.created_by_user_id and user_id and ds.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the dataset owner can modify this dataset"
        )

    # Determine if we should extract node-level I/O instead of workflow-level
    use_node_io = ds.target_type in ("agent", "tool") and ds.target_id

    with get_db() as db:
        # Build query for positive-feedback executions
        query = (
            db.query(GraphExecution)
            .join(
                ExecutionFeedback,
                ExecutionFeedback.graph_execution_id == GraphExecution.id,
            )
            .filter(ExecutionFeedback.rating == "positive")
        )

        if body.execution_ids:
            query = query.filter(GraphExecution.id.in_(body.execution_ids))

        if body.workflow_id:
            query = query.filter(GraphExecution.workflow_id == body.workflow_id)

        executions = query.all()

        # Pre-load node executions for the target node when targeting agent/tool
        node_exec_map: Dict[str, NodeExecution] = {}
        if use_node_io and executions:
            exe_ids = [exe.id for exe in executions]
            node_execs = (
                db.query(NodeExecution)
                .filter(
                    NodeExecution.graph_execution_id.in_(exe_ids),
                    NodeExecution.node_id == ds.target_id,
                    NodeExecution.status == "completed",
                )
                .all()
            )
            for ne in node_execs:
                node_exec_map[ne.graph_execution_id] = ne

    if not executions:
        raise HTTPException(
            status_code=404,
            detail="No positively-rated executions found matching the criteria",
        )

    def _extract_text(data: Any, preferred_keys: List[str]) -> str:
        """Extract a meaningful text string from execution data."""
        if isinstance(data, dict):
            for key in preferred_keys:
                val = data.get(key)
                if val and isinstance(val, str):
                    return val
            # Exclude file_info (contains large base64) from the fallback
            cleaned = {k: v for k, v in data.items() if k != "file_info"}
            if not cleaned:
                # Input was file-only; use the filename as a label
                fi = data.get("file_info")
                if isinstance(fi, dict):
                    name = fi.get("name") or fi.get("filename") or "uploaded file"
                    return f"[File: {name}]"
                return ""
            return json.dumps(cleaned)
        return str(data)

    # Convert executions to test cases, tracking file_info per case
    cases = []
    file_infos: List[Optional[Dict[str, Any]]] = []
    for exe in executions:
        # When targeting a specific node, use node-level I/O
        if use_node_io:
            node_exe = node_exec_map.get(str(exe.id))
            if not node_exe or not node_exe.input_data:
                continue  # Skip executions where the target node wasn't found
            source_input = node_exe.input_data
            source_output = node_exe.output_data
        else:
            if not exe.input_data:
                continue  # Skip executions without input
            source_input = exe.input_data
            source_output = exe.output_data

        input_str = _extract_text(source_input, ["message", "input", "prompt", "query"])

        # Extract file_info from the execution's input_data (if present)
        fi: Optional[Dict[str, Any]] = None
        if isinstance(source_input, dict):
            fi = source_input.get("file_info")

        case: Dict[str, Any] = {
            "input_data": input_str,
            "tags": list(set(["from-execution", "positive"] + (body.tags or []))),
            "judge_criteria": {
                "source": "execution_feedback",
                "execution_id": str(exe.id),
            },
        }

        if body.include_expected_output and source_output:
            # For tool targets, extract the "data" field from the node output.
            # Tool node output_data is stored as the direct response dict, e.g.
            # {"status_code": 200, "headers": {...}, "data": <body>, "error": null, ...}.
            # The agent LLM only receives the "data" portion via ToolMessage, so
            # extract just that to match what the wrapper agent will see.
            if (
                ds.target_type == "tool"
                and isinstance(source_output, dict)
                and "data" in source_output
            ):
                body_data = source_output["data"]
                output_str = (
                    json.dumps(body_data, indent=2)
                    if isinstance(body_data, (dict, list))
                    else str(body_data)
                )
            else:
                output_str = _extract_text(
                    source_output, ["final_output", "message", "output", "response"]
                )
            case["expected_output"] = output_str

        cases.append(case)
        file_infos.append(fi)

    if not cases:
        raise HTTPException(
            status_code=422,
            detail="No valid test cases could be extracted from the matched executions",
        )

    try:
        saved = _dataset_service.add_manual_test_cases(dataset_id, cases)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Create TestCaseFile records for cases whose executions had file uploads
    import base64 as _b64

    has_files = False
    with get_db() as db:
        for i, case_dict in enumerate(saved):
            fi = file_infos[i] if i < len(file_infos) else None
            if not fi or not isinstance(fi, dict):
                continue
            b64_data = fi.get("base64")
            if not b64_data:
                continue
            try:
                content = _b64.b64decode(b64_data)
            except Exception:
                continue
            filename = fi.get("name") or fi.get("filename") or "uploaded_file"
            mime_type = fi.get("type", "application/octet-stream")
            file_size = fi.get("size") or len(content)
            if file_size > _MAX_TEST_CASE_FILE_SIZE:
                continue

            tcf = TestCaseFile(
                test_case_id=case_dict["id"],
                filename=filename,
                mime_type=mime_type,
                file_size=file_size,
                content=content,
            )
            db.add(tcf)
            has_files = True
        if has_files:
            db.commit()

    # Re-serialize with file metadata if any files were attached
    if has_files:
        with get_db() as db:
            tc_ids = [c["id"] for c in saved]
            tcs = (
                db.query(EvaluationTestCase)
                .filter(EvaluationTestCase.id.in_(tc_ids))
                .order_by(EvaluationTestCase.created_at.asc())
                .all()
            )
            return [_serialize_test_case(tc) for tc in tcs]

    return saved


# ═══════════════════════════════════════════════════════════════════════
# Run endpoints
# ═══════════════════════════════════════════════════════════════════════


@router.post("/runs", response_model=RunResponse, status_code=201, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def create_run(
    body: CreateRunRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create and start a new evaluation run (non-blocking)."""
    user_id = _get_user_id(current_user)

    # Verify dataset exists
    ds = _dataset_repo.get(body.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Count test cases
    with get_db() as db:
        case_count = _dataset_repo.count_test_cases(body.dataset_id, db)

    # Generate a default run name if not provided
    name_slug = (body.workflow_id or body.target_id or "eval")[:8]
    run_name = (
        body.name
        or f"manual-{name_slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )

    # Resolve target_id: for workflow type default to workflow_id; others use body.target_id directly
    if body.target_type == "workflow":
        target_id = body.target_id or body.workflow_id
    else:
        target_id = body.target_id

    # Resolve the latest graph_definition_id for version tracking
    graph_definition_id = None
    if body.workflow_id:
        with get_db() as db:
            from backend.models.workflows import GraphDefinition

            latest_gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == body.workflow_id,
                    GraphDefinition.is_latest.is_(True),
                )
                .first()
            )
            if latest_gd:
                graph_definition_id = str(latest_gd.id)

    run_data: Dict[str, Any] = {
        "name": run_name,
        "target_id": target_id,
        "target_type": body.target_type,
        "dataset_id": body.dataset_id,
        "trigger": body.trigger,
        "status": "pending",
        "total_cases": case_count,
        "triggered_by_user_id": user_id,
    }

    # Only include workflow_id when provided (model target type doesn't need one)
    if body.workflow_id:
        run_data["workflow_id"] = body.workflow_id

    if graph_definition_id:
        run_data["graph_definition_id"] = graph_definition_id

    # Populate optional config fields when provided
    if body.environment is not None:
        run_data["environment"] = body.environment
    if body.pillar_weights is not None:
        run_data["pillar_weights"] = body.pillar_weights
    if body.concurrency_limit is not None:
        run_data["concurrency_limit"] = body.concurrency_limit
    if body.judge_model_config is not None:
        run_data["judge_model_config"] = body.judge_model_config
    if body.judge_output_policy is not None:
        run_data["judge_output_policy"] = body.judge_output_policy
    if body.external_integration_config is not None:
        run_data["external_integration_config"] = body.external_integration_config
    if body.quality_judge_provider is not None:
        ext = run_data.get("external_integration_config") or {}
        ext["quality_judge_provider"] = body.quality_judge_provider
        run_data["external_integration_config"] = ext
    run = _run_repo.create(run_data)

    # Fire-and-forget orchestration in a background thread
    background_tasks.add_task(_run_orchestration, str(run.id))

    return _serialize_run(run)


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    workflow_id: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    trigger: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    show_all: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List evaluation runs with optional filters. Only shows runs owned by the current user unless admin uses show_all."""
    user_id = _get_user_id(current_user)
    is_admin = current_user.get("is_admin", False)
    effective_user_id = None if (show_all and is_admin) else user_id
    runs = _run_repo.list(
        workflow_id=workflow_id,
        dataset_id=dataset_id,
        status=status,
        trigger=trigger,
        target_type=target_type,
        target_id=target_id,
        user_id=effective_user_id,
        limit=limit,
        offset=offset,
    )
    return {"runs": [_serialize_run(r) for r in runs]}


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single evaluation run with scores and per-case results."""
    user_id = _get_user_id(current_user)
    is_admin = current_user.get("is_admin", False)
    run = _run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (
        not is_admin
        and user_id
        and run.triggered_by_user_id
        and run.triggered_by_user_id != user_id
    ):
        raise HTTPException(
            status_code=403, detail="You do not have access to this run"
        )
    return _serialize_run(run, include_results=True)


@router.get("/results/{result_id}", response_model=ResultDetailResponse)
async def get_result_detail(
    result_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single evaluation result with raw pillar data, test case, and execution summary."""
    user_id = _get_user_id(current_user)
    is_admin = current_user.get("is_admin", False)
    with get_db() as db:
        result = (
            db.query(EvaluationResult).filter(EvaluationResult.id == result_id).first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        # Check ownership via the parent run (admins bypass)
        run = db.query(EvaluationRun).filter(EvaluationRun.id == result.run_id).first()
        if (
            not is_admin
            and run
            and user_id
            and run.triggered_by_user_id
            and run.triggered_by_user_id != user_id
        ):
            raise HTTPException(
                status_code=403, detail="You do not have access to this result"
            )
        return _serialize_result_detail(result, db)


@router.delete("/runs/{run_id}", status_code=204, dependencies=[Depends(require_scope("evaluation:*:write"))])
async def delete_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete an evaluation run and its associated results/recommendations."""
    user_id = _get_user_id(current_user)

    # Prevent deletion of runs that are still executing
    run = _run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete a run with status '{run.status}'. Wait for it to complete or cancel it first.",
        )

    try:
        ok = _run_repo.delete(run_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Run not found")


@router.get("/runs/{run_id}/compare/{peer_id}", response_model=RunCompareResponse)
async def compare_runs(
    run_id: str,
    peer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compare two evaluation runs side-by-side."""
    user_id = _get_user_id(current_user)
    is_admin = current_user.get("is_admin", False)
    run_a = _run_repo.get(run_id)
    run_b = _run_repo.get(peer_id)
    if not run_a:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if not run_b:
        raise HTTPException(status_code=404, detail=f"Run {peer_id} not found")
    for r, rid in [(run_a, run_id), (run_b, peer_id)]:
        if (
            not is_admin
            and user_id
            and r.triggered_by_user_id
            and r.triggered_by_user_id != user_id
        ):
            raise HTTPException(
                status_code=403, detail=f"You do not have access to run {rid}"
            )

    a = _serialize_run(run_a, include_results=True)
    b = _serialize_run(run_b, include_results=True)

    score_keys = [
        "composite_score",
        "cost_score",
        "quality_score",
        "reliability_score",
        "latency_score",
    ]
    delta: Dict[str, Optional[float]] = {}
    for key in score_keys:
        val_a = a.get(key)
        val_b = b.get(key)
        if val_a is not None and val_b is not None:
            delta[key] = round(val_a - val_b, 4)
        else:
            delta[key] = None

    # Determine winner based on composite_score delta
    winner: Optional[str] = None
    winner_reason: Optional[str] = None
    composite_delta = delta.get("composite_score")
    if composite_delta is not None:
        if composite_delta > 0:
            winner = run_id
            winner_reason = f"Run A composite score is {composite_delta:.4f} higher"
        elif composite_delta < 0:
            winner = peer_id
            winner_reason = (
                f"Run B composite score is {abs(composite_delta):.4f} higher"
            )
        else:
            winner = None
            winner_reason = "Both runs have equal composite scores"

    return {
        "run_a": a,
        "run_b": b,
        "delta": delta,
        "winner": winner,
        "winner_reason": winner_reason,
    }


# ═══════════════════════════════════════════════════════════════════════
# Recommendation endpoints
# ═══════════════════════════════════════════════════════════════════════


@router.get("/runs/{run_id}/recommendations", response_model=RecommendationListResponse)
async def list_recommendations(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List recommendations for a given evaluation run."""
    user_id = _get_user_id(current_user)
    run = _run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if user_id and run.triggered_by_user_id and run.triggered_by_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="You do not have access to this run"
        )
    recs = _rec_repo.list_by_run(run_id)
    return {"recommendations": [_serialize_recommendation(r) for r in recs]}


@router.get(
    "/runs/{run_id}/recommendations/{rec_id}/preview",
    response_model=RecommendationPreviewResponse,
)
async def preview_recommendation(
    run_id: str,
    rec_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Preview a recommendation showing current vs proposed values."""
    user_id = _get_user_id(current_user)
    try:
        return _rec_engine.preview_recommendation(
            recommendation_id=rec_id,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/runs/{run_id}/recommendations/{rec_id}/apply",
    response_model=RecommendationActionResponse,
)
async def apply_recommendation(
    run_id: str,
    rec_id: str,
    body: ApplyRecommendationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Apply a recommendation (risk-policy enforced)."""
    user_id = _get_user_id(current_user)
    try:
        result = await _rec_engine.apply_recommendation(
            recommendation_id=rec_id,
            user_id=user_id,
            confirmed=body.confirmed,
            impact_acknowledged=body.impact_acknowledged,
            proposed_change_override=body.proposed_change_override,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/runs/{run_id}/recommendations/{rec_id}/dismiss",
    response_model=RecommendationActionResponse,
)
async def dismiss_recommendation(
    run_id: str,
    rec_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dismiss a recommendation."""
    user_id = _get_user_id(current_user)
    try:
        result = await _rec_engine.dismiss_recommendation(
            recommendation_id=rec_id,
            user_id=user_id,
        )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════
# Workflow-scoped helpers
# ═══════════════════════════════════════════════════════════════════════


@router.get("/workflows/{workflow_id}/latest-run", response_model=RunResponse)
async def get_latest_run(workflow_id: str) -> Dict[str, Any]:
    """Get the latest completed evaluation run for a workflow."""
    run = _run_repo.get_latest_for_workflow(workflow_id)
    if not run:
        raise HTTPException(
            status_code=404, detail="No completed run found for this workflow"
        )
    return _serialize_run(run)


@router.get("/workflows/{workflow_id}/auto-eval-config", response_model=AutoEvalConfig)
async def get_auto_eval_config(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get auto-evaluation configuration for a workflow."""
    require_workflow_access_by_id(current_user, workflow_id)

    with get_db() as db:
        wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    cfg = wf.auto_eval_config or {}
    return {
        "enabled": cfg.get("enabled", False),
        "dataset_id": cfg.get("dataset_id"),
        "environment": cfg.get("environment"),
        "pillar_weights": cfg.get("pillar_weights"),
        "concurrency_limit": cfg.get("concurrency_limit"),
        "judge_model_config": cfg.get("judge_model_config"),
        "judge_output_policy": cfg.get("judge_output_policy"),
        "trigger_on_publish": cfg.get("trigger_on_publish", False),
        "trigger_on_modify": cfg.get("trigger_on_modify", False),
        "debounce_window_seconds": cfg.get("debounce_window_seconds"),
        "quality_judge_provider": cfg.get("quality_judge_provider"),
    }


@router.put(
    "/workflows/{workflow_id}/auto-eval-config",
    response_model=AutoEvalConfig,
    dependencies=[Depends(require_scope("evaluation:*:write"))],
)
async def update_auto_eval_config(
    workflow_id: str,
    body: AutoEvalConfig,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update auto-evaluation configuration for a workflow."""
    require_workflow_access_by_id(current_user, workflow_id)

    with get_db() as db:
        wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        wf.auto_eval_config = body.model_dump()
        db.commit()
        db.refresh(wf)

    cfg = wf.auto_eval_config or {}
    return {
        "enabled": cfg.get("enabled", False),
        "dataset_id": cfg.get("dataset_id"),
        "environment": cfg.get("environment"),
        "pillar_weights": cfg.get("pillar_weights"),
        "concurrency_limit": cfg.get("concurrency_limit"),
        "judge_model_config": cfg.get("judge_model_config"),
        "judge_output_policy": cfg.get("judge_output_policy"),
        "trigger_on_publish": cfg.get("trigger_on_publish", False),
        "trigger_on_modify": cfg.get("trigger_on_modify", False),
        "debounce_window_seconds": cfg.get("debounce_window_seconds"),
        "quality_judge_provider": cfg.get("quality_judge_provider"),
    }


# ═══════════════════════════════════════════════════════════════════════
# Target context endpoint
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/targets/{target_type}/{target_id}/context",
    response_model=TargetContextResponse,
)
async def get_target_context(
    target_type: str = Path(..., pattern="^(workflow|agent|model|tool)$"),
    target_id: str = Path(...),
    workflow_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Resolve rich context for an evaluation target."""
    try:
        return _target_context_service.resolve_context(
            target_type, target_id, workflow_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
