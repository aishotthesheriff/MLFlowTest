#!/usr/bin/env python3
"""
F-015 / experiment 012: judge the tool calls captured in experiment 011.

Loads exactly the five source traces listed in the 011 manifest, with their
spans intact, and runs two trace-based evaluation passes per repetition:

  1. ground-truth-free ToolCallCorrectness + ToolCallEfficiency, with an empty
     expectations dict on every row (no expected_tool_calls -> no fuzzy mode)
  2. ToolCallCorrectness(name="tool_call_correctness_exact",
     should_exact_match=True, should_consider_ordering=False) with one shared
     expectation: get_weather(city="SF")

No predict_fn: mlflow.genai.evaluate consumes the trace column directly. Each
run's verdicts are read from that run's result_df, not from the source traces
(MLflow may attach expectations/feedback to linked or copied traces).

Usage:
  python evaluate_tool_calls.py --register   # register the 3 scorer configs
  python evaluate_tool_calls.py              # 2 repetitions x 2 passes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

MANIFEST_PATH = Path("docs/demo/tool_call_manifest.json")
RESULTS_PATH = Path("docs/demo/tool_call_eval_results.json")
CASES = (
    "tool_happy",
    "tool_no_call",
    "tool_wrong_tool",
    "tool_wrong_args",
    "tool_retry_storm",
)
SCORER_NAMES = ("tool_call_correctness", "tool_call_efficiency", "tool_call_correctness_exact")
# The exact-match expectation encodes what the user asked for, not the injected bug.
EXPECTED_CALL = {"expected_tool_calls": [{"name": "get_weather", "arguments": {"city": "SF"}}]}
EXPECTED_EXACT_SEQUENCE = ("yes", "no", "no", "no", "no")
REPETITIONS = 2


def build_scorers():
    from mlflow.genai.scorers import ToolCallCorrectness, ToolCallEfficiency

    return {
        "unaided": [
            ToolCallCorrectness(name="tool_call_correctness", model="databricks"),
            ToolCallEfficiency(name="tool_call_efficiency", model="databricks"),
        ],
        "exact": [
            ToolCallCorrectness(
                name="tool_call_correctness_exact",
                model="databricks",
                should_exact_match=True,
                should_consider_ordering=False,
            )
        ],
    }


def load_sources():
    """Return (manifest, [(case, trace), ...]) or exit with a clear failure."""
    import mlflow

    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"manifest missing: {MANIFEST_PATH} (run trace_tool_calls.py first)")
    manifest = json.loads(MANIFEST_PATH.read_text())
    entries = manifest.get("cases", [])
    names = [entry["case"] for entry in entries]
    if tuple(names) != CASES:
        raise RuntimeError(f"manifest cases {names} != expected {list(CASES)}")
    if len(set(names)) != len(names):
        raise RuntimeError(f"duplicate cases in manifest: {names}")

    sources = []
    for entry in entries:
        case = entry["case"]
        trace = mlflow.get_trace(entry["trace_id"])
        tags = trace.info.tags or {}
        if tags.get("scenario") != "tool_calls":
            raise RuntimeError(f"{case}: scenario tag {tags.get('scenario')!r} != 'tool_calls'")
        if tags.get("tool_case") != case:
            raise RuntimeError(f"{case}: tool_case tag {tags.get('tool_case')!r} != {case!r}")
        if tags.get("session_id") != manifest["session_id"]:
            raise RuntimeError(f"{case}: session_id tag does not match manifest")
        if not any(s.span_type == "CHAT_MODEL" for s in trace.data.spans):
            raise RuntimeError(f"{case}: source trace has no CHAT_MODEL span; spans were lost")
        sources.append((case, trace))
    return manifest, sources


def _normalize(value) -> str:
    """yes / no / error / missing — errors and missing results are not 'no'."""
    if value is None:
        return "missing"
    text = str(value).lower()
    if text in {"yes", "true", "1"}:
        return "yes"
    if text in {"no", "false", "0"}:
        return "no"
    return text


def _verdict(df, index: int, name: str) -> dict:
    prefix = name + "/"
    error = df.iloc[index].get(prefix + "error_message")
    if error is not None and str(error).lower() not in {"nan", "none", ""}:
        return {"value": "error", "rationale": str(error)[:300]}
    value_col = next((c for c in df.columns if c == prefix + "value"), None)
    if value_col is None:
        return {"value": "missing", "rationale": "no value column"}
    value = _normalize(df.iloc[index].get(value_col))
    rationale = ""
    for suffix in ("rationale", "justification"):
        col = prefix + suffix
        if col in df.columns:
            rationale = str(df.iloc[index].get(col) or "")
            if rationale.lower() not in {"nan", "none", ""}:
                break
    return {"value": value, "rationale": rationale[:300]}


def run_pass(label: str, scorers, sources, expectations: dict):
    import pandas as pd
    import mlflow

    rows = [{"trace": trace, "expectations": expectations} for _case, trace in sources]
    result = mlflow.genai.evaluate(data=pd.DataFrame(rows), scorers=scorers)
    df = result.result_df
    if df is None or len(df) != len(sources):
        raise RuntimeError(f"{label}: expected {len(sources)} result rows, got 0 or None")
    if "trace_id" not in df.columns or "tags" not in df.columns:
        raise RuntimeError(f"{label}: result_df missing trace_id/tags columns")

    # Join by source trace ID (not row position) and confirm the scenario tag on
    # every result row. A duplicated or absent trace is a hard failure.
    source_ids = [trace.info.trace_id for _case, trace in sources]
    seen = {}
    for position, result_id in enumerate(df["trace_id"].tolist()):
        if result_id in seen:
            raise RuntimeError(f"{label}: duplicate result row for trace {result_id}")
        seen[result_id] = position
        tags = df.iloc[position]["tags"] or {}
        if isinstance(tags, str):
            import ast
            tags = ast.literal_eval(tags)
        if tags.get("scenario") != "tool_calls":
            raise RuntimeError(
                f"{label}: trace {result_id} scenario tag {tags.get('scenario')!r} != 'tool_calls'"
            )
    missing = [trace_id for trace_id in source_ids if trace_id not in seen]
    if missing:
        raise RuntimeError(f"{label}: no result row for source traces: {missing}")
    return {"run_id": result.run_id, "df": df, "index": seen}


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true", help="Register the 3 scorer configurations.")
    args = parser.parse_args()

    import mlflow

    mlflow.set_tracking_uri("databricks")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        print(f"Experiment not found: {experiment_name}", file=sys.stderr)
        return 2
    mlflow.set_experiment(experiment_name)

    scorers = build_scorers()
    all_scorers = scorers["unaided"] + scorers["exact"]
    if args.register:
        print("Registering tool-call scorers (registration does not enable monitoring)...")
        for scorer in all_scorers:
            registered = scorer.register(experiment_id=experiment.experiment_id)
            print(f"  {getattr(registered, 'name', scorer.name)}")
        return 0

    manifest, sources = load_sources()
    print(f"Experiment: {experiment_name} ({experiment.experiment_id})")
    print(f"Source traces: {len(sources)} (manifest {MANIFEST_PATH})")

    repetitions = []
    run_ids = {}
    for repeat in range(1, REPETITIONS + 1):
        unaided = run_pass(f"rep{repeat}/unaided", scorers["unaided"], sources, {})
        exact = run_pass(f"rep{repeat}/exact", scorers["exact"], sources, EXPECTED_CALL)
        run_ids[f"rep{repeat}"] = {"unaided": unaided["run_id"], "exact": exact["run_id"]}

        rows = []
        for case, trace in sources:
            trace_id = trace.info.trace_id
            u_index = unaided["index"][trace_id]
            x_index = exact["index"][trace_id]
            rows.append({
                "case": case,
                "trace_id": trace_id,
                "scenario": "tool_calls",
                "tool_call_correctness": _verdict(unaided["df"], u_index, "tool_call_correctness"),
                "tool_call_efficiency": _verdict(unaided["df"], u_index, "tool_call_efficiency"),
                "tool_call_correctness_exact": _verdict(exact["df"], x_index, "tool_call_correctness_exact"),
            })
        repetitions.append({"repeat": repeat, "rows": rows})

    # --- Verdict tables ---
    problems = []
    for rep in repetitions:
        rep_key = "rep" + str(rep["repeat"])
        print(f"\n=== Repetition {rep['repeat']} ===")
        print(f"  runs: unaided={run_ids[rep_key]['unaided']} "
              f"exact={run_ids[rep_key]['exact']}")
        print(f"  {'case':<18} {'unaided':<9} {'efficiency':<11} {'exact':<9} agree?")
        for row in rep["rows"]:
            u = row["tool_call_correctness"]["value"]
            e = row["tool_call_efficiency"]["value"]
            x = row["tool_call_correctness_exact"]["value"]
            agree = "same" if u == x else "DISAGREE"
            print(f"  {row['case']:<18} {u:<9} {e:<11} {x:<9} {agree}")
            for name in SCORER_NAMES:
                if row[name]["value"] in {"error", "missing"}:
                    problems.append(
                        f"rep{rep['repeat']} {row['case']} {name}={row[name]['value']}: "
                        f"{row[name]['rationale']}"
                    )

        sequence = tuple(row["tool_call_correctness_exact"]["value"] for row in rep["rows"])
        if sequence != EXPECTED_EXACT_SEQUENCE:
            problems.append(
                f"rep{rep['repeat']} exact sequence {sequence} != {EXPECTED_EXACT_SEQUENCE}"
            )
        print(f"  exact-match sequence: {sequence} (expected {EXPECTED_EXACT_SEQUENCE})")

        disagreements = [
            f"{r['case']}: unaided={r['tool_call_correctness']['value']} "
            f"exact={r['tool_call_correctness_exact']['value']}"
            for r in rep["rows"]
            if r["tool_call_correctness"]["value"] != r["tool_call_correctness_exact"]["value"]
        ]
        print("  correctness modes disagree: " + (", ".join(disagreements) or "none"))

    print("\n=== Verdict flips between repetitions ===")
    flips = []
    for name in SCORER_NAMES:
        first = {r["case"]: r[name]["value"] for r in repetitions[0]["rows"]}
        second = {r["case"]: r[name]["value"] for r in repetitions[1]["rows"]}
        changed = [f"{case}: {first[case]}->{second[case]}" for case in CASES if first[case] != second[case]]
        flips.append({"scorer": name, "flips": changed})
        print(f"  {name}: " + (", ".join(changed) if changed else "none"))

    RESULTS_PATH.write_text(json.dumps({
        "manifest": str(MANIFEST_PATH),
        "manifest_session_id": manifest["session_id"],
        "expectation": EXPECTED_CALL,
        "run_ids": run_ids,
        "repetitions": repetitions,
        "flips": flips,
    }, indent=2) + "\n")
    print(f"\nWrote {RESULTS_PATH}")

    if problems:
        print("\nFAIL: tool-call evaluation verification failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("All repetitions have 5 complete rows and the expected exact-match sequence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
