"""Integrated Claude Code harness for SDLC Agent.

Provides observability, state management, permissions, and lifecycle hooks
directly within the Python agent instead of relying on external JS hooks.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field


# ── Configuration ────────────────────────────────────────────────────────────


class HarnessConfig(BaseModel):
    """Harness configuration loaded from .claude/settings.json"""

    observability_dir: Path = Field(default=Path(".claude/observability"))
    state_file: Path = Field(default=Path(".claude/sdlc-state.json"))
    runs_dir: Path = Field(default=Path("./sdlc_agent_output/runs"))
    coverage_threshold: int = Field(default=80, ge=0, le=100)
    auto_advance_stages: bool = Field(default=False)
    enable_observability: bool = Field(default=True)
    enable_hooks: bool = Field(default=True)


# ── Observability Models ─────────────────────────────────────────────────────


class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class TokenUsage(BaseModel):
    """Token usage metrics for LLM calls"""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0


class ToolSpan(BaseModel):
    """Tool execution span for distributed tracing"""

    trace_id: str
    span_id: str
    tool: str
    stage: str | None = None
    persona: str | None = None
    input: str | None = None
    status: Literal["ok", "error"] = "ok"
    duration_ms: int | None = None
    token_usage: TokenUsage | None = None
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LogEntry(BaseModel):
    """Structured log entry"""

    level: Severity
    stage: str | None = None
    persona: str | None = None
    message: str
    tool: str | None = None
    snippet: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Metrics(BaseModel):
    """Aggregated pipeline metrics"""

    totals: dict[str, Any] = Field(default_factory=dict)
    by_stage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_tool: dict[str, dict[str, Any]] = Field(default_factory=dict)
    last_updated: str | None = None


# ── SDLC State ───────────────────────────────────────────────────────────────


class SDLCState(BaseModel):
    """Central SDLC pipeline state"""

    stage: str = "init"
    trace_id: str | None = None
    epic: dict[str, Any] | None = None
    current_card: str | None = None
    branch: str | None = None
    pr_url: str | None = None
    coverage_pct: float | None = None
    persona: str | None = None

    # Stage-specific data
    source: str | None = None
    stories: list[dict[str, Any]] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    nfr: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    answered_questions: list[str] = Field(default_factory=list)

    # Audit trail
    history: list[dict[str, Any]] = Field(default_factory=list)
    requirements_ingested: list[dict[str, Any]] = Field(default_factory=list)
    jira_creates: list[dict[str, Any]] = Field(default_factory=list)
    prs_created: list[dict[str, Any]] = Field(default_factory=list)
    test_generations: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Harness Core ─────────────────────────────────────────────────────────────


class Harness:
    """Claude Code harness integration for SDLC Agent"""

    PIPELINE_STAGES = [
        ("ingest", "Winston"),
        ("clarify", "Winston"),
        ("plan", "Priya"),
        ("breakdown", "Priya"),
        ("sprint", "Marcus"),
        ("build", "Amelia"),
        ("commit", "Amelia"),
        ("pr", "Amelia"),
        ("qa", "Quinn"),
        ("review", "Devon"),
        ("fix", "Devon"),
    ]

    def __init__(self, config: HarnessConfig | None = None, auto_register_hooks: bool = True):
        self.config = config or self._load_config()
        self._ensure_dirs()
        self.state = self._load_state()
        self.metrics = self._load_metrics()
        self._current_span: ToolSpan | None = None
        self._hooks: dict[str, list[Callable]] = {}
        self._hooks_registered = False

        # Auto-register default hooks on initialization
        if auto_register_hooks:
            self._auto_register_hooks()

    def _load_config(self) -> HarnessConfig:
        """Load config from .claude/settings.json"""
        settings_path = Path(".claude/settings.json")
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text())
                env = data.get("env", {})
                return HarnessConfig(
                    runs_dir=Path(env.get("SDLC_AGENT_RUNS_DIR", "./sdlc_agent_output/runs")),
                    coverage_threshold=int(env.get("COVERAGE_THRESHOLD", "80")),
                    auto_advance_stages=env.get("AUTO_ADVANCE_STAGES", "false").lower() == "true",
                    enable_observability=env.get("ENABLE_OBSERVABILITY", "true").lower() == "true",
                    enable_hooks=env.get("ENABLE_HOOKS", "true").lower() == "true",
                )
            except Exception:
                pass
        return HarnessConfig()

    def _ensure_dirs(self) -> None:
        """Create required directories"""
        self.config.observability_dir.mkdir(parents=True, exist_ok=True)
        self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.runs_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> SDLCState:
        """Load SDLC state from disk"""
        if self.config.state_file.exists():
            try:
                return SDLCState.model_validate_json(
                    self.config.state_file.read_text(encoding="utf-8")
                )
            except Exception:
                pass
        return SDLCState()

    def _save_state(self) -> None:
        """Persist SDLC state to disk"""
        self.config.state_file.write_text(
            self.state.model_dump_json(indent=2),
            encoding="utf-8"
        )

    def _load_metrics(self) -> Metrics:
        """Load metrics from disk"""
        metrics_path = self.config.observability_dir / "metrics.json"
        if metrics_path.exists():
            try:
                return Metrics.model_validate_json(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return Metrics()

    def _save_metrics(self) -> None:
        """Persist metrics to disk"""
        self.metrics.last_updated = datetime.now(timezone.utc).isoformat()
        metrics_path = self.config.observability_dir / "metrics.json"
        metrics_path.write_text(
            self.metrics.model_dump_json(indent=2),
            encoding="utf-8"
        )

    # ── Tracing ──────────────────────────────────────────────────────────────

    def _short_id(self) -> str:
        """Generate short unique ID"""
        import random
        import string
        ts = int(time.time() * 1000)
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        return f"{ts:x}{rand}"

    def get_or_create_trace_id(self) -> str:
        """Get or create trace ID for current pipeline session"""
        if not self.state.trace_id:
            self.state.trace_id = f"trace-{self._short_id()}"
            self._save_state()
        return self.state.trace_id

    def start_span(self, tool: str, input_data: str | None = None) -> ToolSpan:
        """Start a new tool execution span"""
        span = ToolSpan(
            trace_id=self.get_or_create_trace_id(),
            span_id=f"span-{self._short_id()}",
            tool=tool,
            stage=self.state.stage,
            persona=self.state.persona,
            input=input_data[:100] if input_data else None,
            token_usage=None,
        )
        self._current_span = span
        return span

    def end_span(
        self,
        status: Literal["ok", "error"] = "ok",
        duration_ms: int | None = None,
        token_usage: TokenUsage | None = None,
    ) -> None:
        """End the current span and write to traces.jsonl"""
        if not self._current_span:
            return

        self._current_span.status = status
        self._current_span.duration_ms = duration_ms
        if token_usage:
            self._current_span.token_usage = token_usage

        if self.config.enable_observability:
            traces_path = self.config.observability_dir / "traces.jsonl"
            with traces_path.open("a", encoding="utf-8") as f:
                f.write(self._current_span.model_dump_json() + "\n")

            # Update metrics
            self._update_metrics_for_span(self._current_span)

        self._current_span = None

    def _update_metrics_for_span(self, span: ToolSpan) -> None:
        """Update aggregated metrics from a completed span"""
        # Totals
        totals = self.metrics.totals
        totals["tool_calls"] = totals.get("tool_calls", 0) + 1
        if span.status == "error":
            totals["errors"] = totals.get("errors", 0) + 1
        if totals["tool_calls"] > 0:
            totals["error_rate_pct"] = round(100 * totals.get("errors", 0) / totals["tool_calls"], 2)

        # Token usage aggregation
        if span.token_usage:
            totals["total_input_tokens"] = totals.get("total_input_tokens", 0) + span.token_usage.input_tokens
            totals["total_output_tokens"] = totals.get("total_output_tokens", 0) + span.token_usage.output_tokens
            totals["total_cache_creation_tokens"] = totals.get("total_cache_creation_tokens", 0) + span.token_usage.cache_creation_tokens
            totals["total_cache_read_tokens"] = totals.get("total_cache_read_tokens", 0) + span.token_usage.cache_read_tokens
            totals["total_tokens"] = totals.get("total_tokens", 0) + span.token_usage.total_tokens

        # By stage
        if span.stage:
            stage_data = self.metrics.by_stage.setdefault(span.stage, {})
            stage_data["tool_calls"] = stage_data.get("tool_calls", 0) + 1
            if span.status == "error":
                stage_data["errors"] = stage_data.get("errors", 0) + 1
            if span.duration_ms:
                calls = stage_data["tool_calls"]
                avg = stage_data.get("avg_tool_duration_ms", 0)
                stage_data["avg_tool_duration_ms"] = round((avg * (calls - 1) + span.duration_ms) / calls, 2)
            if stage_data["tool_calls"] > 0:
                stage_data["error_rate_pct"] = round(
                    100 * stage_data.get("errors", 0) / stage_data["tool_calls"], 2
                )
            # Stage-level token aggregation
            if span.token_usage:
                stage_data["total_tokens"] = stage_data.get("total_tokens", 0) + span.token_usage.total_tokens
                stage_data["input_tokens"] = stage_data.get("input_tokens", 0) + span.token_usage.input_tokens
                stage_data["output_tokens"] = stage_data.get("output_tokens", 0) + span.token_usage.output_tokens

        # By tool
        tool_data = self.metrics.by_tool.setdefault(span.tool, {})
        tool_data["calls"] = tool_data.get("calls", 0) + 1
        if span.status == "error":
            tool_data["errors"] = tool_data.get("errors", 0) + 1
        if span.duration_ms:
            calls = tool_data["calls"]
            avg = tool_data.get("avg_duration_ms", 0)
            tool_data["avg_duration_ms"] = round((avg * (calls - 1) + span.duration_ms) / calls, 2)
        # Tool-level token aggregation
        if span.token_usage:
            tool_data["total_tokens"] = tool_data.get("total_tokens", 0) + span.token_usage.total_tokens
            tool_data["input_tokens"] = tool_data.get("input_tokens", 0) + span.token_usage.input_tokens
            tool_data["output_tokens"] = tool_data.get("output_tokens", 0) + span.token_usage.output_tokens

        self._save_metrics()

    # ── Logging ──────────────────────────────────────────────────────────────

    def log(
        self,
        level: Severity,
        message: str,
        tool: str | None = None,
        snippet: str | None = None
    ) -> None:
        """Write structured log entry"""
        entry = LogEntry(
            level=level,
            stage=self.state.stage,
            persona=self.state.persona,
            message=message,
            tool=tool,
            snippet=snippet[:150] if snippet else None,
            trace_id=self.state.trace_id,
            span_id=self._current_span.span_id if self._current_span else None,
        )

        if self.config.enable_observability:
            logs_path = self.config.observability_dir / "logs.jsonl"
            with logs_path.open("a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")

        # Also track errors in state
        if level == Severity.ERROR:
            self.state.errors.append({
                "stage": self.state.stage,
                "tool": tool,
                "message": message,
                "ts": entry.ts,
            })
            self._save_state()

    # ── Stage Management ─────────────────────────────────────────────────────

    def transition_to(self, stage: str, persona: str | None = None) -> None:
        """Transition to a new pipeline stage"""
        old_stage = self.state.stage
        self.state.stage = stage
        self.state.persona = persona or self._get_persona_for_stage(stage)

        # Record in history
        self.state.history.append({
            "stage": stage,
            "persona": self.state.persona,
            "card": self.state.current_card,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        self._save_state()
        self._trigger_hook("on_stage_transition", old_stage=old_stage, new_stage=stage)
        self.log(Severity.INFO, f"Stage transition: {old_stage} → {stage}")

    def _get_persona_for_stage(self, stage: str) -> str | None:
        """Get persona name for a stage"""
        for s, p in self.PIPELINE_STAGES:
            if s == stage:
                return p
        return None

    def can_advance_to(self, target_stage: str) -> tuple[bool, str | None]:
        """Check if pipeline can advance to target stage"""
        # Check coverage gate for commit/push stages
        if target_stage in ("commit", "pr") and self.state.coverage_pct is not None:
            if self.state.coverage_pct < self.config.coverage_threshold:
                return False, (
                    f"Coverage gate: {self.state.coverage_pct}% < {self.config.coverage_threshold}%"
                )

        return True, None

    # ── Hooks ────────────────────────────────────────────────────────────────

    def register_hook(self, event: str, callback: Callable) -> None:
        """Register a hook callback"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def _auto_register_hooks(self) -> None:
        """Auto-register default hooks on harness initialization"""
        if self._hooks_registered:
            return

        try:
            # Import here to avoid circular dependency
            from . import hooks as hooks_module
            hooks_module.register_default_hooks(self)
            self._hooks_registered = True
        except Exception as e:
            # Non-fatal - harness still works without hooks
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to auto-register hooks: {e}")

    def _trigger_hook(self, event: str, **kwargs) -> None:
        """Trigger all registered hooks for an event"""
        if not self.config.enable_hooks:
            return

        for callback in self._hooks.get(event, []):
            try:
                callback(harness=self, **kwargs)
            except Exception as e:
                self.log(Severity.ERROR, f"Hook {event} failed: {e}", tool="harness")

    # ── Status Display ───────────────────────────────────────────────────────

    def render_status(self) -> str:
        """Render SDLC pipeline status banner"""
        def badge(target: str) -> str:
            stages = [s for s, _ in self.PIPELINE_STAGES]
            try:
                ci = stages.index(self.state.stage)
                ca = stages.index(target)
            except ValueError:
                return "⬜"

            if ca < ci:
                return "✅"
            elif ca == ci:
                return "⏳"
            return "⬜"

        sep = "─" * 52
        lines = [
            sep,
            f"  SDLC · {self.state.epic.get('summary') if self.state.epic else 'No active session'}",
            sep,
            f"  {badge('ingest')} ingest  {badge('clarify')} clarify",
            f"  {badge('plan')} plan    {badge('breakdown')} breakdown  {badge('sprint')} sprint",
            f"  {badge('build')} build   {badge('commit')} commit     {badge('pr')} pr",
            f"  {badge('qa')} qa      {badge('review')} review     {badge('fix')} fix",
            sep,
        ]

        if self.state.current_card:
            lines.append(f"  Card:   {self.state.current_card}")
        if self.state.branch:
            lines.append(f"  Branch: {self.state.branch}")
        if self.state.pr_url:
            lines.append(f"  PR:     {self.state.pr_url}")

        stage_errors = [e for e in self.state.errors if e.get("stage") == self.state.stage]
        if stage_errors:
            last = stage_errors[-1]
            lines.append(f"  Errors: {len(stage_errors)} this stage (last: {last.get('tool', 'unknown')})")

        lines.append(sep)
        return "\n".join(lines)

    # ── Context Manager ──────────────────────────────────────────────────────

    def tool_span(self, tool: str, input_data: str | None = None):
        """Context manager for automatic span tracking"""
        class SpanContext:
            def __init__(self, harness: Harness, tool: str, input_data: str | None):
                self.harness = harness
                self.tool = tool
                self.input_data = input_data
                self.start_time = 0
                self.token_usage: TokenUsage | None = None

            def __enter__(self):
                self.start_time = time.perf_counter_ns()
                self.harness.start_span(self.tool, self.input_data)
                return self

            def set_token_usage(
                self,
                input_tokens: int = 0,
                output_tokens: int = 0,
                cache_creation_tokens: int = 0,
                cache_read_tokens: int = 0,
            ) -> None:
                """Set token usage for this span"""
                self.token_usage = TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_read_tokens=cache_read_tokens,
                    total_tokens=input_tokens + output_tokens + cache_creation_tokens,
                )

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration_ms = int((time.perf_counter_ns() - self.start_time) / 1_000_000)
                status = "error" if exc_type else "ok"
                self.harness.end_span(status, duration_ms, self.token_usage)
                if exc_type:
                    self.harness.log(
                        Severity.ERROR,
                        f"{self.tool} failed: {exc_val}",
                        tool=self.tool,
                        snippet=str(exc_val)[:150],
                    )
                return False

        return SpanContext(self, tool, input_data)


# ── Global Instance ──────────────────────────────────────────────────────────

_harness: Harness | None = None


def get_harness() -> Harness:
    """Get or create global harness instance"""
    global _harness
    if _harness is None:
        _harness = Harness()
    return _harness


def reset_harness() -> None:
    """Reset global harness (useful for testing)"""
    global _harness
    _harness = None


# ── Utility Functions ────────────────────────────────────────────────────────


def record_llm_usage(
    span_context: Any,
    response: Any,
) -> None:
    """Extract and record token usage from an LLM API response.

    Args:
        span_context: The SpanContext from harness.tool_span()
        response: The API response object with usage data
    """
    if not hasattr(span_context, "set_token_usage"):
        return

    # Handle Anthropic Messages API response
    if hasattr(response, "usage"):
        usage = response.usage
        span_context.set_token_usage(
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0),
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
        )
    # Handle dict-based usage (from ClaudeClient.last_token_usage)
    elif isinstance(response, dict) and "input_tokens" in response:
        span_context.set_token_usage(
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
            cache_creation_tokens=response.get("cache_creation_input_tokens", 0),
            cache_read_tokens=response.get("cache_read_input_tokens", 0),
        )
