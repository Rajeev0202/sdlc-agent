"""
Repository layer for card database operations.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from .models import Card, CardStatus
from .exceptions import CardNotFoundException, DatabaseOperationException

logger = logging.getLogger(__name__)


class CardRepository(ABC):
    """Abstract repository interface for card operations."""

    @abstractmethod
    def get_card_by_id(self, card_id: str) -> Optional[Card]:
        """
        Retrieve card by ID.

        Args:
            card_id: Unique card identifier

        Returns:
            Card object if found, None otherwise

        Raises:
            DatabaseOperationException: If database operation fails
        """
        pass

    @abstractmethod
    def update_card_status(
        self, card_id: str, new_status: CardStatus, updated_at: datetime
    ) -> Card:
        """
        Update card status in database.

        Args:
            card_id: Card identifier
            new_status: New status to set
            updated_at: Timestamp of update

        Returns:
            Updated Card object

        Raises:
            CardNotFoundException: If card not found
            DatabaseOperationException: If update fails
        """
        pass

    @abstractmethod
    def verify_customer_ownership(self, card_id: str, customer_id: str) -> bool:
        """
        Verify that customer owns the card.

        Args:
            card_id: Card identifier
            customer_id: Customer identifier

        Returns:
            True if customer owns card, False otherwise

        Raises:
            DatabaseOperationException: If verification fails
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin database transaction."""
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit database transaction."""
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback database transaction."""
        pass


class PostgresCardRepository(CardRepository):
    """PostgreSQL implementation of card repository."""

    def __init__(self, connection_pool):
        """
        Initialize repository with database connection pool.

        Args:
            connection_pool: Database connection pool (psycopg2/asyncpg)
        """
        self.pool = connection_pool
        self._connection = None
        self._transaction = None

    def get_card_by_id(self, card_id: str) -> Optional[Card]:
        """Retrieve card by ID from PostgreSQL."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT card_id, customer_id, card_number, status,
                               created_at, updated_at
                        FROM cards
                        WHERE card_id = %s
                    """
                    cursor.execute(query, (card_id,))
                    row = cursor.fetchone()

                    if not row:
                        logger.warning(f"Card not found: {card_id}")
                        return None

                    return Card(
                        card_id=row[0],
                        customer_id=row[1],
                        card_number=row[2],
                        status=CardStatus(row[3]),
                        created_at=row[4],
                        updated_at=row[5],
                    )

        except Exception as e:
            logger.error(f"Database error retrieving card {card_id}: {e}")
            raise DatabaseOperationException(
                f"Failed to retrieve card: {str(e)}"
            ) from e

    def update_card_status(
        self, card_id: str, new_status: CardStatus, updated_at: datetime
    ) -> Card:
        """Update card status in PostgreSQL."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE cards
                        SET status = %s, updated_at = %s
                        WHERE card_id = %s
                        RETURNING card_id, customer_id, card_number, status,
                                  created_at, updated_at
                    """
                    cursor.execute(
                        query, (new_status.value, updated_at, card_id)
                    )
                    row = cursor.fetchone()

                    if not row:
                        logger.error(f"Card not found for update: {card_id}")
                        raise CardNotFoundException(
                            f"Card {card_id} not found"
                        )

                    conn.commit()

                    updated_card = Card(
                        card_id=row[0],
                        customer_id=row[1],
                        card_number=row[2],
                        status=CardStatus(row[3]),
                        created_at=row[4],
                        updated_at=row[5],
                    )

                    logger.info(
                        f"Card {card_id} status updated to {new_status.value}"
                    )
                    return updated_card

        except CardNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error updating card {card_id}: {e}")
            raise DatabaseOperationException(
                f"Failed to update card status: {str(e)}"
            ) from e

    def verify_customer_ownership(
        self, card_id: str, customer_id: str
    ) -> bool:
        """Verify customer ownership in PostgreSQL."""
        try:
            with self.pool.getconn() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT COUNT(*)
                        FROM cards
                        WHERE card_id = %s AND customer_id = %s
                    """
                    cursor.execute(query, (card_id, customer_id))
                    count = cursor.fetchone()[0]

                    result = count > 0
                    logger.debug(
                        f"Ownership verification for card {card_id}, "
                        f"customer {customer_id}: {result}"
                    )
                    return result

        except Exception as e:
            logger.error(
                f"Database error verifying ownership for "
                f"card {card_id}: {e}"
            )
            raise DatabaseOperationException(
                f"Failed to verify ownership: {str(e)}"
            ) from e

    def begin_transaction(self) -> None:
        """Begin PostgreSQL transaction."""
        try:
            self._connection = self.pool.getconn()
            self._transaction = self._connection.cursor()
            logger.debug("Transaction started")
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise DatabaseOperationException(
                f"Transaction begin failed: {str(e)}"
            ) from e

    def commit_transaction(self) -> None:
        """Commit PostgreSQL transaction."""
        try:
            if self._connection:
                self._connection.commit()
                logger.debug("Transaction committed")
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            raise DatabaseOperationException(
                f"Transaction commit failed: {str(e)}"
            ) from e
        finally:
            self._cleanup_transaction()

    def rollback_transaction(self) -> None:
        """Rollback PostgreSQL transaction."""
        try:
            if self._connection:
                self._connection.rollback()
                logger.info("Transaction rolled back")
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise DatabaseOperationException(
                f"Transaction rollback failed: {str(e)}"
            ) from e
        finally:
            self._cleanup_transaction()

    def _cleanup_transaction(self) -> None:
        """Clean up transaction resources."""
        if self._transaction:
            self._transaction.close()
            self._transaction = None
        if self._connection:
            self.pool.putconn(self._connection)
            self._connection = None
