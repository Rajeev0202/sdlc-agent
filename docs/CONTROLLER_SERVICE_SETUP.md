# Controller-Service Architecture Setup Guide

## Overview

The SDLC Agent now supports **Controller-Service architecture** - a clean separation of HTTP handling (controllers) and business logic (services).

---

## Quick Setup

### Enable Controller-Service Layout

**Option 1**: Edit configuration file

```python
# sdlc_agent/core/code_layout.py (line 62)
LAYOUT_CONFIG = CodeLayoutConfig(
    style=LayoutStyle.CONTROLLER_SERVICE,  # ← Change this
    src_dir="src",
    test_dir="tests",
    default_layer="both",  # Generate both controller and service
)
```

**Option 2**: Use preset function

```python
from sdlc_agent.core.code_layout import configure_controller_service_layout

# In your initialization code
configure_controller_service_layout(generate_both=True)
```

**Option 3**: Environment variable

```bash
export CODE_LAYOUT_STYLE=controller_service
```

---

## Generated Structure

For a story: **"As a Customer, I want to freeze my card"**

```
src/
├── controllers/
│   └── card_controller.py       ← HTTP request handling
├── services/
│   └── card_service.py          ← Business logic
└── models/                      ← (optional, future)
    └── card_model.py

tests/
├── controllers/
│   └── card_controller_test.py
└── services/
    └── card_service_test.py
```

---

## Controller Layer

**Responsibilities**:
- HTTP request validation
- Extract user authentication
- Delegate to service layer
- Return HTTP responses

**Example** (`src/controllers/card_controller.py`):

```python
from flask import Blueprint, request, jsonify
from ..services.card_service import CardService

card_bp = Blueprint("card", __name__, url_prefix="/api/cards")


class CardController:
    def __init__(self):
        self.service = CardService()

    @card_bp.route("/freeze", methods=["POST"])
    def freeze_card(self):
        # 1. Extract request data
        data = request.get_json()

        # 2. Extract user authentication
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # 3. Delegate to service
        result = self.service.freeze_card(user_id=user_id, **data)

        # 4. Return HTTP response
        return jsonify(result), 200 if result["success"] else 400
```

---

## Service Layer

**Responsibilities**:
- Business logic implementation
- Authorization checks
- Audit logging
- Data orchestration

**Example** (`src/services/card_service.py`):

```python
import logging

logger = logging.getLogger(__name__)


class CardService:
    def __init__(self, audit_service=None, auth_service=None):
        self.audit_service = audit_service
        self.auth_service = auth_service

    def freeze_card(self, user_id: str, card_id: str, **kwargs):
        # 1. Validate inputs
        if not user_id or not card_id:
            raise ValueError("user_id and card_id are required")

        # 2. Check authorization
        if self.auth_service:
            if not self.auth_service.can_freeze_card(user_id, card_id):
                raise PermissionError("User not authorized to freeze this card")

        # 3. Execute business logic
        logger.info(f"Freezing card {card_id} for user {user_id}")
        result = self._perform_freeze(card_id)

        # 4. Audit log
        if self.audit_service:
            self.audit_service.log_action(
                user_id=user_id,
                action="FREEZE_CARD",
                card_id=card_id,
                result="success"
            )

        return {"success": True, "card_id": card_id, "status": "FROZEN"}

    def _perform_freeze(self, card_id: str):
        # TODO: Actual freeze logic (database update, external API call, etc.)
        pass
```

---

## Entity Extraction

The system automatically extracts the entity name from the story's "I want" clause:

| Story "I want" | Entity | Files Generated |
|---|---|---|
| "freeze my **card**" | card | `card_controller.py`, `card_service.py` |
| "view **account** balance" | account | `account_controller.py`, `account_service.py` |
| "create **payment**" | payment | `payment_controller.py`, `payment_service.py` |
| "update user **profile**" | profile | `profile_controller.py`, `profile_service.py` |

### Custom Entity Keywords

Edit `code_layout.py` to add custom entities:

```python
def _extract_entity_name(story_want: str) -> str:
    entity_keywords = {
        "card": "card",
        "account": "account",
        # Add your custom entities:
        "beneficiary": "beneficiary",
        "mandate": "mandate",
        "limit": "limit",
    }
    # ...
```

---

## Layer Inference

When `default_layer != "both"`, the system infers the layer from keywords:

| Keywords in "I want" | Layer | File |
|---|---|---|
| "endpoint", "api", "route" | controller | `controllers/card_controller.py` |
| **business logic** (default) | service | `services/card_service.py` |
| "database", "persist", "store" | repository | `repositories/card_repository.py` |
| "model", "schema", "entity" | model | `models/card_model.py` |

---

## Configuration Options

### Generate Both Controller + Service (Recommended)

```python
LAYOUT_CONFIG.default_layer = "both"

# Result: 4 files per story
# - src/controllers/card_controller.py
# - src/services/card_service.py
# - tests/controllers/card_controller_test.py
# - tests/services/card_service_test.py
```

### Generate Service Only

```python
LAYOUT_CONFIG.default_layer = "service"

# Result: 2 files per story
# - src/services/card_service.py
# - tests/services/card_service_test.py
```

### Auto-Detect Layer

```python
LAYOUT_CONFIG.default_layer = None  # or any other value

# System will infer from story keywords
# Story: "Create API endpoint for card" → controller
# Story: "Freeze card business logic" → service
```

---

## Testing

### Test Structure

```
tests/
├── controllers/
│   └── test_card_controller.py  ← HTTP integration tests
└── services/
    └── test_card_service.py     ← Business logic unit tests
```

### Controller Test Example

```python
import pytest
from flask import Flask
from src.controllers.card_controller import card_bp, CardController


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(card_bp)
    return app.test_client()


def test_freeze_card_success(client):
    response = client.post(
        "/api/cards/freeze",
        json={"card_id": "1234"},
        headers={"X-User-ID": "user-123"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_freeze_card_missing_auth(client):
    response = client.post(
        "/api/cards/freeze",
        json={"card_id": "1234"}
    )

    assert response.status_code == 401
```

### Service Test Example

```python
import pytest
from src.services.card_service import CardService


@pytest.fixture
def service():
    return CardService()


def test_freeze_card_success(service):
    result = service.freeze_card(user_id="user-123", card_id="1234")

    assert result["success"] is True
    assert result["status"] == "FROZEN"


def test_freeze_card_missing_user_id(service):
    with pytest.raises(ValueError, match="user_id.*required"):
        service.freeze_card(card_id="1234")
```

---

## Migration from Flat Structure

### Before (Flat)
```
src/us_001.py
src/us_002.py
tests/test_us_001.py
tests/test_us_002.py
```

### After (Controller-Service)
```
src/
├── controllers/
│   ├── card_controller.py
│   └── account_controller.py
└── services/
    ├── card_service.py
    └── account_service.py

tests/
├── controllers/
│   ├── test_card_controller.py
│   └── test_account_controller.py
└── services/
    ├── test_card_service.py
    └── test_account_service.py
```

### Migration Steps

1. **Enable Controller-Service layout** in `code_layout.py`
2. **Re-run Stage 3** on existing backlog
3. **Verify generated structure**
4. **Move old files** (optional):
   ```bash
   mkdir -p src/controllers src/services
   # Manual refactoring of existing files
   ```

---

## Best Practices

### ✅ Do's

- **Thin controllers**: Only handle HTTP concerns
- **Fat services**: Encapsulate all business logic
- **Inject dependencies**: Pass services via constructor
- **Test both layers**: Integration tests for controllers, unit tests for services
- **Consistent naming**: `{entity}_controller.py`, `{entity}_service.py`

### ❌ Don'ts

- **No business logic in controllers**: Delegate to services
- **No HTTP concerns in services**: Keep them framework-agnostic
- **No direct database access in controllers**: Use services/repositories
- **Avoid tight coupling**: Services shouldn't depend on Flask/HTTP

---

## Advanced: Multiple Services per Entity

For complex entities, you can manually organize:

```
src/
├── controllers/
│   └── card_controller.py       ← Routes all card operations
└── services/
    ├── card_freeze_service.py   ← Freeze-specific logic
    ├── card_unfreeze_service.py ← Unfreeze-specific logic
    └── card_query_service.py    ← Read operations
```

---

## FAQ

### Q: Can I mix with other layouts?
**A**: No, choose one layout style per project. Controller-Service is best for API backends.

### Q: What about repositories/models?
**A**: Currently, the system generates controllers and services. You can add repositories/models manually or extend the system.

### Q: Does this work with Django/FastAPI?
**A**: The pattern applies, but generated code is Flask-specific. You'd need to customize templates for other frameworks.

### Q: Can I change entity extraction logic?
**A**: Yes! Edit `_extract_entity_name()` in `code_layout.py` to customize keyword matching.

---

## Summary

**Controller-Service architecture** provides:
- ✅ Clean separation of concerns
- ✅ Testable business logic
- ✅ Framework-agnostic services
- ✅ Scalable codebase structure

Enable it with one line:
```python
LAYOUT_CONFIG.style = LayoutStyle.CONTROLLER_SERVICE
```

For more details, see [CODE_LAYOUT_CONFIGURATION.md](CODE_LAYOUT_CONFIGURATION.md).
