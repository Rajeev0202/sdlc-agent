# Fix: Web App Now Commits Code

## The Issue You Found (Again!)

> "Code Stage is Completed but still the Code is not committed."

**You were right AGAIN!** Even though I fixed `stage3_code.py`, the **web app uses a different code path** (`BuildSkillAutomation`) that was NOT committing files.

## Root Cause

The web app uses `BuildSkillAutomation` class instead of calling `stage3_code.run()` directly:

```python
# Web app routes.py:
skill_automation = BuildSkillAutomation(ROOT)
pr = skill_automation.run(backlog, inject_defect=inject)  # ❌ Only in-memory!
```

**Problem:** `BuildSkillAutomation.run()` only:
- ✅ Generated code files (in-memory)
- ✅ Created PR object (in-memory)
- ❌ NEVER wrote files to disk
- ❌ NEVER committed to git
- ❌ NEVER pushed to GitHub

## The Fix

Updated `BuildSkillAutomation` to:
1. Generate code files
2. **Write files to disk** ⭐ NEW
3. **git add files** ⭐ NEW
4. **git commit** ⭐ NEW
5. **git push (if GitHub token)** ⭐ NEW
6. **Create GitHub PR (if GitHub token)** ⭐ NEW
7. Create PR model
8. Update state

## Code Changes

### Before (Broken)

```python
def run(self, backlog, inject_defect=False):
    # Generate files (in-memory)
    code_files = self._generate_code_files(backlog, inject_defect)
    
    # Create PR model (in-memory)
    pr = self._create_pull_request(backlog, code_files)
    
    # ❌ Files never written to disk!
    # ❌ Nothing committed to git!
    
    return pr
```

### After (Fixed)

```python
def run(self, backlog, inject_defect=False):
    # 1. Generate files (in-memory)
    code_files = self._generate_code_files(backlog, inject_defect)
    
    # 2. Commit files to git ✅ NEW!
    branch_name = f"feature/{backlog.brief_title}"
    self._commit_files_to_git(code_files, backlog, branch_name)
    
    # 3. Create PR model
    pr = self._create_pull_request(backlog, code_files, branch_name)
    
    # 4. Create real GitHub PR ✅ NEW!
    if self.github:
        pr = self._create_github_pr(pr)
    
    return pr

def _commit_files_to_git(self, files, backlog, branch_name):
    """NEW METHOD: Commit files to git."""
    # Create branch
    self.git_ops.create_branch(branch_name)
    
    # Write files to disk
    written_paths = self.git_ops.write_files(files)
    
    # Stage files
    self.git_ops.stage_files(written_paths)
    
    # Commit changes
    commit_sha = self.git_ops.commit_changes(message, backlog)
    
    # Push to remote (if GitHub token available)
    if self.github:
        self.git_ops.push_branch(branch_name)
```

## New Web App Behavior

### With GITHUB_TOKEN

```
User clicks "Run Stage 3" in web app
          ↓
BuildSkillAutomation.run()
          ↓
1. Generate code files
2. Create git branch              ✅ NEW
3. Write files to disk            ✅ NEW
4. git add files                  ✅ NEW
5. git commit                     ✅ NEW
6. git push to GitHub             ✅ NEW
7. Create GitHub PR               ✅ NEW
8. Return PR object
          ↓
Web app shows PR created
GitHub has the actual PR!
```

### Without GITHUB_TOKEN

```
User clicks "Run Stage 3" in web app
          ↓
BuildSkillAutomation.run()
          ↓
1. Generate code files
2. Create git branch              ✅ NEW
3. Write files to disk            ✅ NEW
4. git add files                  ✅ NEW
5. git commit                     ✅ NEW
6. Skip push (no token)           ⚠️  Not pushed
7. Skip GitHub PR (no token)      ⚠️  Not on GitHub
8. Return PR object
          ↓
Web app shows PR created
Files ARE committed locally!
```

## What You'll See in Web App

### Console Output (New)

```
[Stage 3] Generating code for 3 stories (backend: live)
[Stage 3] [1/3] LLM generating US-001...
[Stage 3] [2/3] LLM generating US-002...
[Stage 3] [3/3] LLM generating US-003...

[Stage 3] 📝 Committing files to git...          ← NEW
[Stage 3] ✅ Wrote 6 files to disk               ← NEW
[Stage 3] ✅ Committed: abc12345                 ← NEW
[Stage 3] ✅ Pushed branch to GitHub             ← NEW (if token set)

[Stage 3] 🚀 Creating GitHub PR...               ← NEW (if token set)
[Stage 3] ✅ GitHub PR created: #42              ← NEW (if token set)
```

### Git Verification

After Stage 3 completes, you can verify:

```bash
# Check branch was created
git branch
# Output: * feature/card-freeze-service

# Check commit was made
git log -1
# Output: feat: Card Freeze Service

# Check files were written
ls src/
# Output: us_001_feature.py, us_002_feature.py, ...

# Check files were committed
git show HEAD --stat
# Output: Shows the committed files
```

## Files Changed

1. **`sdlc_agent/skills/build_skill.py`**
   - Added `self.git_ops = GitOperations()` in `__init__`
   - Added `self.github = GitHubRestClient()` in `__init__` (if token available)
   - Updated `run()` to call `_commit_files_to_git()`
   - Added `_commit_files_to_git()` method ⭐ NEW
   - Added `_create_github_pr()` method ⭐ NEW
   - Updated `_create_pull_request()` to accept `branch_name` parameter

## Why This Happened

**Two code paths:**

1. **CLI Path** (python -m sdlc_agent.cli run):
   - Uses `stage3_code.run()` directly
   - ✅ I fixed this yesterday
   - ✅ Was already committing

2. **Web App Path** (http://localhost:5000):
   - Uses `BuildSkillAutomation.run()`
   - ❌ Was NOT committing
   - ✅ NOW FIXED!

The web app path was **completely separate** and had **its own implementation** that I missed!

## Verification Steps

### 1. Start Web App

```bash
python -m sdlc_agent.web.app
```

### 2. Run Stage 3 via Web UI

1. Navigate to http://localhost:5000
2. Load a BRD (Stage 1)
3. Generate stories (Stage 2)
4. Click "Run Stage 3" button

### 3. Check Git

```bash
# Should see new branch
git branch

# Should see commit
git log -1

# Should see files on disk
ls src/

# Should see files in git
git show HEAD --stat
```

### 4. Check GitHub (if token set)

1. Visit https://github.com/owner/repo/pulls
2. Should see new PR
3. Should see files in PR
4. Should see commits in PR

## Module Cache Issue

**Important:** If the web app is still running, you need to restart it!

```bash
# Stop the web app (Ctrl+C)

# Start it again
python -m sdlc_agent.web.app
```

Python caches imported modules, so the old `BuildSkillAutomation` code stays in memory until you restart the process.

## Summary

**Fixed both code paths:**

| Path | Before | After |
|------|--------|-------|
| **CLI** | ❌ Not committing | ✅ FIXED (yesterday) |
| **Web App** | ❌ Not committing | ✅ FIXED (today) |

**Now ALL paths commit code:**
- ✅ CLI (`stage3_code.run()`)
- ✅ Web App (`BuildSkillAutomation.run()`)
- ✅ Files written to disk
- ✅ Committed to git
- ✅ Pushed to GitHub (if token available)

---

**Status:** ✅ FIXED

Thank you for your persistence in catching these issues! The code is now correct in BOTH the CLI and Web App paths.
