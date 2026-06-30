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
            from ..integrations.anthropic_client import ClaudeClient
            self._llm = ClaudeClient()
        return self._llm

    def run(self, source: str) -> dict[str, Any]:
        """
        Execute the /sdlc-ingest skill logic with codebase analysis.

        Args:
            source: Confluence URL, file path, or search query

        Returns:
            dict with parsed requirements, codebase analysis, and contextual questions
        """
        # Step 1: Fetch the requirements
        print("[Ingest] Step 1: Fetching requirements...")
        content = self._fetch_requirements(source)

        # Step 2: Parse and structure
        print("[Ingest] Step 2: Parsing requirements...")
        parsed = self._parse_requirements(content, source)

        # Step 3: Analyze current codebase for impact
        print("[Ingest] Step 3: Analyzing codebase for impact...")
        codebase_analysis = self._analyze_codebase(parsed)

        # Step 4: Generate contextual questions (combining requirement gaps + codebase insights)
        print("[Ingest] Step 4: Generating contextual questions...")
        questions = self._identify_gaps_with_context(parsed, codebase_analysis)
        parsed["open_questions"] = questions

        # Step 5: Save state with codebase analysis
        print("[Ingest] Step 5: Saving state...")
        state = self._create_state(source, parsed, codebase_analysis)
        self._save_state(state)

        print(f"[Ingest] ✓ Complete: {len(parsed['stories'])} stories, {len(questions)} questions")
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
        Parse requirements from plain English business documents.

        Strategy:
        1. PRIMARY: Use LLM to convert plain English into structured requirements
           - Business users write in natural language (not formal user stories)
           - LLM understands context and extracts intent
        2. FALLBACK: If LLM unavailable, use basic regex extraction
           - Only works if document happens to have structured sections
           - Limited capability compared to LLM
        """
        # Clean content: strip markdown bold/italic
        cleaned = self._clean_markdown(content)

        # Debug logging
        print(f"[Ingest Parser] Content length: {len(content)} chars")
        print(f"[Ingest Parser] First 300 chars: {cleaned[:300]}...")

        # Initialize result structure
        result = {
            "epic": "",
            "stories": [],
            "acceptance_criteria": [],
            "nfr": [],
            "out_of_scope": [],
            "dependencies": [],
        }

        # STRATEGY 1: Use LLM to parse plain English requirements (PRIMARY)
        if self.llm.is_live and len(cleaned.strip()) > 50:
            print(f"[Ingest Parser] Using LLM ({self.llm.backend}) to parse plain English requirements...")
            llm_result = self._llm_extract(cleaned)
            if llm_result and llm_result.get("stories"):
                print(f"[Ingest Parser] ✓ LLM extracted {len(llm_result['stories'])} stories from business requirements")
                return llm_result
            else:
                print("[Ingest Parser] LLM extraction returned no results, falling back to regex")
        else:
            print("[Ingest Parser] LLM unavailable, using fallback regex parser")

        # STRATEGY 2: Fallback regex extraction (LIMITED - only if LLM fails)
        print("[Ingest Parser] WARNING: Using limited regex parser - results may be incomplete")

        lines = cleaned.split("\n")

        # Extract title/epic from first heading
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                result["epic"] = line.lstrip("#").strip()
                break

        # Try to find formal user stories (rare in business docs)
        story_pattern = r"(?is)\bas\s+a[n]?\s+(.+?)[,\n]\s*i\s+want\s+(?:to\s+)?(.+?)[,\n]\s*so\s+that\s+(.+?)(?=\.\s|\n\s*\n|\n#|\n-|\n\*|$)"
        for match in re.finditer(story_pattern, cleaned):
            story = {
                "as_a": self._cleanup_text(match.group(1)),
                "i_want": self._cleanup_text(match.group(2)),
                "so_that": self._cleanup_text(match.group(3)),
            }
            if not any(s["i_want"] == story["i_want"] for s in result["stories"]):
                result["stories"].append(story)

        # Extract any bullet points as potential requirements
        if not result["stories"]:
            bullet_requirements = []
            for line in lines:
                stripped = line.strip()
                if (stripped.startswith("-") or stripped.startswith("*")) and len(stripped) > 10:
                    req_text = stripped.lstrip("-*").strip()
                    # Convert bullet point to basic story structure
                    bullet_requirements.append({
                        "as_a": "User",
                        "i_want": req_text,
                        "so_that": "fulfill business requirements",
                    })
            result["stories"] = bullet_requirements[:10]  # Limit to avoid noise

        # Extract acceptance criteria if section exists
        in_ac_section = False
        for line in lines:
            stripped = line.strip()
            if re.search(r"(?i)acceptance\s+criteria|definition\s+of\s+done", stripped):
                in_ac_section = True
                continue
            if stripped.startswith("#") and in_ac_section:
                in_ac_section = False
            if in_ac_section and (stripped.startswith("-") or stripped.startswith("*")):
                result["acceptance_criteria"].append(stripped.lstrip("-*").strip())

        # Extract NFRs (basic keyword matching)
        nfr_keywords = ["performance", "security", "accessibility", "scalability", "availability"]
        for line in lines:
            if any(kw in line.lower() for kw in nfr_keywords):
                if line.strip().startswith("-") or line.strip().startswith("*"):
                    result["nfr"].append(line.strip().lstrip("-*").strip())

        print(f"[Ingest Parser] Regex fallback: {len(result['stories'])} stories (may be incomplete)")
        return result

    def _llm_extract(self, content: str) -> dict[str, Any] | None:
        """Use Claude LLM to extract structured requirements from plain English business documents.

        Handles:
        - Plain English descriptions ("The system needs to...", "Users should be able to...")
        - Bullet lists without formal structure
        - Prose paragraphs explaining business needs
        - Confluence pages, Word docs, meeting notes
        - Any informal business language
        """
        system_prompt = """You are a Senior Business Analyst converting plain English business requirements into structured, development-ready user stories.

**INPUT**: Business users write requirements in natural language:
- "The system needs to allow customers to freeze their cards"
- "We want agents to see a history of all card freezes"
- "Users should be able to unfreeze cards they previously froze"
- Prose paragraphs, bullet points, meeting notes, informal descriptions

**YOUR JOB**: Convert ALL business requirements into structured user stories that developers can implement.

**EXTRACTION RULES**:
1. **Identify Personas** - Infer who benefits from each feature:
   - Customer, User, End User (external users)
   - Admin, Administrator (internal power users)
   - Support Agent, Call Center Agent (support staff)
   - System, Application (automated processes)

2. **Extract Capabilities** - Each distinct action = ONE story:
   - "freeze card" → one story
   - "unfreeze card" → separate story
   - "view freeze history" → separate story

3. **Infer Business Value** - Why does the persona need this?
   - Security: "prevent fraud", "protect account"
   - Efficiency: "save time", "reduce manual work"
   - Compliance: "meet regulations", "audit trail"
   - Usability: "improve experience", "self-service"

4. **Extract Non-Functionals** (NFR):
   - Performance: response time, throughput, concurrency
   - Security: authentication, authorization, encryption
   - Compliance: GDPR, PCI-DSS, SOX, audit requirements
   - Scalability: user load, data volume

5. **Identify Out of Scope** - Explicitly mentioned exclusions

6. **Extract Dependencies** - Services, APIs, systems mentioned

**OUTPUT FORMAT** (JSON only, no markdown):
{
  "epic": "High-level feature name (extract from title or infer from context)",
  "stories": [
    {
      "as_a": "Customer",
      "i_want": "freeze my debit card instantly from the mobile app",
      "so_that": "I can immediately prevent unauthorized transactions if my card is lost",
      "acceptance_criteria": ["Card status changes to FROZEN within 2 seconds", "SMS confirmation sent to registered mobile"]
    },
    {
      "as_a": "Support Agent",
      "i_want": "view the complete freeze/unfreeze history for a customer's card",
      "so_that": "I can answer customer queries about past card activity"
    }
  ],
  "acceptance_criteria": ["All card state changes must be audited with timestamp and user ID", "System must support 10,000 concurrent freeze requests"],
  "nfr": ["Performance: Freeze/unfreeze API must respond within 500ms p95", "Security: All operations require OAuth2 authentication", "Audit: All transactions logged to immutable audit store"],
  "out_of_scope": ["Credit card freeze (only debit cards in scope)", "Physical card replacement process"],
  "dependencies": ["Card Management Service v2", "Customer Notification Service", "Audit Logging Service"]
}

**IMPORTANT**:
- Be generous in extraction - if business need is implied, include it
- Keep stories small and testable (one capability per story)
- Infer reasonable acceptance criteria even if not explicitly stated
- Extract ALL mentioned requirements - don't skip anything
- If unsure about persona, default to "User"
- Return empty arrays for missing sections (don't omit them)"""

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

    def _analyze_codebase(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze the current codebase to understand:
        - Existing architecture and patterns
        - Similar features that exist
        - Integration points and impacts
        - Technical risks and challenges

        Returns codebase analysis summary
        """
        print("[Codebase Analysis] Scanning repository structure...")

        analysis = {
            "architecture_summary": "",
            "similar_features": [],
            "integration_points": [],
            "potential_impacts": [],
            "technical_risks": [],
            "recommended_approach": "",
        }

        # Scan codebase structure
        codebase_context = self._scan_codebase_structure()

        # Use LLM to analyze if available
        if self.llm.is_live and codebase_context:
            print(f"[Codebase Analysis] Analyzing with {self.llm.backend}...")
            llm_analysis = self._llm_analyze_codebase(parsed, codebase_context)
            if llm_analysis:
                analysis = llm_analysis
                print(f"[Codebase Analysis] ✓ Found {len(analysis.get('integration_points', []))} integration points")
            else:
                print("[Codebase Analysis] LLM analysis unavailable, using structural scan only")
                analysis["architecture_summary"] = f"Repository structure: {codebase_context['summary']}"
        else:
            print("[Codebase Analysis] LLM unavailable, using basic structural analysis")
            analysis["architecture_summary"] = f"Repository structure: {codebase_context.get('summary', 'Not analyzed')}"

        return analysis

    def _scan_codebase_structure(self) -> dict[str, Any]:
        """Scan repository to understand structure and key files."""
        structure = {
            "summary": "",
            "key_files": [],
            "technologies": set(),
            "patterns": [],
        }

        # Common source directories to scan
        scan_dirs = ["src", "sdlc_agent", "app", "lib", "api", "services"]

        for dir_name in scan_dirs:
            scan_path = self.root_dir / dir_name
            if scan_path.exists():
                # Scan Python files
                py_files = list(scan_path.rglob("*.py"))
                if py_files:
                    structure["technologies"].add("Python")
                    structure["key_files"].extend([str(f.relative_to(self.root_dir)) for f in py_files[:20]])

                # Scan TypeScript/JavaScript
                ts_files = list(scan_path.rglob("*.ts")) + list(scan_path.rglob("*.tsx"))
                if ts_files:
                    structure["technologies"].add("TypeScript")
                    structure["key_files"].extend([str(f.relative_to(self.root_dir)) for f in ts_files[:20]])

                js_files = list(scan_path.rglob("*.js")) + list(scan_path.rglob("*.jsx"))
                if js_files:
                    structure["technologies"].add("JavaScript")

        # Check for common framework indicators
        if (self.root_dir / "package.json").exists():
            structure["patterns"].append("Node.js project")
        if (self.root_dir / "requirements.txt").exists() or (self.root_dir / "pyproject.toml").exists():
            structure["patterns"].append("Python project")
        if (self.root_dir / "manage.py").exists():
            structure["patterns"].append("Django project")
        if any(Path(self.root_dir).glob("**/flask*")):
            structure["patterns"].append("Flask project")

        structure["summary"] = f"{', '.join(structure['technologies'])} project with {len(structure['key_files'])} source files"
        return structure

    def _llm_analyze_codebase(self, parsed: dict[str, Any], codebase_context: dict[str, Any]) -> dict[str, Any] | None:
        """Use LLM to analyze compatibility between requirements and existing codebase."""

        # Read sample files for context (limit to avoid token overflow)
        sample_files_content = []
        for file_path in codebase_context.get("key_files", [])[:10]:
            try:
                full_path = self.root_dir / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding="utf-8")
                    # Include first 500 chars of each file
                    sample_files_content.append(f"### {file_path}\n{content[:500]}...")
            except Exception:
                continue

        system_prompt = """You are a Technical Architect analyzing how new requirements will integrate with an existing codebase.

Analyze:
1. **Architecture** - Current tech stack and patterns
2. **Similar Features** - Existing functionality that's similar to new requirements
3. **Integration Points** - Where new features will touch existing code
4. **Potential Impacts** - Files/modules that will need changes
5. **Technical Risks** - Complexity, breaking changes, migration challenges
6. **Recommended Approach** - Implementation strategy

Return ONLY valid JSON:
{
  "architecture_summary": "Brief description of current architecture",
  "similar_features": ["Feature X in module Y", "Feature Z in service W"],
  "integration_points": ["API endpoint /api/cards", "Database table card_status", "Service CardManagementService"],
  "potential_impacts": ["card_service.py will need new freeze/unfreeze methods", "Database migration for freeze_timestamp column"],
  "technical_risks": ["Breaking change to Card API contract", "Need backward compatibility for existing clients"],
  "recommended_approach": "Extend existing CardService with freeze/unfreeze methods. Add new status field to cards table with migration."
}"""

        requirements_summary = f"""Epic: {parsed.get('epic', 'N/A')}

User Stories:
{json.dumps(parsed.get('stories', [])[:5], indent=2)}

Dependencies: {', '.join(parsed.get('dependencies', []))}

NFRs: {', '.join(parsed.get('nfr', []))}"""

        codebase_summary = f"""Tech Stack: {codebase_context.get('summary', 'Unknown')}

Patterns: {', '.join(codebase_context.get('patterns', []))}

Sample Files:
{''.join(sample_files_content[:3000])}"""

        user_prompt = f"""Analyze how these requirements integrate with the existing codebase:

## New Requirements
{requirements_summary}

## Current Codebase
{codebase_summary}

Return only the JSON analysis object."""

        try:
            result = self.llm.complete_json(
                system=system_prompt,
                user=user_prompt,
                max_tokens=2048,
                temperature=0.2,
            )

            if result and isinstance(result, dict):
                return {
                    "architecture_summary": str(result.get("architecture_summary", "")),
                    "similar_features": [str(f) for f in (result.get("similar_features") or [])],
                    "integration_points": [str(i) for i in (result.get("integration_points") or [])],
                    "potential_impacts": [str(p) for p in (result.get("potential_impacts") or [])],
                    "technical_risks": [str(r) for r in (result.get("technical_risks") or [])],
                    "recommended_approach": str(result.get("recommended_approach", "")),
                }
        except Exception as e:
            print(f"[Codebase Analysis] LLM analysis failed: {e}")

        return None

    def _identify_gaps_with_context(
        self, parsed: dict[str, Any], codebase_analysis: dict[str, Any]
    ) -> list[str]:
        """
        Generate contextual questions combining requirement gaps AND codebase insights.

        This produces smarter questions that consider both:
        - Missing/vague requirements
        - Integration challenges discovered in codebase analysis
        """
        questions = []
        q_num = 1

        # Start with basic requirement gaps
        basic_gaps = self._identify_gaps(parsed)
        questions.extend(basic_gaps)
        q_num = len(questions) + 1

        # Add codebase-specific questions
        if codebase_analysis.get("technical_risks"):
            questions.append(
                f"Q{q_num}. [Integration Risk] — Analysis found potential risks: "
                f"{'; '.join(codebase_analysis['technical_risks'][:2])}. "
                "How should we mitigate these?"
            )
            q_num += 1

        if codebase_analysis.get("similar_features"):
            questions.append(
                f"Q{q_num}. [Existing Features] — Similar features exist: "
                f"{'; '.join(codebase_analysis['similar_features'][:2])}. "
                "Should new features reuse/extend these or be built separately?"
            )
            q_num += 1

        if codebase_analysis.get("potential_impacts"):
            questions.append(
                f"Q{q_num}. [Breaking Changes] — {len(codebase_analysis['potential_impacts'])} files may be impacted. "
                "Do we need a migration strategy for existing users?"
            )
            q_num += 1

        # Ask about integration points if discovered
        integration_points = codebase_analysis.get("integration_points", [])
        if integration_points:
            questions.append(
                f"Q{q_num}. [Integration] — New features will integrate with: "
                f"{', '.join(integration_points[:3])}. "
                "Are these the correct integration points, or should we use different services/APIs?"
            )
            q_num += 1

        return questions

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

    def _create_state(
        self,
        source: str,
        parsed: dict[str, Any],
        codebase_analysis: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create state object with requirements and codebase analysis."""
        state = {
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

        # Include codebase analysis if available
        if codebase_analysis:
            state["codebase_analysis"] = codebase_analysis

        return state

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
