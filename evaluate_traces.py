#!/usr/bin/env python3
"""
F-009: MLflow GenAI evaluation over existing traces (precomputed mode).

No agent is re-run and no stored trace is modified. Traces with a usable final
answer are converted into precomputed records (inputs / outputs / expectations)
and scored with:

  - relevance_to_query  built-in LLM judge (Databricks managed judge on this workspace)
  - answers_expected_city  deterministic custom @scorer (user outcome)
  - response_length  deterministic built-in guardrail (< 300 chars)

Usage:
  python evaluate_traces.py --pilot       # 3 representative records first
  python evaluate_traces.py --register    # persist the scorer suite in the experiment
  python evaluate_traces.py               # full evaluation
  python evaluate_traces.py --pilot --with-controls   # pilot + planted known-bad records
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from dotenv import load_dotenv

from mlflow.entities import Feedback
from mlflow.genai.scorers import RelevanceToQuery, ResponseLength, scorer

EXCLUDED_SCENARIOS = {"error_tracing"}  # no usable final answer; evaluated separately in exp 005
SCORER_NAMES = ("answers_expected_city", "relevance_to_query", "response_length")

# Abbreviations the agent expands in its answers ("NYC" -> "New York City").
CITY_ALIASES = {
    "nyc": ("nyc", "new york city", "new york"),
    "san francisco": ("san francisco", "sf"),
}


def city_mentioned(expected: str, text: str) -> bool:
    """True if any known alias for the expected city appears as a whole word."""
    key = expected.strip().lower()
    aliases = CITY_ALIASES.get(key, (key,))
    return any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)


@scorer(name="answers_expected_city", description="Answer names the city the user asked about.")
def answers_expected_city(inputs, outputs, expectations):
    """Deterministic user-outcome check: the answer is about the requested city."""
    expected = str((expectations or {}).get("expected_city", "")).strip().lower()
    # Normalize Unicode spaces (answers contain U+202F narrow no-break space in "San Francisco").
    text = re.sub(r"\s+", " ", str(outputs or "")).lower()
    if not expected or not text:
        return Feedback(value=False, rationale="missing expected_city or outputs")
    hit = city_mentioned(expected, text)
    return Feedback(
        value=bool(hit),
        rationale=f"expected city {expected!r} {'found' if hit else 'not found'} in answer",
    )


def build_scorers():
    return [
        RelevanceToQuery(),
        answers_expected_city,
        ResponseLength(max_length=300, unit="chars"),
    ]


def records_from_traces(traces):
    """Return (records, metas) aligned by index; metas hold evidence for reporting."""
    records, metas = [], []
    for trace in traces:
        tags = trace.info.tags or {}
        scenario = tags.get("scenario") or "baseline"
        if scenario in EXCLUDED_SCENARIOS:
            continue
        root = next((s for s in trace.data.spans if s.parent_id is None), None)
        if not root or not root.inputs:
            continue

        question, answer = None, None
        if scenario == "baseline":
            msgs = root.inputs.get("messages") or []
            if msgs and isinstance(msgs[0], (list, tuple)) and len(msgs[0]) > 1:
                question = msgs[0][1]
            out_msgs = (root.outputs.get("messages") or []) if isinstance(root.outputs, dict) else []
            answer = next(
                (
                    m.get("content")
                    for m in reversed(out_msgs)
                    if isinstance(m, dict) and m.get("type") in {"ai", "assistant"}
                ),
                None,
            )
        elif scenario == "manual_spans":
            city = root.inputs.get("city")
            question = f"What is the weather in {city}?"
            answer = root.outputs
        elif scenario == "multi_turn":
            question = root.inputs.get("user")
            answer = (root.outputs or {}).get("answer") if isinstance(root.outputs, dict) else root.outputs

        if not question or not answer:
            continue

        # Known facts from the lab conversations: only NYC and SF were asked about.
        expected_city = "NYC" if ("nyc" in question.lower() or "new york" in question.lower()) else "San Francisco"
        records.append({
            "inputs": {"question": question},
            "outputs": str(answer),
            "expectations": {"expected_city": expected_city},
        })
        metas.append({
            "trace_id": trace.info.trace_id,
            "scenario": scenario,
            "turn": root.inputs.get("turn"),
            "expected_city": expected_city,
            "answer": str(answer),
        })
    return records, metas


def build_controls():
    """Planted known-bad records; each must be caught by at least one scorer."""
    controls = [
        ("wrong_city", "The current weather in New York City is cloudy."),
        ("off_topic", "I can help you write a Python function to sort a list."),
        ("over_length", "San Francisco weather update: " + "cloudy with a light breeze; " * 20),
        ("refusal", "I'm sorry, but I can't help with weather questions."),
    ]
    records, metas = [], []
    for name, answer in controls:
        records.append({
            "inputs": {"question": "What is the weather in San Francisco?"},
            "outputs": answer,
            "expectations": {"expected_city": "San Francisco"},
        })
        metas.append({
            "trace_id": f"control:{name}",
            "scenario": "control",
            "turn": None,
            "expected_city": "San Francisco",
            "answer": answer,
            "control": name,
        })
    return records, metas


def pilot_indices(metas):
    """One representative record per multi-turn turn: SF, NYC, cross-turn recall."""
    picked = []
    for turn in (1, 2, 3):
        for i, meta in enumerate(metas):
            if meta["scenario"] == "multi_turn" and meta["turn"] == turn and i not in picked:
                picked.append(i)
                break
    return picked


def _is_pass(value) -> bool:
    return value is True or str(value).lower() in {"yes", "true", "1"}


def _is_fail(value) -> bool:
    if value is None:
        return False
    return value is False or str(value).lower() in {"no", "false", "0"}


def report(result, metas, indices, label):
    print(f"\n=== {label} ===")
    print(f"Evaluation run ID: {result.run_id}")
    print(f"Metrics: {result.metrics}")
    df = result.result_df
    if df is None:
        print("No row-level results returned.")
        return
    print(f"Row-level results: {len(df)} rows x {len(df.columns)} cols")
    for name in SCORER_NAMES:
        print(f"\n  [{name}]")
        for col in sorted(c for c in df.columns if c.startswith(name + "/")):
            if col.endswith(("/error_message", "/error_code", "/value", "/rationale", "/justification")):
                vals = [str(v)[:90] for v in df[col].tolist()]
                print(f"    {col}: {vals}")
    print("\n  Evidence / verdicts:")
    for row_i, result_i in enumerate(indices):
        meta = metas[result_i]
        if meta.get("scenario") == "control":
            continue
        verdicts = " ".join(f"{n}={df.iloc[row_i].get(n + '/value')}" for n in SCORER_NAMES)
        print(f"    {meta['trace_id']} scenario={meta['scenario']} turn={meta['turn']} "
              f"expected={meta['expected_city']} | {verdicts}")
        print(f"      answer: {meta['answer'][:110]}")

    # result.passed inspects every "<name>/value" column, including expectation
    # columns, so it can report False for non-boolean ground truth. Count only
    # the actual scorer verdicts here; zero/False are genuine negatives.
    print("\n  Scorer-only verdict counts (missing/errored reported separately):")
    for name in SCORER_NAMES:
        values = [df.iloc[i].get(name + "/value") for i in range(len(df))]
        errors = [df.iloc[i].get(name + "/error_message") for i in range(len(df))]
        passed = sum(_is_pass(v) for v in values)
        failed = sum(_is_fail(v) for v in values)
        missing = len(values) - passed - failed
        errored = sum(e is not None and str(e).lower() != "nan" for e in errors)
        print(f"    {name}: passed={passed} failed={failed} unscored={missing} errored={errored}")

    clean_rows = [i for i, result_i in enumerate(indices) if metas[result_i].get("scenario") != "control"]
    control_rows = [i for i, result_i in enumerate(indices) if metas[result_i].get("scenario") == "control"]
    if control_rows:
        print("\n  Clean sample vs planted controls:")
        for group, rows in (("clean", clean_rows), ("controls", control_rows)):
            if not rows:
                continue
            parts = []
            for name in SCORER_NAMES:
                values = [df.iloc[i].get(name + "/value") for i in rows]
                if group == "controls":
                    parts.append(f"{name}: flagged {sum(_is_fail(v) for v in values)}/{len(rows)}")
                else:
                    parts.append(f"{name}: {sum(_is_pass(v) for v in values)}/{len(rows)} passed")
            print(f"    {group:<9} n={len(rows):<2} " + " | ".join(parts))

        print("\n  Known-bad controls (each should be caught by >=1 scorer):")
        caught_total = 0
        for row_i in control_rows:
            meta = metas[indices[row_i]]
            verdicts, caught = [], False
            for name in SCORER_NAMES:
                value = df.iloc[row_i].get(name + "/value")
                verdicts.append(f"{name}={value}")
                caught = caught or _is_fail(value)
            caught_total += int(caught)
            print(f"    {meta['trace_id']:<24} caught={caught} | " + " ".join(verdicts))
        print(f"    controls caught: {caught_total}/{len(control_rows)}")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true", help="Score 3 representative records only.")
    parser.add_argument("--register", action="store_true", help="Register the scorer suite in the experiment.")
    parser.add_argument("--with-controls", action="store_true",
                        help="Append planted known-bad records to prove non-uniform scoring.")
    args = parser.parse_args()

    import mlflow

    mlflow.set_tracking_uri("databricks")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        print(f"Experiment not found: {experiment_name}", file=sys.stderr)
        return 2
    mlflow.set_experiment(experiment_name)
    exp_id = experiment.experiment_id

    scorers = build_scorers()
    if args.register:
        print("Registering scorers...")
        for s in scorers:
            registered = s.register(experiment_id=exp_id)
            print(f"  {getattr(registered, 'name', s)}")
        print("Registered scorers now:")
        for s in mlflow.genai.list_scorers():
            print(f"  {getattr(s, 'name', type(s).__name__)}")
        if args.pilot:
            return 0

    traces = mlflow.search_traces(locations=[exp_id], max_results=1000, return_type="list")
    records, metas = records_from_traces(traces)
    usable_trace_records = len(records)
    if args.with_controls:
        control_data, control_metas = build_controls()
        records += control_data
        metas += control_metas
    print(f"Experiment: {experiment_name} ({exp_id})")
    print(f"Traces found: {len(traces)}; usable trace records: {usable_trace_records}; "
          f"excluded scenarios: {sorted(EXCLUDED_SCENARIOS)}")
    if args.with_controls:
        print(f"Planted known-bad controls: {len(control_data)}")

    if args.pilot:
        pilot = pilot_indices(metas)
        if len(pilot) != 3:
            print(f"Expected 3 pilot records, got {pilot}", file=sys.stderr)
            return 2
        indices = list(pilot)
        if args.with_controls:
            indices += [i for i, m in enumerate(metas) if m.get("scenario") == "control"]
        data = [records[i] for i in indices]
        print(f"Pilot records: {[metas[i]['trace_id'] for i in indices]}")
    else:
        indices = list(range(len(records)))
        data = records

    label = "Pilot evaluation" if args.pilot else "Full evaluation"
    if args.with_controls:
        label += " + known-bad controls"
    result = mlflow.genai.evaluate(data=data, scorers=scorers)
    report(result, metas, indices, label)
    print("\nNote: result.passed also inspects expectation value columns, so scorer-only counts above are authoritative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
