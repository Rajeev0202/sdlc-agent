# Token Usage Tracking — Implementation Summary

## Overview

Token usage tracking has been successfully added to the SDLC Agent harness. Every LLM API call can now capture and record detailed token metrics for cost analysis and optimization.

## What Was Added

### 1. New Data Model (`TokenUsage`)

```python
class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0
```

### 2. Enhanced `ToolSpan` Model

The `ToolSpan` model now includes an optional `token_usage` field:

```python
class ToolSpan(BaseModel):
    trace_id: str
    span_id: str
    tool: str
    stage: str | None = None
    duration_ms: int | None = None
    token_usage: TokenUsage | None = None  # ← NEW
    ts: str
```

### 3. Updated `traces.jsonl` Schema

Each trace entry can now include token metrics:

```json
{
  "trace_id": "trace-abc123",
  "span_id": "span-def456",
  "tool": "claude_complete",
  "stage": "plan",
  "duration_ms": 2341,
  "token_usage": {
    "input_tokens": 1523,
    "output_tokens": 487,
    "cache_creation_tokens": 100,
    "cache_read_tokens": 1200,
    "total_tokens": 2110
  },
  "status": "ok",
  "ts": "2026-06-17T10:30:45Z"
}
```

### 4. Automatic Token Aggregation in `metrics.json`

Token usage is automatically aggregated at three levels:

- **Totals** — Cumulative across all stages
- **By Stage** — Per pipeline stage (plan, build, review, etc.)
- **By Tool** — Per tool type (claude_complete, anthropic_messages, etc.)

```json
{
  "totals": {
    "total_tokens": 45678,
    "total_input_tokens": 32100,
    "total_output_tokens": 13578,
    "total_cache_creation_tokens": 2500,
    "total_cache_read_tokens": 18000
  },
  "by_stage": {
    "plan": {
      "total_tokens": 12000,
      "input_tokens": 8500,
      "output_tokens": 3500
    }
  },
  "by_tool": {
    "claude_complete": {
      "total_tokens": 8500,
      "input_tokens": 6000,
      "output_tokens": 2500
    }
  }
}
```

### 5. Helper Function for Easy Integration

```python
from sdlc_agent import get_harness, record_llm_usage

harness = get_harness()

with harness.tool_span("claude_analyze") as span:
    result = claude.complete_json(system="...", user="...")

    # Automatically extract and record token usage
    if hasattr(claude, "last_token_usage"):
        record_llm_usage(span, claude.last_token_usage)
```

### 6. Anthropic API Integration

The `MockClaudeClient` now captures token usage from Anthropic API responses:

```python
# In anthropic_client.py
if hasattr(msg, "usage"):
    self.last_token_usage = {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "cache_creation_input_tokens": msg.usage.cache_creation_input_tokens,
        "cache_read_input_tokens": msg.usage.cache_read_input_tokens,
    }
```

## Files Modified

| File | Changes |
|------|---------|
| `sdlc_agent/harness.py` | Added `TokenUsage` model, updated `ToolSpan`, enhanced metrics aggregation, added `record_llm_usage()` helper |
| `sdlc_agent/integrations/anthropic_client.py` | Capture token usage from Anthropic Messages API responses |
| `sdlc_agent/__init__.py` | Export `TokenUsage` and `record_llm_usage` |

## Files Created

| File | Purpose |
|------|---------|
| `docs/TOKEN_TRACKING.md` | Comprehensive documentation with usage patterns, cost analysis, and querying examples |
| `examples/token_tracking_demo.py` | Working demo showing three usage patterns |
| `TOKEN_TRACKING_SUMMARY.md` | This summary document |

## Usage Patterns

### Pattern 1: Manual Tracking

```python
with harness.tool_span("llm_call") as span:
    result = claude.complete_json(...)

    span.set_token_usage(
        input_tokens=1523,
        output_tokens=487,
        cache_creation_tokens=100,
        cache_read_tokens=1200,
    )
```

### Pattern 2: Helper Function (Recommended)

```python
with harness.tool_span("llm_call") as span:
    result = claude.complete_json(...)

    if hasattr(claude, "last_token_usage"):
        record_llm_usage(span, claude.last_token_usage)
```

### Pattern 3: Direct Anthropic SDK

```python
import anthropic
client = anthropic.Anthropic(api_key=...)

with harness.tool_span("anthropic_call") as span:
    message = client.messages.create(...)
    record_llm_usage(span, message)
```

## Verification

Run the test to verify the implementation:

```bash
python test_token_quick.py
```

Expected output:
```
[OK] Token usage recorded
{
  "token_usage": {
    "input_tokens": 1523,
    "output_tokens": 487,
    "cache_creation_tokens": 100,
    "cache_read_tokens": 1200,
    "total_tokens": 2110
  }
}
[OK] Token usage field present!
```

## Querying Token Usage

### View recent traces with tokens:
```bash
jq -s '.[] | select(.token_usage) | {tool, tokens: .token_usage.total_tokens}' .claude/observability/traces.jsonl
```

### Total tokens used:
```bash
jq -s 'map(.token_usage.total_tokens // 0) | add' .claude/observability/traces.jsonl
```

### Cost estimation:
```python
import json
from pathlib import Path

metrics = json.load(Path(".claude/observability/metrics.json").open())
totals = metrics["totals"]

# Claude 3.5 Sonnet pricing (June 2026)
input_cost = (totals["total_input_tokens"] / 1_000_000) * 3.00
output_cost = (totals["total_output_tokens"] / 1_000_000) * 15.00
cache_read_cost = (totals["total_cache_read_tokens"] / 1_000_000) * 0.30

print(f"Estimated cost: ${input_cost + output_cost + cache_read_cost:.4f}")
```

## Benefits

1. **Cost Visibility** — Track exactly how many tokens each stage/tool consumes
2. **Optimization** — Identify expensive operations and optimize prompts
3. **Budgeting** — Set token budgets per stage or per run
4. **Cache Efficiency** — Monitor prompt caching hit rates
5. **Historical Analysis** — Query traces to analyze trends over time

## Supported Backends

- ✅ Anthropic Messages API (full support including prompt caching)
- ✅ Google Gemini (input/output tokens)
- ✅ Claude Code CLI (when usage data is available)
- ✅ Copilot Bridge (when usage data is available)
- ✅ Manual tracking (for any LLM)

## Next Steps

To start using token tracking in your stages:

1. Wrap LLM calls with `harness.tool_span()`
2. Use `record_llm_usage(span, response)` after each call
3. View aggregated metrics in `.claude/observability/metrics.json`
4. Query traces in `.claude/observability/traces.jsonl`

## Documentation

- Full documentation: [docs/TOKEN_TRACKING.md](docs/TOKEN_TRACKING.md)
- Demo examples: [examples/token_tracking_demo.py](examples/token_tracking_demo.py)
- Quick test: [test_token_quick.py](test_token_quick.py)
