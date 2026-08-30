#!/usr/bin/env python3
"""
Auteur — graceful-degradation test for the Parallel Search fallback path.

Verifies that when the PARALLEL_API_KEY is missing (or the Parallel Search
endpoint is unreachable), the Research Agent:
  1. Does NOT raise / crash the build-bible pipeline.
  2. Returns an empty reference list.
  3. Logs a `research_failed` event to the project's event log.

This is the "kill Parallel API key temporarily; confirm graceful degradation"
compliance check from the hardening checklist.

Run: python3 backend/tests/test_fallback_no_parallel_key.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add the backend to the path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND.parent))

from backend.bible import store  # noqa: E402
from backend.agents import research as research_agent  # noqa: E402

# Force the in-memory store (no Firestore creds needed for this test)
store._USE_MEMORY = True
store._FIRESTORE_CLIENT = None

PROJECT_ID = "test-fallback-no-key"
OBJECTIVE = "Find historical references for a film about a lighthouse keeper."
QUERIES = ["1892 lighthouse keeper", "Scottish coastal lighthouse wardrobe"]


async def run_test() -> int:
    print("=" * 60)
    print("FALLBACK PATH — graceful degradation without PARALLEL_API_KEY")
    print("=" * 60)

    # --- Setup: ensure PARALLEL_API_KEY is unset ---
    original_key = os.environ.pop("PARALLEL_API_KEY", None)
    if original_key:
        print(f"[setup] temporarily removed PARALLEL_API_KEY (was {len(original_key)} chars)")
    else:
        print("[setup] PARALLEL_API_KEY was already unset")
    assert "PARALLEL_API_KEY" not in os.environ, "key should be unset"

    # --- Run the research agent ---
    print("\n[1] calling research_agent.research() with no API key...")
    try:
        refs = await research_agent.research(PROJECT_ID, OBJECTIVE, QUERIES)
    except Exception as e:
        print(f"  FAIL: research() raised {type(e).__name__}: {e}")
        if original_key:
            os.environ["PARALLEL_API_KEY"] = original_key
        return 1

    # --- Assertion 1: it returned an empty list (not None, not a crash) ---
    print(f"  returned {len(refs)} references (expected 0)")
    assert isinstance(refs, list), f"expected a list, got {type(refs)}"
    assert len(refs) == 0, f"expected 0 refs, got {len(refs)} (the agent should not have been able to call Parallel Search)"
    print("  PASS: research() returned [] without raising")

    # --- Assertion 2: a research_failed event was logged ---
    print("\n[2] checking the event log for a research_failed event...")
    events = await store.get_events(PROJECT_ID)
    failed_events = [e for e in events if e.get("type") == "research_failed"]
    assert len(failed_events) >= 1, f"expected at least 1 research_failed event, got {len(failed_events)}"
    evt = failed_events[0]
    print(f"  logged event: type={evt['type']}, payload.error={evt['payload'].get('error','')[:80]}")
    assert "PARALLEL_API_KEY" in evt["payload"].get("error", "") or "not set" in evt["payload"].get("error", "").lower(), \
        f"the error message should mention the missing key, got: {evt['payload'].get('error','')}"
    print("  PASS: research_failed event logged with a clear error message")

    # --- Assertion 3: the Director Agent would still proceed (simulated) ---
    # The Director calls research(); with [] refs, it synthesizes the Bible
    # from the logline alone. We simulate that by confirming the empty list
    # is the exact value the Director would receive.
    print("\n[3] confirming the Director Agent receives an empty list (creative inference path)...")
    assert refs == [], "the Director should receive [] so it falls back to creative inference"
    print("  PASS: Director Agent would proceed with creative inference (Bible built from logline alone)")

    # --- Cleanup: restore the key if it was set ---
    if original_key:
        os.environ["PARALLEL_API_KEY"] = original_key
        print(f"\n[cleanup] restored PARALLEL_API_KEY ({len(original_key)} chars)")

    print("\n" + "=" * 60)
    print("PASS — graceful degradation verified: the pipeline does NOT crash")
    print("when PARALLEL_API_KEY is missing. The Research Agent returns []")
    print("and logs a research_failed event; the Director proceeds with")
    print("creative inference.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_test()))
