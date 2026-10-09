"""Tests for EvaluationResultRepository.update()."""

from unittest.mock import MagicMock, patch

from backend.services.evaluation.repositories import EvaluationResultRepository


def test_update_calls_setattr_and_commit():
    mock_result = MagicMock()
    mock_result.id = "result-1"

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_result
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    with patch(
        "backend.services.evaluation.repositories.get_db",
        return_value=mock_session,
    ):
        repo = EvaluationResultRepository()
        updated = repo.update("result-1", {"trace_reference": {"trace_id": "t1"}})

        assert updated is mock_result
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_result)


def test_update_returns_none_when_not_found():
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    with patch(
        "backend.services.evaluation.repositories.get_db",
        return_value=mock_session,
    ):
        repo = EvaluationResultRepository()
        result = repo.update("nonexistent-id", {"trace_reference": {}})

        assert result is None
        mock_session.commit.assert_not_called()
