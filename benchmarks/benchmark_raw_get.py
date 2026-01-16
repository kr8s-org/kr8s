#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""
Benchmark script to compare performance of different ways to list Pods.

This script compares three approaches:
1. kr8s with raw=False (default): Creates APIObject instances
2. kr8s with raw=True: Returns raw dictionaries via kr8s API
3. Direct httpx calls: Baseline using httpx directly with pagination handling

The benchmark creates a deployment with 50 pods and iterates over them 100 times
to simulate processing 5,000 pods total (50 pods × 100 iterations = 5,000).
"""
import asyncio
import time
from statistics import mean, stdev

import anyio
import httpx

import kr8s.asyncio
from kr8s.asyncio.objects import Deployment


async def benchmark_kr8s_with_objects(api, namespace, iterations=100):
    """Benchmark kr8s.get() with raw=False (creates Pod objects)."""
    times = []
    count = 0

    for _ in range(iterations):
        start = time.perf_counter()
        count = 0
        async for pod in api.get("pods", namespace=namespace):
            # Access some attributes to simulate real usage
            _ = pod.metadata.name
            _ = pod.metadata.namespace
            count += 1
        end = time.perf_counter()
        times.append(end - start)

    return times, count


async def benchmark_kr8s_with_raw(api, namespace, iterations=100):
    """Benchmark kr8s.get() with raw=True (returns dicts)."""
    times = []
    count = 0

    for _ in range(iterations):
        start = time.perf_counter()
        count = 0
        async for pod in api.get("pods", namespace=namespace, raw=True):
            # Access some attributes to simulate real usage
            _ = pod["metadata"]["name"]
            _ = pod["metadata"]["namespace"]
            count += 1
        end = time.perf_counter()
        times.append(end - start)

    return times, count


async def benchmark_httpx_direct(api, namespace, iterations=100):
    """Benchmark direct httpx calls with pagination."""
    times = []
    count = 0

    ssl_ctx = await api.auth.ssl_context()
    headers = {"Authorization": f"Bearer {api.auth.token}"} if api.auth.token else {}

    async with httpx.AsyncClient(
        base_url=api.auth.server, headers=headers, verify=ssl_ctx
    ) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            count = 0
            continue_token = None

            while True:
                params = {"limit": "100"}
                if continue_token:
                    params["continue"] = continue_token

                resp = await client.get(
                    f"/api/v1/namespaces/{namespace}/pods", params=params
                )
                data = resp.json()

                for item in data.get("items", []):
                    # Access some attributes to simulate real usage
                    _ = item["metadata"]["name"]
                    _ = item["metadata"]["namespace"]
                    count += 1

                continue_token = data.get("metadata", {}).get("continue")
                if not continue_token:
                    break

            end = time.perf_counter()
            times.append(end - start)

    return times, count


async def create_test_deployment(api, namespace, replicas=50):
    """Create a deployment with the specified number of replicas."""
    deployment_spec = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "kr8s-benchmark-test",
            "namespace": namespace,
        },
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": "kr8s-benchmark"}},
            "template": {
                "metadata": {"labels": {"app": "kr8s-benchmark"}},
                "spec": {
                    "containers": [
                        {
                            "name": "pause",
                            "image": "gcr.io/google_containers/pause",
                        }
                    ]
                },
            },
        },
    }

    deployment = await Deployment(deployment_spec)

    # Check if it already exists and delete it
    if await deployment.exists():
        print("  Deleting existing deployment...")
        await deployment.delete()
        while await deployment.exists():
            await anyio.sleep(0.5)

    # Create the deployment
    print(f"  Creating deployment with {replicas} replicas...")
    await deployment.create()

    # Wait for all pods to be ready
    print(f"  Waiting for {replicas} pods to be ready...")
    while True:
        await deployment.refresh()
        ready = deployment.status.get("readyReplicas", 0)
        if ready == replicas:
            break
        print(f"    {ready}/{replicas} pods ready...")
        await anyio.sleep(2)

    print(f"  ✓ All {replicas} pods are ready")
    return deployment


async def cleanup_deployment(deployment):
    """Clean up the test deployment."""
    print("\nCleaning up test deployment...")
    if await deployment.exists():
        await deployment.delete()
        while await deployment.exists():
            await anyio.sleep(0.5)
    print("✓ Cleanup complete")


def print_stats(name, times, total_pods):
    """Print statistics for a benchmark run."""
    avg = mean(times)
    std = stdev(times) if len(times) > 1 else 0
    total = sum(times)

    print(f"\n{name}:")
    print(f"  Total time:     {total:.3f}s")
    print(f"  Average time:   {avg:.3f}s per iteration")
    print(f"  Std deviation:  {std:.3f}s")
    print(f"  Min time:       {min(times):.3f}s")
    print(f"  Max time:       {max(times):.3f}s")
    print(
        f"  Total pods:     {total_pods} ({total_pods / len(times):.0f} per iteration)"
    )
    print(f"  Throughput:     {total_pods / total:.0f} pods/sec")


def print_comparison(times_objects, times_raw, times_httpx):
    """Print comparison statistics."""
    print("\n" + "=" * 70)
    print("Comparison")
    print("=" * 70)

    avg_objects = mean(times_objects)
    avg_raw = mean(times_raw)
    avg_httpx = mean(times_httpx)

    speedup_raw_vs_objects = ((avg_objects - avg_raw) / avg_objects) * 100
    speedup_raw_vs_httpx = ((avg_httpx - avg_raw) / avg_httpx) * 100

    print("\nraw=True vs raw=False:")
    print(
        f"  {speedup_raw_vs_objects:+.1f}% (raw=True is {abs(speedup_raw_vs_objects):.1f}% "
        f"{'faster' if speedup_raw_vs_objects > 0 else 'slower'})"
    )

    print("\nraw=True vs direct httpx:")
    print(
        f"  {speedup_raw_vs_httpx:+.1f}% (raw=True is {abs(speedup_raw_vs_httpx):.1f}% "
        f"{'faster' if speedup_raw_vs_httpx > 0 else 'slower'})"
    )

    overhead_objects = ((avg_objects - avg_httpx) / avg_httpx) * 100
    overhead_raw = ((avg_raw - avg_httpx) / avg_httpx) * 100

    print("\nOverhead compared to direct httpx:")
    print(f"  raw=False: {overhead_objects:+.1f}%")
    print(f"  raw=True:  {overhead_raw:+.1f}%")


async def main():
    """Run the benchmark."""
    print("=" * 70)
    print("Kr8s Raw Get Benchmark")
    print("=" * 70)

    # Initialize API
    api = await kr8s.asyncio.api()
    namespace = api.namespace

    print(f"\nUsing namespace: {namespace}")

    # Create test deployment
    print("\nSetting up test environment...")
    deployment = await create_test_deployment(api, namespace, replicas=50)

    try:
        # Verify we have 50 pods
        pod_count = sum([1 async for _ in api.get("pods", namespace=namespace)])
        print(f"\n✓ Verified {pod_count} pods are ready in namespace {namespace}")

        if pod_count < 50:
            print(f"\n⚠ Warning: Expected 50 pods but found {pod_count}")
            print("Proceeding with benchmark anyway...")

        iterations = 100
        num_runs = 10
        print(f"\nRunning {num_runs} complete benchmark runs")
        print(
            f"Each run performs {iterations} iterations (simulating {pod_count * iterations} pod reads per run)"
        )
        print(f"Total simulated pod reads: {pod_count * iterations * num_runs}")

        # Warmup
        print("\nWarming up...")
        _ = [pod async for pod in api.get("pods", namespace=namespace)]

        # Storage for all runs
        all_results_objects = []
        all_results_raw = []
        all_results_httpx = []

        # Run multiple benchmark iterations
        for run in range(1, num_runs + 1):
            print(f"\n{'=' * 70}")
            print(f"Benchmark Run {run}/{num_runs}")
            print(f"{'=' * 70}")

            print("\n1/3: Benchmarking kr8s with raw=False (APIObject instances)...")
            times_objects, count_objects = await benchmark_kr8s_with_objects(
                api, namespace, iterations
            )
            all_results_objects.append(
                {
                    "times": times_objects,
                    "count": count_objects,
                    "avg": mean(times_objects),
                    "total": sum(times_objects),
                }
            )

            print("2/3: Benchmarking kr8s with raw=True (raw dictionaries)...")
            times_raw, count_raw = await benchmark_kr8s_with_raw(
                api, namespace, iterations
            )
            all_results_raw.append(
                {
                    "times": times_raw,
                    "count": count_raw,
                    "avg": mean(times_raw),
                    "total": sum(times_raw),
                }
            )

            print("3/3: Benchmarking direct httpx calls...")
            times_httpx, count_httpx = await benchmark_httpx_direct(
                api, namespace, iterations
            )
            all_results_httpx.append(
                {
                    "times": times_httpx,
                    "count": count_httpx,
                    "avg": mean(times_httpx),
                    "total": sum(times_httpx),
                }
            )

            # Print quick summary for this run
            print(f"\nRun {run} Summary:")
            print(
                f"  raw=False: {all_results_objects[-1]['total']:.3f}s (avg {all_results_objects[-1]['avg']:.3f}s)"
            )
            print(
                f"  raw=True:  {all_results_raw[-1]['total']:.3f}s (avg {all_results_raw[-1]['avg']:.3f}s)"
            )
            print(
                f"  httpx:     {all_results_httpx[-1]['total']:.3f}s (avg {all_results_httpx[-1]['avg']:.3f}s)"
            )

        # Calculate aggregate statistics
        print("\n" + "=" * 70)
        print("AGGREGATE RESULTS (averaged over all runs)")
        print("=" * 70)

        # Flatten all times from all runs
        all_times_objects = [
            t for result in all_results_objects for t in result["times"]
        ]
        all_times_raw = [t for result in all_results_raw for t in result["times"]]
        all_times_httpx = [t for result in all_results_httpx for t in result["times"]]

        total_pods_processed = count_objects * iterations * num_runs

        print_stats(
            "kr8s with raw=False (APIObject instances)",
            all_times_objects,
            total_pods_processed,
        )
        print_stats(
            "kr8s with raw=True (raw dictionaries)", all_times_raw, total_pods_processed
        )
        print_stats(
            "Direct httpx calls (baseline)", all_times_httpx, total_pods_processed
        )

        # Print comparison
        print_comparison(all_times_objects, all_times_raw, all_times_httpx)

        # Print run-by-run variance
        print("\n" + "=" * 70)
        print("Run-by-Run Variance")
        print("=" * 70)

        avg_totals_objects = [r["total"] for r in all_results_objects]
        avg_totals_raw = [r["total"] for r in all_results_raw]
        avg_totals_httpx = [r["total"] for r in all_results_httpx]

        print("\nraw=False total time across runs:")
        print(f"  Mean:   {mean(avg_totals_objects):.3f}s")
        print(f"  StdDev: {stdev(avg_totals_objects):.3f}s")
        print(f"  Min:    {min(avg_totals_objects):.3f}s")
        print(f"  Max:    {max(avg_totals_objects):.3f}s")

        print("\nraw=True total time across runs:")
        print(f"  Mean:   {mean(avg_totals_raw):.3f}s")
        print(f"  StdDev: {stdev(avg_totals_raw):.3f}s")
        print(f"  Min:    {min(avg_totals_raw):.3f}s")
        print(f"  Max:    {max(avg_totals_raw):.3f}s")

        print("\nhttpx total time across runs:")
        print(f"  Mean:   {mean(avg_totals_httpx):.3f}s")
        print(f"  StdDev: {stdev(avg_totals_httpx):.3f}s")
        print(f"  Min:    {min(avg_totals_httpx):.3f}s")
        print(f"  Max:    {max(avg_totals_httpx):.3f}s")

        print("\n" + "=" * 70)

    finally:
        # Cleanup
        await cleanup_deployment(deployment)


if __name__ == "__main__":
    asyncio.run(main())
