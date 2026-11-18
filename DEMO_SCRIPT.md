# Live Demo Script: Databricks MLflow 3 GenAI Tracing

**Total Runtime:** ~7 minutes (~9 minutes with optional Act 5B). For a 4-minute cut, run Act 1 and Act 5 only.

**Story shape:** show the result first, explain it second, prove it third. Companion deck: `DEMO_DECK.html` (minimal — cue slides point to the terminal and the Databricks Traces tab).

| Act | What the audience sees | Time |
| --- | --- | --- |
| 1 | Cold open: one question, one live trace, no API key | ~1.5 min |
| 2 | "What you just saw": autolog + manual spans in one waterfall | ~1 min |
| 3 | Multi-turn: three traces, one session, cross-turn recall | ~1.5 min |
| 4 | Failure signatures: trace `ERROR` vs span `ERROR` | ~1 min |
| 5 | Proof: latency/cost + an evaluation run over stored traces | ~2 min |
| 5B (opt.) | A deterministic scorer caught a bug in a "perfect" run | ~1.5 min |

---

## Pre-Flight Checklist (10 minutes before)

> **One-command check:** `./start_demo.sh --check-only` verifies the venv, Databricks auth, the experiment, the eight evidence traces, and the three registered scorers. `./start_demo.sh` also opens the deck and the Traces tab. The manual steps below are what the launcher automates.

1. **Verify the environment** from `/Users/yourbabes/dev/Databricks/MLFlowTest`:
   ```bash
   test -x .venv/bin/python && echo "venv OK"
   MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/python - <<'PY'
   import mlflow
   mlflow.set_tracking_uri("databricks")
   e = mlflow.get_experiment_by_name("/Shared/my-first-trace")
   print("experiment:", e.experiment_id)
   mlflow.set_experiment("/Shared/my-first-trace")
   print("scorers:", [s.name for s in mlflow.genai.list_scorers()])
   PY
   ```
   Expected: experiment `1675992194464286`; scorers `relevance_to_query`, `answers_expected_city`, `response_length`. If the PAT in `~/.databrickscfg` has expired, fix it before the demo — not during.

2. **Open two browser tabs**:
   - **Tab 0 — Deck:** `open DEMO_DECK.html`
   - **Tab 1 — Databricks Traces:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/traces`
   Zoom Tab 1 to ~125%. Keep a terminal open for the live runs.

3. **Know the evidence trace IDs** (all verified in the experiment on 2026-11-18):

   | Beat | Trace ID (short) | What it shows |
   | --- | --- | --- |
   | Baseline | `tr-054cbbc9…` | 7 spans, `ChatDatabricks` + `get_weather` |
   | Manual spans | `tr-0cb5f6d2…` | 10 spans, app boundary + pre/post |
   | Multi-turn | `tr-e07c3271…`, `tr-66e408aa…`, `tr-6f99921d…` | three turns, one session |
   | Tool error | `tr-cbd09f84…` | trace `ERROR` |
   | Unhandled | `tr-3dbea41e…` | trace `ERROR` + exception events |
   | Handled | `tr-193c937a…` | trace `OK`, child span `ERROR` |

   Full IDs are in `docs/experiments/001`–`007` and `docs/FINDINGS_AND_LEARNINGS.md`. Search by the short prefix in the Databricks Traces search box.

4. **Note:** every evaluation run appends traces to this experiment. The count grows (17 original lab traces, 34 at last check). The demo always selects by scenario/tag, never by row number.

---

## Act 1: Cold Open — One Question, One Live Trace (~1.5 min)

**Screen:** Terminal for the run, then Tab 1 (Databricks Traces) full width. Cue from Slide 2 of `DEMO_DECK.html`.

**Say (one sentence, then run):**
> "I'm going to ask a weather question and show you the entire execution — model, tool, and timing — with no OpenAI key anywhere."

**Action:**
```bash
.venv/bin/python trace_example.py
```
Expected: a one-line answer about cloudy weather in San Francisco, then `Trace ID for this run: tr-…`. Copy that ID.

**In Tab 1:** search the ID, click into the trace, expand the waterfall. Point at `ChatDatabricks` (CHAT_MODEL) and `get_weather` (TOOL).

**Say:**
> "That is a Databricks Foundation Model endpoint through the workspace CLI profile — `~/.databrickscfg` — and LangChain autologging captured the model call and the tool call as spans. The same script used to need an external API key. Now it needs only a Databricks login."

**Land the open:**
> "That's the baseline. Now I'll show you what the trace can see that the script cannot."

---

## Act 2: "What You Just Saw" — Manual Spans Compose With Autolog (~1 min)

**Screen:** Tab 1, the `tr-0cb5f6d2…` trace (or run `trace_manual_spans.py` live).

**Action (optional live run):**
```bash
.venv/bin/python trace_manual_spans.py
```

**Say (point at the nesting):**
> "Autolog sees framework calls. It does not see my own preprocessing and postprocessing. One outer `@mlflow.trace` span marks the application boundary; two manual spans mark the work before and after the model. The baseline trace had seven spans. This one has ten — same agent, same model, same tool, one coherent trace. The manual spans parent the autolog spans instead of fragmenting the trace."

**If asked "why not just log to stdout?":**
> "Stdout has no timing, no parent/child, and no link to the model call. Here every span carries inputs, outputs, attributes and tags, and the whole thing is queryable later."

---

## Act 3: Multi-Turn — Group Turns, Don't Merge Them (~1.5 min)

**Screen:** Terminal for the run, then Tab 1 filtered by session.

**Action:**
```bash
.venv/bin/python trace_multi_turn.py
```
Expected: `Session ID: lab-f005-…`, `Traces captured: 3`, one trace per turn, turns 1–3.

**In Tab 1:** search the session ID (it is both a tag and `request_metadata["mlflow.trace.session"]`). Show the three traces.

**Say:**
> "Three turns, three traces, one session ID. MLflow does not merge a conversation into one giant span — it groups separate traces under a session, which keeps each turn's inputs and outputs clean and still lets me pull the whole conversation back."

**Point at turn 2 (NYC) and turn 3:**
> "Turn 2 switches cities. Turn 3 asks 'What was the first city I asked about?' and answers 'San Francisco' — from conversation history, with no tool call. Fewer spans, but the recall is there in the output."

**Honest note (if asked about the earlier bug):**
> "My first attempt read `get_last_active_trace_id()` inside the span and got the previous trace's ID. The correct source is `span.trace_id` on the live span. I discarded that run rather than report a misattributed ID."

---

## Act 4: Failure Signatures — Trace `ERROR` vs Span `ERROR` (~1 min)

**Screen:** Terminal for the run, then Tab 1 with `status = 'ERROR'` filter.

**Action:**
```bash
.venv/bin/python trace_errors.py
```
Expected: `Session ID: lab-f007-…` and three trace IDs (tool error, unhandled exception, handled error).

**In Tab 1:** filter `status = 'ERROR'` (`status`, not `state`) and open each case.

**Say (point at each):**
> "Case A, the tool raises: the trace is `ERROR`, the exception type, message and stacktrace are on the span, and the spans that completed before it are still there. Case B, an unhandled exception: same trace-level `ERROR`. Case C, I catch the error and record it deliberately: the child span is `ERROR`, but the trace stays `OK` because the application handled it. That distinction matters — a pager should fire on B, not on C."

**The compelling detail:**
> "The first time I built Case A, the model refused to call the tool because its description said 'deliberately broken' — so no error span was produced at all. I renamed it to a normal `get_weather` and required its use in the prompt. The lesson: to trace a failure you have to design a failure the model will actually walk into."

---

## Act 5: Proof — Metrics and Evaluation Over Stored Traces (~2 min)

**Screen:** Terminal, then Tab 1 for the evaluation run link.

**Action 1 — measure:**
```bash
.venv/bin/python analyze_trace_metrics.py
```
**Say:**
> "No re-run, no extra API. `execution_time_ms`, `token_usage` and `cost` are first-class fields on the traces. At the time of the writeup, 17 traces: slowest was 4,304 ms, almost entirely two model calls (2,742 + 1,530 ms); graph and tool overhead was about 4 ms. Most expensive was $0.000121 — multi-turn, because context grows."

**Important qualifier:**
> "Six error-tracing traces had no completed model call, so they have `null` usage, `null` cost and very short latency. Mixed together they dragged the mean down and made the median meaningless. Segment by scenario and status before you compare anything."

**Action 2 — score:**
```bash
.venv/bin/python evaluate_traces.py --pilot     # 3 representative records, fast
.venv/bin/python evaluate_traces.py              # full: 11 records x 3 scorers
```
**Say (point at the run URL):**
> "This is MLflow GenAI evaluation in precomputed mode: I selected 11 traces with a usable answer out of the original 17, excluded the six answerless error traces, and scored them without calling the agent again. One LLM judge — `relevance_to_query`, running the managed Databricks judge — plus two deterministic checks: does the answer name the city the user asked about, and is it under 300 characters. All 11 records scored, none unscored, none errored, all means 1.0."

**Land it:**
> "And I registered all three scorers in the experiment, so this is a repeatable harness, not a one-off script."

---

## Act 5B (Optional): The Bug Inside a "Perfect" Run (~1.5 min)

**Screen:** Deck slide 6, then the terminal/pilot evidence.

**Say:**
> "A 1.0 mean is not evidence by itself. My first pilot had a scorer that returned `False` for correct answers — twice."

**Point at the two failures:**
> "Correct answers used a narrow no-break space in 'San Francisco' and a period after 'sf.' — both defeated naive text matching. I fixed it with whitespace normalization and a word-boundary regex. And MLflow's `result.passed` reported failure because the ground-truth column looks like a scorer verdict to it, so I count only real scorer columns."

**Then the proof that it discriminates:**
> "I tested the fixed scorer on a wrong city and an off-topic answer. It returns `False`. So the clean 11/11 is a known-good sample, not a dead scorer — and I'll be the first to say it is not a quality claim about a production agent."

---

## Closing (~30 sec)

> "Seven experiments in one afternoon: keyless tracing, manual spans, multi-turn sessions, failures you can diagnose, latency and cost from the trace metadata, and an evaluation harness over stored traces. The artifact is a repeatable measurement loop — the lab book, the findings doc, and three runnable scripts. The limits are explicit: toy agent, 11 answers, no known-bad set in the full run yet. That is the next experiment."

Then open Q&A with `DEMO_DECK.html` slide 6 up and the Traces tab still open.

---

## Quick Troubleshooting Card

| Symptom | Fix |
| --- | --- |
| `MlflowException` / auth prompt | Check `~/.databrickscfg` DEFAULT profile; re-authenticate before the demo. |
| Experiment not found | Default is `/Shared/my-first-trace`; override with `MLFLOW_EXPERIMENT_NAME`. |
| No traces in the UI | Run `mlflow.flush_trace_async_logging()` (all scripts do) and check you are in the right experiment. |
| `INVALID_PARAMETER_VALUE` filtering errors | Use `status = 'ERROR'`, not `state = 'ERROR'`. |
| Evaluation says 0 usable records | The selector needs root-span inputs; generated evaluation traces have none, and the eight evidence traces must still exist. Run `./start_demo.sh --check-only`. |
| Trace IDs look shifted | Read `span.trace_id` from the live span, not `get_last_active_trace_id()`. |
| Post-commit hook noise | Harmless fork warning from the global hook; commits succeed. |
