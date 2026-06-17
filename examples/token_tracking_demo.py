#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo: Token usage tracking in traces.jsonl

Shows how to capture and record token usage from LLM API calls in the
observability traces.
"""
import sys
import io

# Force UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from sdlc_agent import get_harness, record_llm_usage
from sdlc_agent.integrations import MockClaudeClient


def example_1_manual_tracking():
    """Example 1: Manually set token usage in a span"""
    harness = get_harness()
    claude = MockClaudeClient()

    # Start a traced operation
    with harness.tool_span("claude_complete", input_data="Generate user stories") as span:
        # Make the LLM call
        result = claude.complete_json(
            system="You are a requirements analyst",
            user="Extract user stories from: [BRD text here]",
            max_tokens=2000,
        )

        # If the client captured token usage, record it
        if hasattr(claude, "last_token_usage") and claude.last_token_usage:
            usage = claude.last_token_usage
            span.set_token_usage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            )

    print("✅ Token usage recorded in .claude/observability/traces.jsonl")


def example_2_helper_function():
    """Example 2: Use the helper function for cleaner code"""
    harness = get_harness()
    claude = MockClaudeClient()

    with harness.tool_span("claude_code_review", input_data="Review PR #123") as span:
        result = claude.complete_json(
            system="You are a code reviewer",
            user="Review this code: [diff here]",
            max_tokens=3000,
        )

        # Helper extracts usage from the client
        if hasattr(claude, "last_token_usage"):
            record_llm_usage(span, claude.last_token_usage)

    print("✅ Token usage recorded via helper function")


def example_3_anthropic_sdk():
    """Example 3: Direct Anthropic SDK usage (when ANTHROPIC_API_KEY is set)"""
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⏩ Skipping - ANTHROPIC_API_KEY not set")
        return

    try:
        import anthropic
    except ImportError:
        print("⏩ Skipping - anthropic SDK not installed")
        return

    harness = get_harness()
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    with harness.tool_span("anthropic_messages", input_data="Analyze requirements") as span:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "What are the key features of Python?"}
            ],
        )

        # Record usage from the message response
        record_llm_usage(span, message)

    print("✅ Anthropic API token usage recorded")
    print(f"   Input tokens: {message.usage.input_tokens}")
    print(f"   Output tokens: {message.usage.output_tokens}")


def view_traces():
    """View the last few traces with token usage"""
    from pathlib import Path
    import json

    traces_file = Path(".claude/observability/traces.jsonl")
    if not traces_file.exists():
        print("No traces file found yet")
        return

    print("\n📊 Recent traces with token usage:")
    print("=" * 80)

    with open(traces_file) as f:
        lines = f.readlines()
        # Show last 5 traces
        for line in lines[-5:]:
            trace = json.loads(line)
            if trace.get("token_usage"):
                usage = trace["token_usage"]
                print(f"\n🔧 {trace['tool']} ({trace['status']})")
                print(f"   Duration: {trace.get('duration_ms', 0)}ms")
                print(f"   Tokens: {usage['total_tokens']} total")
                print(f"     - Input: {usage['input_tokens']}")
                print(f"     - Output: {usage['output_tokens']}")
                if usage.get('cache_read_tokens', 0) > 0:
                    print(f"     - Cache read: {usage['cache_read_tokens']}")
                if usage.get('cache_creation_tokens', 0) > 0:
                    print(f"     - Cache creation: {usage['cache_creation_tokens']}")


def view_metrics():
    """View aggregated token metrics"""
    from pathlib import Path
    import json

    metrics_file = Path(".claude/observability/metrics.json")
    if not metrics_file.exists():
        print("No metrics file found yet")
        return

    with open(metrics_file) as f:
        metrics = json.load(f)

    print("\n📈 Token Usage Metrics:")
    print("=" * 80)

    totals = metrics.get("totals", {})
    if totals.get("total_tokens"):
        print(f"\n🌍 Total across all stages:")
        print(f"   Total tokens: {totals['total_tokens']:,}")
        print(f"   Input tokens: {totals.get('total_input_tokens', 0):,}")
        print(f"   Output tokens: {totals.get('total_output_tokens', 0):,}")

    by_stage = metrics.get("by_stage", {})
    if by_stage:
        print(f"\n📊 By Stage:")
        for stage, data in by_stage.items():
            if data.get("total_tokens"):
                print(f"   {stage}: {data['total_tokens']:,} tokens")

    by_tool = metrics.get("by_tool", {})
    if by_tool:
        print(f"\n🔧 By Tool:")
        for tool, data in sorted(by_tool.items(), key=lambda x: x[1].get("total_tokens", 0), reverse=True):
            if data.get("total_tokens"):
                print(f"   {tool}: {data['total_tokens']:,} tokens")


if __name__ == "__main__":
    print("🚀 Token Usage Tracking Demo\n")

    print("Example 1: Manual token tracking")
    example_1_manual_tracking()

    print("\nExample 2: Using helper function")
    example_2_helper_function()

    print("\nExample 3: Anthropic SDK")
    example_3_anthropic_sdk()

    # View results
    view_traces()
    view_metrics()

    print("\n✨ Demo complete!")
    print("\n💡 Tips:")
    print("   - Token usage is automatically aggregated in metrics.json")
    print("   - Each trace in traces.jsonl includes token_usage if available")
    print("   - Use record_llm_usage() helper to extract from API responses")
    print("   - Supports Anthropic API, Gemini, and Claude Code CLI")
