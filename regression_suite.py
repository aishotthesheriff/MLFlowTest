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
  --compare A B       diff two tool-call result artifacts (the A/B view)

A/B workflow: run --run baseline, change the prompt/model, run --run variant_b,
then --compare the two snapshots. Output-control A/B uses evaluate_traces.py's
printed pass/fail table, which the suite includes in --run.
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
)
from lab_tags import git_sha  # noqa: E402

REGRESSION_DIR = Path("docs/demo/regression")

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
        subprocess.run(cmd, cwd=Path(__file__).resolve().parent, check=True)

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


def _verdict_map(doc: dict) -> dict[tuple[int, str], tuple[str, ...]]:
    out = {}
    for rep in doc["repetitions"]:
        for row in rep["rows"]:
            out[(rep["repeat"], row["case"])] = _verdict(row)
    return out


def compare(path_a: Path, path_b: Path) -> int:
    a, b = _verdict_map(_load(path_a)), _verdict_map(_load(path_b))
    if set(a) != set(b):
        print(f"FAIL: artifacts cover different case sets ({sorted(a)} vs {sorted(b)})", file=sys.stderr)
        return 1

    changes = 0
    for key in sorted(a):
        for scorer, before, after in zip(TOOL_SCORERS, a[key], b[key]):
            if before != after:
                changes += 1
                print(f"  {key[1]:<18} rep {key[0]} {scorer:<27} {before} -> {after}")
    for label, doc in (("A", _load(path_a)), ("B", _load(path_b))):
        flips = {entry["scorer"]: len(entry["flips"]) for entry in doc.get("flips", [])}
        print(f"  flips {label}: {flips}")
    print(f"\nA/B COMPLETE: {changes} verdict change(s) across {len(a)} case/repetition pairs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate", action="store_true", help="offline standing-set check (default)")
    group.add_argument("--summary", action="store_true", help="print the standing test matrix")
    group.add_argument("--run", metavar="LABEL", help="run both suites and snapshot results")
    group.add_argument("--compare", nargs=2, metavar=("A", "B"), help="diff two result artifacts")
    args = parser.parse_args()

    if args.summary:
        return summary()
    if args.run:
        return run(args.run)
    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
