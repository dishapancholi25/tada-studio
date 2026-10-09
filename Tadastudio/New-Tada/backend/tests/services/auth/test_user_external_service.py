"""Tests for UserExternalServiceService."""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.auth import UserExternalService
from backend.services.auth.user_external_service import UserExternalServiceService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "user-123"


@pytest.fixture
def sample_service_name():
    """Sample service name."""
    return "tavily"


@pytest.fixture
def sample_api_key():
    """Sample API key."""
    return "tvly-test-key-12345"


@pytest.fixture
def sample_encrypted_key():
    """Sample encrypted key."""
    return "encrypted_key_base64"


@pytest.fixture
def sample_service(sample_user_id, sample_service_name, sample_encrypted_key):
    """Sample UserExternalService object."""
    service = UserExternalService(
        id="service-123",
        user_id=sample_user_id,
        service_name=sample_service_name,
        encrypted_api_key=sample_encrypted_key,
        settings={},
        is_active=True,
    )
    return service


class TestGetService:
    """Tests for get_service method."""

    @patch("backend.services.auth.user_external_service.get_db")
    def test_get_service_found(
        self, mock_get_db, mock_db, sample_service, sample_user_id, sample_service_name
    ):
        """Test getting an existing service."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_service
        )

        result = UserExternalServiceService.get_service(
            sample_user_id, sample_service_name
        )

        assert result == sample_service
        mock_db.expunge.assert_called_once_with(sample_service)

    @patch("backend.services.auth.user_external_service.get_db")
    def test_get_service_not_found(
        self, mock_get_db, mock_db, sample_user_id, sample_service_name
    ):
        """Test getting a non-existent service."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = UserExternalServiceService.get_service(
            sample_user_id, sample_service_name
        )

        assert result is None


class TestGetDecryptedApiKey:
    """Tests for get_decrypted_api_key method."""

    @patch("backend.services.auth.user_external_service.decrypt_credential")
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_get_decrypted_api_key_success(
        self,
        mock_get_service,
        mock_decrypt,
        sample_service,
        sample_user_id,
        sample_service_name,
        sample_api_key,
    ):
        """Test successful API key decryption."""
        mock_get_service.return_value = sample_service
        mock_decrypt.return_value = sample_api_key

        result = UserExternalServiceService.get_decrypted_api_key(
            sample_user_id, sample_service_name
        )

        assert result == sample_api_key
        mock_decrypt.assert_called_once_with(sample_service.encrypted_api_key)

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_get_decrypted_api_key_service_not_found(
        self, mock_get_service, sample_user_id, sample_service_name
    ):
        """Test decryption when service not found."""
        mock_get_service.return_value = None

        result = UserExternalServiceService.get_decrypted_api_key(
            sample_user_id, sample_service_name
        )

        assert result is None

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_get_decrypted_api_key_service_inactive(
        self, mock_get_service, sample_service, sample_user_id, sample_service_name
    ):
        """Test decryption when service is inactive."""
        sample_service.is_active = False
        mock_get_service.return_value = sample_service

        result = UserExternalServiceService.get_decrypted_api_key(
            sample_user_id, sample_service_name
        )

        assert result is None

    @patch("backend.services.auth.user_external_service.decrypt_credential")
    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_service"
    )
    def test_get_decrypted_api_key_decryption_error(
        self,
        mock_get_service,
        mock_decrypt,
        sample_service,
        sample_user_id,
        sample_service_name,
    ):
        """Test decryption failure handling."""
        mock_get_service.return_value = sample_service
        mock_decrypt.side_effect = Exception("Decryption failed")

        result = UserExternalServiceService.get_decrypted_api_key(
            sample_user_id, sample_service_name
        )

        assert result is None


class TestGetTavilyApiKey:
    """Tests for get_tavily_api_key convenience method."""

    @patch(
        "backend.services.auth.user_external_service.UserExternalServiceService.get_decrypted_api_key"
    )
    def test_get_tavily_api_key(
        self, mock_get_decrypted, sample_user_id, sample_api_key
    ):
        """Test Tavily API key retrieval."""
        mock_get_decrypted.return_value = sample_api_key

        result = UserExternalServiceService.get_tavily_api_key(sample_user_id)

        assert result == sample_api_key
        mock_get_decrypted.assert_called_once_with(
            sample_user_id, UserExternalServiceService.SERVICE_TAVILY
        )


class TestListUserServices:
    """Tests for list_user_services method."""

    @patch("backend.services.auth.user_external_service.get_db")
    def test_list_user_services(self, mock_get_db, mock_db, sample_user_id):
        """Test listing user services."""
        service1 = MagicMock()
        service2 = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            service1,
            service2,
        ]

        result = UserExternalServiceService.list_user_services(sample_user_id)

        assert len(result) == 2
        assert service1 in result
        assert service2 in result
        assert mock_db.expunge.call_count == 2


class TestSaveService:
    """Tests for save_service method."""

    @patch("backend.services.auth.user_external_service.encrypt_credential")
    @patch("backend.services.auth.user_external_service.get_db")
    def test_save_service_upsert(
        self,
        mock_get_db,
        mock_encrypt,
        mock_db,
        sample_user_id,
        sample_service_name,
        sample_api_key,
        sample_service,
    ):
        """Test save_service with ON CONFLICT upsert."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_encrypt.return_value = "encrypted_key"
        mock_db.execute.return_value = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_service
        )

        result = UserExternalServiceService.save_service(
            user_id=sample_user_id,
            service_name=sample_service_name,
            api_key=sample_api_key,
            settings={"key": "value"},
        )

        assert result == sample_service
        mock_encrypt.assert_called_once_with(sample_api_key)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.expunge.assert_called_once_with(sample_service)

    @patch("backend.services.auth.user_external_service.encrypt_credential")
    @patch("backend.services.auth.user_external_service.get_db")
    def test_save_service_failure(
        self,
        mock_get_db,
        mock_encrypt,
        mock_db,
        sample_user_id,
        sample_service_name,
        sample_api_key,
    ):
        """Test save_service when retrieval fails after save."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_encrypt.return_value = "encrypted_key"
        mock_db.execute.return_value = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(RuntimeError, match="Failed to save/retrieve service"):
            UserExternalServiceService.save_service(
                user_id=sample_user_id,
                service_name=sample_service_name,
                api_key=sample_api_key,
            )


class TestDeleteService:
    """Tests for delete_service method."""

    @patch("backend.services.auth.user_external_service.get_db")
    def test_delete_service_success(
        self, mock_get_db, mock_db, sample_service, sample_user_id, sample_service_name
    ):
        """Test successful service deletion."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_service
        )

        result = UserExternalServiceService.delete_service(
            sample_user_id, sample_service_name
        )

        assert result is True
        mock_db.delete.assert_called_once_with(sample_service)
        mock_db.commit.assert_called_once()

    @patch("backend.services.auth.user_external_service.get_db")
    def test_delete_service_not_found(
        self, mock_get_db, mock_db, sample_user_id, sample_service_name
    ):
        """Test deleting non-existent service."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = UserExternalServiceService.delete_service(
            sample_user_id, sample_service_name
        )

        assert result is False
        mock_db.delete.assert_not_called()


class TestDeactivateService:
    """Tests for deactivate_service method."""

    @patch("backend.services.auth.user_external_service.get_db")
    def test_deactivate_service_success(
        self, mock_get_db, mock_db, sample_service, sample_user_id, sample_service_name
    ):
        """Test successful service deactivation."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_service
        )

        result = UserExternalServiceService.deactivate_service(
            sample_user_id, sample_service_name
        )

        assert result is True
        assert sample_service.is_active is False
        mock_db.commit.assert_called_once()

    @patch("backend.services.auth.user_external_service.get_db")
    def test_deactivate_service_not_found(
        self, mock_get_db, mock_db, sample_user_id, sample_service_name
    ):
        """Test deactivating non-existent service."""
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = UserExternalServiceService.deactivate_service(
            sample_user_id, sample_service_name
        )

        assert result is False


class TestMaskApiKey:
    """Tests for mask_api_key method."""

    def test_mask_api_key_normal(self):
        """Test masking a normal API key."""
        result = UserExternalServiceService.mask_api_key("tvly-1234567890abcdef")
        assert result == "****...cdef"

    def test_mask_api_key_short(self):
        """Test masking a short API key."""
        result = UserExternalServiceService.mask_api_key("abc")
        assert result == "****"

    def test_mask_api_key_empty(self):
        """Test masking an empty API key."""
        result = UserExternalServiceService.mask_api_key("")
        assert result == "****"

    def test_mask_api_key_none(self):
        """Test masking None API key."""
        result = UserExternalServiceService.mask_api_key(None)
        assert result == "****"
