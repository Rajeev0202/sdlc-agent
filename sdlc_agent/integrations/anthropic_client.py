"""Claude / Anthropic client.

Three modes, picked at construction time (in priority order):

1. **Claude Code CLI** — if `claude` CLI is available, invoke it as a
   subprocess. Uses your Claude Code subscription. No API key needed.
   (Preferred for local development)
2. **Live Anthropic API** — if `ANTHROPIC_API_KEY` is set AND the `anthropic`
   SDK is installed, calls hit the Messages API directly.
   (For production/automation)
3. **Stub** — deterministic offline mode (default fallback).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .llm_cache import get_cache

logger = logging.getLogger(__name__)


def _make_cache_key(system: str, user: str, model: str = "default") -> str:
    """Build a deterministic cache key — delegates to LLMCache.make_key."""
    return get_cache().make_key(system, user, model)


def get_cache_stats() -> dict[str, Any]:
    """Return cache stats from the active backend (Redis or memory)."""
    return get_cache().stats()


# Known locations where claude.exe may live on Windows
_CLAUDE_CLI_HINTS = [
    "claude",  # PATH
    str(Path.home() / ".local" / "bin" / "claude.exe"),
    str(Path.home() / ".local" / "bin" / "claude"),
    str(Path.home() / ".vscode" / "extensions"),  # walked below
]


def _find_claude_cli() -> str | None:
    """Locate the claude CLI executable on this system."""
    # 1. PATH lookup
    found = shutil.which("claude")
    if found:
        return found

    # 2. Common install location
    local_bin = Path.home() / ".local" / "bin"
    for name in ("claude.exe", "claude"):
        candidate = local_bin / name
        if candidate.exists():
            return str(candidate)

    # 3. VS Code extension bundle (Windows)
    ext_root = Path.home() / ".vscode" / "extensions"
    if ext_root.exists():
        for ext_dir in ext_root.glob("anthropic.claude-code-*"):
            for sub in ("resources/native-binary/claude.exe", "resources/native-binary/claude"):
                candidate = ext_dir / sub
                if candidate.exists():
                    return str(candidate)

    # 4. Environment override
    env_path = os.getenv("CLAUDE_CLI_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    return None


class ClaudeClient:
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL") or self.DEFAULT_MODEL
        self.calls: list[dict[str, Any]] = []
        self._client = None
        self._claude_cli: str | None = None

        # Mode 1: Claude Code CLI (uses subscription, no API key needed)
        # Skip if user explicitly opts out
        if os.getenv("SDLC_DISABLE_CLAUDE_CLI", "").lower() not in ("1", "true", "yes"):
            cli_path = _find_claude_cli()
            if cli_path:
                self._claude_cli = cli_path
                logger.info("Claude Code CLI detected at %s", cli_path)
                return

        # Mode 2: Anthropic API (fallback)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude live client initialised (model=%s).", self.model)
            except Exception as exc:  # pragma: no cover - depends on env
                logger.warning("Falling back to stub mode: %s", exc)
                self._client = None

    @property
    def is_live(self) -> bool:
        """True if any real LLM backend is configured."""
        return self._claude_cli is not None or self._client is not None

    @property
    def backend(self) -> str:
        if self._claude_cli:
            return f"claude-code-cli ({self._claude_cli})"
        if self._client:
            return f"anthropic ({self.model})"
        return "stub"

    def complete(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Record the call and return a stage-appropriate stub."""
        self.calls.append({"task": task, "payload": payload})
        return {"task": task, "model": self.model, "ok": True, "text": ""}

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        """Call the LLM expecting a JSON response. Returns parsed JSON or None.

        Also populates self.last_token_usage if available from the API.
        """
        text: str | None = None
        self.last_token_usage: dict[str, int] | None = None

        if self._claude_cli is not None:
            # 90s timeout per call - fail fast to avoid 10-min stalls
            text = _claude_cli_complete(
                self._claude_cli, system=system, user=user, timeout=90.0
            )
            if text is not None:
                self.calls.append({"task": "complete_json", "backend": "claude-code-cli"})
        elif self._client is not None:
            # Result cache (Redis or in-memory): avoid re-calling LLM with identical prompts
            cache = get_cache()
            cache_key = cache.make_key(system, user, self.model)
            cached_text = cache.get(cache_key)
            if cached_text is not None:
                logger.info(
                    f"[Cost Save] LLM cache HIT ({cache.stats()['backend']}) for {self.model} "
                    f"(saved ~{(len(system) + len(user)) // 4} tokens)"
                )
                text = cached_text
                self.calls.append({"task": "complete_json", "backend": f"anthropic-cached-{cache.stats()['backend']}"})
            else:
                try:
                    # Prompt caching: mark system prompt for ephemeral 5-min cache.
                    # Reduces input token cost by ~90% on repeated calls with same system.
                    msg = self._client.messages.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=[
                            {
                                "type": "text",
                                "text": system,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                        messages=[{"role": "user", "content": user}],
                    )
                    text = "".join(getattr(b, "text", "") for b in msg.content).strip()

                    # Capture token usage and log prompt-cache stats from the response.
                    if hasattr(msg, "usage") and msg.usage:
                        usage = msg.usage
                        self.last_token_usage = {
                            "input_tokens": getattr(usage, "input_tokens", 0),
                            "output_tokens": getattr(usage, "output_tokens", 0),
                            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                        }
                        cache_read = self.last_token_usage["cache_read_input_tokens"] or 0
                        cache_write = self.last_token_usage["cache_creation_input_tokens"] or 0
                        if cache_read or cache_write:
                            logger.info(
                                "[Prompt Cache] read=%s write=%s tokens", cache_read, cache_write
                            )

                    if text:
                        cache.set(cache_key, text)
                    self.calls.append({"task": "complete_json", "backend": "anthropic"})
                except Exception as exc:  # pragma: no cover - network/SDK errors
                    logger.warning("Claude live call failed, falling back: %s", exc)
                    text = None

        if text is None:
            return None

        extracted = _extract_json(text)
        logger.debug("JSON extraction: input_len=%s extracted=%s", len(text), extracted is not None)
        return extracted


def _claude_cli_complete(
    cli_path: str, *, system: str, user: str, timeout: float = 180.0
) -> str | None:
    """Invoke the claude CLI as a subprocess to use the Claude Code subscription.

    Uses `claude -p <prompt>` in print mode (non-interactive) and reads stdout.
    Combines system and user prompts since the CLI takes a single prompt argument.
    """
    # Combine system + user prompts; claude CLI takes a single prompt
    full_prompt = f"{system}\n\n---\n\n{user}"

    try:
        # Use --output-format text (default) to get plain response
        # --no-color to strip ANSI codes
        result = subprocess.run(
            [cli_path, "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            logger.warning(
                "Claude CLI returned non-zero exit %d: %s",
                result.returncode,
                (result.stderr or "")[:500],
            )
            return None

        output = (result.stdout or "").strip()
        if not output:
            logger.warning("Claude CLI returned empty output")
            return None

        return output

    except subprocess.TimeoutExpired:
        logger.warning("Claude CLI timed out after %s seconds", timeout)
        return None
    except (OSError, FileNotFoundError) as exc:
        logger.warning("Claude CLI invocation failed: %s", exc)
        return None


def _extract_json(text: str) -> dict[str, Any] | list[Any] | None:
    """Best-effort JSON extraction from a chat response."""
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if "\n" in stripped:
            first, rest = stripped.split("\n", 1)
            if first.strip().lower() in {"json", "javascript", ""}:
                stripped = rest
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = stripped.find(open_ch)
            end = stripped.rfind(close_ch)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(stripped[start : end + 1])
                except json.JSONDecodeError:
                    continue
        return None
