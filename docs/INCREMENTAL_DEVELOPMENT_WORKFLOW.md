# Incremental Development Workflow - Adding New APIs

## Overview

This guide explains what happens when a **new requirement** arrives for an existing project that already uses the Controller-Service architecture.

---

## Scenario: New API Requirement

### Example Requirement

> **"As a Customer, I want to unfreeze my previously frozen card via the mobile app, so that I can resume normal card usage"**

Your existing codebase already has:
```
src/
├── controllers/
│   └── card_controller.py       ← Existing: freeze card
└── services/
    └── card_service.py          ← Existing: freeze card logic
```

---

## Automatic Workflow (Full Pipeline)

### **Step 1: Ingest the New Requirement** (Stage 1)

Run the SDLC pipeline:
```bash
# Via CLI
/sdlc-ingest https://confluence.company.com/new-requirement

# Via UI
Click "Stage 1: Ingest" → Enter Confluence URL
```

**What Happens**:
- ✅ Parses the requirement from Confluence/BRD
- ✅ Extracts user story: "unfreeze card"
- ✅ Identifies entity: `card` (same as existing)
- ✅ Saves to `sdlc_agent_output/runs/<new-run-id>/01_brief.json`

**Key Decision**: The system detects the entity is `card` (same as existing freeze feature).

---

### **Step 2: Create User Story** (Stage 2)

```bash
/sdlc-plan KAN
```

**What Happens**:
- ✅ Creates Jira card: `KAN-002: Unfreeze card`
- ✅ Generates structured user story
- ✅ Saves to `sdlc_agent_output/runs/<new-run-id>/02_backlog.json`

**Output**: New Jira card ready for PO approval

---

### **Step 3: Approve Backlog**

PO reviews the story and approves it:
```bash
/approve-backlog
```

**What Happens**:
- ✅ Sets `approved: true` in backlog JSON
- ✅ Unlocks Stage 3 (code generation gate)

---

### **Step 4: Generate Code** (Stage 3)

```bash
/sdlc-build KAN-002
```

**What Happens** - This is where it gets interesting!

#### **Option A: Entity Exists (Same Controller/Service)**

If the new API is for the **same entity** (e.g., both `freeze` and `unfreeze` are for `card`):

**Before**:
```
src/
├── controllers/
│   └── card_controller.py       ← Has freeze_card() method
└── services/
    └── card_service.py          ← Has freeze_card() method
```

**After** (files are **UPDATED**, not replaced):
```
src/
├── controllers/
│   └── card_controller.py       ← NOW has freeze_card() + unfreeze_card()
└── services/
    └── card_service.py          ← NOW has freeze_card() + unfreeze_card()
```

**How It Works**:
1. System detects `card_controller.py` **already exists**
2. **Reads the existing file**
3. **Appends new method** `unfreeze_card()` to the class
4. **Preserves existing methods** (freeze_card stays intact)
5. Writes updated file

**Generated Code Addition**:
```python
# src/controllers/card_controller.py

class CardController:
    def __init__(self):
        self.service = CardService()

    @card_bp.route("/freeze", methods=["POST"])
    def freeze_card(self):
        # Existing code - UNTOUCHED
        ...

    @card_bp.route("/unfreeze", methods=["POST"])  # ← NEW METHOD ADDED
    def unfreeze_card(self):
        """Unfreeze a previously frozen card."""
        data = request.get_json()
        user_id = request.headers.get("X-User-ID")
        
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        result = self.service.unfreeze_card(user_id=user_id, **data)
        return jsonify(result), 200 if result["success"] else 400
```

Similarly for service:
```python
# src/services/card_service.py

class CardService:
    def freeze_card(self, user_id: str, card_id: str):
        # Existing code - UNTOUCHED
        ...

    def unfreeze_card(self, user_id: str, card_id: str):  # ← NEW METHOD ADDED
        """Unfreeze a card."""
        if not user_id or not card_id:
            raise ValueError("user_id and card_id required")

        logger.info(f"Unfreezing card {card_id} for user {user_id}")
        # Business logic here...
        return {"success": True, "status": "ACTIVE"}
```

#### **Option B: New Entity (New Controller/Service)**

If the new API is for a **different entity** (e.g., "block account"):

**Before**:
```
src/
├── controllers/
│   └── card_controller.py
└── services/
    └── card_service.py
```

**After** (new files **CREATED**):
```
src/
├── controllers/
│   ├── card_controller.py       ← Unchanged
│   └── account_controller.py    ← NEW FILE
└── services/
    ├── card_service.py          ← Unchanged
    └── account_service.py       ← NEW FILE
```

**How It Works**:
1. System extracts entity: `account` (different from `card`)
2. **Creates new files**: `account_controller.py`, `account_service.py`
3. **Leaves existing files untouched**
4. Each entity gets its own controller/service pair

---

### **Step 5: Code Review** (Stage 4)

```bash
/sdlc-review
```

**What Happens**:
- ✅ Reviews **only the new/changed files**
- ✅ Runs security checks (no hardcoded secrets, verify=True, etc.)
- ✅ Validates coding standards (logging, docstrings, type hints)
- ✅ Checks for conflicts with existing code
- ✅ Generates review report

**Output**: `sdlc_agent_output/code_review/<run-id>_review.json`

**Possible Issues Detected**:
- ⚠️ New method has same route as existing (`/freeze`)
- ⚠️ Missing authorization check
- ⚠️ Duplicate business logic (should reuse existing helper)

---

### **Step 6: Generate Tests** (Stage 5)

```bash
/sdlc-test-manual
/sdlc-test-automation
```

**What Happens**:
- ✅ Generates tests for **new methods only**
- ✅ Extends existing test files (if entity exists)
- ✅ Creates new test files (if new entity)

**Before** (existing tests):
```python
# tests/controllers/test_card_controller.py

def test_freeze_card_success():
    # Existing test
    ...
```

**After** (tests **APPENDED**):
```python
# tests/controllers/test_card_controller.py

def test_freeze_card_success():
    # Existing test - UNTOUCHED
    ...

def test_unfreeze_card_success():  # ← NEW TEST
    response = client.post(
        "/api/cards/unfreeze",
        json={"card_id": "1234"},
        headers={"X-User-ID": "user-123"}
    )
    assert response.status_code == 200
    assert response.json["status"] == "ACTIVE"

def test_unfreeze_card_unauthorized():  # ← NEW TEST
    response = client.post("/api/cards/unfreeze", json={"card_id": "1234"})
    assert response.status_code == 401
```

---

### **Step 7: Deploy Decision** (Stage 6)

```bash
/sdlc-deploy
```

**What Happens**:
- ✅ Validates all tests pass
- ✅ Checks code coverage (>= 80%)
- ✅ Verifies no critical review findings
- ✅ Confirms CI/CD pipeline green
- ✅ Generates release notes

**Output**: GO / NO-GO decision

---

## Smart File Management

### How the System Handles Existing Files

The SDLC Agent uses **intelligent file merging**:

#### **1. File Detection**
```python
# Pseudo-code of what happens
if file_exists("src/controllers/card_controller.py"):
    mode = "UPDATE"  # Append new method
else:
    mode = "CREATE"  # Create new file
```

#### **2. Method Extraction** (if UPDATE mode)
```python
# Read existing file
existing_code = read_file("src/controllers/card_controller.py")

# Parse AST to find existing methods
existing_methods = ["freeze_card", "create_card"]

# Generate new method
new_method = "unfreeze_card"

# Check for conflicts
if new_method in existing_methods:
    raise Error("Method already exists!")

# Append new method to class
updated_code = append_method(existing_code, new_method_code)
```

#### **3. Smart Merging**

The system:
- ✅ Preserves imports
- ✅ Keeps existing class structure
- ✅ Adds new methods at the end
- ✅ Maintains consistent formatting
- ✅ Avoids duplicate routes

**Example Merge**:

**Existing** (`card_controller.py`):
```python
from flask import Blueprint, request, jsonify
from ..services.card_service import CardService

card_bp = Blueprint("card", __name__, url_prefix="/api/cards")

class CardController:
    def __init__(self):
        self.service = CardService()

    @card_bp.route("/freeze", methods=["POST"])
    def freeze_card(self):
        # Existing implementation
        pass
```

**New Requirement**: Add `unfreeze_card()` method

**After Merge**:
```python
from flask import Blueprint, request, jsonify
from ..services.card_service import CardService  # ← Preserved

card_bp = Blueprint("card", __name__, url_prefix="/api/cards")  # ← Preserved

class CardController:  # ← Preserved
    def __init__(self):  # ← Preserved
        self.service = CardService()

    @card_bp.route("/freeze", methods=["POST"])  # ← Preserved
    def freeze_card(self):  # ← Preserved
        # Existing implementation
        pass

    @card_bp.route("/unfreeze", methods=["POST"])  # ← NEW
    def unfreeze_card(self):  # ← NEW
        # New implementation
        pass
```

---

## Entity-Based Organization

### How Entities Are Grouped

The system uses **entity extraction** to decide file placement:

| Requirement | Entity | Action | Result |
|-------------|--------|--------|--------|
| "Freeze card" | `card` | CREATE | `card_controller.py` (new) |
| "Unfreeze card" | `card` | **UPDATE** | `card_controller.py` (add method) |
| "Replace card" | `card` | **UPDATE** | `card_controller.py` (add method) |
| "Block account" | `account` | CREATE | `account_controller.py` (new) |
| "View balance" | `balance` or `account` | CREATE/UPDATE | Depends on config |

### Customize Entity Extraction

Edit `sdlc_agent/core/code_layout.py`:

```python
def _extract_entity_name(story_want: str) -> str:
    # Custom logic to map stories to entities
    if "freeze" in story_want or "unfreeze" in story_want or "replace" in story_want:
        return "card"  # All card operations → same file
    
    if "balance" in story_want or "statement" in story_want:
        return "account"  # Balance/statement → account controller
    
    # Default extraction
    return _default_entity_extraction(story_want)
```

---

## Best Practices

### ✅ **Do's**

1. **Group related APIs by entity**
   - Freeze, Unfreeze, Replace card → `card_controller.py`
   - Create, Update, Delete account → `account_controller.py`

2. **Review existing files before generating**
   - Check if the entity already exists
   - Ensure new method doesn't conflict with existing routes

3. **Run Stage 4 (Review) after each addition**
   - Catches duplicate logic
   - Validates integration with existing code

4. **Maintain consistent naming**
   - `freeze_card()`, `unfreeze_card()` (verb_entity pattern)

5. **Update tests incrementally**
   - Add new test methods to existing test files
   - Keep test coverage > 80%

### ❌ **Don'ts**

1. **Don't create separate files for each API**
   - ❌ `freeze_card_controller.py`, `unfreeze_card_controller.py`
   - ✅ One `card_controller.py` with multiple methods

2. **Don't skip the approval gate**
   - Always have PO approve new stories before code generation

3. **Don't ignore code review warnings**
   - Duplicate routes, missing auth, etc.

4. **Don't manually edit generated files without re-running pipeline**
   - Manual changes get overwritten on next generation
   - Use the pipeline for all changes

---

## Advanced: Handling Conflicts

### Scenario: Duplicate Route

**Problem**: New requirement uses same route as existing API

**Existing**:
```python
@card_bp.route("/status", methods=["GET"])
def get_status(self):
    # Returns card frozen/active status
```

**New Requirement**: "Get card transaction status"
```python
@card_bp.route("/status", methods=["GET"])  # ← CONFLICT!
def get_transaction_status(self):
    # Returns transaction pending/completed status
```

**Solution Options**:

1. **Stage 4 detects conflict** → Returns `verdict: FAIL`
   ```
   ❌ Duplicate route detected: /api/cards/status
   Suggested fix: Use different route (/transaction-status)
   ```

2. **Manual intervention required**:
   - Rename new route to `/api/cards/transaction-status`
   - Or refactor existing route to handle both cases
   - Re-run Stage 3 after fixing requirement

3. **Automated resolution** (future enhancement):
   - System appends query parameter: `/status?type=transaction`
   - Or uses different HTTP method: `POST /status`

---

## Summary: New Requirement Flow

```
┌────────────────────────────────────────────────────────────┐
│ 1. New Requirement Arrives                                 │
│    → Confluence page, Jira ticket, BRD document           │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Stage 1: Ingest                                         │
│    → Parse requirement, extract user story                │
│    → Identify entity (card, account, payment, etc.)       │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Stage 2: Create Jira Story                             │
│    → KAN-002: Unfreeze card                               │
│    → Wait for PO approval                                 │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 4. Stage 3: Generate Code                                 │
│    ┌─────────────────────────────────────────────────┐   │
│    │ IF entity exists (card):                        │   │
│    │   → UPDATE card_controller.py (add method)      │   │
│    │   → UPDATE card_service.py (add method)         │   │
│    │                                                  │   │
│    │ ELSE (new entity - account):                    │   │
│    │   → CREATE account_controller.py (new file)     │   │
│    │   → CREATE account_service.py (new file)        │   │
│    └─────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 5. Stage 4: Code Review                                   │
│    → Check for conflicts, duplicates, security issues     │
│    → If FAIL → Fix and re-run Stage 3                    │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 6. Stage 5: Generate Tests                                │
│    → UPDATE test_card_controller.py (add test methods)    │
│    → UPDATE test_card_service.py (add test methods)       │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ 7. Stage 6: Deploy Decision                               │
│    → All tests pass? Coverage > 80%? GO / NO-GO          │
└────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Incremental additions are automatic** - Run the pipeline, system handles merging
2. **Same entity = Updated files** - Methods appended to existing controller/service
3. **New entity = New files** - Separate controller/service pair created
4. **Tests follow the same pattern** - New tests appended or new test file created
5. **Code review catches conflicts** - Duplicate routes, missing auth, etc.
6. **PO approval gate always required** - Ensures business sign-off before coding

**The system is designed for iterative, incremental development!** 🚀
