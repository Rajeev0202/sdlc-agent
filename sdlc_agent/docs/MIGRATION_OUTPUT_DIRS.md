# Directory Structure Migration - Final

## Summary

Reorganized directory structure to clearly separate:
1. **SDLC Agent code** (the tool itself)
2. **Generated application code** (output from the tool)
3. **Runtime artifacts** (JSON files, reports)

## Final Structure

```
sdlc-agent/
├── sdlc_agent/              # The SDLC Agent tool itself
│   ├── core/                # Core models and orchestrator
│   ├── stages/              # Stage 1-6 implementations
│   ├── web/                 # Web UI
│   ├── tests/               # Unit tests for SDLC Agent ⭐ NEW
│   └── ...
├── samples/                 # Input BRDs
├── src/                     # Generated production code (VERSIONED) ⭐
├── tests/                   # Tests for generated application (VERSIONED) ⭐
│   ├── unit/                # Unit tests (e.g., test_us_001.py)
│   ├── automation/          # Playwright/Selenium scripts
│   ├── manual/              # Manual test case files
│   └── results/             # Test execution results (gitignored)
└── sdlc_agent_output/       # Runtime artifacts only (gitignored) ⭐
    ├── runs/                # Stage 1-6 JSON artifacts
    └── code_review/         # Review reports
```

## Key Principles

| Directory | Purpose | Versioned? |
|-----------|---------|------------|
| `sdlc_agent/` | The SDLC Agent tool | ✅ Yes |
| `sdlc_agent/tests/` | Unit tests for the tool itself | ✅ Yes |
| `src/` | Generated production code | ✅ Yes (gets committed) |
| `tests/` | Tests for generated application | ✅ Yes (gets committed) |
| `tests/unit/` | Unit tests for generated app | ✅ Yes |
| `tests/automation/` | E2E test scripts (Playwright) | ✅ Yes |
| `tests/manual/` | Manual test cases | ✅ Yes |
| `tests/results/` | Test execution results | ❌ No (gitignored) |
| `sdlc_agent_output/` | Runtime JSON & reports | ❌ No (gitignored) |

## Files Updated

### 1. Code Files

| File | Changes |
|------|---------|
| `sdlc_agent/web/helpers.py` | `TESTING_DIR` → `TESTS_DIR`, added `UNIT_TESTS_DIR` |
| `sdlc_agent/web/routes.py` | All references updated from `TESTING_DIR` to `TESTS_DIR` |

### 2. Configuration Files

| File | Changes |
|------|---------|
| `.claude/settings.json` | Added permissions for `./tests/**` and `./sdlc_agent/tests/**` |
| `.gitignore` | `testing/results/` → `tests/results/`, added note about test versioning |

### 3. Documentation Files

| File | Changes |
|------|---------|
| `CLAUDE.md` | Updated pipeline table and repo map with new paths |
| `README.md` | Updated references to test directories |

## Migration Actions Performed

✅ **Created**:
- `sdlc_agent/tests/` - for SDLC Agent unit tests (empty, ready for future tests)
- `tests/unit/` - for generated application unit tests
- `tests/automation/` - for Playwright/Selenium scripts
- `tests/manual/` - for manual test cases

✅ **Moved**:
- `tests/` → `tests/unit/test_us_001.py` (test for generated code)
- `testing/` → `tests/` (renamed for consistency)

🗑️ **Cleaned up**:
- Old `Testing/` directory (uppercase)
- Old `runs/` directory at root
- Temporary `tests_temp/` directory

## Rationale

### Why `sdlc_agent/tests/`?
Unit tests for the tool should live with the tool's source code. This follows the standard Python package structure where tests are a subpackage.

### Why `tests/` at repo root?
Tests for the **generated application** belong at repo root alongside `src/` because:
1. They test the application code, not the SDLC Agent
2. They get committed and reviewed alongside the generated code
3. They run in CI/CD as part of the application's test suite

### Why subdirectories in `tests/`?
Different test types have different purposes and tooling:
- `unit/` - Fast, isolated tests run with pytest
- `automation/` - E2E tests run with Playwright/Selenium
- `manual/` - Test cases for human QA testers
- `results/` - Throw-away execution logs (gitignored)

## Testing the Changes

```bash
# Run SDLC Agent unit tests (when they exist)
pytest sdlc_agent/tests/

# Run generated application unit tests
pytest tests/unit/

# Run full test suite
pytest tests/

# Run automation tests
cd tests/automation
npx playwright test
```

## Benefits

1. **Clear separation of concerns**:
   - `sdlc_agent/tests/` = tests for the tool
   - `tests/` = tests for the generated app

2. **Standard Python structure**:
   - Package tests live in `package/tests/`
   - Application tests live in `tests/` at root

3. **CI/CD friendly**:
   - All test code is versioned
   - Only results are gitignored
   - Clear paths for pytest, Playwright, etc.

4. **Onboarding clarity**:
   - New devs immediately understand what's what
   - No confusion about "which tests go where"

---

**Migration completed**: June 19, 2026  
**Final structure verified**: ✅