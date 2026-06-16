#!/bin/bash
# Test that harness works when running via uvicorn

echo "=========================================="
echo "  Testing Harness in Uvicorn Web Server"
echo "=========================================="
echo

# Start uvicorn in background
echo "1. Starting uvicorn..."
uvicorn sdlc_agent.web.app:app --port 8000 &
UVICORN_PID=$!

# Wait for server to start
echo "   Waiting for server to start..."
sleep 3

echo
echo "2. Testing harness status endpoint..."
curl -s http://localhost:8000/api/harness/status | python -m json.tool

echo
echo "3. Testing Jira hook endpoint..."
curl -s http://localhost:8000/api/test/jira-hook | python -m json.tool

echo
echo "4. Stopping uvicorn..."
kill $UVICORN_PID

echo
echo "=========================================="
echo "  Test Complete"
echo "=========================================="
echo
echo "If you see:"
echo "  - hooks_registered: true"
echo "  - hook_fired: true"
echo
echo "Then the harness works correctly with uvicorn!"
