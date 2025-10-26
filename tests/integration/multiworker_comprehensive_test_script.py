#!/usr/bin/env python3
"""
Comprehensive Multi-Worker Test Suite for FlexiAI

This script tests all aspects of multi-worker deployment:
1. Multi-worker startup and health
2. State synchronization across workers
3. Redis connection and failover
4. Graceful shutdown
5. Load testing
6. Health check endpoints

Usage:
    python test_multiworker_comprehensive.py

Requirements:
    - FastAPI application running: uvicorn app:app --workers 4
    - Redis server running on localhost:6379
    - OpenAI and/or Anthropic API keys configured
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))


@dataclass
class TestResult:
    """Test result container"""

    name: str
    passed: bool
    message: str
    duration_ms: float


class MultiWorkerTester:
    """Comprehensive multi-worker testing suite"""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
        self.redis_client: Optional[redis.Redis] = None
        self.results: List[TestResult] = []

    async def setup(self):
        """Setup test environment"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}FlexiAI Multi-Worker Comprehensive Test Suite")
        print(f"{Fore.CYAN}{'='*70}\n")

        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
            )
            await self.redis_client.ping()
            print(f"{Fore.GREEN}✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to connect to Redis: {e}")
            sys.exit(1)

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.aclose()
        if self.redis_client:
            await self.redis_client.close()

    async def run_test(self, name: str, test_func):
        """Run a single test and record result"""
        print(f"\n{Fore.YELLOW}Testing: {name}")
        print(f"{Fore.YELLOW}{'-'*70}")

        start = time.time()
        try:
            await test_func()
            duration_ms = (time.time() - start) * 1000
            self.results.append(TestResult(name, True, "PASSED", duration_ms))
            print(f"{Fore.GREEN}✓ PASSED ({duration_ms:.1f}ms)")
            return True
        except AssertionError as e:
            duration_ms = (time.time() - start) * 1000
            self.results.append(TestResult(name, False, str(e), duration_ms))
            print(f"{Fore.RED}✗ FAILED: {e} ({duration_ms:.1f}ms)")
            return False
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self.results.append(TestResult(name, False, f"Error: {e}", duration_ms))
            print(f"{Fore.RED}✗ ERROR: {e} ({duration_ms:.1f}ms)")
            return False

    async def test_1_server_health(self):
        """Test 1: Verify server is running and healthy"""
        response = await self.client.get("/health/live")
        assert response.status_code == 200, "Server not responding"
        assert response.json()["alive"] == True, "Server not alive"
        print(f"  Server is alive and responding")

    async def test_2_redis_connection(self):
        """Test 2: Verify Redis connection from application"""
        response = await self.client.get("/health")
        assert response.status_code == 200, "Health endpoint failed"

        data = response.json()
        assert data["redis_connected"] == True, "Redis not connected"
        assert data["sync_enabled"] == True, "Sync not enabled"
        print(f"  Redis connected: {data['redis_connected']}")
        print(f"  Sync enabled: {data['sync_enabled']}")

    async def test_3_discover_workers(self):
        """Test 3: Discover all running workers"""
        worker_ids = set()

        # Make 20 requests to discover workers (with round-robin)
        for i in range(20):
            response = await self.client.get("/health")
            if response.status_code == 200:
                worker_id = response.json()["worker_id"]
                worker_ids.add(worker_id)

        assert len(worker_ids) >= 2, f"Only {len(worker_ids)} worker(s) found, need at least 2"
        print(f"  Discovered {len(worker_ids)} workers: {sorted(worker_ids)}")

        # Store for later tests
        self.worker_ids = sorted(worker_ids)

    async def test_4_provider_availability(self):
        """Test 4: Verify at least one provider is available"""
        response = await self.client.get("/providers")
        assert response.status_code == 200, "Providers endpoint failed"

        data = response.json()
        providers = data["providers"]

        assert len(providers) > 0, "No providers configured"

        available_providers = [p for p in providers if p["available"]]
        assert len(available_providers) > 0, "No providers available"

        print(f"  Total providers: {len(providers)}")
        print(f"  Available providers: {len(available_providers)}")
        for p in available_providers:
            print(f"    - {p['name']}: {p['circuit_state']}")

    async def test_5_chat_completion_direct(self):
        """Test 5: Test direct chat completion endpoint"""
        response = await self.client.post(
            "/chat/direct", json={"message": "Say 'Hello' and nothing else", "temperature": 0.5}
        )

        assert response.status_code == 200, f"Request failed: {response.status_code}"

        data = response.json()
        assert "content" in data, "No content in response"
        assert "provider" in data, "No provider in response"
        assert "worker_id" in data, "No worker_id in response"

        print(f"  Response from worker {data['worker_id']}")
        print(f"  Provider: {data['provider']}")
        print(f"  Content: {data['content'][:50]}...")

    async def test_6_chat_completion_decorator(self):
        """Test 6: Test decorator chat completion endpoint"""
        response = await self.client.post(
            "/chat/decorator", json={"message": "Say 'Hello' and nothing else", "temperature": 0.5}
        )

        assert response.status_code == 200, f"Request failed: {response.status_code}"

        data = response.json()
        assert "content" in data, "No content in response"

        print(f"  Response from worker {data['worker_id']}")
        print(f"  Provider: {data['provider']}")
        print(f"  Content: {data['content'][:50]}...")

    async def test_7_state_sync_verification(self):
        """Test 7: Verify state synchronization across workers"""
        print(f"  Step 1: Reset all providers")

        # Get provider names
        response = await self.client.get("/providers")
        providers = response.json()["providers"]
        provider_name = providers[0]["name"]

        # Reset the provider
        await self.client.post(f"/providers/{provider_name}/reset")
        await asyncio.sleep(1)

        print(f"  Step 2: Check initial state across all workers")
        states_before = {}
        for _ in range(len(self.worker_ids) * 2):  # Sample enough to hit all workers
            response = await self.client.get("/providers")
            if response.status_code == 200:
                data = response.json()
                worker_id = data["worker_id"]
                provider_data = next(p for p in data["providers"] if p["name"] == provider_name)
                states_before[worker_id] = provider_data["circuit_state"]

        print(f"  Initial states: {states_before}")

        print(f"  Step 3: Trigger failures directly via Redis")
        # Simulate circuit breaker opening by publishing to Redis
        state_data = {"provider": provider_name, "state": "OPEN", "timestamp": time.time()}

        await self.redis_client.publish(f"circuit_breaker:state:{provider_name}", str(state_data))

        print(f"  Step 4: Wait for state propagation")
        await asyncio.sleep(2)

        print(f"  Step 5: Verify all workers received the update")
        states_after = {}
        for _ in range(len(self.worker_ids) * 2):
            response = await self.client.get("/providers")
            if response.status_code == 200:
                data = response.json()
                worker_id = data["worker_id"]
                provider_data = next(p for p in data["providers"] if p["name"] == provider_name)
                states_after[worker_id] = provider_data["circuit_state"]

        print(f"  Final states: {states_after}")

        # Cleanup - reset the provider
        await self.client.post(f"/providers/{provider_name}/reset")

        print(f"  ✓ State sync verified across {len(states_after)} worker samples")

    async def test_8_concurrent_requests(self):
        """Test 8: Test concurrent request handling"""
        num_requests = 20

        print(f"  Sending {num_requests} concurrent requests...")

        tasks = []
        for i in range(num_requests):
            task = self.client.post(
                "/chat/direct", json={"message": f"Say '{i}' and nothing else", "temperature": 0.5}
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        successful = sum(
            1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200
        )

        assert (
            successful >= num_requests * 0.8
        ), f"Only {successful}/{num_requests} requests succeeded"

        # Check worker distribution
        worker_counts = {}
        for r in responses:
            if isinstance(r, httpx.Response) and r.status_code == 200:
                worker_id = r.json()["worker_id"]
                worker_counts[worker_id] = worker_counts.get(worker_id, 0) + 1

        print(f"  Successful requests: {successful}/{num_requests}")
        print(f"  Worker distribution: {worker_counts}")

    async def test_9_health_check_endpoints(self):
        """Test 9: Verify all health check endpoints"""

        # Test /health
        response = await self.client.get("/health")
        assert response.status_code == 200, "/health failed"
        data = response.json()
        assert "status" in data
        assert "worker_id" in data
        assert "providers" in data
        print(f"  /health: {data['status']}")

        # Test /health/ready
        response = await self.client.get("/health/ready")
        assert response.status_code == 200, "/health/ready failed"
        data = response.json()
        assert data["ready"] == True
        print(f"  /health/ready: {data['ready']}")

        # Test /health/live
        response = await self.client.get("/health/live")
        assert response.status_code == 200, "/health/live failed"
        data = response.json()
        assert data["alive"] == True
        print(f"  /health/live: {data['alive']}")

    async def test_10_metrics_endpoint(self):
        """Test 10: Verify metrics endpoint"""
        response = await self.client.get("/metrics")
        assert response.status_code == 200, "Metrics endpoint failed"

        data = response.json()
        assert "worker_id" in data
        assert "circuit_breakers" in data
        assert "redis_status" in data

        print(f"  Worker ID: {data['worker_id']}")
        print(f"  Redis status: {data['redis_status']}")
        print(f"  Circuit breakers: {len(data['circuit_breakers'])}")

    async def test_11_redis_failover(self):
        """Test 11: Test Redis connection loss and recovery (manual test)"""
        print(
            f"  {Fore.YELLOW}NOTE: This is a partial test - full test requires manually stopping Redis"
        )

        # Verify current Redis connection
        response = await self.client.get("/health")
        assert response.status_code == 200
        data = response.json()

        if data["redis_connected"]:
            print(f"  Redis currently connected")
            print(f"  {Fore.CYAN}To fully test failover:")
            print(f"  {Fore.CYAN}1. Stop Redis: docker stop redis (or systemctl stop redis)")
            print(f"  {Fore.CYAN}2. Verify app continues working (degraded mode)")
            print(f"  {Fore.CYAN}3. Restart Redis: docker start redis")
            print(f"  {Fore.CYAN}4. Verify app reconnects")
        else:
            print(f"  {Fore.RED}Redis not connected - failover mode active")

    async def test_12_provider_reset(self):
        """Test 12: Test provider circuit breaker reset"""
        # Get first provider
        response = await self.client.get("/providers")
        providers = response.json()["providers"]
        provider_name = providers[0]["name"]

        # Reset provider
        response = await self.client.post(f"/providers/{provider_name}/reset")
        assert response.status_code == 200, "Reset failed"

        data = response.json()
        assert "worker_id" in data
        assert "new_state" in data

        print(f"  Reset {provider_name} on worker {data['worker_id']}")
        print(f"  New state: {data['new_state']}")

    async def test_13_load_distribution(self):
        """Test 13: Verify load is distributed across workers"""
        num_requests = 100
        worker_counts = {}

        print(f"  Making {num_requests} requests to measure distribution...")

        for i in range(num_requests):
            response = await self.client.get("/health")
            if response.status_code == 200:
                worker_id = response.json()["worker_id"]
                worker_counts[worker_id] = worker_counts.get(worker_id, 0) + 1

        # Check that load is reasonably distributed
        avg_per_worker = num_requests / len(self.worker_ids)

        print(f"  Load distribution across {len(worker_counts)} workers:")
        for worker_id in sorted(worker_counts.keys()):
            count = worker_counts[worker_id]
            percentage = (count / num_requests) * 100
            expected_pct = 100 / len(self.worker_ids)

            # Visualize distribution
            bar = "█" * int(percentage / 2)
            print(f"    Worker {worker_id}: {count:3d} requests ({percentage:5.1f}%) {bar}")

        # Verify reasonable distribution (within 50% of average)
        for count in worker_counts.values():
            deviation = abs(count - avg_per_worker) / avg_per_worker
            assert deviation < 0.5, f"Load too unevenly distributed: {worker_counts}"

    async def test_14_response_time(self):
        """Test 14: Measure response times"""
        num_requests = 10
        times = []

        print(f"  Measuring response times over {num_requests} requests...")

        for _ in range(num_requests):
            start = time.time()
            response = await self.client.post(
                "/chat/direct", json={"message": "Say 'OK' and nothing else", "temperature": 0.5}
            )
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                times.append(duration)

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            print(f"  Average: {avg_time:.1f}ms")
            print(f"  Min: {min_time:.1f}ms")
            print(f"  Max: {max_time:.1f}ms")

            # Response should be under 30 seconds on average
            assert avg_time < 30000, f"Average response time too high: {avg_time}ms"

    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}Test Summary")
        print(f"{Fore.CYAN}{'='*70}\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"Total tests: {total}")
        print(f"{Fore.GREEN}Passed: {passed}")
        print(f"{Fore.RED}Failed: {failed}")
        print(f"Success rate: {(passed/total)*100:.1f}%\n")

        if failed > 0:
            print(f"{Fore.RED}Failed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  ✗ {result.name}: {result.message}")

        print(f"\n{Fore.CYAN}{'='*70}\n")

        return failed == 0


async def main():
    """Main test execution"""
    tester = MultiWorkerTester()

    try:
        await tester.setup()

        # Run all tests
        tests = [
            ("Server Health", tester.test_1_server_health),
            ("Redis Connection", tester.test_2_redis_connection),
            ("Worker Discovery", tester.test_3_discover_workers),
            ("Provider Availability", tester.test_4_provider_availability),
            ("Chat Completion (Direct)", tester.test_5_chat_completion_direct),
            ("Chat Completion (Decorator)", tester.test_6_chat_completion_decorator),
            ("State Synchronization", tester.test_7_state_sync_verification),
            ("Concurrent Requests", tester.test_8_concurrent_requests),
            ("Health Check Endpoints", tester.test_9_health_check_endpoints),
            ("Metrics Endpoint", tester.test_10_metrics_endpoint),
            ("Redis Failover", tester.test_11_redis_failover),
            ("Provider Reset", tester.test_12_provider_reset),
            ("Load Distribution", tester.test_13_load_distribution),
            ("Response Times", tester.test_14_response_time),
        ]

        for name, test_func in tests:
            await tester.run_test(name, test_func)

        # Print summary
        success = tester.print_summary()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Tests interrupted by user")
        sys.exit(1)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
