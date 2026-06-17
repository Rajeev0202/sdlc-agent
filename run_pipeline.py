"""
Terminal CLI to trigger the SDLC autonomous pipeline.

Usage:
    python run_pipeline.py                                    # Use default sample BRD
    python run_pipeline.py <source>                           # Use custom BRD
    python run_pipeline.py <source> --auto-approve            # Skip PO gate
    python run_pipeline.py status <run_id>                    # Check run status
    python run_pipeline.py approve <run_id> <approver_name>   # Manual PO approval

Examples:
    python run_pipeline.py
    python run_pipeline.py samples_requirements/brd.md
    python run_pipeline.py https://confluence.com/wiki/pages/12345
    python run_pipeline.py samples_requirements/brd.md --auto-approve
"""
import sys
import json
import time
from pathlib import Path

# Force UTF-8 output for emoji support on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

import requests

SERVER_URL = "http://127.0.0.1:5002"
DEFAULT_SOURCE = "samples_requirements/brd_natwest_card_freeze.md"


def check_server():
    """Verify the SDLC agent server is running."""
    try:
        r = requests.get(SERVER_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        print(f"[ERROR] SDLC server not running at {SERVER_URL}")
        print(f"        Start it with: python -m sdlc_agent.web.app")
        return False


def render_history(history):
    """Pretty-print pipeline history."""
    for i, h in enumerate(history, 1):
        stage = h.get("stage", "?")
        status = h.get("status") or h.get("verdict") or h.get("decision") or "OK"
        iters = f" (×{h['iterations']})" if h.get("iterations") else ""

        # Add extra details for specific stages
        extra = ""
        if "stories" in h:
            extra = f" ({h['stories']} stories)"
        elif "test_cases" in h:
            extra = f" ({h['test_cases']} test cases)"
        elif "scripts" in h:
            extra = f" ({h['scripts']} scripts)"
        elif "passed" in h and "failed" in h:
            extra = f" (passed={h['passed']}, failed={h['failed']})"

        icon = "✓" if status in ("complete", "success", "pass", "GO") else "⚠️" if status == "NO-GO" else "→"
        print(f"  {icon} [{i:02d}] Stage {stage}: {status}{extra}{iters}")


def run_phase1(source, auto_approve=False):
    """Run Phase 1: Stages 1-2."""
    print(f"\n{'=' * 60}")
    print(f"🤖 AUTONOMOUS SDLC PIPELINE — Phase 1")
    print(f"{'=' * 60}")
    print(f"Source:      {source}")
    print(f"Auto-approve: {auto_approve}")
    print()

    start = time.time()
    print("→ Running Stages 1-2 (Ingest + Plan)...")

    r = requests.post(
        f"{SERVER_URL}/api/autonomous-pipeline",
        json={"source": source, "auto_approve": auto_approve},
        timeout=300,
    )

    if r.status_code != 200:
        print(f"[ERROR] HTTP {r.status_code}: {r.text[:200]}")
        return None

    result = r.json()
    elapsed = time.time() - start

    print(f"\n{'─' * 60}")
    print(f"Status:    {result['status']}")
    print(f"Duration:  {elapsed:.1f}s")
    print(f"Run ID:    {result.get('final_output', {}).get('run_id')}")
    print(f"\nHistory:")
    render_history(result.get("history", []))

    if result.get("error"):
        print(f"\n[ERROR] {result['error']}")

    # Show stories if backlog present
    backlog = result.get("backlog")
    if backlog:
        stories = backlog.get("stories", [])
        print(f"\n{'─' * 60}")
        print(f"📋 Generated {len(stories)} User Stories:")
        for s in stories[:10]:
            print(f"  • {s['id']}: {s.get('want', 'N/A')[:60]}...")
        if len(stories) > 10:
            print(f"  ... and {len(stories) - 10} more")

    return result


def run_phase2(run_id):
    """Run Phase 2: Stages 3-6 with loops."""
    print(f"\n{'=' * 60}")
    print(f"🤖 AUTONOMOUS SDLC PIPELINE — Phase 2")
    print(f"{'=' * 60}")
    print(f"Run ID: {run_id}")
    print()

    start = time.time()
    print("→ Running Stages 3-6 with remediation & heal loops...")

    r = requests.post(
        f"{SERVER_URL}/api/autonomous-pipeline-resume",
        json={"run_id": run_id},
        timeout=600,
    )

    if r.status_code != 200:
        print(f"[ERROR] HTTP {r.status_code}: {r.text[:200]}")
        return None

    result = r.json()
    elapsed = time.time() - start

    print(f"\n{'─' * 60}")
    print(f"Status:    {result['status']}")
    print(f"Duration:  {elapsed:.1f}s")

    final = result.get("final_output", {})
    decision = final.get("decision")
    if decision:
        verdict = "✅ GO" if decision.get("go") else "❌ NO-GO"
        print(f"Decision:  {verdict}")
        gates = decision.get("gates", {})
        for gate, ok in gates.items():
            icon = "✓" if ok else "✗"
            print(f"           {icon} {gate}")

    print(f"\nHistory:")
    render_history(result.get("history", []))

    if final.get("remediation_iterations", 0) > 1:
        print(f"\n🔁 Remediation loop ran {final['remediation_iterations']} times")
    if final.get("heal_iterations", 0) > 1:
        print(f"🔁 Heal loop ran {final['heal_iterations']} times")

    return result


def approve_backlog(run_id, approver):
    """Manually approve the PO gate."""
    print(f"→ Approving backlog for {run_id} as {approver}...")
    r = requests.post(
        f"{SERVER_URL}/api/approve",
        json={"run_id": run_id, "approver": approver},
        timeout=30,
    )
    if r.status_code == 200:
        print(f"✓ Approved by {approver}")
        return True
    print(f"[ERROR] {r.text[:200]}")
    return False


def main():
    args = sys.argv[1:]

    # Command: status <run_id>
    if args and args[0] == "status":
        if len(args) < 2:
            print("Usage: python run_pipeline.py status <run_id>")
            sys.exit(1)
        run_id = args[1]
        run_dir = Path("runs") / run_id
        if not run_dir.exists():
            print(f"Run not found: {run_id}")
            sys.exit(1)
        print(f"\nFiles in {run_dir}:")
        for f in sorted(run_dir.iterdir()):
            print(f"  • {f.name} ({f.stat().st_size} bytes)")
        return

    # Command: approve <run_id> <approver>
    if args and args[0] == "approve":
        if len(args) < 3:
            print("Usage: python run_pipeline.py approve <run_id> <approver_name>")
            sys.exit(1)
        if not check_server():
            sys.exit(1)
        if approve_backlog(args[1], args[2]):
            run_phase2(args[1])
        return

    # Default: run pipeline
    if not check_server():
        sys.exit(1)

    source = args[0] if args and not args[0].startswith("--") else DEFAULT_SOURCE
    auto_approve = "--auto-approve" in args

    # Run Phase 1
    phase1 = run_phase1(source, auto_approve=auto_approve)
    if not phase1:
        sys.exit(1)

    if auto_approve:
        # Auto-approve mode runs everything
        print(f"\n✓ Pipeline complete (auto-approve mode)")
        return

    # Halted at PO gate - prompt for approval
    run_id = phase1.get("final_output", {}).get("run_id")
    if phase1["status"] != "awaiting_approval":
        print(f"\n⚠️ Pipeline did not halt at PO gate (status: {phase1['status']})")
        return

    print(f"\n{'─' * 60}")
    print(f"⏸️  PO APPROVAL GATE")
    print(f"{'─' * 60}")
    response = input(f"Enter your name to approve, or Ctrl+C to abort: ").strip()
    if not response:
        print("Approval cancelled.")
        return

    if not approve_backlog(run_id, response):
        sys.exit(1)

    # Phase 2: Run remaining stages
    run_phase2(run_id)
    print(f"\n{'=' * 60}")
    print(f"✓ Pipeline finished")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
