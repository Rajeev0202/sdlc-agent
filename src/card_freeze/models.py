"""
Data models for card freeze functionality.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator


class CardStatus(str, Enum):
    """Valid card status values."""
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class Card(BaseModel):
    """Card entity model."""
    card_id: str = Field(..., description="Unique card identifier")
    customer_id: str = Field(..., description="Customer identifier")
    card_number: str = Field(..., description="Masked card number")
    status: CardStatus = Field(..., description="Current card status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator("card_number")
    def validate_card_number(cls, v: str) -> str:
        """Ensure card number is masked."""
        if not v.startswith("****"):
            raise ValueError("Card number must be masked")
        return v


class FreezeCardRequest(BaseModel):
    """Request model for freezing a card."""
    card_id: str = Field(..., description="Card ID to freeze")
    customer_id: str = Field(..., description="Customer ID for authorization")


class FreezeCardResponse(BaseModel):
    """Response model for freeze operation."""
    card_id: str = Field(..., description="Card ID that was frozen")
    status: CardStatus = Field(..., description="Updated card status")
    message: str = Field(..., description="Operation result message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    """Error response model."""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
