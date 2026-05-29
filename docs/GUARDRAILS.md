# Code Quality Guardrails

## Overview

The **Code Quality Guardrails** system is a multi-layer validation framework that ensures LLM-generated code meets security, quality, and compliance standards before being accepted into the codebase.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Generates Code                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Syntax Validation                                 │
│  ✓ Valid Python syntax (AST parsing)                        │
│  ✓ Code is parseable and executable                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Security Scan                                     │
│  ✓ No eval()/exec()                                         │
│  ✓ No hard-coded credentials                                │
│  ✓ TLS verification enabled                                 │
│  ✓ No shell=True in subprocess                              │
│  ✓ No dangerous imports                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Standards Check                                   │
│  ✓ Uses logging (not print)                                 │
│  ✓ Has docstrings                                           │
│  ✓ Line length < 120 chars                                  │
│  ✓ Follows NatWest coding standards                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Quality Metrics                                   │
│  ✓ Has error handling (try-except)                          │
│  ✓ Has input validation                                     │
│  ✓ Has audit logging (sensitive ops)                        │
│  ✓ Has authentication (user_id)                             │
│  ✓ Not a stub/TODO                                          │
│  ✓ Reasonable complexity                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Accept/Reject Code
              (with detailed feedback)
```

## Violation Severity Levels

### 🔴 BLOCK
- **Action**: Code is rejected immediately
- **Examples**: 
  - Invalid syntax
  - Security vulnerabilities (eval, exec, verify=False)
  - Hard-coded credentials
  - Missing authentication for sensitive operations
- **Impact**: Must fix before code is accepted

### 🟡 WARN
- **Action**: Code is accepted with warnings
- **Examples**:
  - Missing docstrings
  - Missing error handling
  - Missing input validation
  - No audit logging
- **Impact**: Should fix but not blocking

### ℹ️ INFO
- **Action**: Informational only
- **Examples**:
  - Line length > 120 chars
  - High cyclomatic complexity
  - Style inconsistencies
- **Impact**: Nice to have but optional

## Quality Scoring

Code receives a quality score from 0-100:

```
Starting Score: 100
- BLOCK violation: -20 points each
- WARN violation: -5 points each
- INFO violation: -1 point each

Minimum Score: 0
```

**Score Interpretation**:
- **90-100**: Excellent - Production ready
- **70-89**: Good - Minor improvements recommended
- **50-69**: Fair - Several issues to address
- **0-49**: Poor - Major issues, likely rejected

## Integration with Stage 3

Guardrails are automatically applied during code generation:

```python
from sdlc_agent.skills.build_skill import BuildSkillAutomation

# Guardrails enabled by default (strict mode)
automation = BuildSkillAutomation(root_dir, enable_guardrails=True)

# When LLM generates code:
# 1. Code passes through all 4 layers
# 2. If any BLOCK violations → reject code, use template fallback
# 3. If passes → accept code and include in PR
```

## Configuration

### Enable/Disable Guardrails

```python
# Enable (default)
automation = BuildSkillAutomation(root_dir, enable_guardrails=True)

# Disable (for testing/demo)
automation = BuildSkillAutomation(root_dir, enable_guardrails=False)
```

### Strict vs Lenient Mode

```python
from sdlc_agent.guardrails import CodeQualityGuardrails

# Strict mode (default) - enforce all rules as BLOCK
guardrails = CodeQualityGuardrails(strict_mode=True)

# Lenient mode - downgrade some BLOCK to WARN
guardrails = CodeQualityGuardrails(strict_mode=False)
```

## Example Output

### Passing Code
```
======================================================================
🛡️  CODE QUALITY GUARDRAILS REPORT
======================================================================
Status: ✅ PASS
Quality Score: 92.0/100
Total Violations: 2
  🔴 Blocking: 0
  🟡 Warnings: 1
  ℹ️  Info: 1

Violations by Layer:

[STANDARDS] 1 issue(s):
  🟡 Missing docstring for _perform_freeze
     💡 Add docstring describing purpose and parameters

[QUALITY] 1 issue(s):
  ℹ️  Line exceeds 120 characters (132 chars) (line 45)
     💡 Break long lines for better readability
======================================================================
```

### Failing Code
```
======================================================================
🛡️  CODE QUALITY GUARDRAILS REPORT
======================================================================
Status: ❌ FAIL
Quality Score: 25.0/100
Total Violations: 5
  🔴 Blocking: 3
  🟡 Warnings: 2
  ℹ️  Info: 0

Violations by Layer:

[SECURITY] 3 issue(s):
  🔴 Hard-coded API key detected - use environment variables (line 3)
     💡 Remove unsafe pattern and use secure alternative
  🔴 TLS verification disabled - always use verify=True (line 10)
     💡 Remove unsafe pattern and use secure alternative
  🔴 subprocess with shell=True is unsafe - use shell=False (line 13)
     💡 Remove unsafe pattern and use secure alternative

[STANDARDS] 1 issue(s):
  🔴 Use logger instead of print() (line 15)
     💡 Replace print() with logger.info() or logger.debug()

[QUALITY] 1 issue(s):
  🟡 No error handling found - operations should be wrapped in try-except
     💡 Add try-except blocks around operations that could fail
======================================================================
```

## Terminal Output During Stage 3

When guardrails are active, you'll see:

```
[Stage 3] Generating code for story US-001...

🛡️  Running guardrails on src/us_001.py...
======================================================================
🛡️  CODE QUALITY GUARDRAILS REPORT
======================================================================
Status: ✅ PASS
Quality Score: 88.0/100
Total Violations: 3
  🔴 Blocking: 0
  🟡 Warnings: 2
  ℹ️  Info: 1
...
======================================================================
✅ Code ACCEPTED by guardrails (score: 88.0/100)

[Stage 3] Generation Complete:
  ✓ LLM successes: 10
  ✗ LLM failures: 2
  📋 Fallback templates used: 2
  🛡️  Guardrail rejections: 1
```

## Running the Demo

```bash
# Run the interactive demo
python -m examples.guardrails_demo

# This will show:
# - Good code that passes (score 90+)
# - Insecure code that fails (security violations)
# - Stub code that fails (quality issues)
# - Code with missing error handling (warnings)
```

## Benefits

1. **Security**: Catches dangerous patterns before they reach the codebase
2. **Quality**: Ensures consistent code quality standards
3. **Compliance**: Enforces regulatory and organizational policies
4. **Feedback**: Provides actionable suggestions for improvement
5. **Cost Savings**: Reduces rework by catching issues early
6. **Trust**: Builds confidence in LLM-generated code

## Best Practices

### For Development
- Keep guardrails **enabled** in production pipelines
- Use **strict mode** for sensitive/regulated code
- Review guardrail reports even when code passes
- Update rules based on security incidents/lessons learned

### For Testing
- Disable guardrails only for testing/demos
- Use lenient mode for rapid prototyping
- Create test cases that exercise all guardrail layers

### For Customization
- Add organization-specific rules to each layer
- Adjust severity levels based on your risk tolerance
- Integrate with existing security scanning tools
- Track metrics: rejection rate, common violations, etc.

## Metrics to Track

Monitor these KPIs:

1. **Guardrail Pass Rate**: % of generated code that passes
2. **Rejection by Layer**: Which layer rejects most code
3. **Common Violations**: Top 5 most frequent issues
4. **Average Quality Score**: Trend over time
5. **False Positives**: Valid code incorrectly rejected

## Future Enhancements

- [ ] Machine learning-based pattern detection
- [ ] Integration with Semgrep/CodeQL
- [ ] Custom rule DSL for organization policies
- [ ] Real-time feedback in IDE
- [ ] Automated fix suggestions (with LLM)
- [ ] Integration with Jira for tracking violations

## Support

For issues or questions:
- Check [CLAUDE.md](../CLAUDE.md) for context
- Review demo in `examples/guardrails_demo.py`
- See implementation in `sdlc_agent/guardrails/code_quality.py`
