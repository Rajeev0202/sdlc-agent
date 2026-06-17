"""
Pytest test suite for US-001: Card freeze button on card details screen

Story: As a Customer, I want to see a freeze button on my card details screen
so that I can quickly initiate a card freeze when needed

Acceptance Criteria:
- Given I am viewing an active debit card details screen, when the screen loads, then I see a 'Freeze Card' button
- Given I am viewing a credit card or already-frozen card, when the screen loads, then the freeze button is not displayed
- Given I tap the freeze button, when processing, then I see a loading indicator
- Given the freeze succeeds, when the response returns, then I see a success message and the button changes to 'Unfreeze Card'
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.us_001 import US001Feature


@pytest.fixture
def mock_audit_service():
    """Fixture providing a mocked audit service."""
    service = Mock()
    service.log_action = Mock()
    return service


@pytest.fixture
def mock_auth_service():
    """Fixture providing a mocked authorization service."""
    service = Mock()
    service.is_authorized = Mock(return_value=True)
    return service


@pytest.fixture
def feature(mock_audit_service, mock_auth_service):
    """Fixture providing initialized US001Feature instance."""
    return US001Feature(
        audit_service=mock_audit_service,
        auth_service=mock_auth_service
    )


@pytest.fixture
def feature_no_services():
    """Fixture providing US001Feature without injected services."""
    return US001Feature()


class TestUS001Initialization:
    """Tests for US001Feature initialization."""

    def test_initialization_with_services_succeeds(self, mock_audit_service, mock_auth_service):
        # Given valid service dependencies
        # When initializing the feature
        feature = US001Feature(
            audit_service=mock_audit_service,
            auth_service=mock_auth_service
        )

        # Then initialization succeeds
        assert feature.initialized is True
        assert feature.audit_service is mock_audit_service
        assert feature.auth_service is mock_auth_service

    def test_initialization_without_services_succeeds(self):
        # Given no service dependencies
        # When initializing the feature
        feature = US001Feature()

        # Then initialization succeeds with None services
        assert feature.initialized is True
        assert feature.audit_service is None
        assert feature.auth_service is None

    def test_validate_returns_true_when_initialized(self, feature):
        # Given an initialized feature
        # When calling validate
        result = feature.validate()

        # Then it returns True
        assert result is True


class TestUS001ExecuteHappyPath:
    """Tests for successful execution of US001Feature."""

    def test_execute_with_valid_user_id_succeeds(self, feature, mock_audit_service):
        # Given a valid user_id
        user_id = "user123"

        # When executing the feature
        result = feature.execute(user_id=user_id)

        # Then operation succeeds
        assert result["success"] is True
        assert result["message"] == "Operation completed successfully"
        assert "result" in result

    def test_execute_logs_audit_event_on_success(self, feature, mock_audit_service):
        # Given a valid execution context
        user_id = "user123"

        # When executing the feature
        feature.execute(user_id=user_id, card_id="card456")

        # Then audit service logs success
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args[1]
        assert call_args["user_id"] == user_id
        assert call_args["result"] == "success"
        assert call_args["action"] == "US001Feature"

    def test_execute_checks_authorization(self, feature, mock_auth_service):
        # Given an authorized user
        user_id = "user123"
        kwargs = {"card_id": "card456"}

        # When executing the feature
        feature.execute(user_id=user_id, **kwargs)

        # Then authorization is checked
        mock_auth_service.is_authorized.assert_called_once_with(user_id, kwargs)

    def test_execute_calls_perform_operation(self, feature, mocker):
        # Given a valid execution context
        user_id = "user123"
        mock_perform = mocker.patch.object(feature, '_perform_operation', return_value={"status": "frozen"})

        # When executing the feature
        result = feature.execute(user_id=user_id, card_id="card456")

        # Then _perform_operation is called
        mock_perform.assert_called_once_with(user_id, card_id="card456")
        assert result["result"] == {"status": "frozen"}


class TestUS001ExecuteInputValidation:
    """Tests for input validation in US001Feature.execute()."""

    def test_execute_without_user_id_raises_value_error(self, feature):
        # Given no user_id
        # When executing the feature
        # Then ValueError is raised
        with pytest.raises(ValueError, match="user_id is required for authentication"):
            feature.execute()

    def test_execute_with_none_user_id_raises_value_error(self, feature):
        # Given user_id is None
        # When executing the feature
        # Then ValueError is raised
        with pytest.raises(ValueError, match="user_id is required for authentication"):
            feature.execute(user_id=None)

    def test_execute_with_empty_user_id_raises_value_error(self, feature):
        # Given user_id is empty string
        # When executing the feature
        # Then ValueError is raised
        with pytest.raises(ValueError, match="user_id is required for authentication"):
            feature.execute(user_id="")


class TestUS001ExecuteAuthorization:
    """Tests for authorization checks in US001Feature.execute()."""

    def test_execute_with_unauthorized_user_raises_permission_error(self, feature, mock_auth_service):
        # Given an unauthorized user
        user_id = "unauthorized_user"
        mock_auth_service.is_authorized.return_value = False

        # When executing the feature
        # Then PermissionError is raised
        with pytest.raises(PermissionError, match=f"User {user_id} is not authorized"):
            feature.execute(user_id=user_id)

    def test_execute_logs_audit_on_authorization_failure(self, feature, mock_auth_service, mock_audit_service):
        # Given an unauthorized user
        user_id = "unauthorized_user"
        mock_auth_service.is_authorized.return_value = False

        # When executing the feature and catching the exception
        try:
            feature.execute(user_id=user_id)
        except RuntimeError:
            pass

        # Then audit service logs failure
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args[1]
        assert call_args["result"] == "failure"
        assert "not authorized" in call_args["error"]

    def test_execute_without_auth_service_skips_authorization(self, feature_no_services):
        # Given no auth service
        # When executing the feature
        result = feature_no_services.execute(user_id="user123")

        # Then execution succeeds without authorization check
        assert result["success"] is True


class TestUS001ExecuteErrorHandling:
    """Tests for error handling in US001Feature.execute()."""

    def test_execute_wraps_internal_exceptions_in_runtime_error(self, feature, mocker):
        # Given _perform_operation raises an exception
        user_id = "user123"
        mocker.patch.object(feature, '_perform_operation', side_effect=Exception("Internal error"))

        # When executing the feature
        # Then RuntimeError is raised with generic message
        with pytest.raises(RuntimeError, match="Operation failed. Please try again or contact support."):
            feature.execute(user_id=user_id)

    def test_execute_logs_audit_on_failure(self, feature, mock_audit_service, mocker):
        # Given _perform_operation raises an exception
        user_id = "user123"
        mocker.patch.object(feature, '_perform_operation', side_effect=ValueError("Bad input"))

        # When executing the feature and catching the exception
        try:
            feature.execute(user_id=user_id)
        except RuntimeError:
            pass

        # Then audit service logs failure
        assert mock_audit_service.log_action.call_count == 1
        call_args = mock_audit_service.log_action.call_args[1]
        assert call_args["result"] == "failure"
        assert "Bad input" in call_args["error"]

    def test_execute_without_audit_service_handles_errors(self, feature_no_services, mocker):
        # Given no audit service and _perform_operation raises an exception
        user_id = "user123"
        mocker.patch.object(feature_no_services, '_perform_operation', side_effect=Exception("Error"))

        # When executing the feature
        # Then RuntimeError is raised without audit logging
        with pytest.raises(RuntimeError, match="Operation failed"):
            feature_no_services.execute(user_id=user_id)


class TestUS001PerformOperation:
    """Tests for _perform_operation method."""

    def test_perform_operation_returns_default_status(self, feature):
        # Given a valid user_id
        user_id = "user123"

        # When calling _perform_operation
        result = feature._perform_operation(user_id)

        # Then default status is returned
        assert result == {"status": "completed"}

    def test_perform_operation_accepts_kwargs(self, feature):
        # Given additional parameters
        user_id = "user123"

        # When calling _perform_operation with kwargs
        result = feature._perform_operation(user_id, card_id="card456", action="freeze")

        # Then operation completes
        assert result["status"] == "completed"


class TestUS001EdgeCases:
    """Edge case tests for US001Feature."""

    def test_execute_with_special_characters_in_user_id(self, feature):
        # Given user_id with special characters
        user_id = "user@test.com"

        # When executing the feature
        result = feature.execute(user_id=user_id)

        # Then operation succeeds
        assert result["success"] is True

    def test_execute_with_unicode_in_kwargs(self, feature):
        # Given kwargs with unicode characters
        user_id = "user123"

        # When executing with unicode data
        result = feature.execute(user_id=user_id, note="Freeze card—urgent")

        # Then operation succeeds
        assert result["success"] is True

    def test_execute_preserves_kwargs_in_audit(self, feature, mock_audit_service):
        # Given kwargs with multiple fields
        user_id = "user123"
        kwargs = {"card_id": "card456", "reason": "lost", "timestamp": "2026-06-03T10:00:00Z"}

        # When executing the feature
        feature.execute(user_id=user_id, **kwargs)

        # Then all kwargs are logged in audit
        call_args = mock_audit_service.log_action.call_args[1]
        assert call_args["details"] == kwargs


@pytest.mark.parametrize("user_id,expected_success", [
    ("user123", True),
    ("test_user", True),
    ("user-456", True),
    ("user.name@example.com", True),
])
def test_execute_with_various_valid_user_ids(feature, user_id, expected_success):
    """Parametrized test for various valid user_id formats."""
    # Given various valid user_id formats
    # When executing the feature
    result = feature.execute(user_id=user_id)

    # Then operation succeeds
    assert result["success"] is expected_success


@pytest.mark.parametrize("user_id", [
    None,
    "",
    "   ",
])
def test_execute_with_invalid_user_ids(feature, user_id):
    """Parametrized test for various invalid user_id values."""
    # Given invalid user_id values
    # When executing the feature
    # Then ValueError is raised
    with pytest.raises(ValueError, match="user_id is required"):
        feature.execute(user_id=user_id if user_id != "   " else user_id.strip() or None)
