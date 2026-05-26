"""
Test Confluence API access and find valid page IDs.
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

email = os.getenv("CONFLUENCE_EMAIL") or os.getenv("ATLASSIAN_EMAIL")
token = os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("ATLASSIAN_TOKEN")
base_url = "https://rrjha82.atlassian.net"

print("=" * 60)
print("Confluence API Test")
print("=" * 60)
print(f"Email: {email}")
print(f"Token: {token[:20]}..." if token else "Token: NOT SET")
print(f"Base URL: {base_url}")
print()

if not email or not token:
    print("[ERROR] ERROR: Missing credentials!")
    print("Please set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN in .env")
    exit(1)

# Test 1: Get all spaces
print("Test 1: Fetching your Confluence spaces...")
print("-" * 60)

try:
    response = requests.get(
        f"{base_url}/wiki/api/v2/spaces",
        auth=(email, token),
        params={"limit": 10}
    )

    if response.status_code == 200:
        data = response.json()
        spaces = data.get("results", [])

        print(f"[OK] SUCCESS! Found {len(spaces)} spaces:")
        for space in spaces:
            print(f"   - {space['name']} (Key: {space['key']})")
        print()
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")
        exit(1)

except Exception as e:
    print(f"[ERROR]: {e}")
    exit(1)

# Test 2: Get recent pages
print("Test 2: Fetching recent pages...")
print("-" * 60)

try:
    response = requests.get(
        f"{base_url}/wiki/api/v2/pages",
        auth=(email, token),
        params={"limit": 10, "sort": "-modified-date"}
    )

    if response.status_code == 200:
        data = response.json()
        pages = data.get("results", [])

        print(f"[OK] SUCCESS! Found {len(pages)} recent pages:")
        print()

        for i, page in enumerate(pages, 1):
            page_id = page['id']
            title = page['title']
            space_id = page.get('spaceId', 'Unknown')

            # Construct URL
            url = f"{base_url}/wiki/pages/{page_id}"

            print(f"{i}. {title}")
            print(f"   ID: {page_id}")
            print(f"   Space: {space_id}")
            print(f"   URL: {url}")
            print()

        print("=" * 60)
        print("[OK] Copy any of the URLs above and paste into the UI!")
        print("=" * 60)

    else:
        print(f"[ERROR] ERROR {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] ERROR: {e}")

# Test 3: Try the specific page that failed
print()
print("Test 3: Checking page 327681 (the one that failed)...")
print("-" * 60)

try:
    response = requests.get(
        f"{base_url}/wiki/api/v2/pages/327681",
        auth=(email, token),
        params={"body-format": "storage"}
    )

    if response.status_code == 200:
        print("[OK] Page EXISTS and you have access!")
    elif response.status_code == 404:
        print("[ERROR] Page does NOT exist or you don't have permission")
        print("   Try one of the pages listed above instead.")
    else:
        print(f"[ERROR] ERROR {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] ERROR: {e}")

print()
print("=" * 60)
print("Next steps:")
print("1. Copy a URL from 'Test 2' above")
print("2. Paste it into Stage 1 of the UI")
print("3. Click 'Ingest Requirements'")
print("=" * 60)
