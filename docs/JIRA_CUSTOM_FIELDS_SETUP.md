# Jira Custom Fields Setup Guide

## Issue: Custom Field Errors

If you see errors like:
```
JiraError HTTP 400: Field 'customfield_10016' cannot be set. 
It is not on the appropriate screen, or unknown.
```

This means the custom field doesn't exist or isn't configured in your Jira project.

---

## Quick Fix (Recommended)

**The SDLC Agent now disables custom fields by default** to avoid these errors.

Jira cards are created successfully with:
- ✅ Summary
- ✅ Description (comprehensive with AC, DoD, Scope, etc.)
- ✅ Labels
- ✅ Priority
- ✅ Issue Type (Story)

**Custom fields are optional** and disabled by default.

---

## Enable Custom Fields (Optional)

### Step 1: Find Your Custom Field IDs

#### Option A: Using Jira REST API (Recommended)

```bash
# Replace with your Jira URL and credentials
curl -u your-email@example.com:your-api-token \
  https://yourinstance.atlassian.net/rest/api/2/field \
  | jq '.[] | select(.custom == true) | {id, name}'
```

**Example Output**:
```json
{
  "id": "customfield_10028",
  "name": "Story Points"
}
{
  "id": "customfield_10014",
  "name": "Epic Link"
}
```

#### Option B: Using Jira UI

1. Go to **Jira Settings** → **Issues** → **Custom Fields**
2. Find "Story Points" field
3. Click **Configure** → **Edit**
4. Look at the URL: `...customfield_10028...`
5. The number is your field ID

#### Option C: Inspect Element

1. Open a Jira story
2. Click **Edit**
3. Right-click on "Story Points" field → **Inspect**
4. Look for `id="customfield_XXXXX"`

---

### Step 2: Configure Environment Variables

Add to your `.env` file:

```bash
# Jira Custom Field Configuration
# Find your field IDs using the methods above

# Story Points field ID (optional)
JIRA_STORY_POINTS_FIELD_ID=customfield_10028

# Epic Link field ID (optional)
JIRA_EPIC_LINK_FIELD_ID=customfield_10014

# Epic Name field ID (for creating epics, optional)
JIRA_EPIC_NAME_FIELD_ID=customfield_10011
```

**Important**: Replace the field IDs with YOUR actual field IDs from Step 1!

---

### Step 3: Restart the Application

```bash
# Restart the Flask server
python -m sdlc_agent.web
```

---

## Test Custom Fields

```bash
# Check if environment variables are loaded
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('Story Points Field:', os.getenv('JIRA_STORY_POINTS_FIELD_ID'))
print('Epic Link Field:', os.getenv('JIRA_EPIC_LINK_FIELD_ID'))
"
```

**Expected output**:
```
Story Points Field: customfield_10028
Epic Link Field: customfield_10014
```

---

## Common Jira Custom Field IDs

These are **typical** field IDs, but they vary by Jira instance:

| Field | Common ID | Your ID |
|-------|-----------|---------|
| Story Points | `customfield_10016` or `customfield_10028` | _________ |
| Epic Link | `customfield_10014` | _________ |
| Epic Name | `customfield_10011` | _________ |
| Sprint | `customfield_10020` | _________ |

**Always verify your field IDs** - do not assume these are correct for your instance!

---

## Verify Field Configuration

### Check if Field Exists

```bash
curl -u email:token \
  https://yourinstance.atlassian.net/rest/api/2/field \
  | jq '.[] | select(.id == "customfield_10028")'
```

### Check if Field is on Screen

```bash
# Get field configuration for your project
curl -u email:token \
  "https://yourinstance.atlassian.net/rest/api/2/issue/createmeta?projectKeys=KAN&issuetypeNames=Story&expand=projects.issuetypes.fields" \
  | jq '.projects[0].issuetypes[0].fields | keys'
```

This shows all fields available when creating a Story in your project.

---

## Troubleshooting

### Error: "Field cannot be set"

**Cause**: Field ID is wrong or field isn't on the Story screen

**Solutions**:
1. Verify field ID using methods above
2. Check if field is added to Story screen:
   - Jira Settings → Issues → Screens
   - Find "Story" screen → Edit
   - Ensure "Story Points" is added
3. Disable the field by removing from `.env`

---

### Error: "Field is not on appropriate screen"

**Cause**: Field exists but isn't configured for Story issue type

**Solution**:
1. Go to **Jira Settings** → **Issues** → **Screens**
2. Find the screen used for Story creation
3. Click **Configure**
4. Add "Story Points" field to the screen

---

### Cards Created Without Story Points

**Expected behavior** - Story points are optional!

The comprehensive description includes a note about story points:
```
Story Points: 5 (Fibonacci estimation)
```

Even without the custom field, the information is preserved in:
- Description text
- Comments
- Labels

---

## Alternative: Use Description Only

If you don't want to configure custom fields, the story point estimation is already included in the card description:

```
h2. Estimation
Story Points: 5 (based on: 4 ACs, 2 dependencies, 1 risk)

Complexity: Medium
Effort: 3-5 days
```

---

## Summary

### Default Behavior (No Configuration)
✅ Cards created successfully  
✅ All details in description (AC, DoD, Scope)  
✅ Labels & priority work  
❌ Story points field empty (but in description)  
❌ No epic link (but epic mentioned in description)  

### With Custom Fields Configured
✅ Everything above  
✅ Story points in dedicated field  
✅ Epic link as clickable relation  
✅ Sprint assignment (if configured)  

**Both approaches work!** Choose based on your needs.

---

## Example: Complete `.env` Configuration

```bash
# Jira Connection (Required)
JIRA_URL=https://yourinstance.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=KAN

# Jira Automation (Optional)
JIRA_AUTO_STATUS=Ready for Dev

# Custom Fields (Optional - find your IDs first!)
# JIRA_STORY_POINTS_FIELD_ID=customfield_10028
# JIRA_EPIC_LINK_FIELD_ID=customfield_10014
# JIRA_EPIC_NAME_FIELD_ID=customfield_10011
```

**Uncomment and set field IDs only after finding YOUR actual field IDs!**

---

## Quick Reference

| Task | Command |
|------|---------|
| Find all custom fields | `curl -u email:token https://instance.atlassian.net/rest/api/2/field \| jq '.[] \| select(.custom==true)'` |
| Find Story Points field | `curl ... \| jq '.[] \| select(.name=="Story Points")'` |
| Check field on screen | See "Verify Field Configuration" section above |
| Test environment vars | `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('JIRA_STORY_POINTS_FIELD_ID'))"` |

---

## Need Help?

1. **Custom field errors** → Disable custom fields (remove from `.env`)
2. **Story points not showing** → Check field ID and screen configuration
3. **Epic creation fails** → Disable epic creation in `plan_skill.py`
4. **Cards created successfully** → You're good! Custom fields are optional.

**Remember**: The comprehensive description includes ALL information even without custom fields!
