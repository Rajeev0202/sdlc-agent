# Comprehensive Jira Card Creation Guide

## Overview

The SDLC Agent now creates **comprehensive, production-ready Jira cards** with all necessary fields including:
- ✅ Detailed User Story format
- ✅ Acceptance Criteria (with checkboxes)
- ✅ Definition of Done
- ✅ Technical Scope (In/Out of Scope)
- ✅ Dependencies
- ✅ Risks & Mitigations
- ✅ Test Strategy
- ✅ Story Points (Fibonacci estimation)
- ✅ Labels & Components
- ✅ Priority (Auto-inferred)
- ✅ Epic linkage (for multiple stories)

---

## Enhanced Jira Card Structure

### **Example Jira Card**

**Story**: US-001 - Freeze Card

#### **Summary**
```
Customer: freeze my card via mobile app
```

#### **Description** (Jira Wiki Markup)

```
h2. User Story
*As a* Customer
*I want* freeze my card via mobile app
*So that* I can prevent fraudulent transactions immediately

h2. Acceptance Criteria
[ ] *AC1:* Given an authenticated customer, when they request to freeze their card, then the card status is updated to FROZEN within 2 seconds
[ ] *AC2:* Given an unauthenticated request, when freeze is attempted, then the request is rejected with HTTP 401
[ ] *AC3:* Given a frozen card, when the customer attempts a transaction, then the transaction is declined with reason "Card Frozen"
[ ] *AC4:* Given a successful freeze, when the operation completes, then an SMS notification is sent to the customer

h2. Definition of Done
[ ] Code implemented and unit tested
[ ] Code review completed and approved
[ ] All acceptance criteria verified
[ ] Integration tests passing
[ ] Documentation updated
[ ] Security review completed (if applicable)
[ ] Performance tested (if applicable)
[ ] Deployed to staging environment

h2. Dependencies
* Card Management Service v2.1
* Notification Service (SMS gateway)
* Authentication Service (OAuth2)

h2. Technical Scope
*In Scope:*
* Implementation of: freeze my card via mobile app
* Unit tests for all new code
* Integration with existing services

*Out of Scope:*
* UI/UX design changes (unless explicitly mentioned)
* Database schema migrations (unless required)
* Infrastructure/DevOps changes (unless required)

h2. Risks & Mitigations
* External API latency - Mitigation: Implement timeout handling
* SMS delivery delays - Mitigation: Async notification with retry logic

h2. Technical Notes
* Follow NatWest coding standards
* Use Controller-Service architecture pattern
* Ensure proper error handling and logging
* Add audit trail for sensitive operations
* Validate all user inputs

h2. Test Strategy
*Unit Tests:*
* Test each acceptance criterion
* Test error cases and edge conditions
* Achieve >= 80% code coverage

*Integration Tests:*
* Test API endpoints end-to-end
* Verify integration with dependent services
```

#### **Fields**

| Field | Value |
|-------|-------|
| **Issue Type** | Story |
| **Priority** | High *(fraud prevention)* |
| **Story Points** | 5 *(Fibonacci)* |
| **Labels** | `customer`, `card-management`, `security`, `backend` |
| **Components** | Card Management |
| **Epic Link** | KAN-100 (Card Management Epic) |
| **Status** | To Do → Ready for Dev *(auto-transitioned)* |
| **Sprint** | Current Sprint *(auto-added)* |

#### **Comments** (Auto-added)

**Comment 1: Implementation Guidance**
```
h3. Implementation Guidance

*Suggested Approach:*
1. Review existing code in related modules
2. Follow Controller-Service architecture pattern
3. Implement business logic in service layer
4. Add comprehensive unit tests (TDD approach)
5. Update API documentation

*Code Location:*
* Controller: `src/controllers/card_controller.py`
* Service: `src/services/card_service.py`
* Tests: `tests/services/test_card_service.py`

*Review Checklist:*
* [ ] No hardcoded credentials or secrets
* [ ] Proper error handling and logging
* [ ] Input validation implemented
* [ ] Audit logging for sensitive operations
* [ ] Documentation updated
```

---

## Story Point Estimation

### **Automatic Fibonacci Estimation**

The system estimates story points based on:

1. **Complexity** (Acceptance Criteria count)
   - 1-2 ACs → +1 point
   - 3-4 ACs → +3 points
   - 5+ ACs → +5 points

2. **Dependencies** (External services)
   - Each dependency → +2 points

3. **Risks** (Unknowns/Uncertainties)
   - Each risk → +1 point

4. **Technical Complexity** (Keywords)
   - "integrate", "migration", "security", "authentication" → +2 points

**Fibonacci Scale**: 1, 2, 3, 5, 8, 13

### **Examples**

| Story | ACs | Deps | Risks | Keywords | Calculation | Points |
|-------|-----|------|-------|----------|-------------|--------|
| View balance | 2 | 1 | 0 | - | 1 + 2 = 3 | **3** |
| Freeze card | 4 | 2 | 1 | security | 3 + 4 + 1 + 2 = 10 | **13** |
| Update profile | 3 | 0 | 0 | - | 3 | **3** |
| Payment integration | 5 | 3 | 2 | integrate | 5 + 6 + 2 + 2 = 15 | **13** |

---

## Epic Creation

### **When Epics Are Created**

Epics are automatically created when:
- ✅ More than 3 stories in a backlog
- ✅ Using real Jira client (not mock)
- ✅ Stories share a common theme

### **Epic Structure**

**Epic Name**: Extracted from brief title or common keywords

**Epic Description**:
```
h2. Epic Overview
This epic groups 5 related user stories.

h2. Stories Included
* US-001: Customer - freeze my card via mobile app
* US-002: Customer - unfreeze my previously frozen card
* US-003: Customer - view card freeze history
* US-004: Admin - view all frozen cards in system
* US-005: System - auto-freeze card on suspicious activity

h2. Business Value
* Enable customers to prevent fraud immediately
* Reduce fraud losses by 40%
* Improve customer satisfaction
```

### **Story-Epic Linking**

All stories are automatically linked to the epic via the **Epic Link** field.

**Jira Board View**:
```
Epic: Card Management (KAN-100)
├── KAN-101: Freeze card (5 pts)
├── KAN-102: Unfreeze card (3 pts)
├── KAN-103: View freeze history (3 pts)
├── KAN-104: Admin view (5 pts)
└── KAN-105: Auto-freeze (8 pts)
     Total: 24 pts
```

---

## Labels & Components

### **Auto-Generated Labels**

Labels are extracted from story context:

| Keyword in "I want" | Label |
|---------------------|-------|
| "api", "endpoint", "service" | `backend` |
| "ui", "screen", "page" | `frontend` |
| "payment", "transaction" | `payment` |
| "card", "freeze" | `card-management` |
| "auth", "login" | `authentication` |
| "security", "audit" | `security` |
| "database", "migration" | `data` |

**Plus** persona-based label:
- Story persona: "Customer" → Label: `customer`
- Story persona: "Admin" → Label: `admin`

### **Auto-Assigned Components**

Components are matched to keywords:

| Keyword | Component |
|---------|-----------|
| "card" | Card Management |
| "payment" | Payments |
| "account" | Account Management |
| "auth" | Authentication |
| "notification" | Notifications |
| "report" | Reporting |

---

## Priority Inference

### **Automatic Priority Assignment**

Priority is inferred from story keywords:

| Keywords | Priority |
|----------|----------|
| "security", "fraud", "critical", "compliance", "regulatory" | **High** |
| "customer", "payment", "transaction", "important" | **Medium** |
| Default | **Medium** |

### **Override Priority**

To manually set priority, edit the story after creation in Jira.

---

## Custom Field Configuration

### **Common Jira Custom Field IDs**

The system uses standard custom field IDs. **Adjust these** for your Jira instance:

```python
# sdlc_agent/integrations/jira_client.py

# Story Points
'customfield_10016': story_points  # Change ID if different

# Epic Link
'customfield_10014': epic_key  # Change ID if different

# Epic Name (for epics themselves)
'customfield_10011': epic_name  # Change ID if different
```

### **How to Find Your Custom Field IDs**

1. **Via Jira UI**:
   - Edit a story → Inspect element → Find field ID

2. **Via REST API**:
   ```bash
   curl -u email:token \
     https://yourinstance.atlassian.net/rest/api/2/field \
     | jq '.[] | select(.name | contains("Story Points"))'
   ```

3. **Update the code**:
   ```python
   # Find this section in jira_client.py
   if story_points is not None:
       try:
           issue_dict['customfield_XXXXX'] = story_points  # ← Change XXXXX
       except Exception:
           logger.debug("Story points field not available")
   ```

---

## Multiple Cards Strategy

### **Decomposition Rules**

The LLM decomposes requirements into multiple cards based on:

1. **By Microservice/Module**
   - "Customer card freeze" → Separate story
   - "Admin view frozen cards" → Separate story

2. **By Layer**
   - "Freeze card API" → Backend story
   - "Freeze card UI" → Frontend story

3. **By Integration Boundary**
   - "Integrate with Card Service" → Story 1
   - "Integrate with Notification Service" → Story 2

4. **By User Journey Step**
   - "Request freeze" → Story 1
   - "Confirm freeze" → Story 2
   - "Send notification" → Story 3

### **Example: Multi-Card Generation**

**Input Requirement**:
> "Customers should be able to freeze and unfreeze their cards via the mobile app. Admins should be able to view all frozen cards."

**Generated Cards**:

1. **KAN-101**: Customer - freeze my card via mobile app (5 pts)
2. **KAN-102**: Customer - unfreeze my previously frozen card (3 pts)
3. **KAN-103**: Admin - view all frozen cards in the system (5 pts)
4. **Epic**: Card Management (KAN-100) - Groups all 3 stories

---

## Configuration

### **Enable Comprehensive Cards**

Already enabled by default! The enhanced `create_story()` method is automatically used.

### **Customize Fields**

Edit `sdlc_agent/integrations/jira_client.py`:

```python
def _build_comprehensive_description(self, story: UserStory) -> str:
    # Modify sections as needed
    sections.append("h2. Custom Section")
    sections.append("Your custom content here")
```

### **Add More Labels**

Edit `_extract_labels()` method:

```python
def _extract_labels(self, story: UserStory) -> list[str]:
    labels = []

    # Add your custom logic
    if "mobile" in story.want.lower():
        labels.append("mobile-app")

    if "api" in story.want.lower():
        labels.append("rest-api")

    return labels
```

---

## Testing

### **Test Jira Card Creation**

```bash
# Set environment variables
export JIRA_URL="https://yourinstance.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="KAN"

# Run Stage 2
python -c "
from sdlc_agent.integrations.jira_client import JiraClient
from sdlc_agent.core.models import UserStory

# Create client
client = JiraClient(
    server_url='https://yourinstance.atlassian.net',
    email='your-email@example.com',
    api_token='your-api-token',
    project_key='KAN'
)

# Create test story
story = UserStory(
    id='TEST-001',
    persona='Customer',
    want='freeze my card via mobile app',
    so_that='prevent fraud immediately',
    acceptance_criteria=[
        'Card status updates to FROZEN within 2 seconds',
        'Unauthenticated requests are rejected with HTTP 401',
    ],
    dependencies=['Card Service', 'Notification Service'],
    risks=['External API latency']
)

# Create comprehensive card
issue_key = client.create_story(story, story_points=5)
print(f'Created: {issue_key}')
"
```

### **Verify in Jira**

1. Open the created card
2. Check all sections are present
3. Verify story points field
4. Check labels and components
5. Review comments

---

## Best Practices

### ✅ **Do's**

1. **Review auto-generated cards** before sprint planning
2. **Adjust story points** if estimation seems off
3. **Add more context** in comments if needed
4. **Link to design docs** or technical specs
5. **Update Definition of Done** for your team's standards

### ❌ **Don'ts**

1. **Don't skip PO approval** before creating cards
2. **Don't create duplicate cards** - check for existing stories first
3. **Don't ignore custom field errors** - configure field IDs properly
4. **Don't create epics manually** - let the system handle it

---

## Troubleshooting

### **Issue**: Custom field errors

**Solution**: Update field IDs in `jira_client.py` to match your Jira instance

### **Issue**: Epic not created

**Check**:
- More than 3 stories?
- Using real Jira client (not mock)?
- Epic issue type enabled in project?

### **Issue**: Story points not showing

**Solution**: 
1. Find correct field ID for Story Points
2. Update `customfield_XXXXX` in code
3. Ensure field is available in your issue type

---

## Summary

**Comprehensive Jira cards include**:
- ✅ Full user story (As a/I want/So that)
- ✅ Checkboxed Acceptance Criteria
- ✅ Definition of Done checklist
- ✅ Technical scope (In/Out)
- ✅ Dependencies list
- ✅ Risks & mitigations
- ✅ Test strategy
- ✅ Story points (Fibonacci)
- ✅ Auto-inferred priority
- ✅ Auto-generated labels & components
- ✅ Epic linkage (3+ stories)
- ✅ Implementation guidance (comments)

**All cards are sprint-ready and production-quality!** 🎯
