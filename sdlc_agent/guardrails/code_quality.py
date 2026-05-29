"""
Output Quality Guardrails for LLM-Generated Code

Multi-layer validation system to ensure generated code meets
security, quality, and compliance standards before acceptance.
"""
from __future__ import annotations

import ast
import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class GuardrailSeverity(Enum):
    """Severity levels for guardrail violations."""
    BLOCK = "block"      # Must fix - code rejected
    WARN = "warn"        # Should fix - code accepted with warning
    INFO = "info"        # Nice to have - informational only


@dataclass
class GuardrailViolation:
    """A single guardrail violation."""
    layer: str
    severity: GuardrailSeverity
    rule: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    passed: bool
    violations: list[GuardrailViolation]
    score: float  # 0-100 quality score

    def blocking_violations(self) -> list[GuardrailViolation]:
        """Get violations that block acceptance."""
        return [v for v in self.violations if v.severity == GuardrailSeverity.BLOCK]


class CodeQualityGuardrails:
    """
    Multi-layer validation system for LLM-generated code.

    Validates syntax, security, standards, and quality before
    accepting code into the codebase.
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize guardrails.

        Args:
            strict_mode: If True, enforce all rules strictly.
                        If False, downgrade some BLOCKs to WARNs.
        """
        self.strict_mode = strict_mode
        logger.info("CodeQualityGuardrails initialized (strict_mode=%s)", strict_mode)

    def validate(self, code: str, context: dict = None) -> GuardrailResult:
        """
        Validate generated code through all guardrail layers.

        Args:
            code: The Python code to validate
            context: Optional context (story info, requirements, etc.)

        Returns:
            GuardrailResult with pass/fail and violations
        """
        context = context or {}
        violations = []

        # Layer 1: Syntax validation
        syntax_violations, tree = self._layer1_syntax(code)
        violations.extend(syntax_violations)

        # If syntax is invalid, stop here (can't parse AST)
        if any(v.severity == GuardrailSeverity.BLOCK for v in syntax_violations):
            return GuardrailResult(
                passed=False,
                violations=violations,
                score=0.0
            )

        # Layer 2: Security scan
        violations.extend(self._layer2_security(code, tree))

        # Layer 3: Standards check
        violations.extend(self._layer3_standards(code, tree))

        # Layer 4: Quality metrics
        violations.extend(self._layer4_quality(code, tree, context))

        # Calculate quality score
        score = self._calculate_score(violations)

        # Determine pass/fail
        blocking = [v for v in violations if v.severity == GuardrailSeverity.BLOCK]
        passed = len(blocking) == 0

        logger.info(
            "Guardrail validation: %s (score=%.1f, violations=%d, blocking=%d)",
            "PASS" if passed else "FAIL",
            score,
            len(violations),
            len(blocking)
        )

        return GuardrailResult(passed=passed, violations=violations, score=score)

    def _layer1_syntax(self, code: str) -> tuple[list[GuardrailViolation], Optional[ast.AST]]:
        """Layer 1: Syntax validation via AST parsing."""
        violations = []
        tree = None

        try:
            tree = ast.parse(code)
            logger.debug("Layer 1: Syntax valid ✓")
        except SyntaxError as e:
            violations.append(GuardrailViolation(
                layer="syntax",
                severity=GuardrailSeverity.BLOCK,
                rule="valid_python",
                message=f"Invalid Python syntax: {e.msg}",
                line=e.lineno,
                suggestion="Fix syntax errors before submission"
            ))
            logger.warning("Layer 1: Syntax invalid - %s at line %s", e.msg, e.lineno)
        except Exception as e:
            violations.append(GuardrailViolation(
                layer="syntax",
                severity=GuardrailSeverity.BLOCK,
                rule="parseable",
                message=f"Code cannot be parsed: {str(e)}",
                suggestion="Ensure code is valid Python"
            ))
            logger.error("Layer 1: Parse error - %s", e)

        return violations, tree

    def _layer2_security(self, code: str, tree: Optional[ast.AST]) -> list[GuardrailViolation]:
        """Layer 2: Security pattern scanning."""
        violations = []

        # Pattern-based security checks
        security_patterns = [
            (r"\beval\s*\(", "eval() is dangerous - use ast.literal_eval or json.loads"),
            (r"\bexec\s*\(", "exec() is forbidden for security reasons"),
            (r"shell\s*=\s*True", "subprocess with shell=True is unsafe - use shell=False"),
            (r"verify\s*=\s*False", "TLS verification disabled - always use verify=True"),
            (r"['\"](sk_|AKIA|ghp_|AIza)[A-Za-z0-9]{8,}['\"]", "Hard-coded API key detected - use environment variables"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hard-coded password - use secure credential management"),
            (r"\bpickle\.loads?\(", "pickle is insecure - use json or safer serialization"),
            (r"__import__\(", "Dynamic imports can be unsafe - use explicit imports"),
        ]

        for line_no, line in enumerate(code.splitlines(), start=1):
            for pattern, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(GuardrailViolation(
                        layer="security",
                        severity=GuardrailSeverity.BLOCK,
                        rule="security_pattern",
                        message=message,
                        line=line_no,
                        suggestion="Remove unsafe pattern and use secure alternative"
                    ))

        # AST-based security checks
        if tree:
            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name):
                        if func.id in {"eval", "exec", "compile"}:
                            violations.append(GuardrailViolation(
                                layer="security",
                                severity=GuardrailSeverity.BLOCK,
                                rule="dangerous_builtin",
                                message=f"Dangerous builtin: {func.id}()",
                                line=getattr(node, 'lineno', None),
                                suggestion=f"Replace {func.id}() with safer alternative"
                            ))

        logger.debug("Layer 2: Security scan complete (%d violations)", len(violations))
        return violations

    def _layer3_standards(self, code: str, tree: Optional[ast.AST]) -> list[GuardrailViolation]:
        """Layer 3: Coding standards validation (NatWest standards)."""
        violations = []

        # Check for print() statements (should use logging)
        for line_no, line in enumerate(code.splitlines(), start=1):
            if re.match(r"^\s*print\(", line):
                violations.append(GuardrailViolation(
                    layer="standards",
                    severity=GuardrailSeverity.BLOCK if self.strict_mode else GuardrailSeverity.WARN,
                    rule="no_print",
                    message="Use logger instead of print()",
                    line=line_no,
                    suggestion="Replace print() with logger.info() or logger.debug()"
                ))

        # Check for logging import
        has_logging = "import logging" in code or "from logging import" in code
        if not has_logging and "logger" in code:
            violations.append(GuardrailViolation(
                layer="standards",
                severity=GuardrailSeverity.WARN,
                rule="missing_logging_import",
                message="Code uses logger but doesn't import logging module",
                suggestion="Add 'import logging' at the top"
            ))

        # Check for docstrings
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        violations.append(GuardrailViolation(
                            layer="standards",
                            severity=GuardrailSeverity.WARN,
                            rule="missing_docstring",
                            message=f"Missing docstring for {node.name}",
                            line=node.lineno,
                            suggestion="Add docstring describing purpose and parameters"
                        ))

        # Check line length (PEP 8: max 120 chars for enterprise code)
        for line_no, line in enumerate(code.splitlines(), start=1):
            if len(line) > 120:
                violations.append(GuardrailViolation(
                    layer="standards",
                    severity=GuardrailSeverity.INFO,
                    rule="line_length",
                    message=f"Line exceeds 120 characters ({len(line)} chars)",
                    line=line_no,
                    suggestion="Break long lines for better readability"
                ))

        logger.debug("Layer 3: Standards check complete (%d violations)", len(violations))
        return violations

    def _layer4_quality(self, code: str, tree: Optional[ast.AST], context: dict) -> list[GuardrailViolation]:
        """Layer 4: Code quality metrics."""
        violations = []

        # Check for error handling
        has_try_except = "try:" in code and "except" in code
        if not has_try_except:
            violations.append(GuardrailViolation(
                layer="quality",
                severity=GuardrailSeverity.WARN,
                rule="missing_error_handling",
                message="No error handling found - operations should be wrapped in try-except",
                suggestion="Add try-except blocks around operations that could fail"
            ))

        # Check for input validation
        has_validation = any(pattern in code for pattern in [
            "if not", "raise ValueError", "raise TypeError", "assert"
        ])
        if not has_validation:
            violations.append(GuardrailViolation(
                layer="quality",
                severity=GuardrailSeverity.WARN,
                rule="missing_input_validation",
                message="No input validation detected - validate parameters before use",
                suggestion="Add checks like: if not user_id: raise ValueError('user_id required')"
            ))

        # Check for audit logging (for sensitive operations)
        story_id = context.get("story_id", "")
        is_sensitive_operation = any(keyword in story_id.lower() for keyword in [
            "freeze", "payment", "transfer", "card", "account", "auth"
        ])

        if is_sensitive_operation:
            has_audit_log = "audit" in code.lower() or "log_action" in code.lower()
            if not has_audit_log:
                violations.append(GuardrailViolation(
                    layer="quality",
                    severity=GuardrailSeverity.WARN,
                    rule="missing_audit_log",
                    message="Sensitive operation should include audit logging",
                    suggestion="Add audit trail: audit_service.log_action(user_id, action, result)"
                ))

        # Check for authorization checks (user_id parameter)
        has_user_id = "user_id" in code
        if not has_user_id and is_sensitive_operation:
            violations.append(GuardrailViolation(
                layer="quality",
                severity=GuardrailSeverity.BLOCK if self.strict_mode else GuardrailSeverity.WARN,
                rule="missing_authentication",
                message="Sensitive operation missing user_id parameter for authentication",
                suggestion="Add user_id parameter and validate it"
            ))

        # Check for stub/TODO markers
        stub_markers = ["TODO", "FIXME", "STUB", "pass  # TODO", "raise NotImplementedError"]
        for marker in stub_markers:
            if marker in code:
                violations.append(GuardrailViolation(
                    layer="quality",
                    severity=GuardrailSeverity.WARN,
                    rule="incomplete_implementation",
                    message=f"Code contains {marker} - appears to be incomplete",
                    suggestion="Complete the implementation before merging"
                ))
                break  # Only report once

        # Check function complexity (simple heuristic: nested depth)
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    depth = self._calculate_nesting_depth(node)
                    if depth > 4:
                        violations.append(GuardrailViolation(
                            layer="quality",
                            severity=GuardrailSeverity.INFO,
                            rule="high_complexity",
                            message=f"Function {node.name} has high nesting depth ({depth})",
                            line=node.lineno,
                            suggestion="Consider refactoring to reduce complexity"
                        ))

        logger.debug("Layer 4: Quality check complete (%d violations)", len(violations))
        return violations

    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of a function."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _calculate_score(self, violations: list[GuardrailViolation]) -> float:
        """
        Calculate quality score (0-100) based on violations.

        Scoring:
        - Start at 100
        - BLOCK: -20 points each
        - WARN: -5 points each
        - INFO: -1 point each
        """
        score = 100.0

        for v in violations:
            if v.severity == GuardrailSeverity.BLOCK:
                score -= 20
            elif v.severity == GuardrailSeverity.WARN:
                score -= 5
            elif v.severity == GuardrailSeverity.INFO:
                score -= 1

        return max(0.0, score)  # Don't go below 0


def format_guardrail_report(result: GuardrailResult) -> str:
    """Format guardrail result as a human-readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append("🛡️  CODE QUALITY GUARDRAILS REPORT")
    lines.append("=" * 70)
    lines.append(f"Status: {'✅ PASS' if result.passed else '❌ FAIL'}")
    lines.append(f"Quality Score: {result.score:.1f}/100")
    lines.append(f"Total Violations: {len(result.violations)}")
    lines.append(f"  🔴 Blocking: {len(result.blocking_violations())}")
    lines.append(f"  🟡 Warnings: {sum(1 for v in result.violations if v.severity == GuardrailSeverity.WARN)}")
    lines.append(f"  ℹ️  Info: {sum(1 for v in result.violations if v.severity == GuardrailSeverity.INFO)}")

    if result.violations:
        lines.append("\nViolations by Layer:")

        # Group by layer
        by_layer = {}
        for v in result.violations:
            by_layer.setdefault(v.layer, []).append(v)

        for layer, violations in by_layer.items():
            lines.append(f"\n[{layer.upper()}] {len(violations)} issue(s):")
            for v in violations:
                icon = {"block": "🔴", "warn": "🟡", "info": "ℹ️"}[v.severity.value]
                line_info = f" (line {v.line})" if v.line else ""
                lines.append(f"  {icon} {v.message}{line_info}")
                if v.suggestion:
                    lines.append(f"     💡 {v.suggestion}")

    lines.append("=" * 70)
    return "\n".join(lines)
