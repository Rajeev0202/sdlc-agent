# Web Deployment with Harness

## Running via Uvicorn

### ✅ Yes, Harness Works Automatically!

When you run the SDLC agent web app via uvicorn, the harness and all hooks are **automatically initialized**.

## How It Works

### 1. Uvicorn Starts the App

```bash
uvicorn sdlc_agent.web.app:app --host 0.0.0.0 --port 8000
```

### 2. Flask App Module Loads

```python
# sdlc_agent/web/app.py
from ..bootstrap import ensure_harness
_harness = ensure_harness()  # ← Runs when module loads
```

### 3. Harness Auto-Initializes

```
uvicorn starts
    ↓
Loads sdlc_agent.web.app module
    ↓
ensure_harness() called (module-level)
    ↓
Harness initialized with auto_register_hooks=True
    ↓
All 4 hooks registered:
    ✅ on_stage_transition
    ✅ on_jira_card_created
    ✅ on_coverage_measured
    ✅ on_git_push_attempt
    ↓
Web app ready with hooks active!
```

### 4. Requests Use Hooks

When web requests create Jira cards:

```
User clicks "Plan" button
    ↓
POST /api/plan
    ↓
stage2_stories.run()
    ↓
jira_client.create_story()
    ↓
_trigger_jira_hook()  ← Hook fires!
    ↓
on_jira_card_created() executes
    ↓
Card tracked in harness.state.jira_creates ✅
```

## Verification

### Check Harness in Web App

Add this endpoint to verify (optional):

```python
# sdlc_agent/web/app.py
from ..harness import get_harness

@app.route("/api/harness/status")
def harness_status():
    """Check if harness is initialized with hooks."""
    harness = get_harness()
    return jsonify({
        "initialized": True,
        "hooks_registered": harness._hooks_registered,
        "hook_events": list(harness._hooks.keys()),
        "hook_counts": {
            event: len(callbacks)
            for event, callbacks in harness._hooks.items()
        }
    })
```

Then test:

```bash
# Start server
uvicorn sdlc_agent.web.app:app --reload

# Check harness status
curl http://localhost:8000/api/harness/status
```

Expected response:

```json
{
  "initialized": true,
  "hooks_registered": true,
  "hook_events": [
    "on_stage_transition",
    "on_jira_card_created",
    "on_coverage_measured",
    "on_git_push_attempt"
  ],
  "hook_counts": {
    "on_stage_transition": 1,
    "on_jira_card_created": 1,
    "on_coverage_measured": 1,
    "on_git_push_attempt": 1
  }
}
```

## Running the Web App

### Development Mode

```bash
# With auto-reload
uvicorn sdlc_agent.web.app:app --reload --port 8000

# With specific host
uvicorn sdlc_agent.web.app:app --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# With multiple workers (hooks work per-worker)
uvicorn sdlc_agent.web.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

**Note**: Each worker process gets its own harness instance with hooks registered.

### With Gunicorn

```bash
gunicorn sdlc_agent.web.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Deployment Scenarios

### 1. Local Development

```bash
uvicorn sdlc_agent.web.app:app --reload
```

✅ Harness initialized  
✅ Hooks registered  
✅ Auto-reload preserves initialization  

### 2. Docker Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["uvicorn", "sdlc_agent.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t sdlc-agent .
docker run -p 8000:8000 sdlc-agent
```

✅ Harness initialized on container start  
✅ Hooks work in containerized environment  

### 3. Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sdlc-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: web
        image: sdlc-agent:latest
        command: ["uvicorn", "sdlc_agent.web.app:app", "--host", "0.0.0.0"]
        ports:
        - containerPort: 8000
```

✅ Each pod gets harness with hooks  
✅ Works across all replicas  

### 4. Cloud Functions / Serverless

For serverless (AWS Lambda, Google Cloud Functions), harness initializes on cold start:

```python
# handler.py
from sdlc_agent.web.app import app

# Harness initialized when module loads
# Subsequent requests reuse the same instance

def handler(event, context):
    # Hooks already active
    return app(event, context)
```

✅ Cold start: harness initializes  
✅ Warm requests: reuses harness  

## State Persistence in Web

The harness state (`.claude/sdlc-state.json`) is process-local by default.

### Single Worker

```bash
uvicorn sdlc_agent.web.app:app --workers 1
```

✅ State shared across requests  
✅ Works as expected  

### Multiple Workers

```bash
uvicorn sdlc_agent.web.app:app --workers 4
```

⚠️ Each worker has **separate** state  
💡 Use shared storage for multi-worker:

```python
# Configure shared state backend
harness.config.state_file = Path("/shared/sdlc-state.json")
```

Or use database/Redis for state.

## Observability in Web

Observability data (traces, logs, metrics) is written to `.claude/observability/`:

```
.claude/
└── observability/
    ├── traces.jsonl    # Tool execution spans
    ├── logs.jsonl      # Structured logs
    └── metrics.json    # Aggregated metrics
```

### Multi-Worker Considerations

Each worker writes to the same files:

- ✅ JSONL files (traces, logs) - safe for concurrent append
- ⚠️ JSON files (metrics) - may need locking

For production multi-worker, consider:
- Centralized logging (e.g., Elasticsearch, CloudWatch)
- Distributed tracing (e.g., Jaeger, Zipkin)
- Metrics aggregation (e.g., Prometheus)

## Environment Variables

Configure harness behavior via environment:

```bash
# .env or export
export COVERAGE_THRESHOLD=80
export ENABLE_OBSERVABILITY=true
export ENABLE_HOOKS=true
export SDLC_AGENT_RUNS_DIR=./runs
```

Then start uvicorn:

```bash
uvicorn sdlc_agent.web.app:app
```

Harness reads these on initialization.

## Troubleshooting

### Check if Harness is Initialized

```python
# In web route
from ..harness import get_harness

@app.route("/debug/harness")
def debug_harness():
    harness = get_harness()
    return {
        "initialized": True,
        "hooks_registered": harness._hooks_registered,
        "state_stage": harness.state.stage,
        "trace_id": harness.state.trace_id,
        "jira_cards_tracked": len(harness.state.jira_creates)
    }
```

### Verify Hooks Fire

```python
# Create test endpoint
@app.route("/test/jira-hook")
def test_jira_hook():
    from ..integrations.jira_client import MockJiraClient
    from ..models import UserStory
    from ..harness import get_harness
    
    harness = get_harness()
    harness.state.epic = {"key": "WEB-TEST"}
    
    jira = MockJiraClient()
    story = UserStory(
        id="S-TEST",
        persona="Tester",
        want="verify hooks in web",
        so_that="ensure web deployment works",
        acceptance_criteria=["Hooks fire via uvicorn"]
    )
    
    initial = len(harness.state.jira_creates)
    issue_key = jira.create_story(story)
    
    return {
        "hook_fired": len(harness.state.jira_creates) > initial,
        "card_created": issue_key,
        "cards_tracked": harness.state.jira_creates[-1] if harness.state.jira_creates else None
    }
```

Visit: `http://localhost:8000/test/jira-hook`

Expected:
```json
{
  "hook_fired": true,
  "card_created": "SCRUM-1",
  "cards_tracked": {
    "key": "SCRUM-1",
    "summary": "verify hooks in web",
    "parent": "WEB-TEST",
    ...
  }
}
```

### Check Logs

```bash
# Uvicorn logs show initialization
uvicorn sdlc_agent.web.app:app --log-level debug

# Should see:
# [INFO] Loading environment from: /path/to/.env
# (No errors about hooks)
```

## Production Checklist

Before deploying to production:

- [ ] Test harness initialization: `curl /api/harness/status`
- [ ] Test hook execution: `curl /test/jira-hook`
- [ ] Configure state persistence for multi-worker
- [ ] Set up centralized logging
- [ ] Configure environment variables
- [ ] Test with production Jira credentials
- [ ] Verify observability data location
- [ ] Set up monitoring/alerting
- [ ] Test cold start performance
- [ ] Load test with multiple workers

## Summary

**Question**: Will the agent harness work automatically when running via uvicorn?

**Answer**: ✅ **YES!**

The harness auto-initializes when:
1. Uvicorn loads the Flask app module
2. `ensure_harness()` runs at module level
3. Harness creates with `auto_register_hooks=True`
4. All hooks are registered before first request

**No manual setup needed** - it works automatically in:
- ✅ Development (`uvicorn --reload`)
- ✅ Production (`uvicorn --workers N`)
- ✅ Docker containers
- ✅ Kubernetes pods
- ✅ Serverless functions
- ✅ Any ASGI/WSGI server

**Files that ensure it works**:
- `sdlc_agent/web/app.py` - Calls `ensure_harness()` at module level
- `sdlc_agent/bootstrap.py` - Provides auto-initialization
- `sdlc_agent/harness.py` - Auto-registers hooks on init

**Testing**: Add the `/api/harness/status` endpoint above to verify.
