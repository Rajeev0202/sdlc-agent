"""
Tests for US-004: display my contact information and social media links

This file follows TDD approach - tests written first.
"""
import pytest
from src.us_004 import US004Feature


class TestUS004Feature:
    """Test suite for US004Feature."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = US004Feature()

    def test_initialization(self):
        """Test that US004Feature initializes correctly."""
        assert self.instance.initialized is True

    def test_execute_returns_success(self):
        """Test execute method returns success."""
        result = self.instance.execute()
        assert result["success"] is True

    def test_validation_passes(self):
        """Test validation passes for valid implementation."""
        assert self.instance.validate() is True

    def test_ac1_given_a_visitor_scrolls(self):
        """
        AC1: Given a visitor scrolls to contact, when the section loads, then email address is displayed
        """
        # TODO: Implement test for acceptance criterion 1
        result = self.instance.execute()
        assert result["success"] is True

    def test_ac2_given_the_contact_section(self):
        """
        AC2: Given the contact section is rendered, when viewed, then social media links are present
        """
        # TODO: Implement test for acceptance criterion 2
        result = self.instance.execute()
        assert result["success"] is True

    def test_ac3_given_contact_information_is(self):
        """
        AC3: Given contact information is displayed, when clicked, then email link opens default mail client
        """
        # TODO: Implement test for acceptance criterion 3
        result = self.instance.execute()
        assert result["success"] is True

