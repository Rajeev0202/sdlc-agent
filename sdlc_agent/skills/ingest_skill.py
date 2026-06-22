"""
Automated implementation of /sdlc-ingest skill for UI integration.

This module implements the logic from .claude/skills/sdlc-ingest/SKILL.md
so the UI can automate the skill without requiring manual Claude Code invocation.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IngestSkillAutomation:
    """Automates the /sdlc-ingest skill logic with LLM-powered extraction."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.state_file = root_dir / ".claude" / "sdlc-state.json"
        # Lazy-load LLM client (only when needed)
        self._llm = None

    @property
    def llm(self):
        """Lazy-loaded LLM client."""
        if self._llm is None:
            from ..integrations.anthropic_client import MockClaudeClient
            self._llm = MockClaudeClient()
        return self._llm

    def run(self, source: str) -> dict[str, Any]:
        """
        Execute the /sdlc-ingest skill logic.

        Args:
            source: Confluence URL, file path, or search query

        Returns:
            dict with parsed requirements and state
        """
        # Step 1: Fetch the requirements
        content = self._fetch_requirements(source)

        # Step 2: Parse and structure
        parsed = self._parse_requirements(content, source)

        # Step 3: Identify gaps & ambiguities
        questions = self._identify_gaps(parsed)
        parsed["open_questions"] = questions

        # Step 4: Save state (skip user confirmation for UI automation)
        state = self._create_state(source, parsed)
        self._save_state(state)

        return state

    def _fetch_requirements(self, source: str) -> str:
        """Fetch requirements from source (URL or file).

        For Confluence URLs, tries MCP server first, falls back to REST API.
        """
        # Detect source type
        print('Fetch Requirenments')
        if source.startswith("http://") or source.startswith("https://"):
            # URL handling
            if "confluence" in source.lower() or "atlassian" in source.lower():
                # Try MCP server first, fall back to REST API
                content = self._fetch_confluence_via_mcp_or_rest(source)
                print('content', content)
                if content:
                    return content
                raise ValueError(
                    f"Failed to fetch Confluence page from {source}\n\n"
                    "Tried both MCP server and REST API. Please ensure:\n"
                    "1. MCP server is configured in .claude.json, OR\n"
                    "2. Environment variables are set:\n"
                    "   - CONFLUENCE_API_TOKEN (or ATLASSIAN_TOKEN)\n"
                    "   - CONFLUENCE_EMAIL (or ATLASSIAN_EMAIL) for Confluence Cloud"
                )
            else:
                # Generic URL
                raise NotImplementedError("Only Confluence URLs are supported. For other URLs, please download the file locally.")

        # Local file path
        source_path = Path(source)
        if not source_path.exists():
            # Try relative to root
            source_path = self.root_dir / source
            if not source_path.exists():
                raise FileNotFoundError(f"Requirements file not found: {source}")

        # Read file based on extension
        if source_path.suffix == ".md":
            return source_path.read_text(encoding="utf-8")
        elif source_path.suffix == ".txt":
            return source_path.read_text(encoding="utf-8")
        elif source_path.suffix in [".docx", ".pdf"]:
            # TODO: Add document parsing support
            raise NotImplementedError(f"Support for {source_path.suffix} files not yet implemented")
        else:
            # Assume text file
            return source_path.read_text(encoding="utf-8")

    def _fetch_confluence_via_mcp_or_rest(self, page_url: str) -> str | None:
        """Fetch Confluence page via MCP server (preferred) or REST API (fallback).

        Returns:
            Page content as markdown, or None if both methods fail
        """
        # Strategy 1: Try MCP server (if configured)
        # Note: MCP tools are dynamically loaded, so we can't detect them at import time
        # For now, skip MCP and go straight to REST API
        # TODO: When MCP server is configured, add MCP fetch logic here

        # Strategy 2: Fall back to REST API
        try:
            from ..integrations import fetch_confluence_page
            content = fetch_confluence_page(page_url)
            print(f"[Ingest] Fetched Confluence page via REST API ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"[Ingest] REST API fetch failed: {e}")
            return None

    def _parse_requirements(self, content: str, source: str) -> dict[str, Any]:
        """
        Parse requirements from document content.

        Strategy (smart and adaptive):
        1. Try regex extraction first - if BRD already has formal user stories, use them as-is
        2. If no formal stories found OR stories are incomplete, use LLM to convert prose/bullets
        3. Always extract AC, NFR, out-of-scope via regex (these are typically well-structured)
        """
        # Clean content: strip markdown bold/italic that breaks regex matching
        cleaned = self._clean_markdown(content)
        lines = cleaned.split("\n")

        # Debug: log what we received (visible in server console)
        print(f"[Ingest Parser] Content length: {len(content)} chars, {len(lines)} lines")
        print(f"[Ingest Parser] First 500 chars: {cleaned[:500]}")

        # Initialize result
        result = {
            "epic": "",
            "stories": [],
            "acceptance_criteria": [],
            "nfr": [],
            "out_of_scope": [],
            "dependencies": [],
        }

        # Extract title/epic (first heading)
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                result["epic"] = line.lstrip("#").strip()
                break

        # STEP 1: Extract user stories using regex (if they exist in formal format)
        # Support multiple formats:
        #   "As a X, I want Y, so that Z"
        #   "As a X I want Y so that Z" (no commas)
        #   Multi-line stories with line breaks
        story_patterns = [
            # Standard with optional commas, single line or with line breaks (DOTALL)
            r"(?is)\bas\s+a[n]?\s+(.+?)[,\n]\s*i\s+want\s+(?:to\s+)?(.+?)[,\n]\s*so\s+that\s+(.+?)(?=\.\s|\n\s*\n|\n#|\n-|\n\*|$)",
        ]

        for pattern in story_patterns:
            for match in re.finditer(pattern, cleaned):
                story = {
                    "as_a": self._cleanup_text(match.group(1)),
                    "i_want": self._cleanup_text(match.group(2)),
                    "so_that": self._cleanup_text(match.group(3)),
                }
                # Avoid duplicates
                if not any(s["i_want"] == story["i_want"] for s in result["stories"]):
                    result["stories"].append(story)

        print(f"[Ingest Parser] Regex found {len(result['stories'])} formal user stories")

        # DECISION POINT: Use LLM only if no formal stories found
        if len(result["stories"]) == 0 and self.llm.is_live and len(cleaned.strip()) > 50:
            print(f"[Ingest Parser] No formal stories found - using LLM to convert dynamic requirements via {self.llm.backend}")
            llm_result = self._llm_extract(cleaned)
            if llm_result and llm_result.get("stories"):
                print(f"[Ingest Parser] LLM extracted {len(llm_result['stories'])} stories from informal requirements")
                # Merge LLM results (stories + other sections)
                result["epic"] = llm_result.get("epic", result["epic"])
                result["stories"] = llm_result.get("stories", [])
                result["acceptance_criteria"] = llm_result.get("acceptance_criteria", [])
                result["nfr"] = llm_result.get("nfr", [])
                result["out_of_scope"] = llm_result.get("out_of_scope", [])
                result["dependencies"] = llm_result.get("dependencies", [])
                return result  # Return early - LLM handled everything
            print(f"[Ingest Parser] LLM extraction failed - continuing with regex-based parsing")

        # Extract acceptance criteria (Given/When/Then or bullet points)
        in_ac_section = False
        current_criteria = []

        for line in lines:
            stripped = line.strip()

            # Check for AC section headers (including markdown like "## Acceptance Criteria")
            if re.search(r"(?i)acceptance\s+criteria|definition\s+of\s+done", stripped):
                in_ac_section = True
                continue

            # Check for section end (next heading)
            if stripped.startswith("#") and in_ac_section:
                in_ac_section = False
                continue

            # Collect AC items
            if in_ac_section and stripped:
                if stripped.startswith("-") or stripped.startswith("*"):
                    ac = stripped.lstrip("-*").strip()
                    if ac:
                        current_criteria.append(ac)
                elif re.match(r"(?i)^(given|when|then)\s", stripped):
                    current_criteria.append(stripped)
                elif re.match(r"^\d+\.\s", stripped):  # numbered list "1. xxx"
                    current_criteria.append(re.sub(r"^\d+\.\s", "", stripped))

        result["acceptance_criteria"] = current_criteria
        print(f"[Ingest Parser] Found {len(current_criteria)} acceptance criteria")

        # Extract NFRs
        nfr_keywords = ["performance", "security", "accessibility", "scalability", "availability"]
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in nfr_keywords):
                stripped = line.strip()
                if stripped.startswith("-") or stripped.startswith("*"):
                    result["nfr"].append(stripped.lstrip("-*").strip())

        # Extract out of scope
        in_oos_section = False
        for line in lines:
            line_strip = line.strip()
            if re.search(r"(?i)out\s+of\s+scope|not\s+in\s+scope", line_strip):
                in_oos_section = True
                continue

            if line_strip.startswith("#") and in_oos_section:
                in_oos_section = False

            if in_oos_section and (line_strip.startswith("-") or line_strip.startswith("*")):
                result["out_of_scope"].append(line_strip.lstrip("-*").strip())

        # Extract dependencies
        dep_pattern = r"(?i)depends?\s+on|requires?|integration\s+with"
        for line in lines:
            if re.search(dep_pattern, line):
                result["dependencies"].append(line.strip())

        return result

    def _llm_extract(self, content: str) -> dict[str, Any] | None:
        """Use Claude LLM to extract structured requirements from any prose format.

        Works with: bullet lists, formal user stories, prose paragraphs,
        Confluence code blocks, tables, etc.
        """
        system_prompt = """You are a Business Analyst extracting structured requirements from a BRD document.

The document may contain:
- Bullet lists of features ("Customer can freeze card", "Agent can view freeze history")
- Prose descriptions ("The system should allow customers to...")
- Tables with requirements
- Mixed informal formats

Your job: Convert ALL functional requirements into structured user stories.

For EACH requirement, create a separate user story with:
- as_a (who) - infer persona from context (Customer, Agent, Admin, System, etc.)
- i_want (what) - the specific action/capability (be precise and atomic)
- so_that (why) - business value (infer from business goal if not stated)
- acceptance_criteria (optional) - per-story testable conditions if mentioned

IMPORTANT:
- Create ONE story per distinct feature/capability
- If document says "Customer can freeze card and unfreeze card", create TWO stories
- Keep stories atomic and testable
- Infer reasonable personas if not explicit (Customer, Admin, Support Agent, etc.)
- Put document-level ACs in the top-level "acceptance_criteria" field

Return ONLY valid JSON (no markdown, no commentary):
{
  "epic": "Overall feature title from document",
  "stories": [
    {
      "as_a": "Customer",
      "i_want": "freeze my debit card instantly via mobile app",
      "so_that": "I can prevent fraudulent transactions immediately",
      "acceptance_criteria": ["Card status updates to FROZEN within 2 seconds", "Push notification sent on successful freeze"]
    },
    {
      "as_a": "Customer",
      "i_want": "unfreeze my previously frozen card",
      "so_that": "I can resume normal card usage",
      "acceptance_criteria": ["Card status updates to ACTIVE", "Unfreeze requires authentication"]
    }
  ],
  "acceptance_criteria": ["All operations must be audited", "System must handle 1000 concurrent users"],
  "nfr": ["Performance: API response time < 500ms", "Security: All endpoints require OAuth2"],
  "out_of_scope": ["Credit card freeze", "Physical card replacement"],
  "dependencies": ["Card Management Service v2.1", "Notification Service"]
}

If no requirements found, return: {"epic": "", "stories": [], "acceptance_criteria": [], "nfr": [], "out_of_scope": [], "dependencies": []}"""

        user_prompt = f"""Extract structured requirements from this document:

---
{content[:8000]}
---

Return only the JSON object."""

        try:
            result = self.llm.complete_json(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4096,
                temperature=0.2,
            )

            if not result:
                print("[Ingest Parser] LLM returned None/empty result")
                return None

            if not isinstance(result, dict):
                print(f"[Ingest Parser] LLM returned non-dict: {type(result)} - {str(result)[:200]}")
                return None

            # Debug: show what the LLM returned
            stories_count = len(result.get("stories", []))
            ac_count = len(result.get("acceptance_criteria", []))
            print(f"[Ingest Parser] LLM raw result: {stories_count} stories, {ac_count} ACs")
            if stories_count == 0:
                print(f"[Ingest Parser] LLM full result: {json.dumps(result, indent=2)[:500]}")

            # Validate structure
            return {
                "epic": str(result.get("epic", "")),
                "stories": [
                    {
                        "as_a": str(s.get("as_a", "User")),
                        "i_want": str(s.get("i_want", "")),
                        "so_that": str(s.get("so_that", "")),
                        "acceptance_criteria": s.get("acceptance_criteria", []) if isinstance(s.get("acceptance_criteria"), list) else [],
                    }
                    for s in (result.get("stories") or [])
                    if isinstance(s, dict) and s.get("i_want")
                ],
                "acceptance_criteria": [str(ac) for ac in (result.get("acceptance_criteria") or []) if ac],
                "nfr": [str(n) for n in (result.get("nfr") or []) if n],
                "out_of_scope": [str(o) for o in (result.get("out_of_scope") or []) if o],
                "dependencies": [str(d) for d in (result.get("dependencies") or []) if d],
            }
        except Exception as e:
            print(f"[Ingest Parser] LLM extraction failed: {e}")
            return None

    def _clean_markdown(self, content: str) -> str:
        """Strip markdown formatting and Confluence artifacts that interfere with regex matching."""
        # Remove Confluence-specific HTML tags that might survive conversion
        text = re.sub(r"<ac:[^>]*?>.*?</ac:[^>]*?>", "", content, flags=re.DOTALL)  # <ac:rich-text-body>, etc.
        text = re.sub(r"<ac:[^>]*?/>", "", text)  # Self-closing <ac:*/>
        text = re.sub(r"<ri:[^>]*?/>", "", text)  # Confluence resource identifiers

        # Remove HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&quot;", '"')
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")

        # Remove bold/italic markers but keep the text
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # **bold**
        text = re.sub(r"__(\S.+?\S)__", r"\1", text)     # __bold__ (with non-space boundaries)
        text = re.sub(r"(?<!\*)\*(?!\*)([^\*]+?)\*(?!\*)", r"\1", text)  # *italic*
        # _italic_ — only if surrounded by whitespace/punctuation (NOT inside identifiers like user_id)
        text = re.sub(r"(?<![A-Za-z0-9_])_(?!_)([^_]+?)_(?![A-Za-z0-9_])", r"\1", text)
        # Remove inline code backticks
        text = re.sub(r"`([^`]+)`", r"\1", text)

        return text

    def _cleanup_text(self, text: str) -> str:
        """Clean captured text: strip whitespace, trailing punctuation, formatting."""
        text = text.strip()
        # Remove trailing punctuation that's not meaningful
        text = re.sub(r"[,;:]+$", "", text)
        # Collapse multiple whitespace/newlines into single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _identify_gaps(self, parsed: dict[str, Any]) -> list[str]:
        """
        Identify gaps and ambiguities in requirements.

        Returns list of clarifying questions.
        """
        questions = []
        q_num = 1

        # Check for missing epic
        if not parsed["epic"]:
            questions.append(f"Q{q_num}. [Epic] — What is the name/title of this feature or epic?")
            q_num += 1

        # Check for missing stories
        if not parsed["stories"]:
            questions.append(f"Q{q_num}. [User Stories] — No user stories found. Who are the users and what do they need?")
            q_num += 1

        # Check for missing acceptance criteria
        if not parsed["acceptance_criteria"]:
            questions.append(f"Q{q_num}. [Acceptance Criteria] — What are the specific conditions that must be met for this feature to be considered complete?")
            q_num += 1

        # Check for vague acceptance criteria
        for i, ac in enumerate(parsed["acceptance_criteria"]):
            if len(ac.split()) < 5:  # Too short
                questions.append(f"Q{q_num}. [AC #{i+1}] — '{ac}' is too vague. Can you provide more specific details?")
                q_num += 1

        # Check for missing NFRs
        if not parsed["nfr"]:
            questions.append(f"Q{q_num}. [Non-Functional] — Are there any performance, security, or scalability requirements?")
            q_num += 1

        # Check for contradictions (simple heuristic)
        content_text = str(parsed).lower()
        if "must" in content_text and "optional" in content_text:
            questions.append(f"Q{q_num}. [Clarity] — Document contains both 'must' and 'optional' requirements. Please clarify priorities.")
            q_num += 1

        return questions

    def _create_state(self, source: str, parsed: dict[str, Any]) -> dict[str, Any]:
        """Create state object matching skill's expected format."""
        return {
            "stage": "ingest",
            "source": source,
            "epic": parsed["epic"],
            "stories": parsed["stories"],
            "acceptance_criteria": parsed["acceptance_criteria"],
            "nfr": parsed["nfr"],
            "out_of_scope": parsed["out_of_scope"],
            "dependencies": parsed["dependencies"],
            "open_questions": parsed["open_questions"],
            "answered_questions": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _save_state(self, state: dict[str, Any]) -> None:
        """Save state to .claude/sdlc-state.json"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, indent=2),
            encoding="utf-8"
        )

    @classmethod
    def load_state(cls, root_dir: Path) -> dict[str, Any] | None:
        """Load existing state from file."""
        state_file = root_dir / ".claude" / "sdlc-state.json"
        if not state_file.exists():
            return None

        return json.loads(state_file.read_text(encoding="utf-8"))
