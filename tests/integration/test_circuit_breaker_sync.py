#!/usr/bin/env python3
"""
Test script to verify circuit breaker synchronization across workers.

This script:
1. Checks initial status of all workers
2. Triggers failure on one worker
3. Verifies all workers see the circuit breaker as OPEN

Usage:
    # Terminal 1: Start the server
    uvicorn test_multiworker_fastapi:app --workers 4 --host 0.0.0.0 --port 8000

    # Terminal 2: Run this test
    python test_circuit_breaker_sync.py
"""

import time
from collections import defaultdict

import requests

BASE_URL = "http://localhost:8000"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def get_worker_status():
    """Get status from a worker (will round-robin across workers)."""
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return None


def collect_all_worker_status(num_requests=10):
    """Collect status from all workers by making multiple requests."""
    print(f"📊 Collecting status from all workers ({num_requests} requests)...")

    workers_seen = {}

    for i in range(num_requests):
        status = get_worker_status()
        if status:
            worker_id = status["worker_id"]
            workers_seen[worker_id] = status
            print(f"  Request {i+1}: Worker {worker_id}")
        time.sleep(0.1)  # Small delay

    return workers_seen


def trigger_failure(provider="openai"):
    """Trigger circuit breaker failure on a worker."""
    try:
        response = requests.post(f"{BASE_URL}/trigger-failure/{provider}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error triggering failure: {e}")
        return None


def display_circuit_breaker_states(workers_status):
    """Display circuit breaker states for all workers."""
    print("\n📋 Circuit Breaker States by Worker:\n")

    for worker_id, status in sorted(workers_status.items()):
        print(f"Worker {worker_id}:")
        for provider in status["providers"]:
            cb = provider["circuit_breaker"]
            state_emoji = (
                "🔴" if cb["state"] == "open" else "🟢" if cb["state"] == "closed" else "🟡"
            )
            print(
                f"  {state_emoji} {provider['name']:10} - State: {cb['state']:10} "
                f"Failures: {cb['failure_count']}"
            )
        print()


def verify_synchronization(workers_status, provider="openai", expected_state="open"):
    """Verify that all workers have the same circuit breaker state."""
    print(f"\n🔍 Verifying synchronization for provider '{provider}'...")

    states = defaultdict(list)
    for worker_id, status in workers_status.items():
        for provider_info in status["providers"]:
            if provider_info["name"] == provider:
                state = provider_info["circuit_breaker"]["state"]
                states[state].append(worker_id)

    print(f"\nState distribution:")
    for state, worker_ids in states.items():
        print(f"  {state.upper():10} - {len(worker_ids)} workers: {worker_ids}")

    # Check if all workers have expected state
    if len(states) == 1 and expected_state in states:
        print(f"\n✅ SUCCESS: All workers have circuit breaker in '{expected_state}' state!")
        print(f"   Redis pub/sub synchronization is working correctly!")
        return True
    else:
        print(f"\n⚠️  INCONSISTENT: Workers have different states")
        print(f"   Expected all workers to be '{expected_state}'")
        return False


def main():
    """Run the circuit breaker synchronization test."""
    print_header("FlexiAI Multi-Worker Circuit Breaker Synchronization Test")

    print("Prerequisites:")
    print("  1. Redis server must be running")
    print("  2. FastAPI server must be running with 4 workers")
    print("     uvicorn test_multiworker_fastapi:app --workers 4")
    print()

    input("Press Enter to start the test...")

    # Step 1: Check initial state
    print_header("Step 1: Check Initial State of All Workers")

    initial_status = collect_all_worker_status(num_requests=12)
    print(f"\n✅ Found {len(initial_status)} unique workers")

    if len(initial_status) < 4:
        print(
            f"⚠️  WARNING: Expected 4 workers, found {len(initial_status)}. " "Continuing anyway..."
        )

    display_circuit_breaker_states(initial_status)

    input("\nPress Enter to trigger circuit breaker failure...")

    # Step 2: Trigger failure on one worker
    print_header("Step 2: Trigger OpenAI Failure on One Worker")

    result = trigger_failure("openai")
    if result:
        print(f"✅ Triggered failures on Worker {result['worker_id']}")
        print(f"   Failures triggered: {result['failures_triggered']}")
        if result.get("circuit_breaker"):
            cb = result["circuit_breaker"]
            print(f"   Circuit breaker state: {cb['state']} (failures: {cb['failure_count']})")
    else:
        print("❌ Failed to trigger failure")
        return

    # Wait for Redis pub/sub to propagate
    print("\n⏳ Waiting 2 seconds for Redis pub/sub propagation...")
    time.sleep(2)

    # Step 3: Check all workers again
    print_header("Step 3: Verify All Workers Received Circuit Breaker Event")

    final_status = collect_all_worker_status(num_requests=12)
    print(f"\n✅ Collected status from {len(final_status)} workers")

    display_circuit_breaker_states(final_status)

    # Step 4: Verify synchronization
    print_header("Step 4: Verify Synchronization")

    success = verify_synchronization(final_status, provider="openai", expected_state="open")

    # Summary
    print_header("Test Summary")

    if success:
        print("✅ PASSED: Circuit breaker synchronization is working!")
        print("\nWhat happened:")
        print("  1. Worker A experienced OpenAI failures")
        print("  2. Worker A's circuit breaker tripped to OPEN")
        print("  3. Worker A published event to Redis pub/sub channel")
        print("  4. All workers (A, B, C, D) received the event via Redis")
        print("  5. All workers updated their circuit breakers to OPEN")
        print("\n🎉 Multi-worker synchronization verified!")
    else:
        print("❌ FAILED: Circuit breaker states are not synchronized")
        print("\nPossible issues:")
        print("  - Redis pub/sub not working")
        print("  - Workers not subscribing to events")
        print("  - Timing issue (try waiting longer)")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
