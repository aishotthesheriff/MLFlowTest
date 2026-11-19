# MLFlowTest Demo — Executive Summary & Talk Track

**One-page demo reference.** Order: show the result first, explain it second, prove it third. Full step-by-step version: `DEMO_SCRIPT.md`.

---

## 1. Executive Summary

We built a small lab that turns an agent's execution into **queryable evidence in Databricks**, then measures and scores that evidence — with no external LLM key and no separate observability vendor. Nine experiments (001–009) produced a repeatable loop: trace → inspect → measure → evaluate → document.

**What the trace shows:** a LangGraph weather agent on `databricks-gpt-oss-20b` via `ChatDatabricks`. Autolog captures the model and tool calls; manual `@mlflow.trace` spans capture our own pre/post-processing inside the same waterfall (7 spans → 10). Multi-turn runs become three traces under one `session_id`, so each turn keeps clean I/O while the conversation stays retrievable — turn 3 recalled the first city from history with no tool call.

**What the failures show:** unhandled errors mark the trace `ERROR` with exception type, message and stacktrace; a deliberately handled error marks only its child span `ERROR` and leaves the trace `OK`. Both signatures were produced on purpose and verified in the UI.

**What the numbers show:** latency, tokens and cost are first-class `TraceInfo` fields — no re-run needed. Slowest of 17 original traces: 4,304 ms, ~100% model time. Most expensive: $0.000121, a multi-turn run. Answerless error traces legitimately have `null` usage and distort mixed aggregates, so the lab segments by scenario and status.

**What the evaluation shows:** precomputed GenAI evaluation over persisted traces — one managed Databricks LLM judge (`relevance_to_query`) plus three deterministic scorers (`answers_expected_city`, `answers_expected_fact`, `response_length`). The original full run scored 11 records × 3 scorers with 0 unscored and 0 errored; a fresh full run with the fact check scores 16 records × 4 scorers with 0 failures, 0 errored, and 3 skipped (recall turns with no tool-derived fact). A pilot caught a real false negative ("New York City" for expected "NYC"), fixed with an alias map. Five planted known-bad controls: clean 3/3, controls 5/5 caught. The last control — right city, wrong fact — passes the city, relevance, and length checks and is caught **only** by the new ground-truth fact check. Non-uniform means (0.63 / 0.57 / 0.63 / 0.88). A high mean is not evidence; a caught control is.

**Honest limit:** 11 short weather answers from one toy agent prove the pipeline works, not production quality. The planted controls run in the pilot (5/5 caught); full-run controls and A/B comparisons are next. A deterministic fact check still misses an answer that states the right fact and also contradicts it.

### Key evidence (verified 2026-11-18/19)

| Item | ID |
| --- | --- |
| Experiment | `/Shared/my-first-trace` (`1675992194464286`) |
| Baseline trace | `tr-054cbbc9de1d27ba20aec517e6cda4eb` (7 spans) |
| Manual-span trace | `tr-0cb5f6d26d3dad7fc32c9da9cad10131` (10 spans) |
| Multi-turn session | `lab-f005-1795028845` (3 traces; turn 3 = `tr-6f99921de8fc0c0f8f0271392f7bb606`) |
| Error session | `lab-f007-1795033547` (handled case `tr-193c937a2ab7790e06969f4bb3730a85`) |
| Evaluation run | `345d6069efe64933a8d04e350a264381` (11 records × 3 scorers) |
| Controls run | `a4809bf5e16a42fcaca5ed77f2d38120` (3 clean + 4 controls; 4/4 caught) |
| Fact-check run | `d4e336016b264b8c84720015f550dd3a` (3 clean + 5 controls; 5/5 caught) |
| Full run (4 scorers) | `6c408d499a794bacbc42b842ecfac352` (16 records; 0 failed, 3 skipped) |
| Findings doc | `docs/FINDINGS_AND_LEARNINGS.md` (+ ObsidiBin vault copy) |

---

## 2. Demo Talk Track (2–3 minutes)

### Cold Open — One Question, One Live Trace (45 sec)
*(Terminal: `.venv/bin/python trace_example.py`; then paste the printed trace ID into the Databricks Traces tab.)*

> "I'm going to ask a weather question and show you the entire execution — model, tool, and timing — with no OpenAI key. The Databricks CLI profile is the only credential."

*(Point at `ChatDatabricks` and `get_weather` in the waterfall.)*

> "One trace, seven spans, every call accounted for. That's the baseline."

### What You Just Saw — Manual Spans (30 sec)
*(Open the `tr-0cb5f6d2…` trace.)*

> "Autolog sees framework calls, not my own code. An outer `@mlflow.trace` span marks the application boundary and two manual spans mark pre- and post-processing. Same agent, ten spans, one coherent trace — the manual spans nest with the autolog spans instead of fragmenting them."

### Multi-Turn and Failures (60 sec)
*(Filter the Traces tab by session `lab-f005-…`; then by `status = 'ERROR'`.)*

> "Three turns, three traces, one session. Turn 2 changes city; turn 3 recalls the first city from history with no tool call. We group turns rather than merge them, so every turn keeps its own inputs and outputs."
>
> "For failures: an unhandled error marks the trace `ERROR` and keeps the exception details; a handled error marks only its child span `ERROR` and leaves the trace `OK`. I even had to make the failing tool look legitimate — the model refused to call one labelled 'deliberately broken', so no trace appeared."

### Proof — Measure and Score (60 sec)
*(Terminal: `analyze_trace_metrics.py`, then `evaluate_traces.py --pilot --with-controls`.)*

> "Latency, tokens and cost come straight from trace metadata. Slowest trace: 4.3 seconds, almost all model time. Most expensive: $0.000121. Answerless error traces have null usage, so I segment before aggregating."
>
> "Then evaluation over stored traces — no agent re-run. One managed LLM judge plus three deterministic checks: city named, ground-truth fact stated, under 300 characters. The clean pilot is 3/3; then I append five planted known-bad controls. The first four are obvious — wrong city, off-topic, over-length, refusal. The fifth is the interesting one: 'San Francisco is sunny and 75F.' City check passes, relevance passes, length passes — the original suite would have shipped it. The fact check catches it, and only the fact check. Controls: 5/5. Means: 0.63 / 0.57 / 0.63 / 0.88. That is the point: a high mean is not evidence."

### Close — The Honest Limit (20 sec)
> "The pilot caught a real false negative — 'New York City' scored wrong for expected 'NYC' — and the controls are caught 5/5, including the right-city-wrong-fact case the old suite missed. But 11 short answers still mean the pipeline works, not that the agent is production-ready. Next: full-run controls, contradiction checks, and A/B comparisons."

---

## 3. Quick Reference Commands & Artifacts

```bash
./start_demo.sh --check-only              # read-only preflight
./start_demo.sh                           # preflight + open deck and Traces tab

.venv/bin/python trace_example.py         # Act 1: live baseline trace
.venv/bin/python trace_manual_spans.py    # Act 2: manual spans
.venv/bin/python trace_multi_turn.py      # Act 3: session + 3 turns
.venv/bin/python trace_errors.py          # Act 4: failure signatures
.venv/bin/python analyze_trace_metrics.py # Act 5: latency / tokens / cost
.venv/bin/python evaluate_traces.py --pilot --with-controls   # Act 5: 3 clean + 5 controls
.venv/bin/python evaluate_traces.py       # Act 5: full evaluation (all usable records)
open DEMO_DECK.html                        # companion deck
```

- **Companion deck:** `DEMO_DECK.html` — `→` next, `N` speaker notes, `F` full screen
- **Databricks experiment:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286`
- **Evaluation run:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=345d6069efe64933a8d04e350a264381`
- **Controls run:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=a4809bf5e16a42fcaca5ed77f2d38120`
- **Fact-check run:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=d4e336016b264b8c84720015f550dd3a`
- **Full writeups:** `docs/LAB_BOOK.md`, `docs/experiments/001`–`009`, `docs/FINDINGS_AND_LEARNINGS.md`
