#!/usr/bin/env python3
"""
F-008: Aggregate latency / token / cost analysis over persisted MLflow traces.

Reads all traces in the configured Databricks MLflow experiment and prints:
- per-scenario trace counts, latency percentiles, token totals, and cost totals
- slowest and most expensive traces
- span-level breakdown of the slowest trace

Usage:
  python analyze_trace_metrics.py
"""

from __future__ import annotations

import os
import statistics
import sys
from collections import defaultdict

from dotenv import load_dotenv


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (p in 0..1)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = p * (len(ordered) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def main() -> int:
    load_dotenv()

    if not (os.getenv("DATABRICKS_HOST") or os.path.exists(os.path.expanduser("~/.databrickscfg"))):
        print("Missing Databricks config (see .env.example).", file=sys.stderr)
        return 2

    import mlflow

    mlflow.set_tracking_uri("databricks")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    exp = mlflow.get_experiment_by_name(experiment_name)
    if not exp:
        print(f"Experiment not found: {experiment_name}", file=sys.stderr)
        return 2

    traces = mlflow.search_traces(
        locations=[exp.experiment_id], max_results=1000, return_type="list"
    )
    print(f"Experiment: {experiment_name} ({exp.experiment_id})")
    print(f"Traces analyzed: {len(traces)}")
    print()

    by_scenario: dict[str, list] = defaultdict(list)
    for t in traces:
        scenario = (t.info.tags or {}).get("scenario") or "baseline/unlabeled"
        by_scenario[scenario].append(t)

    print("=== Per-scenario summary ===")
    print(f"{'scenario':<22} {'n':>3} {'lat_avg':>9} {'lat_p50':>9} {'lat_p95':>9} "
          f"{'tokens':>8} {'cost_usd':>10}")
    for scenario, group in sorted(by_scenario.items()):
        lats = [float(t.info.execution_time_ms or 0) for t in group]
        tokens = sum(int((t.info.token_usage or {}).get("total_tokens", 0)) for t in group)
        cost = sum(float((t.info.cost or {}).get("total_cost", 0)) for t in group)
        print(f"{scenario:<22} {len(group):>3} {statistics.mean(lats):>9.0f} "
              f"{percentile(lats, 0.5):>9.0f} {percentile(lats, 0.95):>9.0f} "
              f"{tokens:>8} {cost:>10.6f}")
    print()

    print("=== Slowest traces (ms) ===")
    for t in sorted(traces, key=lambda x: x.info.execution_time_ms or 0, reverse=True)[:5]:
        tags = t.info.tags or {}
        print(f"  {t.info.trace_id}  {t.info.execution_time_ms:>6} ms  "
              f"scenario={tags.get('scenario', 'baseline/unlabeled')} "
              f"turn={tags.get('turn', '-')}")
    print()

    print("=== Most expensive traces (USD) ===")
    for t in sorted(traces, key=lambda x: (x.info.cost or {}).get("total_cost", 0), reverse=True)[:5]:
        cost = t.info.cost or {}
        print(f"  {t.info.trace_id}  ${cost.get('total_cost', 0):.6f}  "
              f"in={cost.get('input_cost', 0):.6f} out={cost.get('output_cost', 0):.6f} "
              f"tokens={(t.info.token_usage or {}).get('total_tokens', 0)}")
    print()

    slowest = max(traces, key=lambda x: x.info.execution_time_ms or 0)
    print(f"=== Span breakdown of slowest trace {slowest.info.trace_id} "
          f"({slowest.info.execution_time_ms} ms) ===")
    spans = sorted(
        slowest.data.spans,
        key=lambda s: (s.end_time_ns or 0) - (s.start_time_ns or 0),
        reverse=True,
    )
    for s in spans[:10]:
        dur_ms = ((s.end_time_ns or 0) - (s.start_time_ns or 0)) / 1e6
        print(f"  {dur_ms:>8.1f} ms  {s.name:<18} {s.span_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
