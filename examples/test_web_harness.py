#!/usr/bin/env python3
"""Test that harness works when running via uvicorn."""

import subprocess
import time
import requests
import json
import sys

print("=" * 60)
print("  Testing Harness in Uvicorn Web Server")
print("=" * 60)
print()

# Start uvicorn
print("1. Starting uvicorn...")
uvicorn_process = subprocess.Popen(
    ["uvicorn", "sdlc_agent.web.app:app", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
print("   Waiting for server to start...")
time.sleep(5)

try:
    # Test harness status
    print("\n2. Testing harness status endpoint...")
    print("   GET http://localhost:8000/api/harness/status")
    try:
        response = requests.get("http://localhost:8000/api/harness/status")
        if response.status_code == 200:
            data = response.json()
            print("\n   Response:")
            print(json.dumps(data, indent=2))

            if data.get("hooks_registered"):
                print("\n   [OK] Hooks are registered!")
            else:
                print("\n   [FAIL] Hooks NOT registered")
                sys.exit(1)
        else:
            print(f"\n   [FAIL] Status code: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"\n   [FAIL] Error: {e}")
        sys.exit(1)

    # Test Jira hook
    print("\n3. Testing Jira hook endpoint...")
    print("   GET http://localhost:8000/api/test/jira-hook")
    try:
        response = requests.get("http://localhost:8000/api/test/jira-hook")
        if response.status_code == 200:
            data = response.json()
            print("\n   Response:")
            print(json.dumps(data, indent=2))

            if data.get("hook_fired"):
                print("\n   [OK] Hook fired successfully!")
            else:
                print("\n   [FAIL] Hook did NOT fire")
                sys.exit(1)
        else:
            print(f"\n   [FAIL] Status code: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"\n   [FAIL] Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  SUCCESS: Harness works with uvicorn!")
    print("=" * 60)
    print("\nThe harness and all hooks are properly initialized")
    print("when running the web app via uvicorn.")
    print()

finally:
    # Cleanup
    print("4. Stopping uvicorn...")
    uvicorn_process.terminate()
    uvicorn_process.wait()
    print("   Server stopped")
