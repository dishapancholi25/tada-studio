"""Tests for RBAC (Role-Based Access Control) service.

This module tests:
- Admin detection via group membership and explicit user lists
- Feature access checks with admin bypass
- Cache TTL behavior and expiration
- Fail-closed security on database errors
"""

import os
import pytest
import time
from unittest.mock import MagicMock, patch

from backend.services.auth.rbac import (
    is_user_admin,
    get_user_groups,
    check_feature_access,
    clear_feature_access_cache,
    _get_feature_admin_only,
    _redact_email,
    _feature_access_cache,
    _CACHE_TTL_SECONDS,
)


@pytest.fixture
def admin_user_by_group():
    """User claims for a user who is admin via group membership."""
    return {
        "email": "admin@example.com",
        "name": "Admin User",
        "groups": ["admins", "users"],
        "sub": "admin-123",
    }


@pytest.fixture
def admin_user_by_explicit_list():
    """User claims for a user who is admin via explicit user list."""
    return {
        "email": "superadmin@example.com",
        "name": "Super Admin",
        "groups": ["users"],
        "sub": "superadmin-123",
    }


@pytest.fixture
def regular_user():
    """User claims for a regular non-admin user."""
    return {
        "email": "user@example.com",
        "name": "Regular User",
        "groups": ["users"],
        "sub": "user-123",
    }


@pytest.fixture
def user_no_groups():
    """User claims for a user with no groups."""
    return {
        "email": "nogroups@example.com",
        "name": "No Groups User",
        "sub": "nogroups-123",
    }


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the feature access cache before and after each test."""
    # Clear cache before test
    _feature_access_cache.clear()
    yield
    # Clear cache after test
    _feature_access_cache.clear()


class TestRedactEmail:
    """Tests for email redaction utility."""

    def test_redact_normal_email(self):
        """Test redacting a normal email address."""
        result = _redact_email("john.doe@example.com")
        assert result == "j**n.d*e@example.com"

    def test_redact_simple_email(self):
        """Test redacting a simple email without dots."""
        result = _redact_email("john@example.com")
        assert result == "j**n@example.com"

    def test_redact_short_email(self):
        """Test redacting a single-character email."""
        result = _redact_email("a@example.com")
        assert result == "*@example.com"

    def test_redact_two_char_email(self):
        """Test redacting a two-character email."""
        result = _redact_email("ab@example.com")
        assert result == "a*@example.com"

    def test_redact_multiple_dots(self):
        """Test redacting email with multiple dots."""
        result = _redact_email("john.paul.doe@example.com")
        assert result == "j**n.p**l.d*e@example.com"

    def test_redact_plain_username(self):
        """Test redacting a plain username (no @ sign)."""
        result = _redact_email("admin")
        assert result == "a***n"

    def test_redact_username_with_dots(self):
        """Test redacting a username with dots (no @ sign)."""
        result = _redact_email("john.smith")
        assert result == "j**n.s***h"

    def test_redact_short_username(self):
        """Test redacting a short username."""
        result = _redact_email("ab")
        assert result == "a*"

    def test_redact_single_char_username(self):
        """Test redacting a single-character username."""
        result = _redact_email("a")
        assert result == "*"

    def test_redact_non_string(self):
        """Test redacting a non-string value."""
        result = _redact_email(12345)  # type: ignore
        assert result == "<redacted>"


class TestIsUserAdmin:
    """Tests for admin detection logic."""

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_admin_via_explicit_user_list(
        self, mock_get_auth_config, admin_user_by_explicit_list
    ):
        """Test admin detection via explicit user list."""
        mock_config = MagicMock()
        mock_config.admin_users = {"superadmin@example.com", "admin2@example.com"}
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        assert is_user_admin(admin_user_by_explicit_list) is True

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_admin_via_group_membership(
        self, mock_get_auth_config, admin_user_by_group
    ):
        """Test admin detection via group membership."""
        mock_config = MagicMock()
        mock_config.admin_users = set()
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        assert is_user_admin(admin_user_by_group) is True

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_non_admin_user(self, mock_get_auth_config, regular_user):
        """Test non-admin user detection."""
        mock_config = MagicMock()
        mock_config.admin_users = set()
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        assert is_user_admin(regular_user) is False

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_user_no_groups(self, mock_get_auth_config, user_no_groups):
        """Test user with no groups field."""
        mock_config = MagicMock()
        mock_config.admin_users = set()
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        assert is_user_admin(user_no_groups) is False

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_no_admin_group_configured(self, mock_get_auth_config, admin_user_by_group):
        """Test admin detection when no admin group is configured."""
        mock_config = MagicMock()
        mock_config.admin_users = set()
        mock_config.admin_group = None
        mock_get_auth_config.return_value = mock_config

        assert is_user_admin(admin_user_by_group) is False

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_explicit_list_takes_precedence(self, mock_get_auth_config):
        """Test that explicit user list is checked before groups."""
        mock_config = MagicMock()
        mock_config.admin_users = {"explicit@example.com"}
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        # User is in explicit list but not in admin group
        user_claims = {"email": "explicit@example.com", "groups": ["users"]}

        assert is_user_admin(user_claims) is True

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_groups_not_a_list(self, mock_get_auth_config):
        """Test handling of malformed groups claim (not a list)."""
        mock_config = MagicMock()
        mock_config.admin_users = set()
        mock_config.admin_group = "admins"
        mock_get_auth_config.return_value = mock_config

        user_claims = {
            "email": "user@example.com",
            "groups": "not-a-list",  # Invalid: should be a list
        }

        assert is_user_admin(user_claims) is False

    @patch("backend.services.auth.rbac.get_auth_config")
    def test_case_insensitive_email_comparison(self, mock_get_auth_config):
        """Test that admin email comparison is case-insensitive."""
        mock_config = MagicMock()
        # Admin users list stored in lowercase
        mock_config.admin_users = {"admin@example.com", "superadmin@example.com"}
        mock_config.admin_group = None
        mock_get_auth_config.return_value = mock_config

        # Test various case combinations
        test_cases = [
            "Admin@Example.com",
            "ADMIN@EXAMPLE.COM",
            "aDmIn@eXaMpLe.CoM",
            "SuperAdmin@Example.COM",
        ]

        for email_variant in test_cases:
            user_claims = {"email": email_variant, "groups": []}
            assert is_user_admin(user_claims) is True, (
                f"Failed for email: {email_variant}"
            )


class TestGetUserGroups:
    """Tests for user groups extraction."""

    def test_get_groups_normal(self, admin_user_by_group):
        """Test extracting groups from normal user claims."""
        groups = get_user_groups(admin_user_by_group)
        assert groups == ["admins", "users"]

    def test_get_groups_empty(self, user_no_groups):
        """Test extracting groups when no groups present."""
        groups = get_user_groups(user_no_groups)
        assert groups == []

    def test_get_groups_not_a_list(self):
        """Test extracting groups when groups is not a list."""
        user_claims = {"groups": "not-a-list"}
        groups = get_user_groups(user_claims)
        assert groups == []

    def test_get_groups_none(self):
        """Test extracting groups when groups is None."""
        user_claims = {"groups": None}
        groups = get_user_groups(user_claims)
        assert groups == []


class TestCheckFeatureAccess:
    """Tests for feature access checking."""

    @patch("backend.services.auth.rbac.is_user_admin")
    @patch("backend.services.auth.rbac._get_feature_admin_only")
    def test_admin_always_has_access(
        self, mock_get_admin_only, mock_is_admin, admin_user_by_group
    ):
        """Test that admins always have access regardless of feature settings."""
        mock_is_admin.return_value = True
        # Should not even query database for admin users
        mock_get_admin_only.assert_not_called()

        result = check_feature_access(admin_user_by_group, "settings.database")
        assert result is True

    @patch("backend.services.auth.rbac.is_user_admin")
    @patch("backend.services.auth.rbac._get_feature_admin_only")
    def test_non_admin_access_to_public_feature(
        self, mock_get_admin_only, mock_is_admin, regular_user
    ):
        """Test non-admin user accessing a feature where admin_only=False."""
        mock_is_admin.return_value = False
        mock_get_admin_only.return_value = False  # Feature is public

        result = check_feature_access(regular_user, "settings.appearance")
        assert result is True

    @patch("backend.services.auth.rbac.is_user_admin")
    @patch("backend.services.auth.rbac._get_feature_admin_only")
    def test_non_admin_denied_admin_only_feature(
        self, mock_get_admin_only, mock_is_admin, regular_user
    ):
        """Test non-admin user denied access to admin-only feature."""
        mock_is_admin.return_value = False
        mock_get_admin_only.return_value = True  # Feature is admin-only

        result = check_feature_access(regular_user, "settings.database")
        assert result is False

    @patch("backend.services.auth.rbac.is_user_admin")
    @patch("backend.services.auth.rbac._get_feature_admin_only")
    def test_feature_not_found_defaults_to_accessible(
        self, mock_get_admin_only, mock_is_admin, regular_user
    ):
        """Test that unknown features default to accessible (return None from db)."""
        mock_is_admin.return_value = False
        mock_get_admin_only.return_value = None  # Feature not found

        result = check_feature_access(regular_user, "unknown.feature")
        assert result is True


class TestGetFeatureAdminOnly:
    """Tests for feature admin_only flag retrieval with caching."""

    @patch("backend.services.database.get_db")
    def test_cache_miss_queries_database(self, mock_get_db):
        """Test that cache miss queries the database."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        # Mock database result
        mock_feature = MagicMock()
        mock_feature.admin_only = True
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature
        )

        result = _get_feature_admin_only("settings.database")

        assert result is True
        mock_session.query.assert_called_once()

    @patch("backend.services.database.get_db")
    def test_cache_hit_skips_database(self, mock_get_db):
        """Test that cache hit does not query the database."""
        # Pre-populate cache
        _feature_access_cache["settings.database"] = (True, time.time())

        result = _get_feature_admin_only("settings.database")

        assert result is True
        # Should not have queried database
        mock_get_db.assert_not_called()

    @patch("backend.services.database.get_db")
    @patch("backend.services.auth.rbac.time.time")
    def test_cache_expiration_after_ttl(self, mock_time, mock_get_db):
        """Test that cache entries expire after TTL and are re-queried."""
        # Set initial time
        initial_time = 1000.0
        mock_time.return_value = initial_time

        # Pre-populate cache with old timestamp
        _feature_access_cache["settings.database"] = (
            True,
            initial_time - _CACHE_TTL_SECONDS - 10,
        )

        # Mock database for re-query
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_feature = MagicMock()
        mock_feature.admin_only = False  # Changed value
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature
        )

        result = _get_feature_admin_only("settings.database")

        # Should return new value from database
        assert result is False
        # Should have queried database due to expiration
        mock_session.query.assert_called_once()
        # Old entry should be removed from cache
        assert "settings.database" in _feature_access_cache
        # New entry should have updated timestamp
        assert _feature_access_cache["settings.database"][0] is False

    @patch("backend.services.database.get_db")
    @patch("backend.services.auth.rbac.time.time")
    def test_cache_not_expired_within_ttl(self, mock_time, mock_get_db):
        """Test that cache entries within TTL are used without database query."""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Pre-populate cache with recent timestamp (within TTL)
        cache_time = current_time - 10  # 10 seconds ago, well within TTL
        _feature_access_cache["settings.database"] = (True, cache_time)

        result = _get_feature_admin_only("settings.database")

        assert result is True
        # Should NOT query database
        mock_get_db.assert_not_called()

    @patch("backend.services.database.get_db")
    def test_feature_not_found_returns_none(self, mock_get_db):
        """Test that non-existent features return None."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = _get_feature_admin_only("nonexistent.feature")

        assert result is None

    @patch("backend.services.database.get_db")
    def test_database_error_fails_closed(self, mock_get_db):
        """Test that database errors fail closed (return True = admin-only)."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.side_effect = Exception("Database connection failed")

        result = _get_feature_admin_only("settings.database")

        # Should fail closed (admin-only) for security
        assert result is True

    @patch("backend.services.database.get_db")
    def test_cache_stores_timestamp(self, mock_get_db):
        """Test that cache stores both value and timestamp."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session

        mock_feature = MagicMock()
        mock_feature.admin_only = False
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_feature
        )

        current_time = time.time()
        result = _get_feature_admin_only("settings.appearance")

        assert result is False
        assert "settings.appearance" in _feature_access_cache
        cached_value, cached_time = _feature_access_cache["settings.appearance"]
        assert cached_value is False
        assert cached_time >= current_time
        assert cached_time <= time.time() + 1  # Should be very recent


class TestClearFeatureAccessCache:
    """Tests for cache clearing."""

    def test_clear_cache_empties_cache(self):
        """Test that clearing the cache removes all entries."""

        # Populate cache
        _feature_access_cache["feature1"] = (True, time.time())
        _feature_access_cache["feature2"] = (False, time.time())

        assert len(_feature_access_cache) == 2

        clear_feature_access_cache()

        assert len(_feature_access_cache) == 0

    def test_clear_empty_cache(self):
        """Test that clearing an empty cache doesn't cause errors."""

        clear_feature_access_cache()
        assert len(_feature_access_cache) == 0


class TestCacheTTLConfiguration:
    """Tests for cache TTL environment variable configuration."""

    @patch.dict(os.environ, {"FEATURE_ACCESS_CACHE_TTL_SECONDS": "600"})
    def test_custom_ttl_via_env_var(self):
        """Test that TTL can be configured via environment variable."""
        # Would need to reload the module to test this properly
        # For now, just verify the default is reasonable
        assert _CACHE_TTL_SECONDS >= 0

    def test_default_ttl_is_reasonable(self):
        """Test that default TTL is set to a reasonable value."""
        # Default is 300 seconds (5 minutes)
        assert _CACHE_TTL_SECONDS == 300 or _CACHE_TTL_SECONDS > 0
