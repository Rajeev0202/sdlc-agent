#!/usr/bin/env python3
"""Verify Anthropic API key configuration"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).parent / ".env"
load_dotenv(env_file)

print("=" * 70)
print("ANTHROPIC API KEY VERIFICATION")
print("=" * 70)

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    print("\n[ERROR] ANTHROPIC_API_KEY not found in environment!")
    print("\nPlease add it to .env file:")
    print("  ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE")
    exit(1)

if api_key == "your-anthropic-api-key-here":
    print("\n[WARNING] ANTHROPIC_API_KEY is still set to placeholder!")
    print("\nPlease replace with your actual API key from:")
    print("  https://console.anthropic.com/")
    print("\nYour .env file location:")
    print(f"  {env_file}")
    exit(1)

if not api_key.startswith("sk-ant-"):
    print(f"\n[WARNING] API key format looks incorrect!")
    print(f"  Expected: sk-ant-api03-...")
    print(f"  Got: {api_key[:20]}...")
    exit(1)

print(f"\n[OK] API key found: {api_key[:15]}...{api_key[-4:]}")
print(f"[OK] Key length: {len(api_key)} characters")

# Test the API key
print("\nTesting API connection...")
try:
    from sdlc_agent.integrations.anthropic_client import MockClaudeClient

    client = MockClaudeClient()
    print(f"[OK] Client backend: {client.backend}")

    if "anthropic" in client.backend.lower():
        print("[SUCCESS] Anthropic API is configured and ready!")

        # Quick test call
        print("\nTesting API with quick call...")
        result = client.complete_json(
            system="You are a helpful assistant.",
            user="Return JSON: {\"test\": \"success\", \"number\": 42}",
            max_tokens=100
        )

        if result and isinstance(result, dict):
            print(f"[SUCCESS] API test call succeeded!")
            print(f"  Response: {result}")
        else:
            print(f"[WARNING] API returned unexpected result: {result}")
    else:
        print(f"[WARNING] Client is using {client.backend} instead of Anthropic API")
        print("  This might mean:")
        print("  - Claude Code CLI was found and is taking priority")
        print("  - Add to .env: SDLC_DISABLE_CLAUDE_CLI=true")

except Exception as e:
    print(f"[ERROR] API test failed: {e}")
    exit(1)

print("\n" + "=" * 70)
print("READY TO USE!")
print("=" * 70)
print("\nYou can now start the server:")
print("  start-server.bat")
print("\nOr manually:")
print("  python -m sdlc_agent.web.app")
print("\nServer will be available at:")
print("  http://127.0.0.1:5002")
print("=" * 70)
