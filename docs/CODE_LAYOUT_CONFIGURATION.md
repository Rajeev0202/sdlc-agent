# Code Layout Configuration Guide

## Overview

The SDLC Agent now supports **configurable code layout** - you can customize where generated code files are placed and how they're named.

---

## Quick Start

### Change Layout Style

Edit `sdlc_agent/core/code_layout.py`:

```python
# Line 62-68: Find the LAYOUT_CONFIG section
LAYOUT_CONFIG = CodeLayoutConfig(
    style=LayoutStyle.BY_DOMAIN,  # ← Change this line
    src_dir="src",
    test_dir="tests",
    module_case="snake_case",
    group_by_type=False,
)
```

Or set environment variable:

```bash
export CODE_LAYOUT_STYLE=by_domain
```

---

## Available Layout Styles

### 1. **FLAT** (Default)
Simple flat structure - all files in one folder.

```
src/
├── us_001.py
├── us_002.py
└── us_003.py

tests/
├── test_us_001.py
├── test_us_002.py
└── test_us_003.py
```

**Use when**: Small projects, simple structure, few stories.

---

### 2. **BY_DOMAIN**
Organize by business domain (payments, auth, accounts, etc.).

```
src/
├── payments/
│   ├── us_001.py
│   └── us_005.py
├── cards/
│   ├── us_002.py
│   └── us_003.py
└── auth/
    └── us_004.py

tests/
├── payments/
│   ├── test_us_001.py
│   └── test_us_005.py
└── cards/
    ├── test_us_002.py
    └── test_us_003.py
```

**Domain mapping** is automatic based on keywords:
- "payment", "transfer" → `payments/`
- "card", "freeze" → `cards/`
- "auth", "login" → `auth/`
- "balance", "account" → `accounts/`
- "audit", "compliance" → `compliance/`

**Custom mapping**:
```python
LAYOUT_CONFIG.domain_mapping = {
    "US": "payments",      # US-001 → src/payments/us_001.py
    "BUG": "bug_fixes",    # BUG-042 → src/bug_fixes/bug_042.py
    "AUTH": "auth"         # AUTH-001 → src/auth/auth_001.py
}
```

**Use when**: Large projects with clear domain boundaries.

---

### 3. **BY_FEATURE**
Group by feature name (extracted from story "I want" clause).

```
src/
├── features/
│   ├── freeze_card/
│   │   ├── us_001.py
│   │   └── us_002.py
│   ├── view_balance/
│   │   └── us_003.py
│   └── transfer_funds/
│       └── us_004.py

tests/
├── features/
│   ├── freeze_card/
│   │   ├── test_us_001.py
│   │   └── test_us_002.py
│   └── view_balance/
│       └── test_us_003.py
```

**Feature extraction** from story "I want":
- "I want to freeze my card" → `features/freeze_card/`
- "I want to view my balance" → `features/view_balance/`

**Use when**: Feature-driven development, epics spanning multiple stories.

---

### 4. **BY_PERSONA**
Organize by user persona (customer, admin, agent, etc.).

```
src/
├── customer/
│   ├── us_001.py
│   ├── us_002.py
│   └── us_003.py
├── admin/
│   └── us_004.py
└── support_agent/
    └── us_005.py

tests/
├── customer/
│   ├── test_us_001.py
│   ├── test_us_002.py
│   └── test_us_003.py
└── admin/
    └── test_us_004.py
```

**Use when**: Different UIs/workflows per persona, role-based access control.

---

### 5. **BY_LAYER**
Organize by application layer (api, ui, data, workflows).

```
src/
├── api/
│   ├── us_001.py    # Backend service
│   └── us_003.py
├── ui/
│   └── us_002.py    # Frontend component
└── data/
    └── us_004.py    # Database migration

tests/
├── api/
│   ├── test_us_001.py
│   └── test_us_003.py
└── ui/
    └── test_us_002.py
```

**Layer detection** from keywords:
- "api", "endpoint", "service" → `api/`
- "ui", "screen", "page", "view" → `ui/`
- "database", "schema", "migration" → `data/`
- "workflow", "process" → `workflows/`

**Use when**: Microservices, layered architecture, separation of concerns.

---

### 6. **FEATURE_MODULES**
Each feature gets its own module with standard naming.

```
src/
├── card_freeze/
│   ├── service.py       # ← Standard name
│   ├── api.py
│   └── models.py
├── balance_view/
│   └── service.py
└── fund_transfer/
    └── service.py

tests/
├── card_freeze/
│   ├── test_service.py
│   └── test_api.py
└── balance_view/
    └── test_service.py
```

**Use when**: Module-based architecture, clean imports, scalable structure.

---

## Advanced Configuration

### File Naming Patterns

```python
LAYOUT_CONFIG = CodeLayoutConfig(
    impl_pattern="{module_name}.py",        # Default
    test_pattern="test_{module_name}.py",   # Default

    # Or customize:
    impl_pattern="{module_name}_impl.py",
    test_pattern="{module_name}_test.py",
)
```

### Module Name Case

```python
LAYOUT_CONFIG.module_case = "snake_case"  # us_001 (default)
# LAYOUT_CONFIG.module_case = "kebab-case"  # us-001
# LAYOUT_CONFIG.module_case = "PascalCase"  # Us001
# LAYOUT_CONFIG.module_case = "camelCase"   # us001
```

### Group by Story Type

```python
LAYOUT_CONFIG.group_by_type = True

# Result:
# src/
# ├── us/
# │   ├── us_001.py
# │   └── us_002.py
# ├── bug/
# │   └── bug_042.py
# └── task/
#     └── task_010.py
```

### Custom Base Directories

```python
LAYOUT_CONFIG.src_dir = "backend/src"
LAYOUT_CONFIG.test_dir = "backend/tests"

# Result:
# backend/
# ├── src/
# │   └── us_001.py
# └── tests/
#     └── test_us_001.py
```

---

## Custom Layout Functions

For complete control, provide a custom function:

```python
def my_custom_layout(story):
    """Custom layout logic."""
    # Example: Year-month folders
    from datetime import datetime
    year_month = datetime.now().strftime("%Y-%m")

    # Extract priority from story
    priority = "high" if "urgent" in story.want.lower() else "normal"

    return f"{year_month}/{priority}"

LAYOUT_CONFIG.style = my_custom_layout

# Result:
# src/
# └── 2026-06/
#     ├── high/
#     │   └── us_001.py
#     └── normal/
#         └── us_002.py
```

---

## Environment Variable Overrides

Set at runtime without code changes:

```bash
# Set layout style
export CODE_LAYOUT_STYLE=by_domain

# Run pipeline
python -m sdlc_agent.web
```

Valid values:
- `flat`
- `by_domain`
- `by_feature`
- `by_persona`
- `by_layer`
- `feature_modules`

---

## Migration Guide

### From Flat to Domain-Based

**Before**:
```
src/us_001.py
src/us_002.py
src/us_003.py
```

**After**:
```
src/payments/us_001.py
src/cards/us_002.py
src/auth/us_003.py
```

**Steps**:
1. Edit `code_layout.py` → Change `FLAT` to `BY_DOMAIN`
2. Run Stage 3 again on existing backlog
3. New files are generated in domain folders
4. Optionally move old files:
   ```bash
   mkdir -p src/payments src/cards
   mv src/us_001.py src/payments/
   mv src/us_002.py src/cards/
   ```

---

## Testing Your Configuration

```python
# Test layout generation
python -c "
from sdlc_agent.core.code_layout import get_implementation_path, get_test_path
from sdlc_agent.core.models import UserStory

# Create test story
story = UserStory(
    id='US-001',
    persona='Customer',
    want='freeze my card via mobile app',
    so_that='prevent fraud',
    acceptance_criteria=[]
)

print('Implementation:', get_implementation_path(story))
print('Test:', get_test_path(story))
"
```

**Expected output (BY_DOMAIN)**:
```
Implementation: src/cards/us_001.py
Test: tests/cards/test_us_001.py
```

---

## Recommended Layouts by Project Size

| Project Size | Stories | Recommended Layout |
|--------------|---------|-------------------|
| **Small** | < 20 | `FLAT` |
| **Medium** | 20-100 | `BY_DOMAIN` or `BY_FEATURE` |
| **Large** | 100-500 | `BY_DOMAIN` + `group_by_type=True` |
| **Enterprise** | > 500 | `FEATURE_MODULES` with custom mapping |

---

## FAQ

### Q: Can I mix layouts?
**A**: Not directly. Pick one style per project. For complex needs, use a custom function.

### Q: Does this affect existing files?
**A**: No. Only new code generation uses the layout. Existing files stay in place.

### Q: Can I change layout mid-project?
**A**: Yes, but you'll need to manually move existing files to match the new structure.

### Q: How do imports work with nested folders?
**A**: Generated tests use relative imports:
```python
# tests/cards/test_us_001.py
from src.cards.us_001 import US001Feature
```

### Q: Can I customize domain keywords?
**A**: Yes! Edit the `_infer_domain()` function in `code_layout.py`.

---

## Complete Example

**Scenario**: NatWest banking project with 50+ stories across multiple domains.

**Configuration**:
```python
# sdlc_agent/core/code_layout.py
LAYOUT_CONFIG = CodeLayoutConfig(
    style=LayoutStyle.BY_DOMAIN,
    src_dir="src",
    test_dir="tests",
    module_case="snake_case",
    group_by_type=True,  # Separate US/BUG/TASK
    domain_mapping={
        "US": None,    # Auto-detect domain
        "BUG": "bugs", # All bugs in bugs/ folder
        "TASK": None   # Auto-detect
    }
)
```

**Result**:
```
src/
├── us/
│   ├── payments/
│   │   ├── us_001.py
│   │   └── us_005.py
│   ├── cards/
│   │   ├── us_002.py
│   │   └── us_003.py
│   └── auth/
│       └── us_004.py
├── bug/
│   ├── bug_042.py
│   └── bug_043.py
└── task/
    └── task_010.py

tests/
├── us/
│   ├── payments/
│   │   ├── test_us_001.py
│   │   └── test_us_005.py
│   └── cards/
│       ├── test_us_002.py
│       └── test_us_003.py
└── bug/
    ├── test_bug_042.py
    └── test_bug_043.py
```

---

## Next Steps

1. **Choose a layout style** that matches your project structure
2. **Edit `code_layout.py`** to configure it
3. **Test with one story** before running full pipeline
4. **Document your choice** in project README for team alignment

For more details, see:
- [CODE_GENERATION_CONFIGURATION.md](CODE_GENERATION_CONFIGURATION.md) - Full code gen guide
- [QUICK_REFERENCE_CODE_STANDARDS.md](QUICK_REFERENCE_CODE_STANDARDS.md) - Cheat sheet
