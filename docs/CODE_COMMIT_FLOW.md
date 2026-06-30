# Code Commit and Review Flow

This document explains how code is committed, pushed, and reviewed in the SDLC Agent pipeline.

## Problem Statement

**Question:** "During Code Review, the code is not committed & pushed to GitHub, then how will the code be reviewed?"

**Answer:** The code IS committed and pushed to GitHub BEFORE the PR is created and reviewed. Here's the complete flow.

## Stage 3: Code Generation Flow

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Code Generation & PR Creation                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 1. Generate Code from Stories            │
    │    - Parse approved backlog              │
    │    - Generate Python module              │
    │    - Create CodeFile objects             │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 2. Create Git Branch                     │
    │    - Branch from 'main'                  │
    │    - Name: feature/<story-slug>          │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 3. Write Files to Disk                   │
    │    - Write to src/ directory             │
    │    - Create parent dirs if needed        │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 4. Stage Files (git add)                 │
    │    - Add all generated files             │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 5. Commit Changes (git commit)           │
    │    - Message: "feat: <story>"            │
    │    - Include story IDs                   │
    │    - Co-authored by Claude               │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 6. Push to Remote (git push)             │
    │    - Push to origin/<branch>             │
    │    - Set upstream tracking               │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 7. Create GitHub PR                      │
    │    - POST to GitHub API                  │
    │    - Draft PR with description           │
    │    - Link to stories                     │
    └──────────────────────────────────────────┘
                        ↓
                   ✅ PR Ready
```

## Stage 4: Code Review Flow

At this point, the code is ALREADY on GitHub in a branch, so Stage 4 can review it:

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: Code Review                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 1. Get PR Details from Stage 3           │
    │    - PR number                           │
    │    - Branch name                         │
    │    - Files (from PullRequest object)     │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 2. Review Code Content                   │
    │    - Scan for security issues            │
    │    - Check coding standards              │
    │    - Validate logic                      │
    │    - Check test coverage                 │
    └──────────────────────────────────────────┘
                        ↓
    ┌──────────────────────────────────────────┐
    │ 3. Post Review Comments to GitHub        │
    │    - Inline comments on code lines       │
    │    - Summary comment with verdict        │
    │    - Grouped by severity/category        │
    └──────────────────────────────────────────┘
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
         [VERDICT]           [VERDICT]
          PASS ✅             FAIL ❌
              ↓                   ↓
         Continue          Return to Stage 3
         to Stage 5        to fix issues
```

## Code Implementation

### Stage 3: `stage3_code.py`

```python
def run(backlog, *, github, claude, inject_defect, use_real_github):
    # 1. Generate code
    files = [CodeFile(path=module_path, contents=contents)]
    branch = f"feature/{slugify(backlog.brief_title)}"
    
    # 2. For real GitHub: perform git operations
    if isinstance(github, GitHubRestClient):
        git_ops = GitOperations()
        
        # 3. Create branch
        git_ops.create_branch(branch)
        
        # 4. Write files to disk
        written_paths = git_ops.write_files(files)
        
        # 5. Stage files
        git_ops.stage_files(written_paths)
        
        # 6. Commit changes
        commit_sha = git_ops.commit_changes(message, backlog)
        
        # 7. Push to remote
        git_ops.push_branch(branch)
    
    # 8. Create PR (code already on GitHub)
    pr = github.open_pull_request(
        branch=branch,
        title=f"feat: {backlog.brief_title}",
        body=body,
        files=files,
        story_ids=story_ids
    )
    
    return pr
```

### Stage 4: `stage4_review.py`

```python
def run(pr, *, claude, github, post_comments):
    # 1. Review the code from PR object
    findings = []
    for file in pr.files:
        findings.extend(scan_file(file.path, file.contents))
    
    # 2. Create review report
    review = ReviewReport(
        pr_number=pr.number,
        findings=findings,
        verdict="pass" if no_blocking else "fail"
    )
    
    # 3. Post comments to GitHub
    if post_comments and github:
        github.post_review_comments(pr.number, review)
    
    return review
```

## Git Operations: `git_operations.py`

The `GitOperations` class handles all git commands:

```python
class GitOperations:
    def create_branch(self, branch_name: str) -> None:
        """Creates and checks out a new branch."""
        # git checkout -b feature/my-feature
    
    def write_files(self, files: list[CodeFile]) -> list[Path]:
        """Writes code files to disk."""
        # Write each file to its path
    
    def stage_files(self, file_paths: list[Path]) -> None:
        """Stages files for commit."""
        # git add src/file.py
    
    def commit_changes(self, message: str, backlog: StoryBacklog) -> str:
        """Commits staged changes."""
        # git commit -m "feat: <message>"
        # Returns commit SHA
    
    def push_branch(self, branch_name: str) -> None:
        """Pushes branch to remote."""
        # git push -u origin feature/my-feature
```

## Actual Git Commands Executed

When Stage 3 runs with real GitHub integration:

```bash
# 1. Create branch
git checkout main
git pull origin main
git checkout -b feature/card-freeze-service

# 2. Write file
# (Python writes: src/card_freeze_service.py)

# 3. Stage file
git add src/card_freeze_service.py

# 4. Commit
git commit -m "feat: Card Freeze Service

Implements user stories:
- US-001: As a customer, I want to freeze my card
- US-002: As a customer, I want to unfreeze my card

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 5. Push to remote
git push -u origin feature/card-freeze-service

# 6. Create PR via GitHub API
# POST https://api.github.com/repos/owner/repo/pulls
```

## Timeline

```
Time  Stage  Action                         Git State              GitHub State
────────────────────────────────────────────────────────────────────────────────
t0    S3     Generate code                  main branch           No PR
t1    S3     Create branch                  feature/xyz branch    No PR
t2    S3     Write files                    local changes         No PR
t3    S3     Commit                         local commit          No PR
t4    S3     Push                           remote branch ✓       Branch exists
t5    S3     Create PR                      remote branch ✓       PR #42 created
────────────────────────────────────────────────────────────────────────────────
t6    S4     Review code                    remote branch ✓       PR #42 (draft)
t7    S4     Post comments                  remote branch ✓       PR #42 + comments
────────────────────────────────────────────────────────────────────────────────
```

**Key Insight:** At time `t6` when Stage 4 starts, the code is already committed (t3), pushed (t4), and the PR exists (t5). Stage 4 reviews the committed code, not uncommitted changes.

## Verification

To verify this flow works:

### 1. Check Git History

```bash
# After Stage 3 completes
git log --oneline -5
# Should show: abc1234 feat: Card Freeze Service

git show HEAD
# Should show the committed code
```

### 2. Check Remote Branch

```bash
# Verify branch exists on GitHub
git ls-remote --heads origin
# Should list: refs/heads/feature/card-freeze-service
```

### 3. Check GitHub PR

```bash
# View PR on GitHub
gh pr view 42
# Or visit: https://github.com/owner/repo/pull/42
```

### 4. Check Review Comments

```bash
# View PR comments
gh pr view 42 --comments
```

## Mock vs Real Mode

### Mock Mode (No GITHUB_TOKEN)

```
Stage 3: Generate code → MockGitHubClient
         ✅ Files written to disk
         ✅ Git branch created
         ✅ Git commit created
         ❌ NOT pushed to GitHub (mock mode)
         ✅ Mock PR created (in-memory)

Stage 4: Review code → From committed files
         ✅ Review performed on committed code
         ❌ No comments posted to GitHub
         ✅ Review report generated
         ✅ Code is in git history for inspection
```

### Real Mode (GITHUB_TOKEN set)

```
Stage 3: Generate code → GitHubRestClient
         ✅ Files written to disk
         ✅ Git branch created
         ✅ Git commit created
         ✅ Pushed to GitHub
         ✅ Real PR created on GitHub

Stage 4: Review code → From PR files
         ✅ Review performed
         ✅ Comments posted to GitHub PR
         ✅ Summary comment posted
```

## Common Issues

### Issue 1: "PR has no code"

**Cause:** Stage 3 created PR but didn't push code first.

**Solution:** ✅ Fixed! Stage 3 now:
1. Writes files
2. Commits
3. Pushes
4. Then creates PR

### Issue 2: "Review can't access code"

**Cause:** Stage 4 tried to review before code was committed.

**Solution:** ✅ Fixed! Stage 4 receives PR object with files from Stage 3, and code is already on GitHub.

### Issue 3: "Branch doesn't exist on GitHub"

**Cause:** Push step failed or was skipped.

**Solution:** Check logs for push errors. Verify git credentials and permissions.

## Logs to Monitor

### Stage 3 Logs

```
INFO: Stage 3 starting (backend=live, is_live=True, inject_defect=False)
INFO: Using real GitHub - performing git operations
INFO: Creating branch feature/card-freeze-service from main
INFO: Created and checked out branch: feature/card-freeze-service
INFO: Writing file: src/card_freeze_service.py (2048 bytes)
INFO: Wrote 1 file(s) to disk
INFO: Staging file: src/card_freeze_service.py
INFO: Committing changes: feat: Card Freeze Service
INFO: Committed changes: abc12345
INFO: Pushing branch feature/card-freeze-service to remote
INFO: Successfully pushed branch: feature/card-freeze-service
INFO: Creating PR: branch=feature/card-freeze-service, title=feat: Card Freeze Service
INFO: Created PR #42: https://github.com/owner/repo/pull/42
```

### Stage 4 Logs

```
INFO: Stage 4 starting (backend=live, is_live=True)
🔍 Stage 4: Code Review Started
======================================================================
PR Number: #42
Files to review: 1
Review backend: live (Live LLM)
======================================================================

📄 Reviewing: src/card_freeze_service.py (150 lines)
   ⚠️  Found 2 issue(s):
      🟠 Line 42: [SECURITY] TLS verification disabled
      🔵 Line 15: [STANDARDS] Use logger, not print()

📝 Posting review comments to GitHub PR #42...
INFO: Posting 2 review comments on PR #42
INFO: Posted 2 inline review comments on PR #42
INFO: Posted comment on PR #42
✅ Successfully posted 2 review comments
```

## Summary

**The code is committed and pushed to GitHub BEFORE the PR is created**, ensuring that:

1. ✅ The PR points to real code on GitHub
2. ✅ Stage 4 can review actual committed code
3. ✅ Review comments appear on the correct lines
4. ✅ The workflow is auditable via git history
5. ✅ Other developers can pull the branch and see the code

The flow is: **Generate → Write → Commit → Push → Create PR → Review → Comment**

Not: ~~Generate → Create PR → Push (this would fail!)~~
