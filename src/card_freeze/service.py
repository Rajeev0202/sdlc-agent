"""
Service layer for card freeze business logic.
"""
import logging
from datetime import datetime, timezone
from typing import Tuple

from .models import Card, CardStatus, FreezeCardRequest, FreezeCardResponse
from .repository import CardRepository
from .exceptions import (
    CardNotFoundException,
    InvalidCardStateException,
    UnauthorizedAccessException,
    DatabaseOperationException,
    FreezeTimeoutException,
)

logger = logging.getLogger(__name__)

FREEZE_TIMEOUT_SECONDS = 2


class CardFreezeService:
    """Service for freezing debit cards."""

    def __init__(self, repository: CardRepository):
        """
        Initialize service with repository dependency.

        Args:
            repository: CardRepository implementation for data access
        """
        self.repository = repository

    def freeze_card(self, request: FreezeCardRequest) -> FreezeCardResponse:
        """
        Freeze a debit card.

        Args:
            request: Freeze request containing card_id and customer_id

        Returns:
            FreezeCardResponse with updated status

        Raises:
            CardNotFoundException: If card does not exist
            UnauthorizedAccessException: If customer does not own card
            InvalidCardStateException: If card is not in ACTIVE state
            DatabaseOperationException: If database operation fails
            FreezeTimeoutException: If operation exceeds 2 seconds
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            f"Starting freeze operation for card {request.card_id}, "
            f"customer {request.customer_id}"
        )

        try:
            # Step 1: Verify customer owns the card
            self._verify_ownership(request.card_id, request.customer_id)

            # Step 2: Retrieve card and validate state
            card = self._get_and_validate_card(request.card_id)

            # Step 3: Update card status to FROZEN
            updated_card = self._update_card_to_frozen(card)

            # Step 4: Verify operation completed within timeout
            elapsed = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()
            if elapsed > FREEZE_TIMEOUT_SECONDS:
                logger.error(
                    f"Freeze operation exceeded timeout: {elapsed}s"
                )
                raise FreezeTimeoutException(
                    f"Freeze operation took {elapsed}s, "
                    f"exceeded {FREEZE_TIMEOUT_SECONDS}s timeout"
                )

            logger.info(
                f"Card {request.card_id} successfully frozen in {elapsed:.3f}s"
            )

            return FreezeCardResponse(
                card_id=updated_card.card_id,
                status=updated_card.status,
                message=f"Card {updated_card.card_id} has been frozen successfully",
            )

        except (
            CardNotFoundException,
            UnauthorizedAccessException,
            InvalidCardStateException,
            FreezeTimeoutException,
        ):
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error freezing card {request.card_id}: {e}"
            )
            # Attempt rollback if transaction is active
            try:
                self.repository.rollback_transaction()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            raise DatabaseOperationException(
                f"Failed to freeze card: {str(e)}"
            ) from e

    def _verify_ownership(self, card_id: str, customer_id: str) -> None:
        """
        Verify customer owns the card.

        Args:
            card_id: Card identifier
            customer_id: Customer identifier

        Raises:
            UnauthorizedAccessException: If customer does not own card
        """
        is_owner = self.repository.verify_customer_ownership(
            card_id, customer_id
        )
        if not is_owner:
            logger.warning(
                f"Unauthorized freeze attempt: customer {customer_id} "
                f"does not own card {card_id}"
            )
            raise UnauthorizedAccessException(
                f"Customer {customer_id} is not authorized to freeze "
                f"card {card_id}"
            )

    def _get_and_validate_card(self, card_id: str) -> Card:
        """
        Retrieve card and validate it can be frozen.

        Args:
            card_id: Card identifier

        Returns:
            Card object if valid

        Raises:
            CardNotFoundException: If card not found
            InvalidCardStateException: If card cannot be frozen
        """
        card = self.repository.get_card_by_id(card_id)

        if not card:
            logger.error(f"Card not found: {card_id}")
            raise CardNotFoundException(f"Card {card_id} not found")

        if card.status != CardStatus.ACTIVE:
            logger.warning(
                f"Cannot freeze card {card_id} with status {card.status.value}"
            )
            raise InvalidCardStateException(
                f"Cannot freeze card with status {card.status.value}. "
                f"Only ACTIVE cards can be frozen."
            )

        return card

    def _update_card_to_frozen(self, card: Card) -> Card:
        """
        Update card status to FROZEN in database.

        Args:
            card: Card to freeze

        Returns:
            Updated Card object

        Raises:
            DatabaseOperationException: If update fails
        """
        updated_at = datetime.now(timezone.utc)

        try:
            updated_card = self.repository.update_card_status(
                card.card_id, CardStatus.FROZEN, updated_at
            )
            return updated_card
        except Exception as e:
            logger.error(
                f"Failed to update card {card.card_id} status: {e}"
            )
            raise DatabaseOperationException(
                f"Failed to update card status: {str(e)}"
            ) from e

    def validate_card_freeze_eligibility(
        self, card_id: str, customer_id: str
    ) -> Tuple[bool, str]:
        """
        Validate if card can be frozen without performing freeze.

        Args:
            card_id: Card identifier
            customer_id: Customer identifier

        Returns:
            Tuple of (is_eligible, reason_message)
        """
        try:
            # Check ownership
            is_owner = self.repository.verify_customer_ownership(
                card_id, customer_id
            )
            if not is_owner:
                return False, "Customer is not authorized for this card"

            # Check card state
            card = self.repository.get_card_by_id(card_id)
            if not card:
                return False, "Card not found"

            if card.status != CardStatus.ACTIVE:
                return (
                    False,
                    f"Card status is {card.status.value}, "
                    f"only ACTIVE cards can be frozen",
                )

            return True, "Card is eligible for freezing"

        except Exception as e:
            logger.error(
                f"Error validating freeze eligibility for {card_id}: {e}"
            )
            return False, f"Validation error: {str(e)}"
