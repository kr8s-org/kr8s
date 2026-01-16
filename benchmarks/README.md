# Kr8s Benchmarks

This directory contains benchmark scripts for measuring kr8s performance.

## benchmark_raw_get.py

Compares the performance of different ways to list Kubernetes Pods:

1. **kr8s with `raw=False`** (default): Creates APIObject instances
2. **kr8s with `raw=True`**: Returns raw dictionaries via kr8s API  
3. **Direct httpx calls**: Baseline using httpx directly with pagination handling

The benchmark creates a deployment with 50 pods and iterates 100 times to simulate processing 5,000 pods (50 × 100 = 5,000).

### Running the Benchmark

```bash
export KUBECONFIG=path/to/kubeconfig
uv run python benchmarks/benchmark_raw_get.py
```

### Example Output

```
======================================================================
Results
======================================================================

kr8s with raw=False (APIObject instances):
  Total time:     2.384s
  Average time:   0.048s per iteration
  Throughput:     4 pods/sec

kr8s with raw=True (raw dictionaries):
  Total time:     0.414s
  Average time:   0.008s per iteration
  Throughput:     24 pods/sec

Direct httpx calls (baseline):
  Total time:     0.409s
  Average time:   0.008s per iteration
  Throughput:     24 pods/sec

======================================================================
Comparison
======================================================================

raw=True vs raw=False:
  +82.6% (raw=True is 82.6% faster)

raw=True vs direct httpx:
  -1.3% (raw=True is 1.3% slower)

Overhead compared to direct httpx:
  raw=False: +483.2%
  raw=True:  +1.3%
```

### Key Findings

- Using `raw=True` is **~83% faster** than creating APIObject instances
- Using `raw=True` has only **~1% overhead** compared to direct httpx calls
- Creating APIObject instances adds significant overhead (~483%) compared to direct httpx

### When to Use `raw=True`

Consider using `raw=True` when:
- Processing large numbers of resources
- You only need to extract simple metadata
- Performance is critical
- You don't need APIObject methods (like `.delete()`, `.patch()`, etc.)

