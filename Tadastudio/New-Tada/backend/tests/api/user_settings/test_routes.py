"""Tests for user settings API routes."""

import pytest
from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException

from backend.api.user_settings.routes import (
    delete_external_service,
    get_external_service,
    get_external_service_for_node,
    get_user_identifier,
    list_external_services,
    save_external_service,
)
from backend.api.user_settings.models import SaveExternalServiceRequest
from backend.models.auth import UserExternalService
from backend.models.configuration.system_external_service import ExternalServiceAuthType


@pytest.fixture
def mock_current_user():
    """Mock current user from JWT."""
    return {"sub": "user-123", "email": "test@example.com"}


@pytest.fixture
def sample_service():
    """Sample UserExternalService."""
    return UserExternalService(
        id="service-123",
        user_id="user-123",
        service_name="tavily",
        encrypted_api_key="encrypted_key",
        settings={},
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        display_name="Tavily Web Search",
        service_url=None,
        auth_type=ExternalServiceAuthType.API_KEY_HEADER,
    )


class TestGetUserIdentifier:
    """Tests for get_user_identifier function."""

    def test_get_user_identifier_success(self):
        """Test extracting user identifier from valid claims."""
        current_user = {"sub": "user-123"}
        result = get_user_identifier(current_user)
        assert result == "user-123"

    def test_get_user_identifier_missing(self):
        """Test error when sub claim is missing."""
        current_user = {"email": "test@example.com"}
        with pytest.raises(HTTPException) as exc_info:
            get_user_identifier(current_user)
        assert exc_info.value.status_code == 401
        assert "missing user identifier" in exc_info.value.detail.lower()


class TestListExternalServices:
    """Tests for list_external_services endpoint."""

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.system_default_configured"
    )
    @patch(
        "backend.api.user_settings.routes.UserExternalServiceService.list_user_services"
    )
    @patch("backend.encryption_utils.decrypt_credential")
    async def test_list_external_services_success(
        self,
        mock_decrypt,
        mock_list_services,
        mock_system_default,
        mock_current_user,
        sample_service,
    ):
        """Test listing external services successfully."""
        mock_list_services.return_value = [sample_service]
        mock_decrypt.return_value = "tvly-test-key-12345"
        mock_system_default.return_value = False

        result = await list_external_services(current_user=mock_current_user)

        assert result.success is True
        assert len(result.services) == 1
        assert result.services[0].service_name == "tavily"
        assert result.services[0].api_key_masked == "****...2345"

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.UserExternalServiceService.list_user_services"
    )
    async def test_list_external_services_empty(
        self, mock_list_services, mock_current_user
    ):
        """Test listing when no services configured."""
        mock_list_services.return_value = []

        result = await list_external_services(current_user=mock_current_user)

        assert result.success is True
        assert len(result.services) == 0

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.system_default_configured"
    )
    @patch(
        "backend.api.user_settings.routes.UserExternalServiceService.list_user_services"
    )
    @patch("backend.encryption_utils.decrypt_credential")
    async def test_list_external_services_decryption_error(
        self,
        mock_decrypt,
        mock_list_services,
        mock_system_default,
        mock_current_user,
        sample_service,
    ):
        """Test handling decryption errors gracefully."""
        mock_list_services.return_value = [sample_service]
        mock_decrypt.side_effect = Exception("Decryption failed")
        mock_system_default.return_value = False

        result = await list_external_services(current_user=mock_current_user)

        assert result.success is True
        assert len(result.services) == 1
        assert result.services[0].api_key_masked is None


class TestGetExternalService:
    """Tests for get_external_service endpoint."""

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.system_default_configured"
    )
    @patch(
        "backend.api.user_settings.routes.UserExternalServiceService.get_decrypted_api_key"
    )
    @patch("backend.api.user_settings.routes.UserExternalServiceService.get_service")
    async def test_get_external_service_success(
        self,
        mock_get_service,
        mock_get_key,
        mock_system_default,
        mock_current_user,
        sample_service,
    ):
        """Test getting an existing external service."""
        mock_get_service.return_value = sample_service
        mock_get_key.return_value = "tvly-test-key-12345"
        mock_system_default.return_value = False

        result = await get_external_service(
            service_name="tavily", current_user=mock_current_user
        )

        assert result.service_name == "tavily"
        assert result.is_active is True
        assert result.api_key_masked == "****...2345"

    @pytest.mark.asyncio
    @patch("backend.api.user_settings.routes.UserExternalServiceService.get_service")
    async def test_get_external_service_not_found(
        self, mock_get_service, mock_current_user
    ):
        """Test getting non-existent service."""
        mock_get_service.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_external_service(
                service_name="tavily", current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "not configured" in exc_info.value.detail.lower()


class TestSaveExternalService:
    """Tests for save_external_service endpoint."""

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.system_default_configured"
    )
    @patch("backend.api.user_settings.routes.UserExternalServiceService.save_service")
    async def test_save_external_service_success(
        self, mock_save_service, mock_system_default, mock_current_user, sample_service
    ):
        """Test saving external service successfully."""
        mock_save_service.return_value = sample_service
        mock_system_default.return_value = False
        request = SaveExternalServiceRequest(
            api_key="tvly-test-key-12345", settings={"key": "value"}
        )

        result = await save_external_service(
            service_name="tavily", request=request, current_user=mock_current_user
        )

        assert result.success is True
        assert "configured successfully" in result.message.lower()
        assert result.service.service_name == "tavily"

    @pytest.mark.asyncio
    async def test_save_external_service_invalid_name(self, mock_current_user):
        """Test saving with invalid service name."""
        request = SaveExternalServiceRequest(api_key="test-key")

        with pytest.raises(HTTPException) as exc_info:
            await save_external_service(
                service_name="invalid_service",
                request=request,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "invalid service name" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("backend.api.user_settings.routes.UserExternalServiceService.save_service")
    async def test_save_external_service_error(
        self, mock_save_service, mock_current_user
    ):
        """Test handling save errors."""
        mock_save_service.side_effect = Exception("Database error")
        request = SaveExternalServiceRequest(api_key="tvly-test-key-12345")

        with pytest.raises(HTTPException) as exc_info:
            await save_external_service(
                service_name="tavily", request=request, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500


class TestDeleteExternalService:
    """Tests for delete_external_service endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.user_settings.routes.UserExternalServiceService.delete_service")
    async def test_delete_external_service_success(
        self, mock_delete_service, mock_current_user
    ):
        """Test deleting external service successfully."""
        mock_delete_service.return_value = True

        result = await delete_external_service(
            service_name="tavily", current_user=mock_current_user
        )

        assert result.success is True
        assert "deleted successfully" in result.message.lower()

    @pytest.mark.asyncio
    @patch("backend.api.user_settings.routes.UserExternalServiceService.delete_service")
    async def test_delete_external_service_not_found(
        self, mock_delete_service, mock_current_user
    ):
        """Test deleting non-existent service."""
        mock_delete_service.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_external_service(
                service_name="tavily", current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "not configured" in exc_info.value.detail.lower()


class TestGetExternalServiceForNode:
    """Tests for get_external_service_for_node endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.user_settings.routes.UserExternalServiceService.get_service")
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.resolve_api_key"
    )
    async def test_get_external_service_for_node_configured(
        self, mock_resolve_api_key, mock_get_service, mock_current_user, sample_service
    ):
        """Test getting service config for node when configured."""
        mock_resolve_api_key.return_value = "tvly-test-key-12345"
        mock_get_service.return_value = sample_service

        result = await get_external_service_for_node(
            service_name="tavily", current_user=mock_current_user
        )

        assert result.configured is True
        assert result.api_key == "tvly-test-key-12345"
        assert result.settings == {}

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.resolve_api_key"
    )
    async def test_get_external_service_for_node_not_configured(
        self, mock_resolve_api_key, mock_current_user
    ):
        """Test getting service config when not configured."""
        mock_resolve_api_key.return_value = None

        result = await get_external_service_for_node(
            service_name="tavily", current_user=mock_current_user
        )

        assert result.configured is False
        assert result.api_key is None
        assert result.settings == {}

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.resolve_api_key"
    )
    async def test_get_external_service_for_node_inactive(
        self, mock_resolve_api_key, mock_current_user
    ):
        """Test getting service config when inactive (no key resolved)."""
        mock_resolve_api_key.return_value = None

        result = await get_external_service_for_node(
            service_name="tavily", current_user=mock_current_user
        )

        assert result.configured is False
        assert result.api_key is None

    @pytest.mark.asyncio
    @patch(
        "backend.api.user_settings.routes.CredentialResolutionService.resolve_api_key"
    )
    async def test_get_external_service_for_node_decryption_error(
        self, mock_resolve_api_key, mock_current_user
    ):
        """Test handling resolution errors."""
        mock_resolve_api_key.side_effect = Exception("Decryption failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_external_service_for_node(
                service_name="tavily", current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
