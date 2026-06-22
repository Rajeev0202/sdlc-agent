# Code Generation Configuration Guide

## Overview

The SDLC Agent's Stage 3 code generation is highly configurable. This guide explains where and how to configure:

1. **Coding Standards** - What rules the generated code must follow
2. **Folder Structure** - Where generated code is placed
3. **Templates** - Fallback code patterns when LLM is unavailable
4. **Quality Guardrails** - Validation layers that accept/reject code

---

## 1. Coding Standards Configuration

### Location: Multiple Files

#### A. **Core Standards (NatWest Rules)**

**File**: `sdlc_agent/stages/stage3_code.py` (lines 164-194)

The LLM system prompt defines mandatory coding standards:

```python
system = (
    "You are a senior NatWest backend engineer. Generate a single Python "
    "Flask module that implements the approved user stories. STRICT NatWest "
    "coding standards: use the standard `logging` module (never print); "
    "TLS verification MUST stay enabled (no verify=False); no hard-coded "
    "credentials, tokens or PII; no eval/exec; no shell=True; every public "
    "function has a docstring. ..."
)
```

**To modify**: Edit the `_generate_with_llm()` function's `system` prompt.

**Standards enforced**:
- ✅ Use `logging` module (never `print()`)
- ✅ TLS verification enabled (`verify=True` explicit)
- ✅ No hard-coded credentials/tokens/PII
- ✅ No dangerous functions (`eval`, `exec`, `subprocess(..., shell=True)`)
- ✅ Docstrings on all public functions
- ✅ Type hints required
- ✅ SSO authentication via `_require_sso()` helper
- ✅ Role-based authorization via `_require_role()`
- ✅ Audit logging for state mutations
- ✅ Input validation (HTTP 400 on malformed data)
- ✅ Timeout on outbound HTTP calls

#### B. **Agent-Level Standards**

**File**: `.claude/agents/stage3-code.md` (lines 22-28)

```markdown
## NatWest standards (non-negotiable)
- Use the project logger; **never `print()`**.
- TLS verification is on by default; never set `verify=False`.
- No hard-coded credentials. Read from `os.environ` or the existing config layer.
- No `eval`, `exec`, `subprocess(..., shell=True)`.
- Every public function has a one-line docstring and type hints.
- Reuse existing utilities — search with Grep before creating new helpers.
```

**To modify**: Edit this markdown file to change what the Stage 3 agent enforces.

---

## 2. Quality Guardrails (Validation Layers)

### Location: `sdlc_agent/guardrails/code_quality.py`

The guardrails module validates generated code through 4 layers:

### **Layer 1: Syntax Validation**
- Ensures code parses as valid Python AST
- **Severity**: BLOCK (code rejected if fails)

### **Layer 2: Security Scan** (lines 150-196)
Pattern-based and AST-based checks:
- ❌ `eval()`, `exec()`, `compile()`
- ❌ `shell=True` in subprocess
- ❌ `verify=False` (TLS disabled)
- ❌ Hard-coded API keys (regex: `sk_|AKIA|ghp_|AIza...`)
- ❌ Hard-coded passwords
- ❌ `pickle.loads()` (insecure serialization)
- ❌ `__import__()` (dynamic imports)

**Severity**: BLOCK

### **Layer 3: Standards Check** (lines 198-252)
- ❌ `print()` statements → Use `logger`
- ⚠️  Missing logging import
- ⚠️  Missing docstrings on functions/classes
- ℹ️  Line length > 120 chars (PEP 8 violation)

**Severity**: BLOCK (strict mode) / WARN (lenient mode)

### **Layer 4: Quality Metrics** (lines 254-339)
- ⚠️  Missing error handling (`try`/`except`)
- ⚠️  Missing input validation
- ⚠️  Sensitive operations without audit logging
- 🔴 Sensitive operations without `user_id` authentication
- ⚠️  Incomplete implementation (TODO/FIXME markers)
- ℹ️  High function complexity (nesting depth > 4)

**Severity**: WARN / INFO / BLOCK (context-dependent)

### **How to Modify Guardrails**

Edit `sdlc_agent/guardrails/code_quality.py`:

```python
# Add new security pattern
security_patterns = [
    (r"pattern_regex", "Error message"),
    # Add your pattern here
]

# Change severity levels
violations.append(GuardrailViolation(
    layer="security",
    severity=GuardrailSeverity.BLOCK,  # Change to WARN or INFO
    rule="rule_name",
    message="Custom message"
))
```

### **Strict Mode Configuration**

**File**: `sdlc_agent/skills/build_skill.py` (line 35)

```python
self.guardrails = CodeQualityGuardrails(strict_mode=True)
```

- `strict_mode=True`: BLOCKing enforcement for print(), missing auth
- `strict_mode=False`: Downgrades some BLOCKs to WARNs

---

## 3. Folder Structure Configuration

### Output Directories

**File**: `sdlc_agent/web/helpers.py` (or check `routes.py`)

```python
SRC_DIR = ROOT / "src"              # Generated production code
TESTS_DIR = ROOT / "tests"          # Generated test files
RUNS_DIR = ROOT / "sdlc_agent_output/runs"  # Run artifacts
REVIEW_DIR = ROOT / "sdlc_agent_output/code_review"
MANUAL_TESTS_DIR = ROOT / "testing/manual"
AUTOMATION_SCRIPTS_DIR = ROOT / "testing/automation"
RESULTS_DIR = ROOT / "testing/results"
```

### Generated File Naming

**File**: `sdlc_agent/stages/stage3_code.py` (line 106)

```python
module_path = f"src/{_slugify(backlog.brief_title)}.py"
```

**Current pattern**:
- Input: "Card Freeze Feature"
- Output: `src/card_freeze_feature.py`

**To customize**:
```python
# Example: Change to kebab-case
module_path = f"src/{backlog.brief_title.lower().replace(' ', '-')}.py"
# → src/card-freeze-feature.py

# Example: Organize by feature domain
module_path = f"src/features/{_slugify(backlog.domain)}/{_slugify(backlog.brief_title)}.py"
# → src/features/payments/card_freeze_feature.py
```

### File Organization Patterns

**File**: `sdlc_agent/skills/build_skill.py` (line 133)

```python
def _generate_implementation(self, story) -> CodeFile:
    module_name = story.id.lower().replace("-", "_")
    # Current: src/us_001.py
    
    # Customize:
    # Option 1: Group by story type
    story_type = story.id.split("-")[0]  # "US", "BUG", "TASK"
    path = f"src/{story_type.lower()}/{module_name}.py"
    
    # Option 2: Group by persona
    persona_slug = _slugify(story.persona)
    path = f"src/{persona_slug}/{module_name}.py"
    
    # Option 3: Flat structure with prefix
    path = f"src/story_{module_name}.py"
```

---

## 4. Code Templates (Fallback Generation)

### Location: `sdlc_agent/stages/stage3_code.py` (lines 26-68)

When LLM is unavailable, a deterministic template is used:

```python
def _render_handler(story: UserStory) -> str:
    fn = _slugify(story.want)
    criteria_comments = "\n".join(
        f"    # AC: {c}" for c in story.acceptance_criteria
    )
    return (
        f"@app.get('/{fn}')\n"
        f"def {fn}():\n"
        f"    # Story {story.id} — {story.as_a_statement}\n"
        f"{criteria_comments}\n"
        f"    # TODO: implement business logic\n"
        f"    return {{'status': 'ok', 'story': '{story.id}'}}\n"
    )
```

### **Customizing Templates**

Edit `_render_module()` and `_render_handler()` functions:

```python
def _render_handler(story: UserStory) -> str:
    # Example: Add authentication scaffolding to template
    fn = _slugify(story.want)
    
    template = f'''
@app.post('/{fn}')
def {fn}():
    """
    {story.as_a_statement}
    
    Acceptance Criteria:
{chr(10).join(f"    - {c}" for c in story.acceptance_criteria)}
    """
    # Authentication
    principal = _require_sso(request)
    
    # Input validation
    data = request.get_json()
    if not data:
        return {{"error": "Invalid request"}}, 400
    
    # TODO: Business logic
    
    # Audit logging
    _audit(principal, "{story.id}", data)
    
    return {{"status": "ok", "story": "{story.id}"}}
'''
    return template
```

---

## 5. Environment Variables

### LLM Backend Selection

```bash
# Use Claude Code CLI as LLM backend
export ANTHROPIC_API_KEY="sk-ant-..."

# Use Google Gemini
export GOOGLE_API_KEY="AIza..."
```

### Stage 3 Specific Settings

```bash
# Batch generation mode (1 LLM call for all stories)
export STAGE3_BATCH_MODE=1  # default: enabled

# Guardrails enforcement
export STAGE3_STRICT_MODE=1  # default: enabled

# Coverage threshold
export COVERAGE_THRESHOLD=80  # default: 80%
```

---

## 6. Configuration Files

### `.env` File (Project Root)

```env
# LLM Integration
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Code Generation
STAGE3_BATCH_MODE=1
STAGE3_STRICT_MODE=1
COVERAGE_THRESHOLD=80

# Output Directories (optional overrides)
SRC_DIR=src
TESTS_DIR=tests
```

### `sdlc_agent/core/config.py`

Application-level configuration:

```python
class BaseConfig:
    # Coverage threshold for quality gates
    COVERAGE_THRESHOLD = int(os.getenv("COVERAGE_THRESHOLD", "80"))
    
    # Add custom settings:
    CODE_STYLE = os.getenv("CODE_STYLE", "pep8")  # or "black", "google"
    MAX_LINE_LENGTH = int(os.getenv("MAX_LINE_LENGTH", "120"))
    REQUIRE_TYPE_HINTS = os.getenv("REQUIRE_TYPE_HINTS", "1") == "1"
```

---

## 7. Quick Reference: What to Edit for Common Tasks

| Task | File to Edit | Lines |
|------|-------------|-------|
| **Change coding standards** | `sdlc_agent/stages/stage3_code.py` | 164-194 |
| **Add/remove guardrail rules** | `sdlc_agent/guardrails/code_quality.py` | 150-339 |
| **Change output folder** | `sdlc_agent/web/helpers.py` or `routes.py` | N/A |
| **Customize file naming** | `sdlc_agent/stages/stage3_code.py` | 106 |
| **Modify fallback template** | `sdlc_agent/stages/stage3_code.py` | 26-68 |
| **Enable/disable strict mode** | `sdlc_agent/skills/build_skill.py` | 35 |
| **Add LLM implementation patterns** | `sdlc_agent/stages/stage3_code.py` | 170-194 |

---

## 8. Example: Adding Custom Coding Standard

### Requirement
> "All API endpoints must include rate limiting headers"

### Step 1: Add to LLM System Prompt

Edit `sdlc_agent/stages/stage3_code.py`:

```python
system = (
    "You are a senior NatWest backend engineer. ..."
    # Add new requirement:
    "8. All Flask routes MUST include rate-limiting decorators: "
    "@limiter.limit('100/hour') before the route decorator. "
    "Import from 'flask_limiter import Limiter'.\n"
)
```

### Step 2: Add Guardrail Validation

Edit `sdlc_agent/guardrails/code_quality.py`:

```python
def _layer3_standards(self, code: str, tree: Optional[ast.AST]) -> list[GuardrailViolation]:
    violations = []
    
    # Existing checks...
    
    # NEW: Check for rate limiting
    has_routes = "@app.route" in code or "@app.get" in code or "@app.post" in code
    has_rate_limit = "@limiter.limit" in code
    
    if has_routes and not has_rate_limit:
        violations.append(GuardrailViolation(
            layer="standards",
            severity=GuardrailSeverity.WARN,
            rule="missing_rate_limit",
            message="API routes should include rate limiting decorators",
            suggestion="Add @limiter.limit('100/hour') above route decorators"
        ))
    
    return violations
```

### Step 3: Update Fallback Template

Edit `sdlc_agent/stages/stage3_code.py`:

```python
def _render_module(stories: list[UserStory], *, inject_defect: bool = False) -> str:
    header = (
        '"""Auto-generated by the SDLC Agent (Stage 3)."""\n'
        "import logging\n"
        "import os\n"
        "import requests\n"
        "from flask import Flask\n"
        "from flask_limiter import Limiter\n"  # NEW
        "from flask_limiter.util import get_remote_address\n"  # NEW
        "\n"
        "log = logging.getLogger(__name__)\n"
        "app = Flask(__name__)\n"
        "limiter = Limiter(app, key_func=get_remote_address)\n"  # NEW
        "\n"
    )
    # ...
```

```python
def _render_handler(story: UserStory) -> str:
    fn = _slugify(story.want)
    criteria_comments = "\n".join(f"    # AC: {c}" for c in story.acceptance_criteria)
    
    return (
        f"@limiter.limit('100/hour')\n"  # NEW
        f"@app.get('/{fn}')\n"
        f"def {fn}():\n"
        f"    # Story {story.id} — {story.as_a_statement}\n"
        f"{criteria_comments}\n"
        f"    # TODO: implement business logic\n"
        f"    return {{'status': 'ok', 'story': '{story.id}'}}\n"
    )
```

---

## 9. Testing Your Configuration

### Validate Changes

```bash
# Run Stage 3 with test backlog
python -m sdlc_agent.cli code \
  --backlog sdlc_agent_output/runs/<run-id>/02_backlog.json \
  --output test_output.json

# Check generated code
cat src/generated_file.py

# Run guardrails manually
python -c "
from sdlc_agent.guardrails.code_quality import CodeQualityGuardrails
from pathlib import Path

code = Path('src/generated_file.py').read_text()
guardrails = CodeQualityGuardrails(strict_mode=True)
result = guardrails.validate(code)

print(f'Pass: {result.passed}')
print(f'Score: {result.score}')
for v in result.violations:
    print(f'  {v.severity.value}: {v.message}')
"
```

---

## 10. Best Practices

1. **Version control your configurations** - Commit changes to `.env.example`, not `.env`
2. **Test in development first** - Use `APP_ENV=development` before production
3. **Document custom rules** - Add comments explaining why standards exist
4. **Keep guardrails in sync** - If you add LLM prompt rules, add matching guardrails
5. **Monitor rejection rates** - Check logs for `Guardrail rejections: N` to tune severity levels
6. **Use strict mode in CI/CD** - Enforce BLOCK-level rules in automated pipelines

---

## Summary

The code generation system is configured through:

1. **LLM System Prompt** → What the AI is told to generate
2. **Quality Guardrails** → What validation runs before accepting code
3. **Fallback Templates** → What deterministic code is used when LLM fails
4. **File Organization** → Where and how files are named/placed
5. **Environment Variables** → Runtime behavior toggles

All components are independently configurable, allowing you to enforce different standards at different stages of the pipeline.
