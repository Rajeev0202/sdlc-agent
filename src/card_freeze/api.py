"""
API endpoint for card freeze functionality.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from .models import FreezeCardRequest, FreezeCardResponse, ErrorResponse
from .service import CardFreezeService
from .exceptions import (
    CardNotFoundException,
    InvalidCardStateException,
    UnauthorizedAccessException,
    DatabaseOperationException,
    FreezeTimeoutException,
)

logger = logging.getLogger(__name__)


class CardFreezeAPI:
    """API controller for card freeze operations."""

    def __init__(self, service: CardFreezeService):
        """
        Initialize API with service dependency.

        Args:
            service: CardFreezeService implementation
        """
        self.service = service

    def freeze_card(self, request_data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
        """
        Handle POST /api/v1/cards/freeze request.

        Args:
            request_data: Dictionary containing card_id and customer_id

        Returns:
            Tuple of (response_body, status_code)
        """
        logger.info(
            f"Received freeze request for card_id: "
            f"{request_data.get('card_id')}"
        )

        try:
            # Validate and parse request
            request = FreezeCardRequest(**request_data)

            # Execute freeze operation
            response = self.service.freeze_card(request)

            # Return success response (200)
            return response.model_dump(), 200

        except ValueError as e:
            # Request validation failed (400)
            logger.warning(f"Invalid request data: {e}")
            error = ErrorResponse(
                error_code="INVALID_REQUEST",
                message=f"Invalid request: {str(e)}",
            )
            return error.model_dump(), 400

        except CardNotFoundException as e:
            # Card not found (404)
            logger.warning(f"Card not found: {e}")
            error = ErrorResponse(
                error_code="CARD_NOT_FOUND", message=str(e)
            )
            return error.model_dump(), 404

        except UnauthorizedAccessException as e:
            # Customer not authorized (403)
            logger.warning(f"Unauthorized access: {e}")
            error = ErrorResponse(
                error_code="UNAUTHORIZED", message=str(e)
            )
            return error.model_dump(), 403

        except InvalidCardStateException as e:
            # Card in invalid state (400)
            logger.warning(f"Invalid card state: {e}")
            error = ErrorResponse(
                error_code="INVALID_CARD_STATE", message=str(e)
            )
            return error.model_dump(), 400

        except FreezeTimeoutException as e:
            # Operation timeout (504)
            logger.error(f"Freeze timeout: {e}")
            error = ErrorResponse(
                error_code="OPERATION_TIMEOUT", message=str(e)
            )
            return error.model_dump(), 504

        except DatabaseOperationException as e:
            # Database error (500)
            logger.error(f"Database operation failed: {e}")
            error = ErrorResponse(
                error_code="DATABASE_ERROR",
                message="An internal error occurred. Please try again later.",
            )
            return error.model_dump(), 500

        except Exception as e:
            # Unexpected error (500)
            logger.error(f"Unexpected error in freeze_card endpoint: {e}", exc_info=True)
            error = ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please contact support.",
            )
            return error.model_dump(), 500

    def health_check(self) -> tuple[Dict[str, Any], int]:
        """
        Handle GET /api/v1/health request.

        Returns:
            Tuple of (response_body, status_code)
        """
        return {
            "status": "healthy",
            "service": "card-freeze-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, 200


def create_app(service: CardFreezeService):
    """
    Factory function to create API application.

    Args:
        service: CardFreezeService instance

    Returns:
        Configured CardFreezeAPI instance
    """
    logger.info("Creating Card Freeze API application")
    api = CardFreezeAPI(service)
    return api
