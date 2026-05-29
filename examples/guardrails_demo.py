"""
Demo script showcasing the Code Quality Guardrails system.

This script demonstrates how guardrails validate generated code
and reject insecure or low-quality implementations.
"""
from sdlc_agent.guardrails import CodeQualityGuardrails, format_guardrail_report


def demo_guardrails():
    """Run demo showing various guardrail scenarios."""
    guardrails = CodeQualityGuardrails(strict_mode=True)

    print("=" * 70)
    print("🛡️  CODE QUALITY GUARDRAILS DEMO")
    print("=" * 70)
    print()

    # Test 1: Good code that passes all guardrails
    print("Test 1: Production-Ready Code")
    print("-" * 70)
    good_code = '''
import logging

logger = logging.getLogger(__name__)


class CardFreezeService:
    """Service for freezing and unfreezing payment cards."""

    def __init__(self, audit_service=None):
        self.audit_service = audit_service
        logger.info("CardFreezeService initialized")

    def freeze_card(self, user_id: str, card_id: str):
        """
        Freeze a payment card.

        Args:
            user_id: ID of authenticated user
            card_id: ID of card to freeze

        Returns:
            dict: Result with success status

        Raises:
            ValueError: If inputs are invalid
            PermissionError: If user doesn't own card
        """
        # Input validation
        if not user_id:
            raise ValueError("user_id is required")
        if not card_id:
            raise ValueError("card_id is required")

        try:
            # Authorization check
            if not self._user_owns_card(user_id, card_id):
                raise PermissionError(f"User {user_id} does not own card {card_id}")

            # Business logic
            logger.info("Freezing card %s for user %s", card_id, user_id)
            result = self._perform_freeze(card_id)

            # Audit logging
            if self.audit_service:
                self.audit_service.log_action(
                    user_id=user_id,
                    action="freeze_card",
                    card_id=card_id,
                    result="success"
                )

            return {"success": True, "message": "Card frozen successfully"}

        except Exception as e:
            logger.error("Failed to freeze card: %s", e, exc_info=True)
            if self.audit_service:
                self.audit_service.log_action(
                    user_id=user_id,
                    action="freeze_card",
                    card_id=card_id,
                    result="failure",
                    error=str(e)
                )
            raise RuntimeError("Failed to freeze card")

    def _user_owns_card(self, user_id: str, card_id: str) -> bool:
        """Check if user owns the card."""
        # Implementation would check database
        return True

    def _perform_freeze(self, card_id: str):
        """Perform the actual freeze operation."""
        # Implementation would update database
        return True
'''

    result = guardrails.validate(good_code, {"story_id": "US-001-freeze-card"})
    print(format_guardrail_report(result))
    print()

    # Test 2: Insecure code with security violations
    print("\nTest 2: Insecure Code (Security Violations)")
    print("-" * 70)
    insecure_code = '''
import subprocess

API_KEY = "sk_live_1234567890abcdef"  # Hard-coded credential!

def process_payment(amount, card_number):
    # Using eval is dangerous!
    result = eval(f"process_{amount}")

    # TLS verification disabled!
    response = requests.post("https://api.bank.com/pay", verify=False)

    # Shell injection risk!
    subprocess.call(f"process_payment.sh {amount}", shell=True)

    print(f"Processing payment for {amount}")  # Should use logging!

    return response
'''

    result = guardrails.validate(insecure_code)
    print(format_guardrail_report(result))
    print()

    # Test 3: Low-quality stub code
    print("\nTest 3: Stub Code (Quality Issues)")
    print("-" * 70)
    stub_code = '''
class PaymentProcessor:
    def process(self, **kwargs):
        # TODO: Implement payment processing
        return {"success": True}
'''

    result = guardrails.validate(stub_code, {"story_id": "US-002-payment"})
    print(format_guardrail_report(result))
    print()

    # Test 4: Code with missing error handling
    print("\nTest 4: Missing Error Handling")
    print("-" * 70)
    no_error_handling = '''
import logging

logger = logging.getLogger(__name__)

class TransferService:
    """Service for bank transfers."""

    def transfer(self, from_account, to_account, amount):
        """Transfer money between accounts."""
        # No input validation!
        # No error handling!
        # No authentication!

        balance = self.get_balance(from_account)
        self.deduct(from_account, amount)
        self.credit(to_account, amount)

        return {"success": True}
'''

    result = guardrails.validate(no_error_handling, {"story_id": "US-003-transfer"})
    print(format_guardrail_report(result))
    print()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo_guardrails()
