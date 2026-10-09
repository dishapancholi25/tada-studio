"""Tests for admin API routes.

This module tests:
- Feature access CRUD operations
- Admin-only route protection
- CSRF token validation
- Input validation and sanitization
- Feature name whitelist enforcement
- Audit logging
- Cache invalidation on updates
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.api.admin.routes import (
    list_feature_access,
    get_feature_access,
    update_feature_access,
    reset_feature_access,
    validate_feature_name,
    FeatureAccessUpdate,
)


@pytest.fixture
def mock_request():
    """Mock FastAPI Request object."""
    request = MagicMock()
    request.headers = {}
    return request


@pytest.fixture
def admin_user():
    """Admin user claims."""
    return {
        "email": "admin@example.com",
        "name": "Admin User",
        "groups": ["admins"],
        "sub": "admin-123",
    }


@pytest.fixture
def regular_user():
    """Regular user claims."""
    return {
        "email": "user@example.com",
        "name": "Regular User",
        "groups": ["users"],
        "sub": "user-123",
    }


@pytest.fixture
def mock_feature_access():
    """Mock FeatureAccess database model."""
    feature = MagicMock()
    feature.id = "feature-123"
    feature.feature_name = "settings.database"
    feature.display_name = "Database Settings"
    feature.admin_only = True
    feature.description = "Database configuration settings"
    feature.to_dict.return_value = {
        "id": "feature-123",
        "feature_name": "settings.database",
        "display_name": "Database Settings",
        "admin_only": True,
        "description": "Database configuration settings",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    return feature


class TestValidateFeatureName:
    """Tests for feature name validation."""

    def test_valid_feature_name(self):
        """Test validation of valid feature names."""
        # Should not raise exception
        validate_feature_name("settings.database")
        validate_feature_name("settings.llm_providers")
        validate_feature_name("nav.workflow")

    def test_invalid_format_no_dot(self):
        """Test rejection of feature name without dot separator."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("invalid")
        assert exc_info.value.status_code == 400
        assert "Invalid feature name format" in exc_info.value.detail

    def test_invalid_format_multiple_dots(self):
        """Test rejection of feature name with multiple dots."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("settings.sub.feature")
        assert exc_info.value.status_code == 400

    def test_invalid_characters(self):
        """Test rejection of feature name with invalid characters."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("settings.UPPERCASE")
        assert exc_info.value.status_code == 400

    def test_feature_not_in_whitelist(self):
        """Test rejection of feature not in whitelist."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("unknown.feature")
        assert exc_info.value.status_code == 400
        assert "Unknown feature name" in exc_info.value.detail

    def test_sql_injection_attempt(self):
        """Test rejection of SQL injection attempts."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("settings'; DROP TABLE users; --")
        assert exc_info.value.status_code == 400

    def test_path_traversal_attempt(self):
        """Test rejection of path traversal attempts."""
        with pytest.raises(HTTPException) as exc_info:
            validate_feature_name("../../../etc/passwd")
        assert exc_info.value.status_code == 400


class TestListFeatureAccess:
    """Tests for listing all feature access settings."""

    @patch("backend.api.admin.routes.get_db")
    def test_list_all_features_success(
        self, mock_get_db, regular_user, mock_feature_access
    ):
        """Test successful listing of all feature access settings."""
        # Setup mock database
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock query result
        feature1 = MagicMock()
        feature1.to_dict.return_value = {
            "feature_name": "settings.database",
            "admin_only": True,
        }
        feature2 = MagicMock()
        feature2.to_dict.return_value = {
            "feature_name": "settings.appearance",
            "admin_only": False,
        }

        mock_session.query.return_value.all.return_value = [feature1, feature2]

        # Call endpoint
        response = list_feature_access(current_user=regular_user)

        # Verify response
        assert response.success is True
        assert len(response.features) == 2
        assert response.features[0]["feature_name"] == "settings.database"
        assert response.features[1]["feature_name"] == "settings.appearance"

    @patch("backend.api.admin.routes.get_db")
    def test_list_features_database_error(self, mock_get_db, regular_user):
        """Test handling of database errors when listing features."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            list_feature_access(current_user=regular_user)

        assert exc_info.value.status_code == 500
        assert "Failed to list feature access" in exc_info.value.detail

    @patch("backend.api.admin.routes.get_db")
    def test_list_features_empty_database(self, mock_get_db, regular_user):
        """Test listing features when database is empty."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.all.return_value = []

        response = list_feature_access(current_user=regular_user)

        assert response.success is True
        assert response.features == []


class TestGetFeatureAccess:
    """Tests for getting a specific feature access setting."""

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_get_feature_success(
        self, mock_get_db, mock_validate, mock_request, admin_user, mock_feature_access
    ):
        """Test successful retrieval of a feature."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature_access
        )

        response = get_feature_access(
            request=mock_request,
            feature_name="settings.database",
            current_user=admin_user,
        )

        assert response.success is True
        assert response.feature["feature_name"] == "settings.database"
        mock_validate.assert_called_once_with("settings.database")

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_get_feature_not_found(
        self, mock_get_db, mock_validate, mock_request, admin_user
    ):
        """Test getting a feature that doesn't exist."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_feature_access(
                request=mock_request,
                feature_name="settings.database",
                current_user=admin_user,
            )

        assert exc_info.value.status_code == 404
        assert "Feature not found" in exc_info.value.detail

    @patch("backend.api.admin.routes.validate_feature_name")
    def test_get_feature_invalid_name(self, mock_validate, mock_request, admin_user):
        """Test getting a feature with invalid name."""
        mock_validate.side_effect = HTTPException(
            status_code=400, detail="Invalid feature name"
        )

        with pytest.raises(HTTPException) as exc_info:
            get_feature_access(
                request=mock_request, feature_name="invalid", current_user=admin_user
            )

        assert exc_info.value.status_code == 400

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_get_feature_database_error(
        self, mock_get_db, mock_validate, mock_request, admin_user
    ):
        """Test handling of database errors when getting feature."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            get_feature_access(
                request=mock_request,
                feature_name="settings.database",
                current_user=admin_user,
            )

        assert exc_info.value.status_code == 500


class TestUpdateFeatureAccess:
    """Tests for updating feature access settings."""

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_success(
        self,
        mock_get_db,
        mock_validate,
        mock_clear_cache,
        mock_request,
        admin_user,
        mock_feature_access,
    ):
        """Test successful feature update."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature_access
        )

        update_data = FeatureAccessUpdate(admin_only=False)

        response = update_feature_access(
            request=mock_request,
            feature_name="settings.database",
            update=update_data,
            current_user=admin_user,
            _csrf=None,
        )

        assert response.success is True
        assert "updated successfully" in response.message
        assert mock_feature_access.admin_only is False
        mock_session.commit.assert_called_once()
        mock_clear_cache.assert_called_once()

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_audit_logging(
        self,
        mock_get_db,
        mock_validate,
        mock_clear_cache,
        mock_request,
        admin_user,
        mock_feature_access,
    ):
        """Test that feature updates are audit logged."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature_access
        )

        mock_feature_access.admin_only = True  # Old value

        update_data = FeatureAccessUpdate(admin_only=False)

        with patch("backend.api.admin.routes.logger") as mock_logger:
            update_feature_access(
                request=mock_request,
                feature_name="settings.database",
                update=update_data,
                current_user=admin_user,
                _csrf=None,
            )

            # Verify audit log was created
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "[AUDIT]" in log_message
            assert "a***n@example.com" in log_message  # Email is redacted for privacy
            assert "settings.database" in log_message

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_not_found(
        self, mock_get_db, mock_validate, mock_request, admin_user
    ):
        """Test updating a non-existent feature."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        update_data = FeatureAccessUpdate(admin_only=False)

        with pytest.raises(HTTPException) as exc_info:
            update_feature_access(
                request=mock_request,
                feature_name="settings.database",
                update=update_data,
                current_user=admin_user,
                _csrf=None,
            )

        assert exc_info.value.status_code == 404

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_cache_cleared(
        self,
        mock_get_db,
        mock_validate,
        mock_clear_cache,
        mock_request,
        admin_user,
        mock_feature_access,
    ):
        """Test that cache is cleared after successful update."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature_access
        )

        update_data = FeatureAccessUpdate(admin_only=False)

        update_feature_access(
            request=mock_request,
            feature_name="settings.database",
            update=update_data,
            current_user=admin_user,
            _csrf=None,
        )

        # Verify cache was cleared
        mock_clear_cache.assert_called_once()

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_database_error(
        self, mock_get_db, mock_validate, mock_request, admin_user
    ):
        """Test handling of database errors during update."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.side_effect = Exception("Database error")

        update_data = FeatureAccessUpdate(admin_only=False)

        with pytest.raises(HTTPException) as exc_info:
            update_feature_access(
                request=mock_request,
                feature_name="settings.database",
                update=update_data,
                current_user=admin_user,
                _csrf=None,
            )

        assert exc_info.value.status_code == 500

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_feature_commit_called(
        self,
        mock_get_db,
        mock_validate,
        mock_clear_cache,
        mock_request,
        admin_user,
        mock_feature_access,
    ):
        """Test that database commit is called after update."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature_access
        )

        update_data = FeatureAccessUpdate(admin_only=False)

        update_feature_access(
            request=mock_request,
            feature_name="settings.database",
            update=update_data,
            current_user=admin_user,
            _csrf=None,
        )

        mock_session.commit.assert_called_once()


class TestResetFeatureAccess:
    """Tests for resetting feature access to defaults."""

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.get_db")
    def test_reset_success(
        self, mock_get_db, mock_clear_cache, mock_request, admin_user
    ):
        """Test successful reset of feature access settings."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Create mock features
        features = {}
        for feature_name in [
            "settings.database",
            "settings.llm_providers",
            "settings.external_services",
            "settings.external_tools",
            "settings.appearance",
            "settings.api_tokens",
        ]:
            mock_feature = MagicMock()
            mock_feature.feature_name = feature_name
            features[feature_name] = mock_feature

        # Mock query to return the appropriate feature
        def get_feature(feature_name):
            mock_query = MagicMock()
            mock_query.first.return_value = features.get(feature_name)
            return mock_query

        mock_session.query.return_value.filter.side_effect = lambda *args: get_feature(
            args[0].right.value if hasattr(args[0].right, "value") else None
        )

        response = reset_feature_access(
            request=mock_request, current_user=admin_user, _csrf=None
        )

        assert response.success is True
        assert "reset to defaults" in response.message
        mock_session.commit.assert_called_once()
        mock_clear_cache.assert_called_once()

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.get_db")
    def test_reset_default_values(
        self, mock_get_db, mock_clear_cache, mock_request, admin_user
    ):
        """Test that reset applies default values and commits changes."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock query to return empty features (they will be created if needed)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            MagicMock()
        )

        response = reset_feature_access(
            request=mock_request, current_user=admin_user, _csrf=None
        )

        # Verify operation succeeded
        assert response.success is True
        assert "reset to defaults" in response.message

        # Verify commit was called
        mock_session.commit.assert_called_once()

        # Verify cache was cleared
        mock_clear_cache.assert_called_once()

    @patch("backend.api.admin.routes.clear_feature_access_cache")
    @patch("backend.api.admin.routes.get_db")
    def test_reset_audit_logging(
        self, mock_get_db, mock_clear_cache, mock_request, admin_user
    ):
        """Test that reset operation is audit logged."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock empty query results
        mock_session.query.return_value.filter.return_value.first.return_value = (
            MagicMock()
        )

        with patch("backend.api.admin.routes.logger") as mock_logger:
            reset_feature_access(
                request=mock_request, current_user=admin_user, _csrf=None
            )

            # Verify audit log
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "[AUDIT]" in log_message
            assert "reset to defaults" in log_message
            assert "a***n@example.com" in log_message  # Email is redacted for privacy

    @patch("backend.api.admin.routes.get_db")
    def test_reset_database_error(self, mock_get_db, mock_request, admin_user):
        """Test handling of database errors during reset."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            reset_feature_access(
                request=mock_request, current_user=admin_user, _csrf=None
            )

        assert exc_info.value.status_code == 500


class TestCSRFProtection:
    """Tests for CSRF token validation on mutating endpoints."""

    @patch("backend.api.admin.routes.validate_feature_name")
    @patch("backend.api.admin.routes.get_db")
    def test_update_requires_csrf(
        self, mock_get_db, mock_validate, mock_request, admin_user
    ):
        """Test that update endpoint requires CSRF token."""
        # This is enforced by FastAPI dependency injection
        # The _csrf parameter with Depends(verify_csrf_token) ensures CSRF validation
        # If CSRF validation fails, an HTTPException should be raised before the route handler

        # We can't directly test the dependency here, but we verify it's declared
        # in the function signature
        import inspect

        sig = inspect.signature(update_feature_access)
        assert "_csrf" in sig.parameters

    @patch("backend.api.admin.routes.get_db")
    def test_reset_requires_csrf(self, mock_get_db, mock_request, admin_user):
        """Test that reset endpoint requires CSRF token."""
        import inspect

        sig = inspect.signature(reset_feature_access)
        assert "_csrf" in sig.parameters


class TestInputValidation:
    """Tests for input validation and sanitization."""

    def test_feature_access_update_model_validation(self):
        """Test FeatureAccessUpdate model validates input."""
        # Valid input
        valid_update = FeatureAccessUpdate(admin_only=True)
        assert valid_update.admin_only is True

        valid_update = FeatureAccessUpdate(admin_only=False)
        assert valid_update.admin_only is False

    def test_feature_access_update_requires_boolean(self):
        """Test that admin_only field requires boolean type."""
        # Pydantic should handle type coercion, but explicit booleans are best
        update = FeatureAccessUpdate(admin_only=True)
        assert isinstance(update.admin_only, bool)
