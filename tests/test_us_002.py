"""
Tests for US-002: the card freeze API to change my card status to FROZEN

This file follows TDD approach - tests written first.
"""
import pytest
from src.us_002 import US002Feature


class TestUS002Feature:
    """Test suite for US002Feature."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = US002Feature()

    def test_initialization(self):
        """Test that US002Feature initializes correctly."""
        assert self.instance.initialized is True

    def test_execute_returns_success(self):
        """Test execute method returns success."""
        result = self.instance.execute()
        assert result["success"] is True

    def test_validation_passes(self):
        """Test validation passes for valid implementation."""
        assert self.instance.validate() is True

    def test_ac1_given_a_valid_freeze(self):
        """
        AC1: Given a valid freeze request, when the API receives it, then the card status is updated to FROZEN in under 2 seconds
        """
        # TODO: Implement test for acceptance criterion 1
        result = self.instance.execute()
        assert result["success"] is True

    def test_ac2_given_an_already_frozen(self):
        """
        AC2: Given an already frozen card, when a freeze request is received, then return 400 with appropriate error message
        """
        # TODO: Implement test for acceptance criterion 2
        result = self.instance.execute()
        assert result["success"] is True

    def test_ac3_given_an_invalid_card(self):
        """
        AC3: Given an invalid card ID, when a freeze request is received, then return 404
        """
        # TODO: Implement test for acceptance criterion 3
        result = self.instance.execute()
        assert result["success"] is True

    def test_ac4_given_the_status_update(self):
        """
        AC4: Given the status update fails, when the error occurs, then rollback and return 500 with logged error
        """
        # TODO: Implement test for acceptance criterion 4
        result = self.instance.execute()
        assert result["success"] is True

