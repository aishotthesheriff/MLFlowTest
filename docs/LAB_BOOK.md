# MLflow GenAI Tracing Lab Book

A living lab notebook for Databricks MLflow 3 GenAI tracing experiments in this workspace: what we ran, what we learned, and what to try next.

**Workspace:** `/Users/yourbabes/dev/Databricks/MLFlowTest`  
**Primary references:** [Databricks tracing overview](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/overview) · [Automatic tracing & integrations](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/automatic-tracing) · [Manual/custom tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/manual-tracing)

---

## 1. Purpose

- Track tracing/observability experiments with enough detail to reproduce and compare runs.
- Capture hypotheses, configuration, outcomes, trace links, and decisions.
- Maintain a prioritized backlog of future experiments and open questions.

## 2. Environment snapshot

| Item | Value / notes |
| --- | --- |
| Date baseline | 2026-11-18 |
| OS | macOS (darwin), Apple Silicon Homebrew at `/opt/homebrew/bin/brew` |
| Python | 3.15.2 (`.venv` in repo) |
| MLflow | 3.18.0 (`mlflow[databricks]`) |
| Agent stack | `langgraph` 1.2.22, `langchain` 1.5.1, `langchain-openai` 1.8.1, `databricks-langchain` 0.22.0, `python-dotenv` |
| Databricks CLI | 1.26.0 (`/opt/homebrew/bin/databricks`) |
| Databricks auth | `~/.databrickscfg` DEFAULT profile (PAT), AWS workspace `https://dbc-5c7ff528-845c.cloud.databricks.com` (validated 2026-11-18) |
| Tracking | `mlflow.set_tracking_uri("databricks")` → traces stored in Databricks workspace |
| Default experiment | `/Shared/my-first-trace` (override via `MLFLOW_EXPERIMENT_NAME`) |
| Sample LLM | Databricks FM endpoint `databricks-gpt-oss-20b` via `ChatDatabricks` (no external key); override with `DATABRICKS_MODEL_ENDPOINT` |
| Judge model | `databricks` managed judge (MLflow default on Databricks tracking); no external key |
| Key scripts | `trace_example.py`, `trace_manual_spans.py`, `trace_multi_turn.py`, `trace_errors.py`, `trace_tool_calls.py`, `analyze_trace_metrics.py`, `evaluate_traces.py`, `.env.example`, `requirements.txt`, `README.md` |

> Update this table when dependencies, workspace targets, models, or auth method change.

## 3. How to use this lab book

### Run the baseline example
```bash
cd /Users/yourbabes/dev/Databricks/MLFlowTest
source .venv/bin/activate
# ensure .env is configured (see .env.example)
python trace_example.py
```
View traces: Databricks **Experiments** → experiment (default `/Shared/my-first-trace`) → **Traces**.

### Log a new experiment
1. Copy `docs/experiments/TEMPLATE.md` to `docs/experiments/NNN-short-slug.md` (next sequence number).
2. Fill in hypothesis, setup, exact config/commands, results, trace IDs/links, and learnings.
3. Add/update the row in the **Experiment register** below.
4. If the experiment creates follow-up ideas, add them to **Ideas & future experiments**.

### What to capture for every run
- **Reproducibility:** script/notebook name, git commit if applicable, dependency versions, env/config knobs (model, temperature, experiment name), date/time.
- **Traceability:** Databricks experiment path, trace/run IDs or deep links, tags.
- **Evidence:** inputs/outputs, latency/token/cost observations (if available), errors, screenshots/notes.
- **Interpretation:** what worked, what didn’t, confidence, decisions, next action.

---

## 4. Experiment register

| ID | Date | Title | Status | Experiment (Databricks) | Script/config | Outcome | Doc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | 2026-11-18 | First traced LangGraph agent run | Completed | `/Shared/my-first-trace` | `trace_example.py`, `gpt-4o-mini`, `get_weather` tool, OpenAI key, `autolog` | Success: trace exported; response "The weather in San Francisco might be cloudy." | [001-first-trace.md](experiments/001-first-trace.md) |
| 002 | 2026-11-18 | Switch agent to Databricks Foundation Model (no OpenAI key) | Completed | `/Shared/my-first-trace` | `trace_example.py`, `ChatDatabricks` on `databricks-gpt-oss-20b`, `langchain.agents.create_agent`, `autolog` | Success: trace `tr-054cbbc9de1d27ba20aec517e6cda4eb` with 7 spans incl. `ChatDatabricks` + `get_weather`; response "The current weather in San Francisco is cloudy." | [002-foundation-model.md](experiments/002-foundation-model.md) |
| 003 | 2026-11-18 | Manual/custom spans for non-autologged logic | Completed | `/Shared/my-first-trace` | `trace_manual_spans.py`, `@mlflow.trace` boundary + pre/post spans, autolog kept on | Success: trace `tr-0cb5f6d26d3dad7fc32c9da9cad10131`, 10 spans (manual + autolog nested), I/O/attrs/tags captured | [003-manual-spans.md](experiments/003-manual-spans.md) |
| 004 | 2026-11-18 | Multi-turn conversation tracing (F-005) | Completed | `/Shared/my-first-trace` | `trace_multi_turn.py`, 3 turns, shared `session_id`, per-turn root spans + autolog | Success: 3 traces in session `lab-f005-1795028845`; context growth 0→2→4 msgs; turn 3 recalled SF | [004-multi-turn-tracing.md](experiments/004-multi-turn-tracing.md) |
| 005 | 2026-11-18 | Error/failure tracing (F-007) | Completed | `/Shared/my-first-trace` | `trace_errors.py`, tool error / unhandled exception / handled error cases | Success: 3 traces; unhandled → trace ERROR + exception events; handled → span ERROR only; `status` filter works | [005-error-tracing.md](experiments/005-error-tracing.md) |
| 006 | 2026-11-18 | Latency, token & cost analysis (F-008) | Completed | `/Shared/my-first-trace` | `analyze_trace_metrics.py`, read-only aggregation over 17 traces | Success: per-scenario latency/token/cost summary; slowest trace `tr-983651f7eb6bf22274142b9362c21858` (4304 ms, two ChatOpenAI spans); most expensive `tr-66e408aab933cac6feb63ec91b042abe` ($0.000121) | [006-latency-cost-analysis.md](experiments/006-latency-cost-analysis.md) |
| 007 | 2026-11-18 | GenAI evaluation on existing traces (F-009) | Completed | `/Shared/my-first-trace` | `evaluate_traces.py`, precomputed mode, 3 scorers (LLM judge + 2 deterministic) | Success: eval run `345d6069efe64933a8d04e350a264381`, 11 records × 3 scorers, all means 1.0, 0 unscored/errored | [007-genai-evaluation.md](experiments/007-genai-evaluation.md) |
| 008 | 2026-11-19 | Known-bad scorer controls | Completed | `/Shared/my-first-trace` | `evaluate_traces.py --pilot --with-controls`, 3 clean + 4 planted controls, city alias map | Success: run `a4809bf5e16a42fcaca5ed77f2d38120`; clean 3/3, controls 4/4 caught, means 0.57/0.57/0.86 | [008-scorer-controls.md](experiments/008-scorer-controls.md) |
| 009 | 2026-11-19 | Right city, wrong fact: factuality check | Completed | `/Shared/my-first-trace` | `evaluate_traces.py --pilot --with-controls`, 3 clean + 5 planted controls, `answers_expected_fact` ground-truth check | Success: run `d4e336016b264b8c84720015f550dd3a`; clean 3/3, controls 5/5 caught, right-city-wrong-fact caught only by the fact check | [009-factuality-check.md](experiments/009-factuality-check.md) |
| 010 | 2026-11-19 | Self-contradiction rubric judge (no expected facts) | Completed | `/Shared/my-first-trace` | `evaluate_traces.py --pilot --with-controls`, 3 clean + 6 planted controls, `Guidelines` self-consistency judge | Success: pilot `30eabe1d8fdf4540a8ef9c8ee5dae368`, controls 6/6 caught, self-contradiction caught only by the judge; full run `99060446d0004248a3f0acab278408d6` all 1.0 | [010-self-consistency-judge.md](experiments/010-self-consistency-judge.md) |
| 011 | 2026-11-19 | Tool-call tracing: capture and verify what the agent did (F-015) | Completed | `/Shared/my-first-trace` | `trace_tool_calls.py`, scripted `GenericFakeChatModel` in real `create_agent` loop, 5 injected tool cases, direct span assertions, zero judge calls | Success: 5 traces in session `lab-f011-1795112059`, all expected tool names/args/counts/outcomes verified, both tools advertised in every case, manifest `docs/demo/tool_call_manifest.json` | [011-tool-call-tracing.md](experiments/011-tool-call-tracing.md) |

**Status legend:** Planned · In progress · Completed · Blocked · Abandoned

---

## 5. Detailed experiment notes

Consolidated cross-experiment reference: [FINDINGS_AND_LEARNINGS.md](FINDINGS_AND_LEARNINGS.md) — fixes, platform findings, and learnings.

Individual writeups live in [`docs/experiments/`](experiments/):

- [TEMPLATE.md](experiments/TEMPLATE.md) — copy for new experiments
- [001-first-trace.md](experiments/001-first-trace.md) — baseline first trace
- [002-foundation-model.md](experiments/002-foundation-model.md) — Databricks FM endpoint (no OpenAI key), deprecation fix
- [003-manual-spans.md](experiments/003-manual-spans.md) — manual @mlflow.trace spans for pre/post-processing
- [004-multi-turn-tracing.md](experiments/004-multi-turn-tracing.md) — session grouping + per-turn I/O across 3 turns
- [005-error-tracing.md](experiments/005-error-tracing.md) — tool errors, unhandled exceptions, handled errors
- [006-latency-cost-analysis.md](experiments/006-latency-cost-analysis.md) — latency percentiles, token/cost totals, span hotspot analysis
- [007-genai-evaluation.md](experiments/007-genai-evaluation.md) — precomputed evaluation, registered scorers, row-level assessments
- [008-scorer-controls.md](experiments/008-scorer-controls.md) — planted known-bad controls, city alias fix, clean-vs-controls reporting
- [009-factuality-check.md](experiments/009-factuality-check.md) — right-city-wrong-fact control, reference-based fact check, skip semantics
- [010-self-consistency-judge.md](experiments/010-self-consistency-judge.md) — scoped `Guidelines` rubric judge, self-contradiction control, no expected facts
- [011-tool-call-tracing.md](experiments/011-tool-call-tracing.md) — scripted tool calls, five verified span patterns, zero judge calls

---

## 6. Ideas & future experiments

Use this backlog to propose, prioritize, and track future work. Move items into the experiment register when scheduled/executed.

### Prioritization guide
- **Impact:** learning value, production relevance, risk reduction
- **Effort:** S (<1h), M (half-day), L (multi-day)
- **Dependencies:** credentials, endpoints, datasets, code changes

### Backlog

| ID | Idea | Hypothesis / question | Priority | Effort | Depends on | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F-001 | Use Databricks Foundation Model APIs instead of OpenAI | Can we get equivalent traces with no external API key using workspace auth only? | High | S-M | FM serving endpoint name/access | Completed (exp 002) | Uses `ChatDatabricks` on `databricks-gpt-oss-20b`; no external key needed. |
| F-002 | Fix deprecation: `create_react_agent` import path | Updating to `langchain.agents.create_agent` keeps traces intact on current LangGraph/LangChain versions. | Medium | S | — | Completed (exp 002) | Warning gone; spans include `ChatDatabricks`/`get_weather`. |
| F-003 | Manual/custom spans and attributes | Adding `@mlflow.trace` / manual spans gives better visibility into non-autologged logic (pre/post-processing, custom tools). | High | S-M | — | Completed (exp 003) | Boundary + pre/post spans nest with autolog spans; 10-span trace verified. |
| F-004 | Try another autolog integration | Different frameworks produce different span schemas/useful metadata. | Medium | M | Install integration deps | Proposed | Candidates: OpenAI SDK direct, LangChain-only chain, other supported agent frameworks per docs. |
| F-005 | Multi-turn conversation tracing | Multi-turn agent state/session behavior is captured clearly across turns. | High | M | Conversation script | Completed (exp 004) | One trace/turn under shared `session_id`; context growth + cross-turn recall verified. |
| F-006 | Tool/use-case expansion (RAG/retrieval) | Retrieval steps appear as spans with useful inputs/outputs for debugging relevance. | High | M-L | Retriever/vector store or mock retriever | Proposed | Trace retriever + generator; evaluate grounding. |
| F-007 | Error/failure tracing | Failures (tool errors, model errors, timeouts) produce diagnosable traces. | High | S-M | Intentional failure cases | Completed (exp 005) | Tool/unhandled errors → trace ERROR + exception events; handled → span ERROR only; partial spans retained. |
| F-008 | Latency and token/cost analysis | Trace metadata is sufficient to identify slow/expensive spans. | Medium | S-M | Runs with usage data | Completed (exp 006) | `TraceInfo.execution_time_ms`/`token_usage`/`cost` suffice; 17 traces aggregated; slowest ~100% LLM-bound; null usage on no-LLM-call traces. |
| F-009 | MLflow GenAI evaluation on traces | Automated scorers/judges can assess quality from traced runs. | High | M-L | Dataset/scorers setup | Completed (exp 007) | Precomputed mode over 11 traces; managed `databricks` judge + 2 deterministic scorers; all scored, no errors; uniform 1.0 reflecting known-good small sample. |
| F-010 | Trace tagging, metadata, and searchability | Consistent tags (env, feature, git SHA, scenario) make traces easy to filter/debug. | Medium | S | — | Proposed | Set tags/metadata in code; document naming conventions. Exp 003 set `lab_book`/`scenario`/`model_endpoint` tags — reuse as convention. |
| F-011 | Unity Catalog trace storage | UC-backed trace storage improves governance/queryability for this workflow. | Medium | M | UC permissions/config | Proposed | Follow [trace-unity-catalog](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog); compare limits/capabilities. |
| F-012 | Experiment organization strategy | Separate dev/test/prod experiments and naming conventions reduce clutter and risk. | Medium | S | Team/workspace conventions | Proposed | Propose path scheme, tags, and retention expectations. |
| F-013 | Production-style monitoring/alerting workflow | Traces can feed dashboards/alerts for ongoing quality and performance monitoring. | Medium | L | Production-like workload | Proposed | Identify key signals and Databricks/Lakehouse integration path. |
| F-014 | Prompt/version comparison (A/B) | Side-by-side traced runs make prompt/model changes measurable. | Medium | M | Variant configs | Proposed | Six known-bad controls via `--with-controls` (exps 008–010), including right-city-wrong-fact and self-contradiction, plus five tool-call cases from exp 011. Hold inputs constant; compare outputs, traces, and eval scores. Reuse `evaluate_traces.py` and the exp 012 tool-call evaluator. |
| F-015 | Tool-call tracing and validation | Tool selection, arguments, and call count can be observed in spans and judged from the same traces. | High | M | Scripted model + fake service | In progress (exp 011) | Exp 011 produced five verified traces and a manifest; exp 012 will judge them with correctness and efficiency scorers. Follow-up: a failure-plus-retry case where retries are legitimate. |

> Add new ideas freely; include a short hypothesis and dependency so they are actionable.

## 7. Open questions

- [x] Which Databricks Foundation Model serving endpoint should be the default for keyless/local-auth runs? → using `databricks-gpt-oss-20b` (exp 002); revisit if quality/latency favors another.
- [ ] Should traces live in shared experiments (`/Shared/...`) or user/project-specific paths?
- [ ] Do we need Unity Catalog-backed trace storage for this project now?
- [ ] What evaluation criteria/scorers matter first (correctness, tool use, latency, cost, safety)? → started with relevance, expected-city outcome, length (exp 007).
- [ ] Should we pin dependency versions for reproducibility once experiments stabilize?

## 8. Learnings & decision log

| Date | Decision / learning | Rationale | Impact |
| --- | --- | --- | --- |
| 2026-11-18 | Baseline tracing via `mlflow.langchain.autolog()` + `set_tracking_uri("databricks")` works from local Python 3.15 venv | First successful end-to-end traced run to Databricks workspace | Establishes reproducible starting point (exp 001) |
| 2026-11-18 | CLI auth in `~/.databrickscfg` is sufficient when env vars are not set | MLflow/Databricks SDK can resolve configured profile | Simplifies local setup; keep secrets out of `.env` where possible |
| 2026-11-18 | `trace_example.py` now flushes and prints the trace ID after each run | Trace IDs are needed to link lab-book entries to concrete evidence | Verified by re-run (`tr-efb8425cc9c44452521a84f94a49c744`); future runs capture IDs automatically |
| 2026-11-18 | Default LLM switched from OpenAI `gpt-4o-mini` to Databricks FM `databricks-gpt-oss-20b` via `ChatDatabricks` | Removes external API-key dependency; all auth via Databricks workspace | Verified in exp 002 (`tr-054cbbc9de1d27ba20aec517e6cda4eb`) |
| 2026-11-18 | `databricks-langchain` deps installed with `--no-deps` | Full resolution fails on Python 3.15 (older scipy needs Fortran compiler) | Works with existing modern stack; pin/revisit if venv rebuilt |
| 2026-11-18 | Manual `@mlflow.trace` spans compose with autolog; use an outer application-boundary span | Adds visible pre/post-processing steps and a stable place for trace tags without duplicating autologged spans | Verified in exp 003 (`tr-0cb5f6d26d3dad7fc32c9da9cad10131`); adopt as pattern for future scripts |
| 2026-11-18 | Multi-turn = one trace per turn grouped by `session_id`; use `span.trace_id` for per-turn IDs | `get_last_active_trace_id()` is off by one inside an active span; session stored in request metadata + tags | Verified in exp 004 (3 traces, session `lab-f005-1795028845`) |
| 2026-11-18 | Unhandled errors → trace ERROR with exception events; handled errors → span ERROR only | `@mlflow.trace` captures type/message/stacktrace automatically; `record_exception` + `set_status(ERROR)` for handled cases | Verified in exp 005; use `status = 'ERROR'` (not `state`) in `search_traces` filters |
| 2026-11-18 | Latency/token/cost come from `TraceInfo.execution_time_ms`, `token_usage`, `cost`; segment by scenario/status | No-LLM-call traces have null usage/cost and fast latency, so mixed aggregates mislead | Verified in exp 006; `analyze_trace_metrics.py` is the reusable read-only harness |
| 2026-11-18 | Precomputed GenAI evaluation works over existing traces with managed `databricks` judge + deterministic scorers | No agent re-run, dataset, or external key needed; row-level results live in the eval run | Verified in exp 007 (11 records, 0 errored); exclude answerless error traces and validate scorers on known-bad inputs |
| 2026-11-18 | Normalize Unicode whitespace and use word boundaries in deterministic text scorers | Model output uses U+202F in "San Francisco" and "sf." at sentence end, causing false negatives | Fixed in exp 007 pilot; `expectations` also pollute `result.passed`, so count real scorer verdicts |
| 2026-11-19 | Add planted known-bad controls and a city-alias map to the evaluation harness | Uniform 1.0 is not evidence; "New York City" for expected "NYC" was a real false negative | Verified in exp 008 (`a4809bf5e16a42fcaca5ed77f2d38120`): clean 3/3, controls 4/4 caught, non-uniform means |
| 2026-11-19 | Add a reference-based factuality check; relevance is not truth | A right-city-wrong-fact answer passed city, relevance, and length; only ground truth catches it | Verified in exp 009 (`d4e336016b264b8c84720015f550dd3a`): 5/5 controls caught, right-city-wrong-fact flagged by `answers_expected_fact` alone |
| 2026-11-19 | Add a scoped self-consistency rubric judge for answers that state the right fact and contradict it | No expected facts are needed when the defect is internal; the deterministic check cannot see it | Verified in exp 010 (`30eabe1d8fdf4540a8ef9c8ee5dae368`): 6/6 controls caught, self-contradiction flagged by `self_consistent` alone |
| 2026-11-19 | Script tool decisions inside the real agent loop instead of relying on model compliance | Five failure modes need deterministic, repeatable tool spans; a live endpoint cannot guarantee them | Verified in exp 011: five cases, exact tool names/args/counts asserted on fetched traces; advertised schemas read from `mlflow.chat.tools`, no judge calls |

## 9. Change log

| Date | Change | Author/notes |
| --- | --- | --- |
| 2026-11-18 | Created lab book structure, experiment register, template, and initial backlog | Initialized from first successful trace run |
| 2026-11-18 | Updated `trace_example.py` to print the trace ID after flushing traces | Verified with a successful re-run; lab-book exp 001 records both original and verification trace IDs |
| 2026-11-18 | Added experiment 002; switched agent to Databricks FM, fixed deprecation, updated config/docs | F-001 and F-002 completed; verified persisted trace |
| 2026-11-18 | Added `trace_manual_spans.py` and experiment 003 | F-003 completed; manual + autolog spans verified in one 10-span trace |
| 2026-11-18 | Added `trace_multi_turn.py` and experiment 004 | F-005 completed; 3-turn session grouping and context recall verified |
| 2026-11-18 | Added `trace_errors.py` and experiment 005 | F-007 completed; 3 error signatures verified with exception events and filtering |
| 2026-11-18 | Added `analyze_trace_metrics.py` and experiment 006 | F-008 completed; 17 traces aggregated by scenario with latency/token/cost and span hotspot breakdown |
| 2026-11-18 | Added `evaluate_traces.py` and experiment 007 | F-009 completed; 3 registered scorers, 11 records scored, pilot bugs fixed and documented |
| 2026-11-19 | Added `--with-controls` and experiment 008; fixed NYC/SF city aliases | Known-bad controls caught 4/4; clean sample 3/3; demo Act 5B now proves discrimination |
| 2026-11-19 | Added `answers_expected_fact` and experiment 009 | Right-city-wrong-fact control caught only by the fact check; 5/5 controls caught; scorer suite is now 4 registered scorers |
| 2026-11-19 | Added `self_consistent` `Guidelines` judge and experiment 010 | Self-contradiction control caught only by the rubric judge; 6/6 controls caught; suite is now 5 registered scorers |
| 2026-11-19 | Added `trace_tool_calls.py`, experiment 011, and `docs/demo/tool_call_manifest.json` | Five tool-call cases verified from fetched spans with zero judge calls; existing scripts and eight evidence traces untouched |

---
*Keep entries factual, link to traces/evidence, and prefer small reproducible experiments over large undocumented changes.*
