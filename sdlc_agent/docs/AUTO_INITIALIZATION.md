# Automatic Harness Initialization

## Problem Solved

Previously, hooks were only registered when you **explicitly called**:
```python
from sdlc_agent import get_harness, register_default_hooks
harness = get_harness()
register_default_hooks(harness)
```

This worked fine for CLI usage, but **failed** when:
- ✅ Agents run in the **web interface**
- ✅ Agents are **spawned** (stage1-requirement, stage2-stories, etc.)
- ✅ Skills are invoked (`/sdlc-ingest`, `/sdlc-plan`, etc.)
- ✅ Code is imported by other modules

## Solution: Auto-Registration

Hooks are now **automatically registered** when the `sdlc_agent` module is imported.

### How It Works

#### 1. Module Import Triggers Bootstrap

```python
# sdlc_agent/__init__.py
from .bootstrap import ensure_harness
ensure_harness()  # ← Auto-initializes on import
```

When **any** code imports `sdlc_agent`, the harness initializes automatically.

#### 2. Harness Auto-Registers Hooks

```python
# sdlc_agent/harness.py
class Harness:
    def __init__(self, auto_register_hooks=True):
        ...
        if auto_register_hooks:
            self._auto_register_hooks()  # ← Hooks registered here
            
    def _auto_register_hooks(self):
        from . import hooks
        hooks.register_default_hooks(self)
        self._hooks_registered = True
```

First time `get_harness()` is called, hooks are automatically registered.

#### 3. Safe for Multiple Calls

```python
ensure_harness()  # First call: initializes + registers hooks
ensure_harness()  # Second call: returns existing instance
ensure_harness()  # Third call: still safe
```

The `_hooks_registered` flag prevents duplicate registration.

## Initialization Points

Hooks are now automatically initialized at **multiple entry points**:

| Entry Point | File | When |
|-------------|------|------|
| **Module import** | `sdlc_agent/__init__.py` | Any `import sdlc_agent` |
| **CLI commands** | `sdlc_agent/cli.py` | `python -m sdlc_agent.cli` |
| **Orchestrator** | `sdlc_agent/orchestrator.py` | `Orchestrator()` init |
| **Stage 2** | `sdlc_agent/stages/stage2_stories.py` | `stage2_stories.run()` |
| **Manual** | Your code | `ensure_harness()` |

## Usage in Different Contexts

### 1. CLI (Already Worked)

```bash
python -m sdlc_agent.cli run --brd samples/brd.md
```

**What happens:**
```
1. CLI module loads
2. ensure_harness() called
3. Harness created, hooks registered
4. Pipeline runs with hooks active ✅
```

### 2. Web Interface (Now Works)

When you use Claude Code in the browser:

```
User: "Run /sdlc-ingest on this page"
  ↓
Claude Code loads skill
  ↓
Skill imports sdlc_agent
  ↓
sdlc_agent.__init__ runs
  ↓
ensure_harness() called
  ↓
Hooks registered ✅
  ↓
Skill executes with hooks active
```

### 3. Spawned Agents (Now Works)

When orchestrator spawns stage agents:

```python
# Claude Code spawns stage2-stories agent
Agent(
    subagent_type="stage2-stories",
    prompt="Generate user stories from brief"
)
```

**What happens:**
```
1. Agent process starts
2. Loads stage2_stories.py
3. Imports sdlc_agent
4. ensure_harness() called
5. Hooks registered ✅
6. Agent runs with hooks active
```

### 4. Skills (Now Works)

When you invoke `/sdlc-plan`:

```
User: /sdlc-plan PROJ
  ↓
Claude Code loads skill
  ↓
Skill calls stage2_stories.run()
  ↓
stage2_stories imports sdlc_agent
  ↓
ensure_harness() called
  ↓
Hooks registered ✅
  ↓
Jira cards created, hooks fire
```

### 5. Direct Python Import (Now Works)

```python
# In any Python script
from sdlc_agent.orchestrator import Orchestrator

# Harness already initialized from import ✅
orchestrator = Orchestrator()
result = orchestrator.run("brd.md")
```

## Verification

### Test 1: Import Test

```python
# test_auto_init.py
import sdlc_agent  # This should auto-initialize

from sdlc_agent import get_harness

harness = get_harness()

# Check hooks are registered
assert "on_jira_card_created" in harness._hooks
assert len(harness._hooks["on_jira_card_created"]) > 0
print("✅ Hooks auto-registered on import")
```

### Test 2: Jira Card Creation

```python
# test_jira_auto.py
from sdlc_agent.integrations.jira_client import MockJiraClient
from sdlc_agent.models import UserStory
from sdlc_agent import get_harness

# Harness already initialized from import
harness = get_harness()
harness.state.epic = {"key": "TEST-1"}

# Create card
jira = MockJiraClient()
story = UserStory(
    id="S-001", persona="User", want="feature",
    so_that="benefit", acceptance_criteria=["AC"]
)

jira.create_story(story)

# Verify hook fired
assert len(harness.state.jira_creates) > 0
print("✅ Hook fired automatically")
```

### Test 3: Web Agent Simulation

```python
# Simulate what happens when agent runs in web
import sys
import importlib

# Fresh import (like new agent process)
if 'sdlc_agent' in sys.modules:
    del sys.modules['sdlc_agent']

# Import (simulates agent loading)
import sdlc_agent
from sdlc_agent import get_harness

harness = get_harness()

# Should have hooks
assert harness._hooks_registered
print("✅ Hooks registered in web agent context")
```

## Configuration

You can disable auto-registration if needed:

```python
from sdlc_agent.harness import Harness

# Disable auto-registration
harness = Harness(auto_register_hooks=False)

# Manually register later
from sdlc_agent import register_default_hooks
register_default_hooks(harness)
```

Or via environment variable:

```bash
export SDLC_AUTO_INIT_HOOKS=false
```

## Troubleshooting

### Hooks not firing in web?

Check if harness is initialized:

```python
from sdlc_agent import get_harness

harness = get_harness()
print(f"Hooks registered: {harness._hooks_registered}")
print(f"Hook count: {len(harness._hooks)}")
```

### Multiple harness instances?

Verify singleton pattern:

```python
from sdlc_agent import get_harness

h1 = get_harness()
h2 = get_harness()

assert h1 is h2  # Should be same instance
print(f"Same instance: {h1 is h2}")
```

### Import errors?

Check bootstrap:

```python
from sdlc_agent.bootstrap import ensure_harness

harness = ensure_harness()
if harness:
    print("✅ Bootstrap successful")
else:
    print("❌ Bootstrap failed")
```

## Implementation Details

### Bootstrap Module

```python
# sdlc_agent/bootstrap.py
_harness = None

def init_harness():
    """Initialize harness - called on module import"""
    from .harness import get_harness
    harness = get_harness()  # Auto-registers hooks
    return harness

def ensure_harness():
    """Ensure harness exists - safe to call multiple times"""
    global _harness
    if _harness is None:
        _harness = init_harness()
    return _harness

# Auto-init on import
_harness = init_harness()
```

### Auto-Registration in Harness

```python
# sdlc_agent/harness.py
class Harness:
    def __init__(self, auto_register_hooks=True):
        ...
        self._hooks_registered = False
        
        if auto_register_hooks:
            self._auto_register_hooks()
    
    def _auto_register_hooks(self):
        if self._hooks_registered:
            return  # Already done
            
        from . import hooks
        hooks.register_default_hooks(self)
        self._hooks_registered = True
```

### Entry Points

```python
# sdlc_agent/__init__.py
from .bootstrap import ensure_harness
ensure_harness()  # Module-level initialization

# sdlc_agent/cli.py
from .bootstrap import ensure_harness
ensure_harness()  # CLI initialization

# sdlc_agent/orchestrator.py
from .bootstrap import ensure_harness
ensure_harness()  # Orchestrator initialization

# sdlc_agent/stages/stage2_stories.py
from ..bootstrap import ensure_harness
ensure_harness()  # Stage initialization
```

## Benefits

✅ **Zero configuration** - Works automatically  
✅ **Web compatible** - Hooks work in browser  
✅ **Agent compatible** - Hooks work in spawned agents  
✅ **Skill compatible** - Hooks work in slash commands  
✅ **Import compatible** - Works with any import  
✅ **Safe** - Multiple calls are idempotent  
✅ **Non-breaking** - Existing code still works  

## Summary

**Before**: Manual registration required
```python
harness = get_harness()
register_default_hooks(harness)  # ← Must call explicitly
```

**After**: Automatic registration
```python
import sdlc_agent  # ← Hooks registered automatically
# Just use it!
```

**Result**: Hooks now work in **all execution contexts** - CLI, web, spawned agents, and skills! 🎉
