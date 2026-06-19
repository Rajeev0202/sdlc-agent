import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from us_001 import US001Feature


@pytest.fixture
def mock_card_service():
    service = Mock()
    service.get_card_status.return_value = "active"
    service.freeze_card.return_value = True
    service.is_card_frozen.return_value = False
    return service


@pytest.fixture
def mock_audit_logger():
    logger = Mock()
    logger.log_freeze_event.return_value = None
    return logger


@pytest.fixture
def us001_feature(mock_card_service, mock_audit_logger):
    return US001Feature(card_service=mock_card_service, audit_logger=mock_audit_logger)


@pytest.fixture
def valid_card_id():
    return "4532-1234-5678-9010"


class TestUS001AcceptanceCriteria:
    def test_freeze_active_debit_card_from_card_details_screen(
        self, us001_feature, mock_card_service, mock_audit_logger, valid_card_id
    ):
        # Given: An active debit card is displayed on the card details screen
        mock_card_service.get_card_status.return_value = "active"
        mock_card_service.is_card_frozen.return_value = False

        # When: Customer initiates card freeze
        result = us001_feature.freeze_card(valid_card_id)

        # Then: System should freeze the card
        assert result is True
        mock_card_service.freeze_card.assert_called_once_with(valid_card_id)
        mock_audit_logger.log_freeze_event.assert_called_once()


class TestUS001HappyPath:
    def test_freeze_card_returns_success_status(self, us001_feature, valid_card_id):
        # Given: A valid active card
        # When: Freeze operation is triggered
        result = us001_feature.freeze_card(valid_card_id)

        # Then: Operation returns success
        assert result is True

    def test_freeze_card_updates_card_status_to_frozen(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: An active card
        # When: Card is frozen
        us001_feature.freeze_card(valid_card_id)

        # Then: Card service freeze method is invoked
        mock_card_service.freeze_card.assert_called_once_with(valid_card_id)

    def test_freeze_card_logs_audit_event(
        self, us001_feature, mock_audit_logger, valid_card_id
    ):
        # Given: An active card
        # When: Card is frozen
        us001_feature.freeze_card(valid_card_id)

        # Then: Audit event is logged
        mock_audit_logger.log_freeze_event.assert_called_once()
        call_args = mock_audit_logger.log_freeze_event.call_args
        assert valid_card_id in str(call_args)


class TestUS001EdgeCases:
    def test_freeze_already_frozen_card_raises_exception(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: A card that is already frozen
        mock_card_service.is_card_frozen.return_value = True

        # When/Then: Attempting to freeze raises appropriate exception
        with pytest.raises(ValueError, match="already frozen"):
            us001_feature.freeze_card(valid_card_id)

    def test_freeze_inactive_card_raises_exception(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: An inactive card
        mock_card_service.get_card_status.return_value = "inactive"

        # When/Then: Attempting to freeze raises appropriate exception
        with pytest.raises(ValueError, match="not active"):
            us001_feature.freeze_card(valid_card_id)

    def test_freeze_nonexistent_card_raises_exception(
        self, us001_feature, mock_card_service
    ):
        # Given: A card ID that doesn't exist
        invalid_card_id = "0000-0000-0000-0000"
        mock_card_service.get_card_status.side_effect = KeyError("Card not found")

        # When/Then: Attempting to freeze raises appropriate exception
        with pytest.raises(KeyError, match="Card not found"):
            us001_feature.freeze_card(invalid_card_id)

    @pytest.mark.parametrize("card_status", ["cancelled", "expired", "blocked"])
    def test_freeze_card_with_invalid_statuses(
        self, us001_feature, mock_card_service, valid_card_id, card_status
    ):
        # Given: A card with various invalid statuses
        mock_card_service.get_card_status.return_value = card_status

        # When/Then: Attempting to freeze raises exception
        with pytest.raises(ValueError):
            us001_feature.freeze_card(valid_card_id)

    @pytest.mark.parametrize("invalid_card_id", [
        "",
        None,
        "123",
        "invalid-format",
        " ",
        "1234567890123456789"
    ])
    def test_freeze_card_with_invalid_card_id_format(
        self, us001_feature, invalid_card_id
    ):
        # Given: Invalid card ID formats
        # When/Then: Attempting to freeze raises validation exception
        with pytest.raises((ValueError, TypeError)):
            us001_feature.freeze_card(invalid_card_id)


class TestUS001ErrorHandling:
    def test_freeze_card_handles_service_timeout(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: Card service times out
        mock_card_service.freeze_card.side_effect = TimeoutError("Service timeout")

        # When/Then: Operation raises timeout exception
        with pytest.raises(TimeoutError, match="Service timeout"):
            us001_feature.freeze_card(valid_card_id)

    def test_freeze_card_handles_network_failure(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: Network connection fails
        mock_card_service.freeze_card.side_effect = ConnectionError("Network unavailable")

        # When/Then: Operation raises connection exception
        with pytest.raises(ConnectionError, match="Network unavailable"):
            us001_feature.freeze_card(valid_card_id)

    def test_freeze_card_handles_database_failure(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: Database operation fails
        mock_card_service.freeze_card.side_effect = RuntimeError("Database error")

        # When/Then: Operation raises runtime exception
        with pytest.raises(RuntimeError, match="Database error"):
            us001_feature.freeze_card(valid_card_id)

    def test_freeze_card_audit_failure_does_not_block_freeze(
        self, us001_feature, mock_card_service, mock_audit_logger, valid_card_id
    ):
        # Given: Audit logger fails
        mock_audit_logger.log_freeze_event.side_effect = Exception("Audit system down")

        # When: Card freeze is attempted
        # Then: Freeze still succeeds despite audit failure
        result = us001_feature.freeze_card(valid_card_id)
        assert result is True
        mock_card_service.freeze_card.assert_called_once_with(valid_card_id)


class TestUS001SecurityAndAuthorization:
    def test_freeze_card_requires_valid_session(self, us001_feature, valid_card_id):
        # Given: No valid session token
        us001_feature_no_auth = US001Feature(
            card_service=Mock(),
            audit_logger=Mock(),
            session_token=None
        )

        # When/Then: Operation raises authorization exception
        with pytest.raises(ValueError, match="session"):
            us001_feature_no_auth.freeze_card(valid_card_id)

    def test_freeze_card_verifies_ownership(
        self, us001_feature, mock_card_service, valid_card_id
    ):
        # Given: User tries to freeze a card they don't own
        mock_card_service.verify_card_ownership.return_value = False

        # When/Then: Operation raises authorization exception
        with pytest.raises(PermissionError, match="not authorized"):
            us001_feature.freeze_card(valid_card_id)


class TestUS001Integration:
    def test_freeze_card_complete_workflow(
        self, mock_card_service, mock_audit_logger, valid_card_id
    ):
        # Given: A complete setup with all dependencies
        mock_card_service.get_card_status.return_value = "active"
        mock_card_service.is_card_frozen.return_value = False
        mock_card_service.verify_card_ownership.return_value = True
        mock_card_service.freeze_card.return_value = True

        feature = US001Feature(
            card_service=mock_card_service,
            audit_logger=mock_audit_logger,
            session_token="valid-session-token"
        )

        # When: Complete freeze workflow is executed
        result = feature.freeze_card(valid_card_id)

        # Then: All steps execute in correct order
        assert result is True
        assert mock_card_service.verify_card_ownership.called
        assert mock_card_service.get_card_status.called
        assert mock_card_service.is_card_frozen.called
        assert mock_card_service.freeze_card.called
        assert mock_audit_logger.log_freeze_event.called
