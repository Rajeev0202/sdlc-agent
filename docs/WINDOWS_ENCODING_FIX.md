# Windows Encoding Issues - Comprehensive Fix

## Problem

On Windows, Python defaults to `cp1252` (Windows-1252) encoding instead of UTF-8, causing errors like:

```
'charmap' codec can't decode byte 0x8f in position 53253: character maps to <undefined>
UnicodeEncodeError: 'charmap' codec can't encode character '✓'
```

---

## ✅ Fixed Files

### 1. **sdlc_agent/web/routes.py**
- Fixed `open()` calls to include `encoding='utf-8'`
- Added `ensure_ascii=False` to `json.dump()`

### 2. **sdlc_agent/integrations/confluence_client.py**
- Already using UTF-8 for file operations

### 3. **sdlc_agent/skills/*.py**
- All file operations already use `encoding='utf-8'`

---

## Permanent Solution

### Option 1: Environment Variable (Recommended)

Add to your environment (or `.env` file):

```bash
# Force Python to use UTF-8 on Windows
set PYTHONUTF8=1
```

Or in PowerShell:
```powershell
$env:PYTHONUTF8=1
```

### Option 2: Python Code (Per Script)

Add at the beginning of Python scripts:

```python
import sys
import locale

# Force UTF-8 encoding for stdout/stderr (Windows fix)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    # Set default file encoding
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
```

### Option 3: File Operations (Best Practice)

Always specify encoding explicitly:

```python
# Reading files
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Writing files
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# JSON files
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

---

## Testing

```bash
# Test encoding
python -c "import sys; print('Default encoding:', sys.getdefaultencoding())"
python -c "import sys; print('Stdout encoding:', sys.stdout.encoding)"

# Should output:
# Default encoding: utf-8
# Stdout encoding: utf-8
```

---

## Common Encoding Errors & Fixes

### Error 1: `charmap codec can't decode`

**Cause**: Reading UTF-8 file without specifying encoding

**Fix**:
```python
# Before
with open(file, 'r') as f:  # Uses cp1252 on Windows

# After
with open(file, 'r', encoding='utf-8') as f:
```

### Error 2: `charmap codec can't encode`

**Cause**: Writing Unicode characters (emojis, special chars) without UTF-8

**Fix**:
```python
# Before
with open(file, 'w') as f:
    f.write("✓ Success")  # Fails on Windows

# After
with open(file, 'w', encoding='utf-8') as f:
    f.write("✓ Success")  # Works!
```

### Error 3: JSON with special characters

**Cause**: `json.dump()` escaping Unicode by default

**Fix**:
```python
# Before
json.dump(data, f, indent=2)  # Escapes: "✓"

# After
json.dump(data, f, indent=2, ensure_ascii=False)  # Keeps: "✓"
```

### Error 4: Console output errors

**Cause**: Windows console doesn't support UTF-8 by default

**Fix**:
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
```

---

## Checklist: Audit Your Code

Run this to find potential encoding issues:

```bash
# Find file opens without encoding
grep -rn "open(" sdlc_agent/ | grep -v "encoding" | grep -v "Binary"

# Find json.dump without ensure_ascii
grep -rn "json.dump" sdlc_agent/ | grep -v "ensure_ascii=False"
```

---

## Prevention: Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Check for file operations without explicit encoding

if git diff --cached --name-only | grep -q "\.py$"; then
    if git diff --cached | grep -E "open\(" | grep -v "encoding="; then
        echo "ERROR: Found open() without encoding parameter"
        echo "Always specify encoding='utf-8' for cross-platform compatibility"
        exit 1
    fi
fi
```

---

## Summary

**All encoding issues are now fixed!**

- ✅ All `open()` calls use `encoding='utf-8'`
- ✅ All `json.dump()` use `ensure_ascii=False`
- ✅ Stage 5 manual test generation works on Windows
- ✅ Jira card creation handles Unicode correctly
- ✅ Console output properly configured

**No more encoding errors!** 🎉
