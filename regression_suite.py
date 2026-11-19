#!/usr/bin/env python3
"""F-014: standing A/B regression set for the MLFlowTest demo.

The set is defined by the evaluation scripts themselves, so there is no fourth
copy of the case lists to drift:

  * 6 output controls  — evaluate_traces.CONTROL_NAMES
  * 5 output scorers   — evaluate_traces.SCORER_NAMES
  * 5 tool-call cases  — evaluate_tool_calls.CASES
  * 3 tool verdicts    — evaluate_tool_calls.SCORER_NAMES

Modes:
  --validate          (default) offline check that the checked-in artifacts
                      still cover the whole standing set and match baseline
  --summary           print the 14-case matrix with its expected detections
  --run LABEL         re-run both eval suites with controls and snapshot the
                      tool-call results under docs/demo/regression/LABEL.json
                      (needs Databricks auth; makes judge calls)
  --ab LABEL          generate a variant trace (--endpoint/--prompt), score it
                      with the 6 standing controls, snapshot structured results.
                      This is the mode that actually varies an endpoint/prompt.
  --compare A B       diff two snapshots (tool-call or output-eval artifacts)

A/B workflow: --ab arm_a, change endpoint/prompt, --ab arm_b, then --compare the
two *.output.json snapshots. Use --run only to re-score the frozen scripted cases.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from evaluate_tool_calls import (  # noqa: E402
    CASES,
    EXPECTED_EXACT_SEQUENCE,
    MANIFEST_PATH,
    RESULTS_PATH,
    SCORER_NAMES as TOOL_SCORERS,
)
from evaluate_traces import (  # noqa: E402
    CONTROL_NAMES,
    SCORER_NAMES as OUTPUT_SCORERS,
    _is_fail,
)
from lab_tags import git_sha  # noqa: E402

REGRESSION_DIR = Path("docs/demo/regression")
ROOT = Path(__file__).resolve().parent

# Exp 012 baseline verdicts, in TOOL_SCORER_NAMES order. These are the reference
# for --validate and the "before" side of --compare; an A/B variant is expected
# to change some of them.
BASELINE_VERDICTS = {
    "tool_happy": ("yes", "yes", "yes"),
    "tool_no_call": ("no", "yes", "no"),  # efficiency disagreeing is F-016
    "tool_wrong_tool": ("no", "no", "no"),
    "tool_wrong_args": ("no", "no", "no"),
    "tool_retry_storm": ("no", "no", "no"),
}


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing artifact: {path}")
    return json.loads(path.read_text())


def _verdict(row: dict) -> tuple[str, ...]:
    values = []
    for scorer in TOOL_SCORERS:
        cell = row.get(scorer)
        values.append(cell.get("value", "missing") if isinstance(cell, dict) else "missing")
    return tuple(values)


def summary() -> int:
    print("Standing A/B regression set (F-014)")
    print(f"\nOutput controls ({len(CONTROL_NAMES)}) — each must be caught by >= 1 scorer:")
    for name in CONTROL_NAMES:
        print(f"  {name:<24} scorers: {', '.join(OUTPUT_SCORERS)}")
    print(f"\nTool-call cases ({len(CASES)}) — baseline verdicts {TOOL_SCORERS}:")
    for case in CASES:
        print(f"  {case:<18} {'/'.join(BASELINE_VERDICTS[case])}")
    print(f"\nExact-match sequence: {','.join(EXPECTED_EXACT_SEQUENCE)}")
    print(f"Dependencies: F-010 tags (scenario/tool_case), F-015 tool traces, F-009 scorers")
    return 0


def validate() -> int:
    problems: list[str] = []

    for label, names, expected in (
        ("output controls", CONTROL_NAMES, 6),
        ("output scorers", OUTPUT_SCORERS, 5),
        ("tool cases", CASES, 5),
        ("tool verdicts", TOOL_SCORERS, 3),
    ):
        if len(names) != expected or len(set(names)) != expected:
            problems.append(f"{label}: expected {expected} unique names, got {names}")
        print(f"OK  {label}: {len(names)} ({', '.join(names)})")

    manifest = _load(MANIFEST_PATH)
    manifest_cases = tuple(entry["case"] for entry in manifest["cases"])
    if manifest_cases != CASES:
        problems.append(f"manifest cases {manifest_cases} != {CASES}")
    else:
        print(f"OK  manifest cases: {len(manifest_cases)}")

    results = _load(RESULTS_PATH)
    exact_sequences: list[tuple[str, ...]] = []
    for rep in results.get("repetitions", []):
        rows = {row["case"]: row for row in rep["rows"]}
        if set(rows) != set(CASES):
            problems.append(f"rep {rep['repeat']}: cases {sorted(rows)} != {sorted(CASES)}")
            continue
        for case in CASES:
            verdict = _verdict(rows[case])
            if any(value not in {"yes", "no"} for value in verdict):
                problems.append(f"rep {rep['repeat']} / {case}: invalid verdict {verdict}")
            expected = BASELINE_VERDICTS[case]
            if verdict != expected:
                problems.append(f"rep {rep['repeat']} / {case}: {verdict} != baseline {expected}")
            if rows[case].get("scenario") != "tool_calls":
                problems.append(f"rep {rep['repeat']} / {case}: scenario tag not tool_calls")
        sequence = tuple(rows[case]["tool_call_correctness_exact"]["value"] for case in CASES)
        exact_sequences.append(sequence)
        if sequence != EXPECTED_EXACT_SEQUENCE:
            problems.append(f"rep {rep['repeat']}: exact-match {sequence} != {EXPECTED_EXACT_SEQUENCE}")
        print(f"OK  rep {rep['repeat']}: {len(rows)} cases, all verdicts valid")

    if not exact_sequences:
        problems.append("no repetitions found in results artifact")
    elif all(seq == EXPECTED_EXACT_SEQUENCE for seq in exact_sequences):
        print(f"OK  exact-match sequence ({len(exact_sequences)} reps): {','.join(EXPECTED_EXACT_SEQUENCE)}")

    if len(results.get("flips", [])) != len(TOOL_SCORERS):
        problems.append("flips report does not cover all three tool scorers")
    else:
        print("OK  cross-repetition flips reported for all three scorers")

    if problems:
        print("\nFAIL: standing regression set is incomplete or drifted:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("\nREGRESSION VALIDATION PASSED (6 controls + 5 tool cases + 3 verdicts)")
    return 0


def run(label: str) -> int:
    if not label or not label.replace("-", "").replace("_", "").isalnum():
        print("FAIL: LABEL must be a simple name (letters, digits, -, _)", file=sys.stderr)
        return 2
    print(f"Running both eval suites for variant '{label}' (judge calls will be made)...")
    for script in ("evaluate_traces.py", "evaluate_tool_calls.py"):
        cmd = [sys.executable, script]
        if script == "evaluate_traces.py":
            cmd.append("--with-controls")  # standing set, not pilot-only
        print(f"  $ {' '.join(cmd)}")
        subprocess.run(cmd, cwd=ROOT, check=True)

    REGRESSION_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = REGRESSION_DIR / f"{label}.json"
    shutil.copy(RESULTS_PATH, snapshot)
    (REGRESSION_DIR / f"{label}.meta.json").write_text(
        json.dumps({
            "label": label,
            "git_sha": git_sha(),
            "source": str(RESULTS_PATH),
            "standing_set": {
                "output_controls": list(CONTROL_NAMES),
                "tool_cases": list(CASES),
                "tool_verdicts": list(TOOL_SCORERS),
            },
        }, indent=2) + "\n"
    )
    print(f"Snapshot: {snapshot} (compare with --compare)")
    return 0


def ab(label: str, endpoint: str | None, prompt: str | None) -> int:
    """Generate one variant arm, score it with the standing controls, snapshot it."""
    if not label or not label.replace("-", "").replace("_", "").isalnum():
        print("FAIL: LABEL must be a simple name (letters, digits, -, _)", file=sys.stderr)
        return 2

    REGRESSION_DIR.mkdir(parents=True, exist_ok=True)
    output_snapshot = REGRESSION_DIR / f"{label}.output.json"

    generate = [sys.executable, "trace_example.py", "--variant", label]
    if endpoint:
        generate += ["--endpoint", endpoint]
    if prompt:
        generate += ["--prompt", prompt]
    print("== Generating variant trace ==")
    print(f"  $ {' '.join(generate)}")
    generated = subprocess.run(generate, cwd=ROOT, check=True, capture_output=True, text=True)
    print(generated.stdout.strip())
    trace_id = next(
        (line.split(":", 1)[1].strip() for line in generated.stdout.splitlines()
         if line.startswith("Trace ID for this run:")),
        None,
    )
    if not trace_id:
        print("FAIL: trace_example.py did not print a Trace ID", file=sys.stderr)
        return 1

    print("== Scoring variant + standing controls ==")
    effective_endpoint = endpoint or os.getenv("DATABRICKS_MODEL_ENDPOINT", "databricks-gpt-oss-20b")
    evaluate = [
        sys.executable, "evaluate_traces.py", "--variant", label,
        "--with-controls", "--output", str(output_snapshot),
        "--endpoint", effective_endpoint,
    ]
    print(f"  $ {' '.join(evaluate)}")
    subprocess.run(evaluate, cwd=ROOT, check=True)

    # Attach the generated trace's measured latency/usage/cost so scorer ties can
    # still be separated on operational grounds.
    import mlflow
    mlflow.set_tracking_uri("databricks")
    trace_info = mlflow.get_trace(trace_id).info
    artifact = json.loads(output_snapshot.read_text())
    artifact["trace_metrics"] = {
        "trace_id": trace_id,
        "execution_time_ms": trace_info.execution_time_ms,
        "token_usage": trace_info.token_usage,
        "cost": trace_info.cost,
    }
    output_snapshot.write_text(json.dumps(artifact, indent=2) + "\n")

    # Scripted tool-call traces do not vary with endpoint/prompt, and re-judging
    # them would overwrite the checked-in exp-012 evidence with judge noise.
    (REGRESSION_DIR / f"{label}.meta.json").write_text(
        json.dumps({
            "label": label,
            "endpoint": effective_endpoint,
            "prompt": prompt,
            "trace_id": trace_id,
            "git_sha": git_sha(),
            "output_snapshot": str(output_snapshot),
            "tool_cases": "arm-independent (scripted traces; see exp 012 evidence)",
        }, indent=2) + "\n"
    )
    print(f"\nSnapshot: {output_snapshot}")
    print("Compare two arms with: regression_suite.py --compare <A>.output.json <B>.output.json")
    return 0


def _verdict_map(doc: dict) -> dict[tuple[int, str], tuple[str, ...]]:
    out = {}
    for rep in doc["repetitions"]:
        for row in rep["rows"]:
            out[(rep["repeat"], row["case"])] = _verdict(row)
    return out


def compare_tools(doc_a: dict, doc_b: dict) -> int:
    a, b = _verdict_map(doc_a), _verdict_map(doc_b)
    if set(a) != set(b):
        print(f"FAIL: artifacts cover different case sets ({sorted(a)} vs {sorted(b)})", file=sys.stderr)
        return 1

    changes = 0
    for key in sorted(a):
        for scorer, before, after in zip(TOOL_SCORERS, a[key], b[key]):
            if before != after:
                changes += 1
                print(f"  {key[1]:<18} rep {key[0]} {scorer:<27} {before} -> {after}")
    for label, doc in (("A", doc_a), ("B", doc_b)):
        flips = {entry["scorer"]: len(entry["flips"]) for entry in doc.get("flips", [])}
        print(f"  flips {label}: {flips}")
    print(f"\nA/B COMPLETE: {changes} verdict change(s) across {len(a)} case/repetition pairs")
    return 0


def compare_output(doc_a: dict, doc_b: dict) -> int:
    """Diff two --ab result snapshots: clean arm record + the 6 planted controls."""
    print(f"A: variant={doc_a.get('variant')} endpoint={doc_a.get('endpoint')}")
    print(f"B: variant={doc_b.get('variant')} endpoint={doc_b.get('endpoint')}")
    scorers = doc_a["scorers"]
    if scorers != doc_b["scorers"]:
        print(f"FAIL: scorer lists differ: {scorers} vs {doc_b['scorers']}", file=sys.stderr)
        return 1

    def row_map(doc: dict, controls: bool) -> dict[str, dict]:
        selected = [r for r in doc["rows"] if bool(r.get("control")) == controls]
        if controls:
            return {r["control"]: r for r in selected}
        return {str(i): r for i, r in enumerate(selected)}

    changes = 0
    for controls in (False, True):
        kind = "control" if controls else "clean"
        ra, rb = row_map(doc_a, controls), row_map(doc_b, controls)
        if set(ra) != set(rb):
            print(f"FAIL: {kind} row keys differ: {sorted(ra)} vs {sorted(rb)}", file=sys.stderr)
            return 1
        for key in sorted(ra):
            for scorer in scorers:
                before = ra[key]["scores"][scorer]["value"]
                after = rb[key]["scores"][scorer]["value"]
                if before != after:
                    changes += 1
                    print(f"  {kind}/{key:<24} {scorer:<27} {before!s:<6} -> {after}")
    for label, doc in (("A", doc_a), ("B", doc_b)):
        controls = [r for r in doc["rows"] if r.get("control")]
        caught = sum(any(_is_fail(r["scores"][s]["value"]) for s in scorers) for r in controls)
        clean = [r for r in doc["rows"] if not r.get("control")]
        print(f"  {label}: controls caught {caught}/{len(controls)}")
        for row in clean:
            print(f"  {label} clean answer: {str(row.get('answer'))[:120]}")
        metrics = doc.get("trace_metrics") or {}
        if metrics:
            print(f"  {label} trace: {metrics.get('execution_time_ms')} ms, "
                  f"tokens={metrics.get('token_usage')}, cost={metrics.get('cost')}")
    print(f"\nOUTPUT A/B COMPLETE: {changes} scorer value change(s)")
    return 0


def compare(path_a: Path, path_b: Path) -> int:
    doc_a, doc_b = _load(path_a), _load(path_b)
    if "repetitions" in doc_a and "repetitions" in doc_b:
        return compare_tools(doc_a, doc_b)
    if "rows" in doc_a and "scorers" in doc_a and "rows" in doc_b:
        return compare_output(doc_a, doc_b)
    print("FAIL: unsupported artifact shape (expected tool-call or output-eval snapshot)", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate", action="store_true", help="offline standing-set check (default)")
    group.add_argument("--summary", action="store_true", help="print the standing test matrix")
    group.add_argument("--run", metavar="LABEL", help="re-score frozen scripted cases")
    group.add_argument("--ab", metavar="LABEL", help="generate + score one endpoint/prompt arm")
    group.add_argument("--compare", nargs=2, metavar=("A", "B"), help="diff two snapshot artifacts")
    parser.add_argument("--endpoint", help="Foundation Model endpoint for --ab")
    parser.add_argument("--prompt", help="User message for --ab (default: lab weather question)")
    args = parser.parse_args()

    if args.summary:
        return summary()
    if args.run:
        return run(args.run)
    if args.ab:
        return ab(args.ab, args.endpoint, args.prompt)
    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
