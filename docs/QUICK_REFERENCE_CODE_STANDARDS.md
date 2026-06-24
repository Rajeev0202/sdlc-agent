# Quick Reference: Code Generation Standards & Configuration

## 🎯 One-Page Cheat Sheet

### 📁 File Locations (Most Important)

```
sdlc-agent/
├── sdlc_agent/
│   ├── stages/
│   │   └── stage3_code.py          ← 🔧 LLM Prompt + Template + File Naming
│   ├── guardrails/
│   │   └── code_quality.py         ← 🛡️ Validation Rules (4 Layers)
│   ├── skills/
│   │   └── build_skill.py          ← ⚙️ Strict Mode Toggle + LLM Config
│   └── core/
│       └── config.py               ← 🌍 Environment Settings
├── .claude/
│   └── agents/
│       └── stage3-code.md          ← 📝 Agent Instructions
└── .env                            ← 🔑 API Keys + Feature Flags
```

---

## 🛠️ Quick Edits by Use Case

### ✅ "Change what coding rules the LLM follows"
**File**: `sdlc_agent/stages/stage3_code.py` → `_generate_with_llm()` function  
**Line**: 164-194  
**Edit**: Modify the `system =` prompt string

### ✅ "Add a new security check"
**File**: `sdlc_agent/guardrails/code_quality.py` → `_layer2_security()` function  
**Line**: 150-196  
**Edit**: Add pattern to `security_patterns` list

### ✅ "Change where generated code is saved"
**File**: `sdlc_agent/stages/stage3_code.py` → `run()` function  
**Line**: 106  
**Edit**: Change `module_path = f"src/{...}.py"`

### ✅ "Customize the fallback template"
**File**: `sdlc_agent/stages/stage3_code.py` → `_render_handler()` function  
**Line**: 26-68  
**Edit**: Modify the template string

### ✅ "Make guardrails more/less strict"
**File**: `sdlc_agent/skills/build_skill.py` → `__init__()` method  
**Line**: 35  
**Edit**: Change `strict_mode=True` to `strict_mode=False`

### ✅ "Add environment variable toggle"
**File**: `.env` (create if missing)  
**Add**:
```bash
STAGE3_BATCH_MODE=1           # Batch LLM calls
STAGE3_STRICT_MODE=1          # Strict guardrails
COVERAGE_THRESHOLD=80         # Test coverage %
```

---

## 🔐 NatWest Coding Standards (Built-in)

### Security Standards (BLOCK Severity)
- ❌ `print()` → Use `logger.info()`
- ❌ `verify=False` → Use `verify=True`
- ❌ `eval()`, `exec()`, `compile()`
- ❌ `shell=True`
- ❌ Hard-coded credentials/tokens
- ❌ `pickle` (insecure serialization)

### Implementation Patterns (Required)
- ✅ `_require_sso(request)` → SSO authentication
- ✅ `_require_role(principal, 'role')` → Authorization
- ✅ `_audit(principal, action, details)` → Audit logging
- ✅ Input validation → HTTP 400 on malformed data
- ✅ Explicit timeouts on HTTP calls
- ✅ Docstrings on all public functions

### Quality Standards (WARN Severity)
- ⚠️ Missing error handling (`try`/`except`)
- ⚠️ Missing input validation
- ⚠️ Missing audit logging (sensitive ops)
- ⚠️ TODO/FIXME markers
- ⚠️ Line length > 120 chars

---

## 🏗️ Folder Structure (Current)

```
sdlc-agent/
├── src/                           ← Generated production code (Stage 3)
│   ├── us_001.py                 ← Implementation files (one per story)
│   ├── us_002.py
│   └── ...
├── tests/                        ← Generated tests (Stage 5)
│   ├── test_us_001.py
│   └── ...
├── testing/                      ← Testing artifacts
│   ├── manual/                   ← Manual test cases (Excel)
│   ├── automation/               ← Playwright scripts
│   └── results/                  ← Execution results (gitignored)
└── sdlc_agent_output/            ← Runtime artifacts (gitignored)
    ├── runs/<run-id>/            ← Per-run JSON outputs (Stage 1-6)
    └── code_review/              ← Review reports (Stage 4)
```

---

## 📝 File Naming Patterns

### Current Pattern
```python
# Input: "Card Freeze Feature"
# Output: src/card_freeze_feature.py
module_path = f"src/{_slugify(backlog.brief_title)}.py"
```

### Custom Patterns (Examples)

#### By Story ID
```python
# us_001.py, bug_042.py
module_name = story.id.lower().replace("-", "_")
path = f"src/{module_name}.py"
```

#### By Domain/Feature
```python
# src/payments/card_freeze.py
domain = backlog.domain  # "payments", "auth", "reports"
path = f"src/{domain}/{_slugify(backlog.brief_title)}.py"
```

#### By Persona
```python
# src/customer/freeze_card.py
persona_slug = _slugify(story.persona)  # "customer", "admin"
path = f"src/{persona_slug}/{_slugify(story.want)}.py"
```

---

## 🛡️ Guardrail Layers (Validation Pipeline)

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: SYNTAX CHECK                              │
│ ✓ Valid Python AST                                 │
│ Severity: BLOCK                                     │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 2: SECURITY SCAN                             │
│ ✓ No eval/exec/shell=True                          │
│ ✓ No verify=False                                  │
│ ✓ No hard-coded secrets                            │
│ Severity: BLOCK                                     │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 3: STANDARDS CHECK                           │
│ ✓ Use logger (not print)                           │
│ ✓ Docstrings present                               │
│ ✓ Line length < 120                                │
│ Severity: BLOCK (strict) / WARN (lenient)          │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Layer 4: QUALITY METRICS                           │
│ ✓ Error handling present                           │
│ ✓ Input validation present                         │
│ ✓ Audit logging (sensitive ops)                    │
│ ✓ Authentication checks                            │
│ Severity: WARN / INFO                               │
└─────────────────────────────────────────────────────┘
                      ↓
               [PASS / FAIL]
```

---

## 🚀 Common Customization Examples

### Example 1: Add Rate Limiting Requirement

**Step 1**: Edit LLM prompt
```python
# sdlc_agent/stages/stage3_code.py:170
system = (
    "...<existing prompt>..."
    "8. All routes must include @limiter.limit('100/hour') decorator.\n"
)
```

**Step 2**: Add guardrail check
```python
# sdlc_agent/guardrails/code_quality.py:_layer3_standards()
if "@app." in code and "@limiter.limit" not in code:
    violations.append(GuardrailViolation(
        layer="standards",
        severity=GuardrailSeverity.WARN,
        rule="missing_rate_limit",
        message="Routes should include rate limiting"
    ))
```

**Step 3**: Update template
```python
# sdlc_agent/stages/stage3_code.py:_render_handler()
return (
    f"@limiter.limit('100/hour')\n"  # ADD THIS
    f"@app.get('/{fn}')\n"
    f"def {fn}():\n"
    # ...
)
```

---

### Example 2: Change Output to Domain Folders

**Edit**: `sdlc_agent/stages/stage3_code.py:106`

```python
# Before:
module_path = f"src/{_slugify(backlog.brief_title)}.py"

# After:
domain = backlog.domain or "general"  # Add domain field to StoryBacklog model
module_path = f"src/{domain}/{_slugify(backlog.brief_title)}.py"
```

**Also create directories**:
```bash
mkdir -p src/{payments,auth,reports,general}
```

---

### Example 3: Enforce Type Hints

**Step 1**: Edit guardrail
```python
# sdlc_agent/guardrails/code_quality.py:_layer3_standards()
if tree:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if function has return annotation
            if node.returns is None:
                violations.append(GuardrailViolation(
                    layer="standards",
                    severity=GuardrailSeverity.WARN,
                    rule="missing_type_hints",
                    message=f"Function {node.name} missing return type hint",
                    line=node.lineno,
                    suggestion="Add -> ReturnType annotation"
                ))
```

**Step 2**: Update LLM prompt
```python
# sdlc_agent/stages/stage3_code.py:165
system = (
    "...<existing>..."
    "All functions MUST include type hints for parameters and return values.\n"
)
```

---

## 🔍 Debugging Tips

### Check What Backend is Active
```bash
python -c "from sdlc_agent.integrations.anthropic_client import MockClaudeClient; \
  llm = MockClaudeClient(); \
  print(f'Backend: {llm.backend}, Live: {llm.is_live}')"
```

### Validate Generated Code Manually
```bash
python -c "
from sdlc_agent.guardrails.code_quality import CodeQualityGuardrails, format_guardrail_report
from pathlib import Path

code = Path('src/us_001.py').read_text()
guardrails = CodeQualityGuardrails(strict_mode=True)
result = guardrails.validate(code)

print(format_guardrail_report(result))
"
```

### Test Template Generation (No LLM)
```bash
# Set env to force template fallback
export ANTHROPIC_API_KEY=""
export GOOGLE_API_KEY=""

python -m sdlc_agent.cli code \
  --backlog sdlc_agent_output/runs/<run-id>/02_backlog.json \
  --output test.json
```

---

## 📊 Quality Score Calculation

```
Score = 100 - (violations × penalty)

Penalty per violation:
- BLOCK:  -20 points
- WARN:   -5 points
- INFO:   -1 point

Examples:
✅ 0 violations → Score: 100/100 (Perfect)
⚠️ 2 WARNs     → Score: 90/100  (Acceptable)
❌ 1 BLOCK     → Score: 80/100  (Rejected)
```

---

## 🎓 Learning Path

1. **Start here**: Read the full configuration guide → [`docs/CODE_GENERATION_CONFIGURATION.md`](CODE_GENERATION_CONFIGURATION.md)
2. **Understand guardrails**: Review → `sdlc_agent/guardrails/code_quality.py`
3. **See LLM prompt**: Read → `sdlc_agent/stages/stage3_code.py:164-214`
4. **Test modifications**: Run Stage 3 on sample backlog
5. **Validate changes**: Check guardrail reports in logs

---

## 📞 Need Help?

- **Full docs**: `docs/CODE_GENERATION_CONFIGURATION.md`
- **Examples**: `samples/brd_*.md` + corresponding `src/*.py`
- **Logs**: Check console output for `[Stage 3]` and `Guardrail validation:` messages
