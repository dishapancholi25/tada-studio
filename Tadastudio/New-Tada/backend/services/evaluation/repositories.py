"""Evaluation repositories for database persistence.

Provides CRUD operations for evaluation runs, results, datasets,
test cases, and recommendations.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import cast, desc, or_, text as sa_text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.sql.expression import literal
from sqlalchemy.types import Text as TextType

from backend.models.auth import User
from backend.models.evaluation import (
    EvaluationDataset,
    EvaluationRecommendation,
    EvaluationResult,
    EvaluationRun,
    EvaluationTestCase,
)
from backend.models.execution import GraphExecution
from backend.services.config import get_logger
from backend.services.database import get_db

logger = get_logger("evaluation.repositories")

MAX_EVAL_DATASET_SIZE = int(os.getenv("MAX_EVAL_DATASET_SIZE", "200"))


class EvaluationRunRepository:
    """Repository for EvaluationRun CRUD operations."""

    def create(self, run_data: Dict[str, Any]) -> EvaluationRun:
        """Create a new evaluation run.

        Args:
            run_data: Dictionary of column values for the new run.

        Returns:
            The created EvaluationRun instance.
        """
        with get_db() as db:
            run = EvaluationRun(**run_data)
            db.add(run)
            db.commit()
            db.refresh(run)
            logger.info(f"Created evaluation run: {run.id}")
            return run

    def get(self, run_id: str) -> Optional[EvaluationRun]:
        """Get an evaluation run by ID.

        Args:
            run_id: The run UUID.

        Returns:
            EvaluationRun or None if not found.
        """
        with get_db() as db:
            return db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()

    def list(
        self,
        workflow_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        status: Optional[str] = None,
        trigger: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EvaluationRun]:
        """List evaluation runs with optional filters.

        Args:
            workflow_id: Filter by workflow.
            dataset_id: Filter by dataset.
            status: Filter by status.
            trigger: Filter by trigger type.
            target_type: Filter by target type (workflow, agent, model, tool).
            target_id: Filter by target ID.
            user_id: Filter to only runs triggered by this user.
            limit: Max results.
            offset: Results to skip.

        Returns:
            List of matching EvaluationRun instances.
        """
        with get_db() as db:
            query = db.query(EvaluationRun)
            if user_id:
                query = query.filter(EvaluationRun.triggered_by_user_id == user_id)
            if workflow_id:
                query = query.filter(EvaluationRun.workflow_id == workflow_id)
            if dataset_id:
                query = query.filter(EvaluationRun.dataset_id == dataset_id)
            if status:
                query = query.filter(EvaluationRun.status == status)
            if trigger:
                query = query.filter(EvaluationRun.trigger == trigger)
            if target_type:
                query = query.filter(EvaluationRun.target_type == target_type)
            if target_id:
                query = query.filter(EvaluationRun.target_id == target_id)
            return (
                query.order_by(desc(EvaluationRun.created_at))
                .limit(limit)
                .offset(offset)
                .all()
            )

    def delete(self, run_id: str, user_id: Optional[str] = None) -> bool:
        """Delete an evaluation run and its associated results/recommendations/executions.

        Args:
            run_id: The run UUID.
            user_id: If provided, only the run owner can delete.

        Returns:
            True if found and deleted, False otherwise.

        Raises:
            PermissionError: If user_id doesn't match the run's triggered_by_user_id.
        """
        with get_db() as db:
            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                return False
            if (
                user_id
                and run.triggered_by_user_id
                and run.triggered_by_user_id != user_id
            ):
                raise PermissionError("Only the run owner can delete this run")
            # Delete associated graph executions (cascade handles their node_executions)
            executions = (
                db.query(GraphExecution)
                .filter(GraphExecution.evaluation_run_id == run_id)
                .all()
            )
            for execution in executions:
                db.delete(execution)
            db.delete(run)
            db.commit()
            logger.info(
                f"Deleted evaluation run: {run_id} and {len(executions)} associated executions"
            )
            return True

    def update_status(
        self,
        run_id: str,
        status: str,
        completed_cases: Optional[int] = None,
        failed_cases: Optional[int] = None,
    ) -> Optional[EvaluationRun]:
        """Update run status and optional case counters.

        Args:
            run_id: The run UUID.
            status: New status value.
            completed_cases: Updated completed count.
            failed_cases: Updated failed count.

        Returns:
            Updated EvaluationRun or None if not found.
        """
        with get_db() as db:
            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                logger.warning(f"Evaluation run not found for status update: {run_id}")
                return None
            run.status = status
            if completed_cases is not None:
                run.completed_cases = completed_cases
            if failed_cases is not None:
                run.failed_cases = failed_cases
            db.commit()
            db.refresh(run)
            return run

    def update_scores(
        self, run_id: str, scores: Dict[str, Any]
    ) -> Optional[EvaluationRun]:
        """Update run scores and arbitrary attributes.

        Sets each key in ``scores`` as an attribute on the run if the
        attribute exists on the model. This allows updating scores,
        ``started_at``, ``completed_at``, ``total_cases``, etc.

        Args:
            run_id: The run UUID.
            scores: Dictionary of attribute names to values.

        Returns:
            Updated EvaluationRun or None if not found.
        """
        with get_db() as db:
            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                logger.warning(f"Evaluation run not found for score update: {run_id}")
                return None
            for key, value in scores.items():
                if hasattr(run, key):
                    setattr(run, key, value)
            db.commit()
            db.refresh(run)
            return run

    def get_latest_for_workflow(self, workflow_id: str) -> Optional[EvaluationRun]:
        """Get the most recent completed run for a workflow.

        Args:
            workflow_id: The workflow UUID.

        Returns:
            Latest completed EvaluationRun or None.
        """
        with get_db() as db:
            return (
                db.query(EvaluationRun)
                .filter(
                    EvaluationRun.workflow_id == workflow_id,
                    EvaluationRun.status.in_(["completed", "completed_with_failures"]),
                )
                .order_by(desc(EvaluationRun.completed_at))
                .first()
            )


class EvaluationResultRepository:
    """Repository for EvaluationResult CRUD operations."""

    def create(self, result_data: Dict[str, Any]) -> EvaluationResult:
        """Create a new evaluation result.

        Args:
            result_data: Dictionary of column values.

        Returns:
            The created EvaluationResult instance.
        """
        with get_db() as db:
            result = EvaluationResult(**result_data)
            db.add(result)
            db.commit()
            db.refresh(result)
            return result

    def list_by_run(self, run_id: str) -> List[EvaluationResult]:
        """List all results for an evaluation run.

        Args:
            run_id: The parent run UUID.

        Returns:
            List of EvaluationResult instances ordered by creation time.
        """
        with get_db() as db:
            return (
                db.query(EvaluationResult)
                .filter(EvaluationResult.run_id == run_id)
                .order_by(EvaluationResult.created_at)
                .all()
            )

    def update(
        self, result_id: str, updates: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """Update fields on an existing evaluation result.

        Args:
            result_id: The result UUID.
            updates: Dictionary of attribute names to new values.

        Returns:
            Updated EvaluationResult or None if not found.
        """
        with get_db() as db:
            result = (
                db.query(EvaluationResult)
                .filter(EvaluationResult.id == result_id)
                .first()
            )
            if not result:
                return None
            for key, value in updates.items():
                if hasattr(result, key):
                    setattr(result, key, value)
            db.commit()
            db.refresh(result)
            return result


class EvaluationDatasetRepository:
    """Repository for EvaluationDataset and EvaluationTestCase operations."""

    def create(self, dataset_data: Dict[str, Any]) -> EvaluationDataset:
        """Create a new evaluation dataset.

        Args:
            dataset_data: Dictionary of column values.

        Returns:
            The created EvaluationDataset instance.
        """
        with get_db() as db:
            dataset = EvaluationDataset(**dataset_data)
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            logger.info(f"Created evaluation dataset: {dataset.id}")
            return dataset

    def get(self, dataset_id: str) -> Optional[EvaluationDataset]:
        """Get a dataset by ID (excludes soft-deleted).

        Args:
            dataset_id: The dataset UUID.

        Returns:
            EvaluationDataset or None.
        """
        with get_db() as db:
            return (
                db.query(EvaluationDataset)
                .filter(
                    EvaluationDataset.id == dataset_id,
                    EvaluationDataset.is_deleted == False,  # noqa: E712
                )
                .first()
            )

    def list(
        self,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_groups: Optional[List[str]] = None,
        filter_type: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List datasets with optional filters and visibility-based access control.

        Args:
            target_type: Filter by target type.
            target_id: Filter by target ID.
            created_by_user_id: Filter by creator (legacy, prefer filter_type).
            user_id: Current user ID for visibility filtering.
            user_groups: Groups the current user belongs to.
            filter_type: 'all' (owned + shared), 'my' (owned only), 'shared' (shared only).
            limit: Max results.

        Returns:
            List of dicts with dataset fields plus creator info and is_read_only.
        """
        if user_groups is None:
            user_groups = []

        with get_db() as db:
            query = (
                db.query(
                    EvaluationDataset,
                    User.name.label("creator_name"),
                    User.email.label("creator_email"),
                )
                .outerjoin(User, EvaluationDataset.created_by_user_id == User.id)
                .filter(EvaluationDataset.is_deleted == False)  # noqa: E712
            )

            if target_type:
                query = query.filter(EvaluationDataset.target_type == target_type)
            if target_id:
                query = query.filter(
                    (EvaluationDataset.target_id == target_id)
                    | (EvaluationDataset.target_id.is_(None))
                )
            if created_by_user_id:
                query = query.filter(
                    EvaluationDataset.created_by_user_id == created_by_user_id
                )

            # Visibility filtering when user_id is provided
            if user_id:
                all_visible = EvaluationDataset.visible_to_groups.op("@>")(
                    sa_text("'[\"__all__\"]'::jsonb")
                )

                if user_groups:
                    groups_overlap = EvaluationDataset.visible_to_groups.op("?|")(
                        cast(literal(user_groups), PG_ARRAY(TextType))
                    )
                    shared_condition = or_(all_visible, groups_overlap)
                else:
                    shared_condition = all_visible

                owned_condition = EvaluationDataset.created_by_user_id == user_id

                if filter_type == "my":
                    query = query.filter(owned_condition)
                elif filter_type == "shared":
                    query = query.filter(
                        shared_condition,
                        EvaluationDataset.created_by_user_id != user_id,
                    )
                else:  # "all"
                    query = query.filter(or_(owned_condition, shared_condition))

            rows = query.order_by(desc(EvaluationDataset.created_at)).limit(limit).all()

            results = []
            for dataset, creator_name, creator_email in rows:
                is_read_only = (
                    user_id is not None and dataset.created_by_user_id != user_id
                )
                results.append(
                    {
                        "dataset": dataset,
                        "creator_name": creator_name,
                        "creator_email": creator_email,
                        "is_read_only": is_read_only,
                    }
                )
            return results

    def update(
        self, dataset_id: str, updates: Dict[str, Any]
    ) -> Optional[EvaluationDataset]:
        """Update mutable fields on a dataset.

        Args:
            dataset_id: The dataset UUID.
            updates: Dictionary of fields to update.

        Returns:
            Updated EvaluationDataset or None if not found.
        """
        with get_db() as db:
            dataset = (
                db.query(EvaluationDataset)
                .filter(
                    EvaluationDataset.id == dataset_id,
                    EvaluationDataset.is_deleted == False,  # noqa: E712
                )
                .first()
            )
            if not dataset:
                return None
            for key, value in updates.items():
                setattr(dataset, key, value)
            db.commit()
            db.refresh(dataset)
            return dataset

    def soft_delete(self, dataset_id: str) -> bool:
        """Soft-delete a dataset.

        Args:
            dataset_id: The dataset UUID.

        Returns:
            True if found and deleted, False otherwise.
        """
        with get_db() as db:
            dataset = (
                db.query(EvaluationDataset)
                .filter(
                    EvaluationDataset.id == dataset_id,
                    EvaluationDataset.is_deleted == False,  # noqa: E712
                )
                .first()
            )
            if not dataset:
                return False
            dataset.is_deleted = True
            db.commit()
            return True

    def count_test_cases(self, dataset_id: str, db) -> int:
        """Count test cases in a dataset using an existing session.

        Args:
            dataset_id: The dataset UUID.
            db: Active SQLAlchemy session.

        Returns:
            Number of test cases.
        """
        return (
            db.query(EvaluationTestCase)
            .filter(EvaluationTestCase.dataset_id == dataset_id)
            .count()
        )

    def add_test_cases(
        self, dataset_id: str, cases: List[Dict[str, Any]], db
    ) -> List[EvaluationTestCase]:
        """Add test cases to a dataset within an existing transaction.

        Uses SELECT ... FOR UPDATE to prevent concurrent cap breaches.
        Calls ``db.flush()`` (not commit) so the caller owns the transaction.

        Args:
            dataset_id: The dataset UUID.
            cases: List of test case data dictionaries.
            db: Active SQLAlchemy session.

        Returns:
            List of created EvaluationTestCase instances.

        Raises:
            ValueError: If adding cases would exceed MAX_EVAL_DATASET_SIZE.
        """
        # Lock the dataset row for update
        dataset = (
            db.query(EvaluationDataset)
            .filter(EvaluationDataset.id == dataset_id)
            .with_for_update()
            .first()
        )
        if dataset is None:
            raise ValueError(
                f"Dataset not found: {dataset_id}. Cannot add test cases to a non-existent dataset."
            )

        current_count = self.count_test_cases(dataset_id, db)
        if current_count + len(cases) > MAX_EVAL_DATASET_SIZE:
            raise ValueError(
                f"Adding {len(cases)} cases would exceed dataset cap of {MAX_EVAL_DATASET_SIZE} "
                f"(current: {current_count})"
            )

        created = []
        for case_data in cases:
            case_data["dataset_id"] = dataset_id
            test_case = EvaluationTestCase(**case_data)
            db.add(test_case)
            created.append(test_case)

        db.flush()
        return created

    def set_baseline_run(
        self, dataset_id: str, run_id: str
    ) -> Optional[EvaluationDataset]:
        """Set the baseline run for a dataset.

        Args:
            dataset_id: The dataset UUID.
            run_id: The baseline run UUID.

        Returns:
            Updated EvaluationDataset or None.
        """
        with get_db() as db:
            dataset = (
                db.query(EvaluationDataset)
                .filter(EvaluationDataset.id == dataset_id)
                .first()
            )
            if not dataset:
                return None
            dataset.baseline_run_id = run_id
            db.commit()
            db.refresh(dataset)
            return dataset

    def update_visibility(
        self, dataset_id: str, visible_to_groups: List[str], user_id: str
    ) -> Optional[EvaluationDataset]:
        """Update visibility groups for a dataset. Only the owner can change visibility.

        Args:
            dataset_id: The dataset UUID.
            visible_to_groups: New list of group names.
            user_id: User requesting the change (must be owner).

        Returns:
            Updated EvaluationDataset or None if not found.

        Raises:
            PermissionError: If user is not the dataset owner.
        """
        with get_db() as db:
            dataset = (
                db.query(EvaluationDataset)
                .filter(
                    EvaluationDataset.id == dataset_id,
                    EvaluationDataset.is_deleted == False,  # noqa: E712
                )
                .first()
            )
            if not dataset:
                return None
            if dataset.created_by_user_id != user_id:
                raise PermissionError("Only the dataset creator can change visibility")
            dataset.visible_to_groups = visible_to_groups
            db.commit()
            db.refresh(dataset)
            logger.info(
                "Updated visibility for dataset %s to %s", dataset_id, visible_to_groups
            )
            return dataset


class EvaluationRecommendationRepository:
    """Repository for EvaluationRecommendation CRUD operations."""

    def list_by_run(self, run_id: str) -> List[EvaluationRecommendation]:
        """List all recommendations for an evaluation run.

        Args:
            run_id: The parent run UUID.

        Returns:
            List of EvaluationRecommendation instances.
        """
        with get_db() as db:
            return (
                db.query(EvaluationRecommendation)
                .filter(EvaluationRecommendation.run_id == run_id)
                .order_by(EvaluationRecommendation.created_at)
                .all()
            )

    def create(self, rec_data: Dict[str, Any]) -> EvaluationRecommendation:
        """Create a new recommendation.

        Args:
            rec_data: Dictionary of column values.

        Returns:
            The created EvaluationRecommendation instance.
        """
        with get_db() as db:
            rec = EvaluationRecommendation(**rec_data)
            db.add(rec)
            db.commit()
            db.refresh(rec)
            return rec

    def update_status(
        self,
        rec_id: str,
        status: str,
        applied_by_user_id: Optional[str] = None,
        applied_version: Optional[int] = None,
        applied_graph_definition_id: Optional[str] = None,
    ) -> Optional[EvaluationRecommendation]:
        """Update recommendation status.

        Sets ``applied_at`` automatically when status is "applied".

        Args:
            rec_id: The recommendation UUID.
            status: New status value.
            applied_by_user_id: User who applied the recommendation.
            applied_version: Graph version the change was applied to.
            applied_graph_definition_id: Graph definition ID of the applied version.

        Returns:
            Updated EvaluationRecommendation or None.
        """
        with get_db() as db:
            rec = (
                db.query(EvaluationRecommendation)
                .filter(EvaluationRecommendation.id == rec_id)
                .first()
            )
            if not rec:
                return None
            rec.status = status
            if status == "applied":
                rec.applied_at = datetime.now(timezone.utc)
                if applied_by_user_id:
                    rec.applied_by_user_id = applied_by_user_id
                if applied_version is not None:
                    rec.applied_version = applied_version
                if applied_graph_definition_id:
                    rec.applied_graph_definition_id = applied_graph_definition_id
            db.commit()
            db.refresh(rec)
            return rec
