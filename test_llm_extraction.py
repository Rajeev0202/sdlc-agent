#!/usr/bin/env python3
"""Test LLM extraction for minimal content"""
from sdlc_agent.integrations.anthropic_client import MockClaudeClient

# Simulate the minimal Confluence page content
content = """# Test-page

Customers want to view their account balance on the mobile app."""

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

print("Testing LLM extraction...")
print(f"Backend: {MockClaudeClient().backend}")
print("")

claude = MockClaudeClient()
result = claude.complete_json(
    system=system_prompt,
    user=user_prompt,
    max_tokens=4096,
    temperature=0.2,
)

print("Result type:", type(result))
print("Result:")
if result:
    import json
    print(json.dumps(result, indent=2))
else:
    print("None/empty")

if result and isinstance(result, dict):
    stories = result.get("stories", [])
    print(f"\n[OK] Extracted {len(stories)} stories")
    for i, story in enumerate(stories, 1):
        print(f"  Story {i}: {story.get('i_want', 'N/A')}")
else:
    print("\n[FAIL] No valid result from LLM")
