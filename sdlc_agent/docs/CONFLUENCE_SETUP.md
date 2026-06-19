# Confluence Integration Setup Guide

## ✅ Now Supports Confluence URLs!

The SDLC Agent can now fetch requirements directly from Confluence pages. Just paste the URL!

---

## 🔧 Setup (One-Time)

### Step 1: Get Your Atlassian API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Give it a name: `SDLC Agent`
4. Copy the token (you won't see it again!)

### Step 2: Configure .env File

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   # For Confluence Cloud (*.atlassian.net)
   CONFLUENCE_EMAIL=your.email@company.com
   CONFLUENCE_API_TOKEN=paste_your_token_here
   ```

   Or use the Atlassian-wide credentials:
   ```bash
   ATLASSIAN_EMAIL=your.email@company.com
   ATLASSIAN_TOKEN=paste_your_token_here
   ```

3. **Note:** If your Jira and Confluence are on the same Atlassian instance, you can use the same `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` for both!

### Step 3: Restart the Server

```bash
python -m sdlc_agent.web.app
```

---

## 🎯 How to Use

### 1. Go to Stage 1 - Requirement Ingestion

Open: http://127.0.0.1:5002

### 2. Paste Your Confluence URL

**Supported URL formats:**

✅ **Confluence Cloud:**
```
https://yourcompany.atlassian.net/wiki/spaces/PROJ/pages/12345/Requirements
```

✅ **Confluence Server/Data Center:**
```
https://confluence.yourcompany.com/display/SPACE/Page+Title?pageId=12345
https://confluence.yourcompany.com/pages/viewpage.action?pageId=12345
```

### 3. Click "Ingest Requirements"

The agent will:
1. ✅ Fetch the page from Confluence
2. ✅ Convert HTML to markdown
3. ✅ Parse user stories, acceptance criteria, NFRs
4. ✅ Identify gaps and generate questions
5. ✅ Save to `.claude/sdlc-state.json`

---

## 📝 Example Confluence Page Format

For best results, structure your Confluence page like this:

```markdown
# Feature Name

## Business Goal
- Increase customer satisfaction by 20%

## User Stories
- As a customer, I want to view my order history, so that I can track my purchases
- As an admin, I want to export reports, so that I can analyze trends

## Acceptance Criteria
- User can see last 30 orders
- Orders show date, amount, status
- Export generates CSV file

## Non-Functional Requirements
- Performance: Page load under 2 seconds
- Security: Requires authentication

## Out of Scope
- Mobile app (Phase 2)
- International orders
```

---

## 🔍 Troubleshooting

### Error: "Failed to fetch Confluence page"

**Check:**
1. ✅ Is your API token correct in `.env`?
2. ✅ Is your email correct?
3. ✅ Do you have permission to view the page?
4. ✅ Is the URL correct?

**Test your credentials:**
```bash
curl -u "your.email@company.com:your_api_token" \
  "https://yourcompany.atlassian.net/wiki/api/v2/pages/12345"
```

Should return JSON with page data.

### Error: "Please set CONFLUENCE_API_TOKEN"

You forgot to configure `.env` file. See Step 2 above.

### Error: "Could not extract page ID from URL"

The URL format isn't recognized. Make sure it's one of:
- `https://*.atlassian.net/wiki/spaces/*/pages/12345/*`
- `https://*/display/*?pageId=12345`
- `https://*/pages/viewpage.action?pageId=12345`

---

## 🎨 Supported Confluence Features

✅ **Text content** - Paragraphs, headings, lists  
✅ **Bold/Italic** - Converted to markdown  
✅ **Lists** - Bullet and numbered  
✅ **Headings** - H1-H4  
⚠️ **Tables** - Basic support (converted to text)  
⚠️ **Macros** - Removed (not converted)  
⚠️ **Attachments** - Not fetched  

---

## 🚀 Quick Test

### Test with a Public Confluence Page:

1. Find any Confluence page you have access to
2. Copy the URL
3. Paste into Stage 1
4. Click "Ingest Requirements"

### Or Test with Local File:

If you don't have Confluence credentials yet, you can still test with local files:

```
samples/brd_natwest_card_freeze.md
```

---

## 📊 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_EMAIL` | Yes (Cloud) | Your Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian |
| `CONFLUENCE_BASE_URL` | No | Only for Server/DC (e.g., `https://confluence.company.com`) |
| `ATLASSIAN_EMAIL` | Alternative | Works for both Jira & Confluence |
| `ATLASSIAN_TOKEN` | Alternative | Works for both Jira & Confluence |

---

## ✨ Tips

1. **Use the same token for Jira and Confluence** - If they're on the same Atlassian instance, set `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` once

2. **Keep your token secure** - Add `.env` to `.gitignore` (already done)

3. **Test with a simple page first** - Before using complex pages with macros and tables

4. **Local files still work!** - You can mix Confluence URLs and local `.md` files

---

## 🎉 You're Ready!

The UI now accepts:
- ✅ Confluence Cloud URLs (`*.atlassian.net/wiki/...`)
- ✅ Confluence Server URLs (`yourserver.com/display/...`)
- ✅ Local file paths (`samples/*.md`)

**Just paste and go!** 🚀
