"""Claude / Anthropic / Gemini client.

Five modes, picked at construction time:

1. **Copilot bridge** — if `SDLC_COPILOT_BRIDGE_URL` is set (or the default
   `http://127.0.0.1:6789` responds to `/health`), requests are POSTed to
   the local VS Code extension which calls GitHub Copilot via the VS Code
   Language Model API. No API key needed.
2. **Claude Code CLI** — if `claude` CLI is available, invoke it as a
   subprocess. Uses your Claude Code subscription. No API key needed.
3. **Google Gemini** — if `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set AND the
   `google-generativeai` SDK is installed, calls hit the Gemini API.
4. **Live Anthropic** — if `ANTHROPIC_API_KEY` is set AND the `anthropic`
   SDK is installed, calls hit the Messages API.
5. **Stub** — deterministic offline mode (default).

Class name `MockClaudeClient` is preserved for backwards compatibility.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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


class MockClaudeClient:
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"
    DEFAULT_BRIDGE_URL = "http://127.0.0.1:6789"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL") or self.DEFAULT_MODEL
        self.calls: list[dict[str, Any]] = []
        self._client = None
        self._gemini_model = None
        self._bridge_url: str | None = None
        self._claude_cli: str | None = None

        # Debug: Check environment variables
        google_key_check = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        print(f"[MockClaudeClient.__init__] GOOGLE_API_KEY present: {bool(google_key_check)}", file=sys.stderr, flush=True)

        # Mode 1: Copilot bridge (preferred when reachable).
        candidate = os.getenv("SDLC_COPILOT_BRIDGE_URL", self.DEFAULT_BRIDGE_URL).rstrip("/")
        if _bridge_alive(candidate):
            self._bridge_url = candidate
            logger.info("Copilot bridge detected at %s", candidate)
            print(f"[MockClaudeClient] Using Copilot bridge at {candidate}", file=sys.stderr, flush=True)
            return

        # Mode 2: Claude Code CLI (uses subscription, no API key needed)
        # Skip if user explicitly opts out
        if os.getenv("SDLC_DISABLE_CLAUDE_CLI", "").lower() not in ("1", "true", "yes"):
            cli_path = _find_claude_cli()
            if cli_path:
                self._claude_cli = cli_path
                logger.info("Claude Code CLI detected at %s", cli_path)
                print(f"[MockClaudeClient] Using Claude Code CLI: {cli_path}", file=sys.stderr, flush=True)
                return

        # Mode 3: Google Gemini API.
        google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if google_key:
            try:
                print(f"[MockClaudeClient] Attempting Gemini init with key: {google_key[:10]}...", file=sys.stderr, flush=True)
                from google import genai  # type: ignore
                from google.genai import types  # type: ignore

                client = genai.Client(api_key=google_key)
                self._gemini_model = client
                logger.info("Gemini client initialized (model=gemini-1.5-flash).")
                print(f"[MockClaudeClient] SUCCESS - Gemini initialized!", file=sys.stderr, flush=True)
                return
            except Exception as exc:  # pragma: no cover - depends on env
                print(f"[MockClaudeClient] FAILED - Gemini error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                logger.warning("Failed to initialize Gemini, trying Anthropic: %s", exc)
                self._gemini_model = None

        # Mode 4: direct Anthropic API.
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude live client initialised (model=%s).", self.model)
            except Exception as exc:  # pragma: no cover - depends on env
                logger.warning("Falling back to mock Claude client: %s", exc)
                self._client = None

    @property
    def is_live(self) -> bool:
        """True if any real LLM backend is configured."""
        return (
            self._bridge_url is not None
            or self._claude_cli is not None
            or self._gemini_model is not None
            or self._client is not None
        )

    @property
    def backend(self) -> str:
        if self._bridge_url:
            return f"copilot-bridge ({self._bridge_url})"
        if self._claude_cli:
            return f"claude-code-cli ({self._claude_cli})"
        if self._gemini_model:
            return "gemini (gemini-1.5-flash)"
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
        """Call the LLM expecting a JSON response. Returns parsed JSON or None."""
        text: str | None = None

        if self._bridge_url:
            text = _bridge_complete(self._bridge_url, system=system, user=user)
            if text is not None:
                self.calls.append({"task": "complete_json", "backend": "copilot-bridge"})
        elif self._claude_cli is not None:
            # 90s timeout per call - fail fast to avoid 10-min stalls
            text = _claude_cli_complete(
                self._claude_cli, system=system, user=user, timeout=90.0
            )
            if text is not None:
                self.calls.append({"task": "complete_json", "backend": "claude-code-cli"})
        elif self._gemini_model is not None:
            # Debug: Log that we're attempting Gemini call
            from pathlib import Path
            import datetime
            debug_file = Path(__file__).resolve().parents[2] / "gemini_debug.log"
            with open(debug_file, "a") as f:
                f.write(f"\n[{datetime.datetime.now()}] Attempting Gemini call\n")
                f.write(f"  Prompt length: {len(system) + len(user)}\n")

            try:
                # Combine system and user prompts for Gemini
                prompt = f"{system}\n\n{user}"

                with open(debug_file, "a") as f:
                    f.write(f"  Calling generate_content...\n")

                response = self._gemini_model.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                )

                with open(debug_file, "a") as f:
                    f.write(f"  Got response object\n")

                text = response.text.strip()

                with open(debug_file, "a") as f:
                    f.write(f"  Response length: {len(text)}\n")
                    f.write(f"  Response preview: {text[:300]}\n")

                self.calls.append({"task": "complete_json", "backend": "gemini"})
            except Exception as exc:  # pragma: no cover - network/SDK errors
                logger.warning("Gemini call failed, falling back: %s", exc)
                with open(debug_file, "a") as f:
                    import traceback
                    f.write(f"  EXCEPTION: {exc}\n")
                    f.write(f"  Traceback: {traceback.format_exc()}\n")
                text = None
        elif self._client is not None:
            try:
                msg = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(getattr(b, "text", "") for b in msg.content).strip()
                self.calls.append({"task": "complete_json", "backend": "anthropic"})
            except Exception as exc:  # pragma: no cover - network/SDK errors
                logger.warning("Claude live call failed, falling back: %s", exc)
                text = None

        if text is None:
            return None

        # Debug: Log JSON extraction
        from pathlib import Path
        debug_file = Path(__file__).resolve().parents[2] / "gemini_debug.log"
        extracted = _extract_json(text)
        with open(debug_file, "a") as f:
            import datetime
            f.write(f"\n[{datetime.datetime.now()}] JSON Extraction\n")
            f.write(f"  Input text length: {len(text) if text else 0}\n")
            f.write(f"  Input preview: {text[:200] if text else 'None'}\n")
            f.write(f"  Extracted result: {extracted}\n")

        return extracted


def _bridge_alive(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=timeout) as r:
            if r.status != 200:
                return False
            data = json.loads(r.read().decode("utf-8"))
            return bool(data.get("ok"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False


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


def _bridge_complete(
    url: str, *, system: str, user: str, timeout: float = 120.0
) -> str | None:
    body = json.dumps({"system": system, "user": user}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/complete",
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
        if not payload.get("ok"):
            logger.warning("Copilot bridge error: %s", payload.get("error"))
            return None
        return str(payload.get("text") or "")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        logger.warning("Copilot bridge call failed: %s", exc)
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
