"""Stage 4 — Code review.

Inspects PR contents for security, coding-standards, logic, test-coverage and
client-specific compliance issues (NatWest standards used as the reference
checklist in Phase 1). Emits a structured report with a pass/fail verdict.

When a live LLM backend is reachable (Copilot bridge or Anthropic), an
LLM-driven review is run alongside the deterministic regex scan. The rule
pass stays in place as a safety net so the seeded-defect demo loop remains
reliable even if the LLM is unavailable.

A failed review is returned to Stage 3 for remediation by the orchestrator.
"""
from __future__ import annotations

import logging
import re

from ..integrations import ClaudeClient
from ..core.models import PullRequest, ReviewFinding, ReviewReport, Severity

logger = logging.getLogger(__name__)


# Crude but explicit security pattern set; in production this would be a
# Semgrep/CodeQL ruleset plus an LLM pass.
_SECURITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\beval\s*\("), "Use of eval() is forbidden."),
    (re.compile(r"\bexec\s*\("), "Use of exec() is forbidden."),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True is unsafe."),
    (re.compile(r"verify\s*=\s*False"), "TLS verification disabled."),
    (re.compile(r"['\"](sk_|AKIA|ghp_)[A-Za-z0-9]{8,}['\"]"), "Hard-coded credential."),
]

_STANDARDS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*print\("), "Use the logger, not print()."),
    (re.compile(r"#\s*TODO", re.I), "TODO left in code — track in Jira or resolve."),
]


def _scan_file(path: str, contents: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for line_no, line in enumerate(contents.splitlines(), start=1):
        for pattern, message in _SECURITY_PATTERNS:
            if pattern.search(line):
                findings.append(ReviewFinding(
                    file=path, line=line_no,
                    severity=Severity.HIGH,
                    category="security",
                    message=message,
                ))
        for pattern, message in _STANDARDS_PATTERNS:
            if pattern.search(line):
                findings.append(ReviewFinding(
                    file=path, line=line_no,
                    severity=Severity.LOW,
                    category="standards",
                    message=message,
                ))
    return findings


def _coverage_gap(pr: PullRequest) -> ReviewFinding | None:
    has_tests = any(
        f.path.startswith("tests/") or "/test_" in f.path
        for f in pr.files
    )
    if has_tests:
        return None
    return ReviewFinding(
        file=pr.files[0].path if pr.files else "(pr)",
        line=None,
        severity=Severity.MEDIUM,
        category="coverage",
        message="No test files in PR — Stage 5 must add coverage before merge.",
    )


def run(
    pr: PullRequest,
    *,
    claude: ClaudeClient | None = None,
) -> ReviewReport:
    claude = claude or ClaudeClient()
    claude.complete("stage4_review", {"pr": pr.number, "files": len(pr.files)})

    backend = getattr(claude, "backend", "stub")
    is_live = getattr(claude, "is_live", False)
    logger.info("Stage 4 starting (backend=%s, is_live=%s)", backend, is_live)
    print(f"\n{'='*70}")
    print(f"🔍 Stage 4: Code Review Started")
    print(f"{'='*70}")
    print(f"PR Number: #{pr.number}")
    print(f"Files to review: {len(pr.files)}")
    print(f"Review backend: {backend} {'(Live LLM)' if is_live else '(Rules-based)'}")
    print(f"{'='*70}\n")

    findings: list[ReviewFinding] = []
    for f in pr.files:
        print(f"📄 Reviewing: {f.path} ({len(f.contents.splitlines())} lines)")
        file_findings = _scan_file(f.path, f.contents)
        if file_findings:
            print(f"   ⚠️  Found {len(file_findings)} issue(s):")
            for finding in file_findings:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}.get(finding.severity.value, "•")
                print(f"      {severity_icon} Line {finding.line}: [{finding.category.upper()}] {finding.message}")
        else:
            print(f"   ✅ No issues found")
        findings.extend(file_findings)

    gap = _coverage_gap(pr)
    if gap:
        print(f"\n📊 Coverage Analysis:")
        print(f"   ⚠️  {gap.message}")
        findings.append(gap)
    else:
        print(f"\n📊 Coverage Analysis:")
        print(f"   ✅ Test files found in PR")

    # Layer an LLM review on top of the deterministic regex pass.
    print(f"\n🤖 LLM Review:")
    llm_findings = _review_with_llm(pr, claude) if is_live else None
    review_source = "rules"
    if llm_findings is not None:
        findings.extend(llm_findings)
        review_source = "llm+rules"
        logger.info("Stage 4 added %d LLM finding(s).", len(llm_findings))
        print(f"   ✅ LLM analysis complete - found {len(llm_findings)} additional issue(s)")
        for finding in llm_findings:
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}.get(finding.severity.value, "•")
            print(f"      {severity_icon} {finding.file}:{finding.line or '?'} [{finding.category.upper()}] {finding.message}")
    else:
        logger.info("Stage 4 ran rules only (backend=%s).", backend)
        print(f"   ℹ️  LLM not available - using rules-based review only")

    # Drop duplicates that both the rule scan and the LLM may surface
    # (same file/line/message).
    seen: set[tuple[str, int | None, str]] = set()
    deduped: list[ReviewFinding] = []
    for f in findings:
        key = (f.file, f.line, f.message.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    findings = deduped

    # `TODO` lines are expected on the freshly generated draft — downgrade
    # them so the verdict is not blocked by Stage 3 scaffolding. Stage 5 will
    # replace the TODOs and Stage 6 will re-check.
    for f in findings:
        if f.category == "standards" and f.message.startswith("TODO"):
            f.severity = Severity.INFO

    blocking = [
        f for f in findings
        if f.severity in (Severity.HIGH, Severity.CRITICAL)
    ]
    verdict = "fail" if blocking else "pass"

    # Print final summary
    print(f"\n{'='*70}")
    print(f"📋 Review Summary")
    print(f"{'='*70}")
    print(f"Total findings: {len(findings)}")
    print(f"  🔴 Critical: {sum(1 for f in findings if f.severity == Severity.CRITICAL)}")
    print(f"  🟠 High:     {sum(1 for f in findings if f.severity == Severity.HIGH)}")
    print(f"  🟡 Medium:   {sum(1 for f in findings if f.severity == Severity.MEDIUM)}")
    print(f"  🔵 Low:      {sum(1 for f in findings if f.severity == Severity.LOW)}")
    print(f"  ℹ️  Info:     {sum(1 for f in findings if f.severity == Severity.INFO)}")
    print(f"\nBlocking issues: {len(blocking)}")
    print(f"Review source: {review_source}")
    if verdict == "pass":
        print(f"\n✅ VERDICT: PASS - Ready to proceed to testing")
    else:
        print(f"\n❌ VERDICT: FAIL - Fix blocking issues before proceeding")
        print(f"\nBlocking issues that must be fixed:")
        for i, finding in enumerate(blocking, 1):
            print(f"  {i}. {finding.file}:{finding.line or '?'} - {finding.message}")
    print(f"{'='*70}\n")

    report = ReviewReport(pr_number=pr.number, findings=findings, verdict=verdict)
    report.__dict__["_review_source"] = review_source
    report.__dict__["_review_backend"] = backend
    return report


_VALID_CATEGORIES = {"security", "standards", "logic", "coverage", "compliance"}
_VALID_SEVERITIES = {s.value for s in Severity}


def _review_with_llm(
    pr: PullRequest, claude: ClaudeClient
) -> list[ReviewFinding] | None:
    """Ask the LLM to review the PR against NatWest standards.

    Returns a list of findings (possibly empty), or None if the call failed
    or returned an unusable response. The caller falls back to rule-based
    findings only when this returns None.
    """
    if not pr.files:
        return []

    system = (
        "You are a senior NatWest staff engineer doing a pull-request code "
        "review. Review the supplied files against these NatWest standards: "
        "(1) use the standard `logging` module — never print(); (2) TLS "
        "verification MUST stay enabled (no verify=False); (3) no hard-coded "
        "credentials, tokens or PII; (4) no eval/exec or shell=True; "
        "(5) every public function has a docstring; (6) input validation "
        "and authn/authz are present at HTTP boundaries; (7) audit-log all "
        "state-changing actions. Also flag obvious logic bugs and missing "
        "test coverage. Return STRICT JSON only — no prose, no fences. "
        "Each finding must include: file, line (integer or null), severity "
        "(one of: info, low, medium, high, critical), category (one of: "
        "security, standards, logic, coverage, compliance), message."
    )
    schema_hint = (
        '{"findings": [ {"file": "src/x.py", "line": 12, '
        '"severity": "high", "category": "security", '
        '"message": "..."} ]}'
    )

    file_block = "\n\n".join(
        f"=== FILE: {f.path} ({f.language}) ===\n{f.contents}"
        for f in pr.files
    )
    user = (
        f"PR #{pr.number} on branch {pr.branch}\n"
        f"Title: {pr.title}\n"
        f"Stories: {', '.join(pr.story_ids) or 'n/a'}\n\n"
        f"{file_block}\n\n"
        "Return JSON matching this shape exactly:\n"
        + schema_hint
    )

    data = claude.complete_json(
        system=system, user=user, max_tokens=4096, temperature=0.1
    )
    if not isinstance(data, dict) or "findings" not in data:
        return None

    parsed: list[ReviewFinding] = []
    for raw in data["findings"]:
        if not isinstance(raw, dict):
            continue
        sev = str(raw.get("severity", "")).strip().lower()
        cat = str(raw.get("category", "")).strip().lower()
        if sev not in _VALID_SEVERITIES or cat not in _VALID_CATEGORIES:
            continue
        line_val = raw.get("line")
        try:
            line = int(line_val) if line_val not in (None, "") else None
        except (TypeError, ValueError):
            line = None
        try:
            parsed.append(ReviewFinding(
                file=str(raw.get("file") or (pr.files[0].path if pr.files else "(pr)")),
                line=line,
                severity=Severity(sev),
                category=cat,  # type: ignore[arg-type]
                message=str(raw.get("message") or "").strip(),
            ))
        except (ValueError, TypeError):
            continue

    # Drop empty messages.
    parsed = [f for f in parsed if f.message]
    return parsed
