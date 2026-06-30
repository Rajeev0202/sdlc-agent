# Quick Start: GitHub Integration

Get the SDLC Agent creating real PRs and posting review comments in 5 minutes.

## Step 1: Get Your GitHub Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Select scopes:
   - ✅ `repo` (all sub-permissions)
4. Click **"Generate token"**
5. **Copy the token** (starts with `ghp_`)

## Step 2: Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN = "ghp_your_token_here"
```

**Linux/Mac:**
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

**Make it permanent (.bashrc / .zshrc):**
```bash
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
source ~/.bashrc
```

## Step 3: Verify Configuration

```bash
# Check token is set
python -c "import os; print('✅ Token configured' if os.getenv('GITHUB_TOKEN') else '❌ Token missing')"

# Check repository remote
git remote -v
# Should show: origin  https://github.com/owner/repo.git (fetch)
```

## Step 4: Run the Pipeline

```bash
# Run with real GitHub integration
python -m sdlc_agent.cli run samples/brd_natwest_card_freeze.md
```

## What You'll See

### Stage 3 Output:
```
🔧 Stage 3: Code Generation Started
======================================================================
✅ Generated module: src/card_freeze_service.py
🌿 Created branch: feature/card-freeze-service
📤 Pushing to GitHub...
✅ Draft PR created: #42
   URL: https://github.com/owner/repo/pull/42
======================================================================
```

### Stage 4 Output:
```
🔍 Stage 4: Code Review Started
======================================================================
📄 Reviewing: src/card_freeze_service.py (150 lines)
   ⚠️  Found 2 issue(s):
      🟠 Line 42: [SECURITY] TLS verification disabled
      🔵 Line 15: [STANDARDS] Use logger, not print()

📝 Posting review comments to GitHub PR #42...
✅ Successfully posted 2 review comments

📋 Review Summary
======================================================================
Total findings: 2
  🟠 High:     1
  🔵 Low:      1

❌ VERDICT: FAIL - Fix blocking issues before proceeding
======================================================================
```

### On GitHub:

**Pull Request Created:**
- Title: `feat: Card Freeze Service`
- Description: Lists all stories and files
- Status: Draft
- Comments: Review findings with inline annotations

## Configuration Options

### Disable Review Comments (PRs only, no comments)

```bash
export POST_REVIEW_COMMENTS=false
```

### Use Mock Mode (Testing)

```bash
unset GITHUB_TOKEN  # Removes token
# Pipeline will use in-memory mock client
```

## Troubleshooting

### "GitHub token required" error
```bash
# Solution: Set the token
export GITHUB_TOKEN=ghp_your_token_here
```

### "401 Unauthorized" error
```bash
# Solution: Token is invalid, generate a new one
# https://github.com/settings/tokens
```

### "Could not determine repository" error
```bash
# Solution: Add GitHub remote
git remote add origin https://github.com/owner/repo.git
```

### Review comments not appearing
```bash
# Check logs for details
cat sdlc_agent_output/runs/latest/04_review.json

# Verify PR exists
gh pr view 42  # If you have gh CLI installed
```

## Next Steps

- 📖 Read full documentation: [GITHUB_INTEGRATION.md](./GITHUB_INTEGRATION.md)
- 🔧 Configure CI/CD: See "CI/CD Integration" section in full docs
- 🔐 Security: Review "Security Best Practices" section
- 🐛 Issues: Check "Troubleshooting" section for common problems

## Example: Full Pipeline Run

```bash
# 1. Set token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# 2. Run pipeline on a BRD
python -m sdlc_agent.cli run samples/brd_natwest_card_freeze.md

# 3. Check the created PR
echo "PR created at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/pulls"

# 4. Review comments posted automatically
# Visit the PR URL to see inline code review comments
```

## Success Checklist

- ✅ GitHub token generated with `repo` scope
- ✅ Token set in environment: `GITHUB_TOKEN`
- ✅ Git remote points to GitHub
- ✅ Pipeline runs without errors
- ✅ PR created on GitHub (check PRs tab)
- ✅ Review comments posted (check PR comments)

---

**Need Help?** See the full [GitHub Integration Guide](./GITHUB_INTEGRATION.md) for detailed information.
