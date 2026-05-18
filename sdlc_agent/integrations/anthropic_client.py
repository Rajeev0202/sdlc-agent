"""Claude / Anthropic client.

Three modes, picked at construction time:

1. **Copilot bridge** — if `SDLC_COPILOT_BRIDGE_URL` is set (or the default
   `http://127.0.0.1:6789` responds to `/health`), requests are POSTed to
   the local VS Code extension which calls GitHub Copilot via the VS Code
   Language Model API. No API key needed.
2. **Live Anthropic** — if `ANTHROPIC_API_KEY` is set AND the `anthropic`
   SDK is installed, calls hit the Messages API.
3. **Stub** — deterministic offline mode (default).

Class name `MockClaudeClient` is preserved for backwards compatibility.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class MockClaudeClient:
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"
    DEFAULT_BRIDGE_URL = "http://127.0.0.1:6789"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL") or self.DEFAULT_MODEL
        self.calls: list[dict[str, Any]] = []
        self._client = None
        self._bridge_url: str | None = None

        # Mode 1: Copilot bridge (preferred when reachable).
        candidate = os.getenv("SDLC_COPILOT_BRIDGE_URL", self.DEFAULT_BRIDGE_URL).rstrip("/")
        if _bridge_alive(candidate):
            self._bridge_url = candidate
            logger.info("Copilot bridge detected at %s", candidate)
            return

        # Mode 2: direct Anthropic API.
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
        return self._bridge_url is not None or self._client is not None

    @property
    def backend(self) -> str:
        if self._bridge_url:
            return f"copilot-bridge ({self._bridge_url})"
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
        return _extract_json(text)


def _bridge_alive(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=timeout) as r:
            if r.status != 200:
                return False
            data = json.loads(r.read().decode("utf-8"))
            return bool(data.get("ok"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False


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
