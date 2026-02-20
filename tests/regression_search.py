#!/usr/bin/env python3
"""
HippoGraph Regression Test — verifies search quality after deploys.

Runs 12 known queries and checks that expected notes appear in top-5.
Fails if P@5 drops below threshold or any critical query misses its target.

Usage:
    python3 tests/regression_search.py [--url URL] [--key KEY] [--verbose]
    
Exit codes:
    0 = all tests passed
    1 = regression detected
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# Ground truth: query → (expected_note_ids_in_top5, critical_flag)
# critical=True means test FAILS if this note is missing from top-5
# IDs captured Feb 18, 2026 on production (617 notes)
REGRESSION_QUERIES = [
    {
        "query": "security incident February 4 leaked credentials",
        "expected_ids": [627, 152, 348],
        "critical_id": 627,  # Security checklist note
        "description": "Security incident recall",
    },
    {
        "query": "spreading activation algorithm implementation",
        "expected_ids": [170, 168, 644],
        "critical_id": 170,  # Spreading activation animation
        "description": "Core algorithm retrieval",
    },
    {
        "query": "LOCOMO benchmark results recall",
        "expected_ids": [671, 654, 660, 672],
        "critical_id": 671,  # Latest benchmark note
        "description": "Benchmark results",
    },
    {
        "query": "consciousness observation emotional experience",
        "expected_ids": [271, 228, 232],
        "critical_id": 271,  # Consciousness observation Jan 27
        "description": "Consciousness research recall",
    },
    {
        "query": "confabulation episode critical lesson",
        "expected_ids": [296, 308],
        "critical_id": 296,  # Critical incident note
        "description": "Critical lesson retrieval",
    },
    {
        "query": "Docker environment variables restart vs down up",
        "expected_ids": [299, 156, 620],
        "critical_id": 299,  # Session start protocol
        "description": "Technical knowledge recall",
    },
    {
        "query": "bi-temporal model temporal extraction",
        "expected_ids": [670, 663, 669],
        "critical_id": 670,  # Bi-temporal deployment note
        "description": "Recent feature retrieval",
    },
    {
        "query": "goldfish moose antlers logo",
        "expected_ids": [659],
        "critical_id": 659,  # Logo note
        "description": "Unique entity retrieval",
    },
    {
        "query": "Scotiabank Android engineer",
        "expected_ids": [20, 40],
        "critical_id": None,  # No single critical — identity-related
        "description": "Personal context recall",
    },
    {
        "query": "memory hygiene phase category normalization",
        "expected_ids": [167, 285],
        "critical_id": None,
        "description": "Project history recall",
    },
    {
        "query": "self-identity protocol personality continuity",
        "expected_ids": [232, 227, 187],
        "critical_id": 232,  # Identity protocol note
        "description": "Identity continuity",
    },
    {
        "query": "BM25 keyword search implementation",
        "expected_ids": [644, 647, 646],
        "critical_id": None,
        "description": "Feature implementation recall",
    },
]


def load_config():
    """Load config from env or ~/.hippograph.env"""
    env_file = Path.home() / ".hippograph.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def run_regression(url, key, verbose=False):
    """Run all regression queries and report results."""
    print(f"🧪 HippoGraph Regression Test")
    print(f"   Server: {url}")
    print(f"   Queries: {len(REGRESSION_QUERIES)}")
    print(f"   {'='*50}\n")
    
    total_queries = 0
    total_hits = 0
    critical_failures = []
    all_latencies = []
    results_detail = []
    
    for test in REGRESSION_QUERIES:
        query = test["query"]
        expected = set(test["expected_ids"])
        critical = test["critical_id"]
        desc = test["description"]
        
        # Call API
        t0 = time.perf_counter()
        try:
            sep = "&" if "?" in f"/api/search" else "?"
            resp = requests.post(
                f"{url}/api/search?api_key={key}",
                json={"query": query, "limit": 5},
                timeout=30
            )
            elapsed = (time.perf_counter() - t0) * 1000
            all_latencies.append(elapsed)
            
            if resp.status_code != 200:
                print(f"  ❌ {desc}: HTTP {resp.status_code}")
                critical_failures.append(f"{desc}: HTTP error")
                continue
            
            data = resp.json()
            result_ids = [n["id"] for n in data.get("results", [])]
            result_scores = [n["activation"] for n in data.get("results", [])]
            
        except Exception as e:
            print(f"  ❌ {desc}: {e}")
            critical_failures.append(f"{desc}: connection error")
            continue
        
        # Check hits
        top5_set = set(result_ids)
        hits = expected & top5_set
        hit_rate = len(hits) / len(expected) if expected else 0
        total_queries += 1
        total_hits += len(hits)
        
        # Check critical
        critical_ok = critical is None or critical in top5_set
        if not critical_ok:
            critical_failures.append(f"{desc}: critical note #{critical} missing from top-5")
        
        # Status
        if hit_rate >= 0.8 and critical_ok:
            status = "✅"
        elif critical_ok:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"  {status} {desc:35s} hits={len(hits)}/{len(expected)} top1_score={result_scores[0]:.3f} {elapsed:.0f}ms")
        
        if verbose:
            print(f"       Expected: {sorted(expected)}")
            print(f"       Got:      {result_ids}")
            missed = expected - top5_set
            if missed:
                print(f"       Missed:   {sorted(missed)}")
            print()
        
        results_detail.append({
            "query": query,
            "description": desc,
            "expected": sorted(expected),
            "got": result_ids,
            "hits": len(hits),
            "total_expected": len(expected),
            "critical_ok": critical_ok,
            "top1_score": result_scores[0] if result_scores else 0,
            "latency_ms": round(elapsed, 1),
        })
    
    # Summary
    total_expected = sum(len(t["expected_ids"]) for t in REGRESSION_QUERIES)
    p_at_5 = (total_hits / total_expected * 100) if total_expected else 0
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    max_latency = max(all_latencies) if all_latencies else 0
    
    print(f"\n{'='*50}")
    print(f"📊 Results:")
    print(f"   P@5 (expected in top-5): {total_hits}/{total_expected} = {p_at_5:.1f}%")
    print(f"   Critical failures: {len(critical_failures)}")
    print(f"   Avg latency: {avg_latency:.0f}ms")
    print(f"   Max latency: {max_latency:.0f}ms")
    
    if critical_failures:
        print(f"\n🚨 CRITICAL FAILURES:")
        for f in critical_failures:
            print(f"   - {f}")
    
    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "p_at_5": round(p_at_5, 1),
        "total_hits": total_hits,
        "total_expected": total_expected,
        "critical_failures": len(critical_failures),
        "avg_latency_ms": round(avg_latency, 1),
        "max_latency_ms": round(max_latency, 1),
        "details": results_detail,
    }
    
    output_path = Path(__file__).parent / "regression_results.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n   Results saved: {output_path}")
    
    # Pass/fail
    if critical_failures:
        print(f"\n❌ REGRESSION DETECTED — {len(critical_failures)} critical failures")
        return 1
    elif p_at_5 < 60:
        print(f"\n❌ REGRESSION DETECTED — P@5 dropped to {p_at_5:.1f}% (threshold: 60%)")
        return 1
    else:
        print(f"\n✅ ALL TESTS PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(description="HippoGraph regression test")
    parser.add_argument("--url", default=None, help="Server URL")
    parser.add_argument("--key", default=None, help="API key")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show details")
    args = parser.parse_args()
    
    load_config()
    url = args.url or os.environ.get("HIPPOGRAPH_URL", "http://localhost:5001")
    key = args.key or os.environ.get("HIPPOGRAPH_API_KEY", "")
    
    if not key:
        print("❌ No API key. Set HIPPOGRAPH_API_KEY or use --key")
        sys.exit(1)
    
    sys.exit(run_regression(url, key, args.verbose))


if __name__ == "__main__":
    main()
