"""Jira client — creates issues for the generated user stories using the JIRA Cloud REST API."""
from __future__ import annotations

import logging
import warnings
from jira import JIRA
from ..core.models import UserStory

# Suppress SSL warnings when verification is disabled
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def _trigger_jira_hook(card_key: str, summary: str | None = None):
    """Trigger the on_jira_card_created hook if harness is available."""
    try:
        from ..harness import get_harness
        harness = get_harness()
        harness._trigger_hook(
            "on_jira_card_created",
            card_key=card_key,
            summary=summary
        )
    except Exception:
        # Harness not available or hook failed - non-fatal
        pass


class MockJiraClient:
    """In-memory Jira client for testing and demo without credentials."""

    def __init__(self, project_key: str = "SCRUM") -> None:
        self.project_key = project_key
        self._issue_counter = 0
        self.created_issues: dict[str, dict] = {}

    def create_story(self, story: UserStory) -> str:
        """Create a mock JIRA issue for the given user story. Returns the issue key."""
        self._issue_counter += 1
        issue_key = f"{self.project_key}-{self._issue_counter}"
        self.created_issues[issue_key] = {
            'key': issue_key,
            'summary': story.want,
            'description': story.as_a_statement + "\n\nAcceptance Criteria:\n" + "\n".join(story.acceptance_criteria),
            'issuetype': 'Story',
            'story': story,
        }
        logger.info("Mock Jira: created issue %s for story %s", issue_key, story.id)

        # Trigger harness hook
        _trigger_jira_hook(card_key=issue_key, summary=story.want)

        return issue_key


class JiraClient:
    """Real Jira client using JIRA Cloud REST API."""

    def __init__(self, server_url: str, email: str, api_token: str, project_key: str = "SCRUM", auto_transition: str = None) -> None:
        self.server_url = server_url
        self.project_key = project_key
        self.auto_transition = auto_transition  # e.g., "Ready for QA"

        # Initialize JIRA client with SSL verification disabled and proxy disabled
        # WARNING: This is for testing purposes only - re-enable for production
        self.jira = JIRA(
            server=server_url,
            basic_auth=(email, api_token),
            options={
                'verify': False,  # Disable SSL verification
                'proxies': {}     # Disable proxy
            }
        )
        logger.info("Real Jira client initialized for %s (project: %s, auto_transition: %s, SSL verify: False)",
                    server_url, project_key, auto_transition)

    def create_story(self, story: UserStory, epic_key: str = None, story_points: int = None) -> str:
        """
        Create a comprehensive JIRA issue for the given user story.

        Args:
            story: UserStory object with all story details
            epic_key: Optional epic key to link this story to
            story_points: Optional story points (estimated effort)

        Returns:
            Issue key (e.g., "KAN-123")
        """
        # Build comprehensive description with all details
        description = self._build_comprehensive_description(story)

        # Build issue dictionary with all fields
        issue_dict = {
            'project': {'key': self.project_key},
            'summary': f"{story.persona}: {story.want}",  # More descriptive summary
            'description': description,
            'issuetype': {'name': 'Story'},  # Use Story type for proper Agile workflow
        }

        # Add optional fields (only standard fields to avoid errors)
        # Custom fields like Story Points are disabled by default

        # Labels (for categorization) - Standard Jira field
        labels = self._extract_labels(story)
        if labels:
            issue_dict['labels'] = labels

        # Priority (derived from story context) - Standard Jira field
        priority = self._infer_priority(story)
        if priority:
            issue_dict['priority'] = {'name': priority}

        # Components - Only add if configured in your Jira project
        # Disabled by default to avoid errors
        # components = self._extract_components(story)
        # if components:
        #     issue_dict['components'] = [{'name': c} for c in components]

        # CUSTOM FIELDS (disabled by default - configure via environment variables)

        # Story Points - Enable by setting JIRA_STORY_POINTS_FIELD_ID
        import os as _os
        story_points_field = _os.getenv('JIRA_STORY_POINTS_FIELD_ID')
        if story_points is not None and story_points_field:
            issue_dict[story_points_field] = story_points
            logger.debug(f"Added story points: {story_points}")

        # Epic Link - Enable by setting JIRA_EPIC_LINK_FIELD_ID
        epic_link_field = _os.getenv('JIRA_EPIC_LINK_FIELD_ID')
        if epic_key and epic_link_field:
            issue_dict[epic_link_field] = epic_key
            logger.debug(f"Linked to epic: {epic_key}")

        # Log what fields we're creating (for debugging)
        logger.debug(f"Creating Jira issue with fields: {list(issue_dict.keys())}")

        try:
            issue = self.jira.create_issue(fields=issue_dict)
            logger.info(
                "Real Jira: created issue %s for story %s (priority=%s, labels=%s)",
                issue.key,
                story.id,
                priority,
                labels
            )

            # Add comments for additional context (Definition of Done, etc.)
            try:
                self._add_issue_comments(issue, story)
            except Exception as comment_error:
                logger.warning(f"Failed to add comments to {issue.key}: {comment_error}")
                # Non-fatal - issue was created successfully

        except Exception as e:
            # Log the full error details for debugging
            logger.error("Failed to create Jira issue for %s: %s", story.id, str(e))
            logger.error("Issue fields attempted: %s", list(issue_dict.keys()))
            if hasattr(e, 'response'):
                response_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
                logger.error("Jira response: %s", response_text)

                # Provide helpful error message for common issues
                if 'customfield' in response_text:
                    logger.error(
                        "Custom field error detected. "
                        "To use custom fields, set environment variables:\n"
                        "  export JIRA_STORY_POINTS_FIELD_ID=customfield_XXXXX\n"
                        "  export JIRA_EPIC_LINK_FIELD_ID=customfield_YYYYY\n"
                        "Find your field IDs: curl -u email:token "
                        "https://yourinstance.atlassian.net/rest/api/2/field"
                    )
            raise

        # Auto-transition to specified status if configured
        if self.auto_transition:
            try:
                self._transition_issue(issue, self.auto_transition)
            except Exception as e:
                logger.warning("Failed to transition %s to '%s': %s", issue.key, self.auto_transition, e)

        # Try to add to active sprint
        try:
            self._add_to_active_sprint(issue)
        except Exception as e:
            logger.warning("Failed to add %s to sprint: %s", issue.key, e)

        # Trigger harness hook
        _trigger_jira_hook(card_key=issue.key, summary=story.want)

        return issue.key

    def transition_to_status(self, issue_key: str, target_status: str, max_hops: int = 4) -> bool:
        """Transition an issue (by key) to the target status.

        Handles multi-step workflows automatically (e.g., To-Do -> In Progress -> Done).
        Returns True on success, False if no path found.
        """
        try:
            target_normalized = target_status.lower().replace(" ", "").replace("-", "")

            for hop in range(max_hops):
                issue = self.jira.issue(issue_key)
                current_status = issue.fields.status.name
                current_normalized = current_status.lower().replace(" ", "").replace("-", "")

                # Already at target?
                if current_normalized == target_normalized:
                    logger.info(f"{issue_key} reached '{target_status}' in {hop} hop(s)")
                    return True

                # Try direct transition first
                transitions = self.jira.transitions(issue)
                direct = self._find_transition(transitions, target_status)

                if direct:
                    self.jira.transition_issue(issue, direct['id'])
                    logger.info(f"{issue_key}: '{current_status}' -> '{direct['to']['name']}'")
                    continue

                # Find best intermediate step (prefer "In Progress" over "Blocked")
                preferred_order = ["in progress", "review", "ready"]
                intermediate = None
                for pref in preferred_order:
                    for t in transitions:
                        to_name = t['to']['name'].lower()
                        if pref in to_name:
                            intermediate = t
                            break
                    if intermediate:
                        break

                if not intermediate:
                    # Fallback: take any forward transition (skip "Blocked")
                    for t in transitions:
                        if "block" not in t['to']['name'].lower() and \
                           t['to']['name'].lower() != current_status.lower():
                            intermediate = t
                            break

                if not intermediate:
                    available = [t['to']['name'] for t in transitions]
                    logger.warning(f"{issue_key}: no forward transition. Available: {available}")
                    return False

                self.jira.transition_issue(issue, intermediate['id'])
                logger.info(f"{issue_key}: '{current_status}' -> '{intermediate['to']['name']}' (intermediate)")

            # Verify final status
            issue = self.jira.issue(issue_key)
            final_normalized = issue.fields.status.name.lower().replace(" ", "").replace("-", "")
            return final_normalized == target_normalized

        except Exception as e:
            logger.error("Failed to transition %s to %s: %s", issue_key, target_status, e)
            return False

    def _find_transition(self, transitions, target_status: str):
        """Find a transition that leads to target_status (case/space/hyphen-insensitive)."""
        target_normalized = target_status.lower().replace(" ", "").replace("-", "")
        for t in transitions:
            name_normalized = t['name'].lower().replace(" ", "").replace("-", "")
            to_normalized = t['to']['name'].lower().replace(" ", "").replace("-", "")
            if target_normalized == name_normalized or target_normalized == to_normalized:
                return t
        return None

    def _transition_issue(self, issue, target_status: str) -> None:
        """Transition issue to target status."""
        transitions = self.jira.transitions(issue)

        # Normalize target: remove spaces, hyphens, lowercase for fuzzy matching
        target_normalized = target_status.lower().replace(" ", "").replace("-", "")

        # Find transition that leads to target status
        target_transition = None
        for t in transitions:
            name_normalized = t['name'].lower().replace(" ", "").replace("-", "")
            to_normalized = t['to']['name'].lower().replace(" ", "").replace("-", "")
            if target_normalized == name_normalized or target_normalized == to_normalized:
                target_transition = t
                break

        if target_transition:
            self.jira.transition_issue(issue, target_transition['id'])
            logger.info("Transitioned %s to '%s'", issue.key, target_transition['to']['name'])
        else:
            available = [t['to']['name'] for t in transitions]
            logger.warning("No transition found for '%s'. Available: %s", target_status, available)

    def _add_to_active_sprint(self, issue) -> None:
        """Add issue to active sprint if one exists."""
        try:
            boards = self.jira.boards(projectKeyOrID=self.project_key)
            if not boards:
                return

            board = boards[0]
            sprints = self.jira.sprints(board.id, state='active')

            if sprints:
                sprint = sprints[0]
                self.jira.add_issues_to_sprint(sprint.id, [issue.key])
                logger.info("Added %s to sprint '%s'", issue.key, sprint.name)
        except Exception as e:
            logger.debug("Could not add to sprint: %s", e)

    def _build_comprehensive_description(self, story: UserStory) -> str:
        """Build a comprehensive Jira description with all story details."""
        sections = []

        # User Story
        sections.append("h2. User Story")
        sections.append(f"*As a* {story.persona}")
        sections.append(f"*I want* {story.want}")
        sections.append(f"*So that* {story.so_that}")
        sections.append("")

        # Acceptance Criteria
        if story.acceptance_criteria:
            sections.append("h2. Acceptance Criteria")
            for i, ac in enumerate(story.acceptance_criteria, 1):
                sections.append(f"[ ] *AC{i}:* {ac}")
            sections.append("")

        # Definition of Done
        sections.append("h2. Definition of Done")
        sections.append("[ ] Code implemented and unit tested")
        sections.append("[ ] Code review completed and approved")
        sections.append("[ ] All acceptance criteria verified")
        sections.append("[ ] Integration tests passing")
        sections.append("[ ] Documentation updated")
        sections.append("")

        # Dependencies
        if story.dependencies:
            sections.append("h2. Dependencies")
            for dep in story.dependencies:
                sections.append(f"* {dep}")
            sections.append("")

        # Technical Scope
        sections.append("h2. Technical Scope")
        sections.append("*In Scope:* Implementation, unit tests, integration")
        sections.append("*Out of Scope:* UI/UX design (unless explicit), infrastructure changes")
        sections.append("")

        # Risks
        if story.risks:
            sections.append("h2. Risks")
            for risk in story.risks:
                sections.append(f"* {risk}")
            sections.append("")

        return "\n".join(sections)

    def _extract_labels(self, story: UserStory) -> list[str]:
        """Extract relevant labels from story context."""
        labels = []
        want_lower = story.want.lower()
        
        if "api" in want_lower: labels.append("backend")
        if "card" in want_lower: labels.append("card-management")
        if "payment" in want_lower: labels.append("payment")
        
        return labels[:5]

    def _infer_priority(self, story: UserStory) -> str:
        """Infer priority based on story context."""
        want_lower = story.want.lower()
        if any(k in want_lower for k in ["security", "fraud", "critical"]):
            return "High"
        return "Medium"

    def _extract_components(self, story: UserStory) -> list[str]:
        """Extract Jira components based on story context."""
        components = []
        want_lower = story.want.lower()
        
        if "card" in want_lower: components.append("Card Management")
        if "payment" in want_lower: components.append("Payments")
        
        return components

    def _add_issue_comments(self, issue, story: UserStory):
        """Add additional context as comments."""
        try:
            guidance = """h3. Implementation Guidance

Follow Controller-Service pattern
Add comprehensive tests
Update documentation"""
            self.jira.add_comment(issue, guidance)
        except Exception as e:
            logger.warning(f"Failed to add comments: {e}")
