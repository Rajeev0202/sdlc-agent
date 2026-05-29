"""
Custom exceptions for card freeze functionality.
"""


class CardFreezeException(Exception):
    """Base exception for card freeze operations."""
    pass


class CardNotFoundException(CardFreezeException):
    """Raised when card is not found in database."""
    pass


class InvalidCardStateException(CardFreezeException):
    """Raised when card is not in a valid state for freezing."""
    pass


class UnauthorizedAccessException(CardFreezeException):
    """Raised when customer does not own the card."""
    pass


class DatabaseOperationException(CardFreezeException):
    """Raised when database operation fails."""
    pass


class FreezeTimeoutException(CardFreezeException):
    """Raised when freeze operation exceeds 2 second timeout."""
    pass
