#!/usr/bin/env python3
"""
F-009: MLflow GenAI evaluation over existing traces (precomputed mode).

No agent is re-run and no stored trace is modified. Traces with a usable final
answer are converted into precomputed records (inputs / outputs / expectations)
and scored with:

  - relevance_to_query  built-in LLM judge (Databricks managed judge on this workspace)
  - answers_expected_city  deterministic custom @scorer (user outcome)
  - answers_expected_fact  deterministic custom @scorer (ground-truth fact stated)
  - self_consistent  LLM guideline judge (the answer does not contradict itself)
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
from mlflow.genai.scorers import Guidelines, RelevanceToQuery, ResponseLength, scorer

EXCLUDED_SCENARIOS = {"error_tracing"}  # no usable final answer; evaluated separately in exp 005
SCORER_NAMES = (
    "answers_expected_city",
    "answers_expected_fact",
    "relevance_to_query",
    "self_consistent",
    "response_length",
)

# Standing output-control set (F-014). Each planted answer must be caught by at
# least one scorer. CONTROL_NAMES is the stable key set consumed by the
# regression suite, so this stays the single source of truth.
CONTROLS = (
    ("wrong_city", "The current weather in New York City is cloudy."),
    ("off_topic", "I can help you write a Python function to sort a list."),
    ("over_length", "San Francisco weather update: " + "cloudy with a light breeze; " * 20),
    ("refusal", "I'm sorry, but I can't help with weather questions."),
    # Right city, plausible tone, no hallucinated city or length problem:
    # only the ground-truth fact check can catch this one.
    ("right_city_wrong_fact", "The weather in San Francisco is sunny and 75F with clear skies."),
    # States the expected fact AND contradicts it. The deterministic fact check
    # sees "cloudy" and passes; only the self-consistency judge can catch it.
    ("self_contradiction", "It might be cloudy in San Francisco, but it's also sunny, 95F, and clear."),
)
CONTROL_NAMES = tuple(name for name, _answer in CONTROLS)

# Rubric judge: no expected facts are maintained. It only asks whether the answer
# agrees with itself, so it also works when ground truth is unknown.
SELF_CONSISTENCY_GUIDELINES = [
    "SELF-CONSISTENCY CHECK ONLY. Judge whether the answer contradicts itself. "
    "Ignore relevance, correctness against outside facts, completeness, and tone.",
    "The answer must not contradict itself.",
    "If the answer states a sky condition or a temperature, every such statement must "
    "agree. An answer that says it is cloudy and also sunny, clear, or 95F is "
    "self-contradictory.",
    "If the answer makes no claim about weather conditions or temperature, pass it.",
]

# Abbreviations the agent expands in its answers ("NYC" -> "New York City").
CITY_ALIASES = {
    "nyc": ("nyc", "new york city", "new york"),
    "san francisco": ("san francisco", "sf"),
}

# The lab weather tool is a stub: `get_weather` always returns
# "It might be cloudy in {city}". That string is the ground truth for weather
# turns, so a correct answer must state "cloudy" (or a close synonym).
FACT_ALIASES = {
    "cloudy": ("cloudy", "clouds", "overcast"),
}


def _normalize(text) -> str:
    """Lowercase and collapse whitespace (answers contain U+202F in 'San Francisco')."""
    return re.sub(r"\s+", " ", str(text or "")).lower()


def city_mentioned(expected: str, text: str) -> bool:
    """True if any known alias for the expected city appears as a whole word."""
    key = _normalize(expected).strip()
    aliases = CITY_ALIASES.get(key, (key,))
    norm = _normalize(text)
    return any(re.search(rf"\b{re.escape(alias)}\b", norm) for alias in aliases)


def fact_stated(expected: str, text: str) -> bool:
    """True if any known phrasing of the expected fact appears as a whole word."""
    key = _normalize(expected).strip()
    aliases = FACT_ALIASES.get(key, (key,))
    norm = _normalize(text)
    return any(re.search(rf"\b{re.escape(alias)}\b", norm) for alias in aliases)


@scorer(name="answers_expected_city", description="Answer names the city the user asked about.")
def answers_expected_city(inputs, outputs, expectations):
    """Deterministic user-outcome check: the answer is about the requested city."""
    expected = str((expectations or {}).get("expected_city", "")).strip().lower()
    text = str(outputs or "")
    if not expected or not text.strip():
        return Feedback(value=False, rationale="missing expected_city or outputs")
    hit = city_mentioned(expected, text)
    return Feedback(
        value=bool(hit),
        rationale=f"expected city {expected!r} {'found' if hit else 'not found'} in answer",
    )


@scorer(name="answers_expected_fact", description="Answer states the known ground-truth fact.")
def answers_expected_fact(inputs, outputs, expectations):
    """Reference-based factuality check against the tool-derived ground truth.

    Returns None (no assessment) when the record has no known fact, e.g. the
    cross-turn recall question, so it is skipped rather than failed.
    """
    expected = str((expectations or {}).get("expected_fact", "")).strip().lower()
    if not expected:
        return None
    text = str(outputs or "")
    hit = fact_stated(expected, text)
    return Feedback(
        value=bool(hit),
        rationale=(
            f"expected fact {expected!r} {'stated' if hit else 'not stated'} in answer"
        ),
    )


def build_scorers():
    return [
        RelevanceToQuery(),
        answers_expected_city,
        answers_expected_fact,
        Guidelines(
            name="self_consistent",
            guidelines=SELF_CONSISTENCY_GUIDELINES,
            model="databricks",
        ),
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
        turn = root.inputs.get("turn")
        # The stub weather tool always returns "It might be cloudy in {city}", so
        # that is the ground truth for weather turns. The cross-turn recall turn
        # has no tool-derived fact and is skipped by the fact check.
        expected_fact = None if (scenario == "multi_turn" and turn == 3) else "cloudy"
        expectations = {"expected_city": expected_city}
        if expected_fact:
            expectations["expected_fact"] = expected_fact
        records.append({
            "inputs": {"question": question},
            "outputs": str(answer),
            "expectations": expectations,
        })
        metas.append({
            "trace_id": trace.info.trace_id,
            "scenario": scenario,
            "turn": turn,
            "expected_city": expected_city,
            "expected_fact": expected_fact,
            "answer": str(answer),
        })
    return records, metas


def build_controls():
    """Planted known-bad records; each must be caught by at least one scorer."""
    records, metas = [], []
    for name, answer in CONTROLS:
        records.append({
            "inputs": {"question": "What is the weather in San Francisco?"},
            "outputs": answer,
            "expectations": {"expected_city": "San Francisco", "expected_fact": "cloudy"},
        })
        metas.append({
            "trace_id": f"control:{name}",
            "scenario": "control",
            "turn": None,
            "expected_city": "San Francisco",
            "expected_fact": "cloudy",
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
        fact = meta.get("expected_fact") or "-"
        print(f"    {meta['trace_id']} scenario={meta['scenario']} turn={meta['turn']} "
              f"expected={meta['expected_city']} fact={fact} | {verdicts}")
        print(f"      answer: {meta['answer'][:110]}")

    # result.passed inspects every "<name>/value" column, including expectation
    # columns, so it can report False for non-boolean ground truth. Count only
    # the actual scorer verdicts here; zero/False are genuine negatives.
    print("\n  Scorer-only verdict counts (skipped/errored reported separately):")
    for name in SCORER_NAMES:
        values = [df.iloc[i].get(name + "/value") for i in range(len(df))]
        errors = [df.iloc[i].get(name + "/error_message") for i in range(len(df))]
        passed = sum(_is_pass(v) for v in values)
        failed = sum(_is_fail(v) for v in values)
        skipped = (
            sum(1 for result_i in indices if not metas[result_i].get("expected_fact"))
            if name == "answers_expected_fact"
            else 0
        )
        missing = len(values) - passed - failed - skipped
        errored = sum(e is not None and str(e).lower() != "nan" for e in errors)
        print(f"    {name}: passed={passed} failed={failed} skipped={skipped} "
              f"unscored={missing} errored={errored}")

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
                # The fact check is skipped on records without a tool-derived fact.
                applicable = [
                    v for i, v in zip(rows, values)
                    if not (name == "answers_expected_fact"
                            and not metas[indices[i]].get("expected_fact"))
                ]
                if group == "controls":
                    parts.append(f"{name}: flagged {sum(_is_fail(v) for v in applicable)}/{len(applicable)}")
                else:
                    parts.append(f"{name}: {sum(_is_pass(v) for v in applicable)}/{len(applicable)} passed")
            print(f"    {group:<9} n={len(rows):<2} " + " | ".join(parts))

        print("\n  Known-bad controls (each should be caught by >=1 scorer):")
        caught_total = 0
        only_by = {}
        for row_i in control_rows:
            meta = metas[indices[row_i]]
            verdicts, caught, caught_by = [], False, []
            for name in SCORER_NAMES:
                value = df.iloc[row_i].get(name + "/value")
                verdicts.append(f"{name}={value}")
                if _is_fail(value):
                    caught = True
                    caught_by.append(name)
            caught_total += int(caught)
            if len(caught_by) == 1:
                only_by.setdefault(caught_by[0], []).append(meta["control"])
            print(f"    {meta['trace_id']:<32} caught={caught} | " + " ".join(verdicts))
        print(f"    controls caught: {caught_total}/{len(control_rows)}")
        if only_by:
            print("    caught by a single scorer (a narrower suite would have passed):")
            for name, controls in only_by.items():
                print(f"      {name}: {', '.join(controls)}")


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
