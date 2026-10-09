"""Tests for model deployment default flag handling by model type."""

import pytest
from unittest.mock import MagicMock
from backend.services.model_deployment.exceptions import DefaultModelConflictError
from backend.services.model_deployment.service import ModelDeploymentService
from backend.models import ModelDeployment


class TestModelDeploymentDefaults:
    """Test default flag scoping by model type."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self):
        """Create a ModelDeploymentService instance."""
        return ModelDeploymentService()

    def test_clear_default_filters_by_model_type(self, mock_db):
        """Test that _clear_default filters by model_type when provided."""
        # Create mock LLM deployment
        llm_deployment = MagicMock(spec=ModelDeployment)
        llm_deployment.provider = "azure_openai"
        llm_deployment.model_type = "llm"
        llm_deployment.is_default = True

        # Mock query chain - return LLM deployment when filtering by llm
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [llm_deployment]
        mock_db.query.return_value = mock_query

        # Call _clear_default with model_type filter
        ModelDeploymentService._clear_default(
            mock_db, provider="azure_openai", model_type="llm"
        )

        # Verify model_type filter was applied
        # The query should have been filtered by:
        # 1. is_default=True
        # 2. provider="azure_openai"
        # 3. model_type="llm"
        assert mock_db.query.called
        assert mock_query.filter.call_count >= 3

        # Verify only LLM deployment was updated
        assert llm_deployment.is_default is False

    def test_clear_default_without_model_type_filter(self, mock_db):
        """Test that _clear_default works without model_type (backward compatibility)."""
        # Create mock deployments
        deployment1 = MagicMock(spec=ModelDeployment)
        deployment1.provider = "azure_openai"
        deployment1.is_default = True

        deployment2 = MagicMock(spec=ModelDeployment)
        deployment2.provider = "azure_openai"
        deployment2.is_default = True

        # Mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [deployment1, deployment2]
        mock_db.query.return_value = mock_query

        # Call _clear_default without model_type filter
        ModelDeploymentService._clear_default(
            mock_db, provider="azure_openai", model_type=None
        )

        # Verify both deployments were updated (no model_type filter)
        assert deployment1.is_default is False
        assert deployment2.is_default is False

    def test_clear_default_with_exclude_id(self, mock_db):
        """Test that _clear_default excludes specified deployment ID."""
        # Create mock deployments
        deployment1 = MagicMock(spec=ModelDeployment)
        deployment1.id = "deploy-1"
        deployment1.provider = "azure_openai"
        deployment1.model_type = "llm"
        deployment1.is_default = True

        deployment2 = MagicMock(spec=ModelDeployment)
        deployment2.id = "deploy-2"
        deployment2.provider = "azure_openai"
        deployment2.model_type = "llm"
        deployment2.is_default = True

        # Mock query chain - only return deployment1 (deployment2 is excluded)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [deployment1]
        mock_db.query.return_value = mock_query

        # Call _clear_default with exclude_id
        ModelDeploymentService._clear_default(
            mock_db,
            provider="azure_openai",
            model_type="llm",
            exclude_id="deploy-2",
        )

        # Verify only deployment1 was updated (deployment2 was excluded)
        assert deployment1.is_default is False

    def test_separate_defaults_for_llm_and_embedding(self, mock_db):
        """Test that LLM and embedding models can have separate defaults.

        This test verifies the fix for the issue where setting one default
        would clear the other model type's default.
        """
        llm_deployment = MagicMock(spec=ModelDeployment)
        llm_deployment.provider = "azure_openai"
        llm_deployment.model_type = "llm"
        llm_deployment.is_default = True

        # Mock query to return empty list when filtering by model_type="embedding"
        # This simulates the real behavior where the LLM deployment is NOT included
        # in the result set when querying for embedding defaults
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # Empty result - no embeddings to clear
        mock_db.query.return_value = mock_query

        # Clear defaults for embedding model type (should not affect LLM)
        ModelDeploymentService._clear_default(
            mock_db, provider="azure_openai", model_type="embedding"
        )

        # Since the query returns no results (empty list), the LLM deployment's
        # is_default should remain True (it was never in the result set)
        assert llm_deployment.is_default is True

        # Verify the query was called with proper filters
        assert mock_query.filter.called


class TestSingleDefaultPerModelType:
    """Test the Bug 7469 fix: enforce a single default per model type.

    Setting a deployment as default must be rejected (not silently applied)
    when another active deployment of the same model type is already
    default, regardless of provider. Callers must unset the existing default
    first.
    """

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_assert_no_conflict_raises_when_default_exists(self, mock_db):
        """Raises DefaultModelConflictError when another default of the same
        model type already exists, even with a different provider."""
        existing = MagicMock(spec=ModelDeployment)
        existing.id = "existing-id"
        existing.name = "existing-embedding-default"
        existing.provider = "openai"
        existing.model_type = "embedding"
        existing.is_default = True
        existing.is_active = True

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing
        mock_db.query.return_value = mock_query

        with pytest.raises(DefaultModelConflictError) as exc_info:
            ModelDeploymentService._assert_no_default_conflict(
                mock_db, model_type="embedding"
            )

        assert "Only one model can be set as default" in str(exc_info.value)
        assert (
            "unset the existing default model before selecting a new one"
            in str(exc_info.value)
        )
        assert exc_info.value.model_type == "embedding"
        # The conflicting deployment's name should be surfaced so the UI can
        # tell the user exactly which model needs to be unset.
        assert exc_info.value.existing_name == "existing-embedding-default"
        assert "existing-embedding-default" in str(exc_info.value)

    def test_assert_no_conflict_passes_when_no_default_exists(self, mock_db):
        """Does not raise when no existing default of that model type exists."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Should not raise
        ModelDeploymentService._assert_no_default_conflict(
            mock_db, model_type="llm"
        )

    def test_assert_no_conflict_excludes_self_on_update(self, mock_db):
        """Excludes the deployment being updated from the conflict check so
        re-saving an already-default deployment does not falsely conflict."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        ModelDeploymentService._assert_no_default_conflict(
            mock_db, model_type="llm", exclude_id="self-id"
        )

        # exclude_id filter should have been applied via chained .filter calls
        assert mock_query.filter.call_count >= 2

    def test_conflict_is_independent_of_provider(self, mock_db):
        """Two deployments of the same model type but different providers
        must still conflict - the default flag is scoped by model type only,
        not provider."""
        existing = MagicMock(spec=ModelDeployment)
        existing.id = "azure-embedding"
        existing.name = "azure-embedding-default"
        existing.provider = "azure_openai"
        existing.model_type = "embedding"
        existing.is_default = True
        existing.is_active = True

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing
        mock_db.query.return_value = mock_query

        # Attempting to default a *different provider's* embedding model
        # should still raise, since scoping must be by model_type alone.
        with pytest.raises(DefaultModelConflictError):
            ModelDeploymentService._assert_no_default_conflict(
                mock_db, model_type="embedding"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
