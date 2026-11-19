# Live Demo Script: Databricks MLflow 3 GenAI Tracing

**Total Runtime:** ~7 minutes (~9 minutes with one optional act, ~11 with both). For a 4-minute cut, run Act 1 and Act 5 only.

**Story shape:** show the result first, explain it second, prove it third. Companion deck: `DEMO_DECK.html` (8 slides with real MLflow UI screenshots from the experiment, including the tool-call waterfall — see `docs/demo/README.md` for provenance). The deck is a visual reference; the terminal and the Databricks Traces tab remain the live screens.

| Act | What the audience sees | Time |
| --- | --- | --- |
| 1 | Cold open: one question, one live trace, no API key | ~1.5 min |
| 2 | "What you just saw": autolog + manual spans in one waterfall | ~1 min |
| 3 | Multi-turn: three traces, one session, cross-turn recall | ~1.5 min |
| 4 | Failure signatures: trace `ERROR` vs span `ERROR` | ~1 min |
| 5 | Proof: latency/cost + an evaluation run over stored traces | ~2 min |
| 5B (opt.) | The controls the old suite missed: wrong fact and self-contradiction | ~2.5 min |
| 5C (opt.) | Tool calls: prove what the agent did, then judge it | ~2.5 min |

---

## Pre-Flight Checklist (10 minutes before)

> **One-command check:** `./start_demo.sh --check-only` verifies the venv, Databricks auth, the experiment, the eight evidence traces, and all eight registered scorers (including the exact tool-call scorer config). `./start_demo.sh` also opens the deck and the Traces tab. The manual steps below are what the launcher automates.

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
   Expected: experiment `1675992194464286`; eight scorers — `relevance_to_query`, `answers_expected_city`, `answers_expected_fact`, `self_consistent`, `response_length`, `tool_call_correctness`, `tool_call_correctness_exact`, `tool_call_efficiency`. If the PAT in `~/.databrickscfg` has expired, fix it before the demo — not during.

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

**Action 2 — score (clean sample + planted controls):**
```bash
.venv/bin/python evaluate_traces.py --pilot --with-controls   # 3 clean + 6 planted controls, fast
.venv/bin/python evaluate_traces.py                          # full: all usable records x 5 scorers
```
**Say (point at the run URL):**
> "This is MLflow GenAI evaluation in precomputed mode: I selected traces with a usable answer, excluded the answerless error traces, and scored them without calling the agent again. Two managed LLM judges — `relevance_to_query` and a self-consistency rubric — plus three deterministic checks: does the answer name the city the user asked about, does it state the ground-truth fact, and is it under 300 characters. The pilot runs 3 clean records and 6 planted known-bad controls. Clean sample: 3/3. Controls: 6/6 caught. The means are 0.67, 0.63, 0.67, 0.89, 0.89 — non-uniform by design."

**Land it:**
> "And I registered all five output-level scorers in the experiment, so this is a repeatable harness, not a one-off script."

---

## Act 5B (Optional): The Controls the Old Suite Missed (~2.5 min)

**Screen:** Deck slide 6, then the terminal/pilot evidence from `--with-controls`.

**Say:**
> "A 1.0 mean is not evidence by itself. So I planted six known-bad records: wrong city, off-topic, over-length, refusal — plus two that are harder: right city with a wrong fact, and a right fact that contradicts itself."

**Point at the output:**
> "Clean sample: 3/3. Controls: 6/6 caught. Look at two rows. `right_city_wrong_fact` — 'The weather in San Francisco is sunny and 75F.' City passes, relevance passes, length passes. The original three-scorer suite would have shipped it. And `self_contradiction` — 'It might be cloudy in San Francisco, but it's also sunny, 95F, and clear.' City passes, the fact check passes because 'cloudy' is there, relevance passes, length passes. A token check cannot see that the answer disagrees with itself."

**Then the fixes:**
> "Two different checks close them. The first is a reference-based fact check: the lab weather tool is a stub that always returns 'It might be cloudy in {city}', so 'cloudy' is the ground truth. The second is a scoped LLM rubric judge that only asks 'does this answer contradict itself?' — no expected facts to maintain. Each control is caught by exactly one scorer: the fact check catches the wrong fact, the consistency judge catches the contradiction. The means drop to 0.67, 0.63, 0.67, 0.89, 0.89, which is the point: a high mean is not evidence, a caught control is."

**Then the live alias bug:**
> "The same pilot caught a real false negative: the model wrote 'New York City' for expected 'NYC' and the literal matcher returned `False`. I fixed it with an alias map and whole-word matching. Same lesson as the earlier U+202F and 'sf.' bugs: deterministic scorers need normalization and aliases, not just a substring check."

**Honest limits:**
> "The rubric judge costs a model call per record and is not deterministic. And it only reads one answer: a contradiction spread across turns, or stated as an implication, can still slip. That is why the deterministic checks stay."

---

## Act 5C (Optional): Tool Calls — Prove It, Then Judge It (~2.5 min)

**Screen:** Databricks Traces tab filtered by `session_id = lab-f011-…`, then the terminal.

**Action 1 — capture and verify (exp 011):**
```bash
.venv/bin/python trace_tool_calls.py
```
**Say:**
> "So far we have only scored what the agent *said*. Now we look at what it *did*. Five cases, the same question about weather and cloud cover in SF, the same two tools advertised every time. Only the scripted model decision changes: one happy call, no call, the wrong tool, the wrong city, and three identical calls. These run through the real LangGraph loop with autolog; I fetch each trace back and assert the tool spans directly — name, arguments, count, and OK outcome. Zero judge calls in this step, and the manifest is written only if all five pass."

**Action 2 — judge the same traces (exp 012):**
```bash
.venv/bin/python evaluate_tool_calls.py
```
**Say (point at the four run IDs):**
> "Now three scorer configurations judge those same five traces — twice, with no agent re-run and no `predict_fn`. The exact-match mode accepts only `get_weather(city='SF')`; the other two read the request alone. Three verdicts per case: unaided correctness, efficiency, exact match. Happy is yes / yes / yes. Look at `tool_no_call`: correctness says no, but efficiency says **yes** — doing nothing is perfectly efficient and still wrong, so the two properties have to be separate scorers. Wrong tool, wrong city, and the retry storm are no across the board. The exact-match sequence is yes, no, no, no, no in both repetitions, with zero flips and no scorer errors."

**Honest limits:**
> "The two correctness modes agreed on all five cases — exact match buys a deterministic, auditable rationale, not a different verdict. These are five unambiguous traces; LLM-judge verdicts on borderline cases can still flip, so two repetitions is a smoke test, not a stability guarantee. Registration does not enable automatic monitoring."

**Troubleshooting:** if `evaluate_tool_calls.py` reports a missing manifest, run `trace_tool_calls.py` first; if it reports a scenario-tag mismatch, the five source traces were overwritten and must be regenerated. Both failures are loud by design — the evaluator never scores a trace it cannot verify.

---

## Closing (~30 sec)

> "Twelve experiments now: keyless tracing, manual spans, multi-turn sessions, failures you can diagnose, latency and cost from the trace metadata, an evaluation harness that catches planted defects — including a right-city-wrong-fact hallucination and a self-contradiction the old suite missed — and tool-call evidence you can prove and then judge. The artifact is a repeatable measurement loop — the lab book, the findings doc, and the runnable scripts. The limits are explicit: toy agent, 11 answers, controls only in the pilot, and five unambiguous tool traces. Full-run controls, legitimate retries, and A/B comparisons are the next experiments."

Then open Q&A with `DEMO_DECK.html` slide 7 up and the Traces tab still open.

---

## Quick Troubleshooting Card

| Symptom | Fix |
| --- | --- |
| `MlflowException` / auth prompt | Check `~/.databrickscfg` DEFAULT profile; re-authenticate before the demo. |
| Experiment not found | Default is `/Shared/my-first-trace`; override with `MLFLOW_EXPERIMENT_NAME`. |
| No traces in the UI | Run `mlflow.flush_trace_async_logging()` (all scripts do) and check you are in the right experiment. |
| `INVALID_PARAMETER_VALUE` filtering errors | Use `status = 'ERROR'`, not `state = 'ERROR'`. |
| Evaluation says 0 usable records | The selector needs root-span inputs; generated evaluation traces have none, and the eight evidence traces must still exist. Run `./start_demo.sh --check-only`. |
| Controls not in the results | Pass `--with-controls`; it is opt-in so the clean full-run numbers stay comparable. |
| Tool-call evaluator says manifest missing | Run `trace_tool_calls.py` first; `evaluate_tool_calls.py` refuses to score unverified traces. |
| Tool-call evaluator says scenario-tag mismatch | The five source traces were overwritten; regenerate them with `trace_tool_calls.py`. |
| Only five scorers listed | Run `python evaluate_tool_calls.py --register` (adds the three tool-call configs; does not enable monitoring). |
| Trace IDs look shifted | Read `span.trace_id` from the live span, not `get_last_active_trace_id()`. |
| Post-commit hook noise | Harmless fork warning from the global hook; commits succeed. |
