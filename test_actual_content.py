#!/usr/bin/env python3
"""Test LLM extraction with the actual Confluence content"""
from sdlc_agent.integrations.anthropic_client import MockClaudeClient
import json

# The ACTUAL content from the server log
content = """# Test-page

Business goal
- Let NatWest retail customers freeze and unfreeze their debit cards instantly from the mobile app, reducing fraud-related call-centre contacts by 25%.

## Functional
- Customer can freeze an active debit card from the card details screen.
- Customer can unfreeze a previously frozen card after passing step-up authentication.
- Compliance officer can audit every freeze and unfreeze event for the last 24 months."""

system_prompt = """You are a Business Analyst extracting structured requirements from a document.

The document may contain:
- Formal user stories ("As a X, I want Y, so that Z")
- Bullet lists of features ("Customer can freeze card")
- Prose descriptions
- Mixed formats

Your job: Convert ALL functional requirements into structured user stories.

For each requirement, infer:
- persona (who) - from context (customer, agent, admin, etc.)
- want (what) - the action/feature
- so_that (why) - business value (infer from business goal if not explicit)
- acceptance_criteria - testable conditions

Return ONLY valid JSON in this exact structure (no markdown, no commentary):
{
  "epic": "Feature title",
  "stories": [
    {
      "as_a": "Customer",
      "i_want": "freeze my debit card from mobile app",
      "so_that": "I can prevent fraud immediately",
      "acceptance_criteria": ["Card status changes to FROZEN within 2 seconds"]
    }
  ],
  "acceptance_criteria": ["AC1 from doc", "AC2 from doc"],
  "nfr": ["Performance: response < 500ms"],
  "out_of_scope": ["Credit cards"],
  "dependencies": ["Auth service"]
}

If no requirements found, return: {"epic": "", "stories": [], "acceptance_criteria": [], "nfr": [], "out_of_scope": [], "dependencies": []}"""

user_prompt = f"""Extract structured requirements from this document:

---
{content}
---

Return only the JSON object."""

print("Testing LLM extraction with ACTUAL Confluence content...")
print("=" * 70)
print(f"Content ({len(content)} chars):")
print(content)
print("=" * 70)

claude = MockClaudeClient()
print(f"Backend: {claude.backend}\n")

result = claude.complete_json(
    system=system_prompt,
    user=user_prompt,
    max_tokens=4096,
    temperature=0.2,
)

print("\nResult:")
print("=" * 70)
if result:
    print(json.dumps(result, indent=2))

    stories = result.get("stories", [])
    acs = []
    for story in stories:
        acs.extend(story.get("acceptance_criteria", []))
    global_acs = result.get("acceptance_criteria", [])

    print("\n" + "=" * 70)
    print(f"[RESULT] Extracted:")
    print(f"  - {len(stories)} user stories")
    print(f"  - {len(acs)} story-level acceptance criteria")
    print(f"  - {len(global_acs)} global acceptance criteria")
    print(f"  - {len(result.get('nfr', []))} NFRs")
    print(f"  - {len(result.get('dependencies', []))} dependencies")

    if stories:
        print(f"\n[SUCCESS] Stories extracted:")
        for i, story in enumerate(stories, 1):
            print(f"  {i}. As a {story.get('as_a')}, I want {story.get('i_want')}")
    else:
        print("\n[FAIL] No stories extracted!")
else:
    print("None/empty result")
    print("[FAIL] LLM returned nothing")
