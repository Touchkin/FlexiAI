#!/usr/bin/env python3
"""
Test client for FastAPI multi-worker circuit breaker synchronization.

This script verifies that when one worker experiences a provider failure,
ALL workers get notified via Redis pub/sub and trip their circuit breakers.

Usage:
    python test_client.py
"""

import time
from collections import defaultdict

import requests

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def check_redis():
    """Check if Redis is running."""
    import subprocess

    try:
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=2)
        return result.stdout.strip() == "PONG"
    except Exception:
        return False


def check_server():
    """Check if FastAPI server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_all_workers_status():
    """
    Query /status multiple times to hit all 4 workers.
    Returns a dict of worker_id -> status.
    """
    workers = {}
    attempts = 0
    max_attempts = 20  # Try up to 20 times to find all 4 workers

    print("🔍 Discovering all workers...")

    while len(workers) < 4 and attempts < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}/status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                worker_id = data["worker_id"]
                if worker_id not in workers:
                    workers[worker_id] = data
                    print(f"   ✓ Found worker {worker_id} ({len(workers)}/4)")
        except Exception as e:
            print(f"   ⚠ Error querying status: {e}")

        attempts += 1
        time.sleep(0.1)

    if len(workers) < 4:
        print(f"\n⚠️  Warning: Only found {len(workers)} workers (expected 4)")
    else:
        print(f"\n✅ Found all 4 workers!")

    return workers


def display_worker_status(workers, title="Worker Status"):
    """Display circuit breaker status for all workers."""
    print(f"\n📊 {title}")
    print("-" * 80)

    for worker_id, status in sorted(workers.items()):
        print(f"\nWorker {worker_id}:")
        for provider in status.get("providers", []):
            cb = provider.get("circuit_breaker", {})
            state = cb.get("state", "unknown")
            failures = cb.get("failure_count", 0)

            # Color code the state
            if state == "open":
                state_display = f"🔴 {state.upper()}"
            elif state == "closed":
                state_display = f"🟢 {state.upper()}"
            elif state == "half_open":
                state_display = f"🟡 {state.upper()}"
            else:
                state_display = f"⚪ {state.upper()}"

            print(f"  {provider['name']:12} - {state_display:15} (failures: {failures})")


def trigger_failure_on_worker(provider_name="openai"):
    """Trigger failures on one worker to open circuit breaker."""
    print(f"\n⚡ Triggering failures for {provider_name}...")

    try:
        response = requests.post(f"{BASE_URL}/trigger-failure/{provider_name}", timeout=30)

        if response.status_code == 200:
            data = response.json()
            worker_id = data.get("worker_id")
            failures = data.get("failures_triggered", 0)
            cb_state = data.get("circuit_breaker", {})

            print(f"\n✅ Triggered {failures} failures on worker {worker_id}")
            if cb_state:
                print(f"   Circuit breaker state: {cb_state.get('state', 'unknown')}")
                print(f"   Failure count: {cb_state.get('failure_count', 0)}")

            return worker_id
        else:
            print(f"❌ Failed to trigger failures: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error triggering failures: {e}")
        return None


def verify_sync(workers_before, workers_after, provider_name="openai"):
    """
    Verify that ALL workers have the circuit breaker in OPEN state.
    """
    print(f"\n🔍 Verifying circuit breaker synchronization for {provider_name}...")
    print("-" * 80)

    all_open = True
    sync_results = {}

    for worker_id in workers_after:
        providers = workers_after[worker_id].get("providers", [])
        provider_info = None

        for p in providers:
            if p["name"] == provider_name:
                provider_info = p
                break

        if provider_info:
            cb_state = provider_info.get("circuit_breaker", {}).get("state", "unknown")
            sync_results[worker_id] = cb_state

            if cb_state == "open":
                print(f"   ✅ Worker {worker_id}: Circuit breaker is OPEN")
            else:
                print(f"   ❌ Worker {worker_id}: Circuit breaker is {cb_state.upper()}")
                all_open = False
        else:
            print(f"   ⚠️  Worker {worker_id}: Provider {provider_name} not found")
            all_open = False

    print()
    if all_open:
        print("🎉 SUCCESS! All workers have synchronized circuit breaker state!")
        print(f"   All {len(sync_results)} workers show {provider_name} circuit as OPEN")
        return True
    else:
        print("❌ FAILURE! Circuit breakers are NOT synchronized")
        print(f"   States: {sync_results}")
        return False


def main():
    """Run the multi-worker circuit breaker synchronization test."""
    print_section("FlexiAI Multi-Worker Circuit Breaker Synchronization Test")

    # Step 1: Pre-flight checks
    print("🔧 Pre-flight checks...")

    if not check_redis():
        print("❌ Redis is not running!")
        print("   Please start Redis: redis-server")
        return False

    print("✅ Redis is running")

    if not check_server():
        print("❌ FastAPI server is not running!")
        print("   Please start server: uvicorn test_multiworker_fastapi:app --workers 4")
        return False

    print("✅ FastAPI server is running")

    # Step 2: Get initial status from all workers
    print_section("Step 1: Initial Worker Status")

    workers_before = get_all_workers_status()
    if not workers_before:
        print("❌ Could not discover any workers!")
        return False

    display_worker_status(workers_before, "Initial Circuit Breaker States")

    # Wait a bit for all workers to stabilize
    time.sleep(1)

    # Step 3: Trigger failure on one worker
    print_section("Step 2: Trigger Provider Failure on One Worker")

    trigger_worker_id = trigger_failure_on_worker("openai")
    if not trigger_worker_id:
        print("❌ Failed to trigger failures!")
        return False

    # Step 4: Wait for Redis pub/sub propagation
    print_section("Step 3: Wait for Redis Pub/Sub Propagation")
    print("⏳ Waiting 2 seconds for circuit breaker events to propagate...")
    time.sleep(2)

    # Step 5: Get status from all workers again
    print_section("Step 4: Verify All Workers Received Circuit Breaker Event")

    workers_after = get_all_workers_status()
    display_worker_status(workers_after, "Circuit Breaker States After Failure")

    # Step 6: Verify synchronization
    print_section("Step 5: Verification Results")

    success = verify_sync(workers_before, workers_after, "openai")

    # Summary
    print_section("Test Summary")

    if success:
        print("✅ PASSED: Multi-worker circuit breaker synchronization works!")
        print("\nWhat happened:")
        print(f"  1. Worker {trigger_worker_id} experienced OpenAI failures")
        print(f"  2. Worker {trigger_worker_id} tripped its circuit breaker to OPEN")
        print(f"  3. Event published to Redis pub/sub channel")
        print(f"  4. All {len(workers_after)} workers received the event")
        print(f"  5. All workers updated their circuit breaker state to OPEN")
        print("\n🎉 Redis pub/sub synchronization is working correctly!")
        return True
    else:
        print("❌ FAILED: Circuit breaker synchronization did not work")
        print("\nPossible issues:")
        print("  - Redis pub/sub not configured correctly")
        print("  - Workers not subscribing to events")
        print("  - Event propagation delay (try waiting longer)")
        return False


if __name__ == "__main__":
    import sys

    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
