# Fixes, Findings & Learnings

A consolidated reference for the Databricks MLflow 3 GenAI tracing lab. It collects the bugs we hit, the fixes that worked, the platform behaviors we confirmed, and the patterns we adopted across experiments 001-012. Source writeups live in [`docs/experiments/`](experiments/); the run log lives in [`docs/LAB_BOOK.md`](LAB_BOOK.md).

**Last updated:** 2026-11-19 · **Workspace:** `/Users/yourbabes/dev/Databricks/MLFlowTest` · **Experiment:** `/Shared/my-first-trace` (`1675992194464286`)

**Second brain copy:** the same material is ingested into the ObsidiBin vault as `~/dev/VAULT/ObsidiBin/raw/notes/2026-11-18-mlflow-genai-tracing-findings.md`, with wiki summaries `MLFlowTest GenAI Tracing Lab` and `MLflow GenAI Tracing Learnings`. This repo file remains the canonical source; if they diverge, update the raw vault note to match.

---

## Quick reference: symptom → cause → fix

| Symptom | Cause | Fix | Source |
| --- | --- | --- | --- |
| `pip install databricks-langchain` tries to build scipy and fails (Fortran compiler missing) on Python 3.15 | Full dependency resolution selects an older scipy requiring Fortran | Install Databricks integration packages with `pip install --no-deps ...`; keep the already-installed modern stack. Documented recipe in exp 002 | [002](experiments/002-foundation-model.md) |
| `create_react_agent` deprecation warning | `langgraph.prebuilt.create_react_agent` moved in LangGraph V1.0 | Use `langchain.agents.create_agent` | [002](experiments/002-foundation-model.md) |
| First trace run produced no local trace ID | ID wasn't captured or printed | Call `mlflow.flush_trace_async_logging()` then record/print the ID | [001](experiments/001-first-trace.md) |
| Per-turn trace IDs were `None` for turn 1 and shifted for later turns | `mlflow.get_last_active_trace_id()` returns the last *completed* trace; inside an active span it is stale | Read `span.trace_id` from the live span, then flush after the span closes | [004](experiments/004-multi-turn-tracing.md) |
| `TraceInfo.session_id` does not exist | Session lives elsewhere | Read `request_metadata["mlflow.trace.session"]` or the `session_id` tag | [004](experiments/004-multi-turn-tracing.md) |
| `mlflow.search_traces` filter returned nothing / needed an experiment | Filtering requires an active experiment or explicit location | Pass `locations=[experiment_id]` | [004](experiments/004-multi-turn-tracing.md) |
| `state = 'ERROR'` filter → `INVALID_PARAMETER_VALUE` | Valid filter column is `status`, not `state` | Use `status = 'ERROR'` (combine with `AND tags...`) | [005](experiments/005-error-tracing.md) |
| Tool-error case returned a normal answer with no tool span | Tool description said "deliberately broken"; the model refused to call it | Give the failing tool a normal name/description and explicitly require its use in the prompt | [005](experiments/005-error-tracing.md) |
| Custom city scorer returned `False` for correct answers | Model emits U+202F in "San Francisco" and `sf.` at sentence end | `re.sub(r"\s+", " ", text)` + word-boundary regex `\bsf\b` | [007](experiments/007-genai-evaluation.md) |
| Correct answer "New York City" scored `False` for expected "NYC" | Model expands the abbreviation; literal token match misses it | Alias map (`nyc` → "new york city") with whole-word matching | [008](experiments/008-scorer-controls.md) |
| `result.passed` was `False` despite every scorer passing | `expectations` become `<key>/value` columns; `result.passed` inspects all of them | Count verdicts from real scorer columns only; report errors/unscored separately | [007](experiments/007-genai-evaluation.md) |
| Right-city, wrong-fact answer passed every scorer | City, relevance, and length checks never compare the answer to ground truth | Add `answers_expected_fact` against the tool-derived fact; plant a control that only it catches | [009](experiments/009-factuality-check.md) |
| Answer states the right fact and contradicts itself ("cloudy, but sunny and 95F") | A deterministic fact check matches tokens, not internal agreement | Add a scoped `Guidelines` self-consistency judge; plant a control that only it catches | [010](experiments/010-self-consistency-judge.md) |
| Baseline root outputs were a string in some traces | Root span output shape varies by run/version | Guard with `isinstance(root.outputs, dict)` before `.get("messages")` | [007](experiments/007-genai-evaluation.md) |
| Rewriting a city inside a tool wrapper left `city="SF"` in the span | LangChain records tool arguments at tool entry | Inject the wrong argument into the scripted tool call before the traced invocation | [011](experiments/011-tool-call-tracing.md) |
| Three service calls inside one tool body appeared as one `TOOL` span | Autolog traces the tool invocation boundary, not internal requests | Dispatch three separate tool calls through the boundary to get three spans | [011](experiments/011-tool-call-tracing.md) |
| Fake model trace advertised no tool schemas | `bind_tools()` returning `self` drops the `tools` kwarg | Return a `RunnableBinding` carrying OpenAI schemas; autolog writes `mlflow.chat.tools` | [011](experiments/011-tool-call-tracing.md) |
| Ground-truth-free correctness scorer behaved like a fuzzy matcher | A row carried `expected_tool_calls`, which switches the default scorer into matching mode | Pass `expectations={}` on every row of the unaided pass; reserve `expected_tool_calls` for the exact-match pass | [012](experiments/012-tool-call-judges.md) |
| `ToolCallEfficiency.__call__()` rejected `expectations` | Unlike correctness, efficiency accepts only `trace` | Build rows with `expectations` only where the scorer supports it; `evaluate` passes no `predict_fn` here | [012](experiments/012-tool-call-judges.md) |

---

## 1. Fixes (what broke and what we changed)

### 1.1 Environment and dependencies
- **scipy/Fortran build failure on Python 3.15.** Full `databricks-langchain` resolution fails while building an older scipy that needs a Fortran compiler. Installed the Databricks/Unity Catalog packages with `--no-deps` on top of the modern stack (scipy 1.18.1 retained). This is version-sensitive; revisit if the venv is rebuilt. (exp 002)
- **External LLM key removed.** Switched `ChatOpenAI`/`gpt-4o-mini` to `ChatDatabricks` on `databricks-gpt-oss-20b` (override via `DATABRICKS_MODEL_ENDPOINT`). Auth is only `~/.databrickscfg` DEFAULT PAT profile; `.env` is gitignored. (exp 001→002)
- **LangGraph deprecation.** Replaced `langgraph.prebuilt.create_react_agent` with `langchain.agents.create_agent`; warning gone, tool calls and spans preserved. (exp 002)

### 1.2 Trace capture and querying
- **Trace IDs are now captured explicitly.** Flush async logging and print the ID after each run so lab entries can link to concrete evidence. (exp 001)
- **Per-turn IDs must come from the live span.** `get_last_active_trace_id()` returns the last *completed* trace; used inside a span it gave `None` on turn 1 and shifted IDs afterwards. The first exploratory multi-turn run (`lab-f005-1795028805`) was discarded for this reason. (exp 004)
- **Filter column is `status`.** `state = 'ERROR'` is invalid in `search_traces`. (exp 005)
- **Error-injection tools must look legitimate.** The model refused a tool described as "deliberately broken," so no tool-error span was produced. Renaming it to `get_weather` and forcing tool use in the prompt produced the intended `RuntimeError` path. (exp 005)

### 1.3 Evaluation script
- **Unicode/normalization bug in the custom scorer.** Correct answers were scored `False` because the model emits "San Francisco" with U+202F and "sf." with trailing punctuation. Fixed with whitespace normalization and `\bsf\b`. Validated with known-good and known-bad answers before re-running the pilot. (exp 007)
- **City alias false negative.** "NYC" was scored `False` when the model wrote "New York City". Added an alias map (`nyc` → "nyc"/"new york city"/"new york", `san francisco` → "san francisco"/"sf") with whole-word matching. (exp 008)
- **Ground-truth columns pollute `result.passed`.** `expectations` are surfaced as `expected_city/value`, which MLflow's `passed` property treats as a scorer verdict and rejects as non-boolean. The script now counts only the real scorers and reports skipped/unscored/errored explicitly. (exp 007)
- **Relevance is not factuality.** A right-city-wrong-fact answer ("San Francisco is sunny and 75F") passed the city check, the relevance judge, and the length check. Added a reference-based `answers_expected_fact` check against the tool's ground truth, and a fifth control that only that check catches. (exp 009)
- **Case-sensitive helper trap.** `city_mentioned()` assumed the caller had already lowercased and normalized the text, so a direct call on mixed-case text returned `False`. Moved normalization inside `_normalize()` so both matchers are case- and U+202F-insensitive by construction. (exp 009)
- **An unscoped rubric judge drifts into relevance.** The first `self_consistent` rubric caught the intended contradiction but also flagged the off-topic control. Adding "ignore relevance, correctness, completeness, and tone" plus "pass answers with no weather claim" made it fire only on the contradiction. (exp 010)
- **Defensive output parsing.** Baseline root spans sometimes hold a string rather than a dict; added an `isinstance` guard. (exp 007)

---

## 2. Findings (what we confirmed about the platform)

### 2.1 Tracing
- `mlflow.langchain.autolog()` with `set_tracking_uri("databricks")` works from the local Python 3.15 venv and captures LangGraph/LangChain agent execution, including `ChatDatabricks` CHAT_MODEL and `get_weather` TOOL spans. (exp 001-002)
- Manual `@mlflow.trace` spans compose cleanly with autolog: 7 autolog-only spans became 10 spans with an application-boundary root plus pre/post-processing spans, all in one trace with correct nesting and no duplicates. (exp 003)
- **Multi-turn = one trace per turn grouped by a shared `session_id`,** not a single merged trace. Both `request_metadata["mlflow.trace.session"]` and the `session_id` tag are searchable; `TraceInfo` has no `session_id` attribute. (exp 004)
- Cross-turn recall worked: turn 3 answered "You asked about San Francisco first." Turn 3 had fewer spans because it answered from history without a tool call. (exp 004)
- **Error signatures are distinguishable:** unhandled tool/app errors → trace `ERROR` with exception type/message/stacktrace on affected spans and partial OK spans retained; explicitly recorded/handled errors → child span `ERROR` only, trace stays `OK`. (exp 005)
- Non-blocking MLflow messages encountered: a hint to load the installed `mlflow-trace-instrumentation` skill and a Unity Catalog storage suggestion. (exp 001)
- **Scripted decisions in a real agent loop give deterministic tool traces.** A `GenericFakeChatModel` emitting `AIMessage(tool_calls=...)` through `create_agent` + autolog produced exactly the intended `TOOL` spans for five injected cases, with no live endpoint. (exp 011)
- **One tool call = one `TOOL` span; internal retries collapse.** Three service requests inside one tool body yield one span, so duplicate-call defects must be dispatched as three boundary-crossing tool calls. All three were kept successful because the efficiency rubric permits retries after failures. (exp 011)
- **Advertised tool schemas are on the `CHAT_MODEL` span.** `mlflow.chat.tools` records every tool offered to the model, including the no-call case; the model's recorded bindings are a fallback. Reading them directly keeps trace verification at zero judge calls. (exp 011)
- **Efficiency is not correctness.** On the no-call trace, both correctness modes said `no` while the efficiency judge said `yes` — doing nothing is maximally efficient and still wrong. Keep the two properties as separate scorers. (exp 012)
- **Two correctness modes agreed on five clean-cut defects.** Ground-truth-free and exact-match returned the same verdicts; exact match earns its place with a deterministic, auditable rationale ("Expected 1, got 0/3"), not a different answer. (exp 012)
- **Judge verdicts were stable on the five unambiguous cases.** Two repetitions of all three configurations produced zero flips and zero errors; that is a smoke test, not a flakiness guarantee for borderline cases. (exp 012)

### 2.2 Latency, tokens, cost
- `TraceInfo.execution_time_ms`, `token_usage`, and `cost` are first-class fields — no re-run or extra API needed. Request metadata also carries `mlflow.trace.tokenUsage` / `mlflow.trace.cost`, but the first-class fields are simpler. (exp 006)
- Traces with no completed LLM call legitimately have `token_usage`/`cost` = `None` and very short latency. Four of six error traces were like this, dragging the `error_tracing` mean down and making p50 (46 ms) misleading. **Segment by scenario/status before comparing latency.** (exp 006)
- Slowest trace was ~100% LLM-bound: two `ChatOpenAI` spans (2742 ms + 1530 ms) of 4304 ms total; graph/tool overhead ~4 ms. It was the exp 001 OpenAI baseline, so not a like-for-like FM comparison. (exp 006)
- Cost is output-token-heavy; multi-turn had the highest total cost because context grows across turns. (exp 006)

### 2.3 Evaluation
- GenAI precomputed evaluation works directly over persisted traces: no `predict_fn`, no new dataset, no new credentials. Selected 11 of 17 traces (6 multi-turn, 4 baseline, 1 manual-spans); excluded 6 answerless error traces. (exp 007)
- On Databricks tracking, `RelevanceToQuery()` defaults to the managed `databricks` judge — verified with a real direct call before the pilot. No external key. (exp 007)
- Scorers can be registered and listed in the experiment (`mlflow.genai.list_scorers()`): `relevance_to_query`, `answers_expected_city`, `answers_expected_fact`, `response_length`. (exps 007–009)
- All 11 records scored with valid values, rationales, and no errors; means all 1.0. The uniform scores reflect a small known-good sample — direct negative tests proved the custom scorer can return `False`, so this is not a broken scorer, but it is not production-quality evidence. (exp 007)
- **Planted controls prove discrimination.** Four known-bad records (wrong city, off-topic, over-length, refusal) were caught 4/4; the clean pilot stayed 3/3 green and the means became non-uniform (0.57/0.57/0.86). A high mean alone is not evidence. (exp 008)
- **A relevance judge does not catch a wrong fact.** The managed judge marked "San Francisco is sunny and 75F" as relevant; city and length checks also passed it. With the ground-truth fact check added, five controls are caught 5/5 and that control is flagged by `answers_expected_fact` alone. (exp 009)
- A fresh full run with the fact check scored 16 records × 4 scorers: 0 failures, 0 errored, 3 skipped (recall turns with no tool-derived fact), every mean 1.0. The deterministic fact check produced no false negatives on the real answers. (exp 009)
- Returning `None` from a custom scorer is a supported empty assessment (skipped), not an error; the report distinguishes `skipped` from `unscored`. (exp 009)
- **A scoped rubric judge catches self-contradiction with no expected facts.** `Guidelines(name="self_consistent", model="databricks")` flagged "cloudy, but also sunny, 95F, and clear" while passing the right-city-wrong-fact control, which is internally consistent. Six controls are caught 6/6; the contradiction is caught by that judge alone. (exp 010)
- **The two checks are complementary by construction.** A wrong-but-consistent answer fails only the ground-truth fact check; a right-fact-but-contradictory answer fails only the consistency judge. Neither replaces the other. (exps 009–010)
- Evaluation runs add their own traces to the experiment (untagged `root_span` records), so filter by scenario or trace name before counting agent runs. (exp 010)
- Precomputed mode stores row-level results in the evaluation run, **not** on the original traces (their `assessments` list stays empty). Each evaluation run also adds new traces to the experiment. (exp 007)

---

## 3. Learnings (patterns we adopted)

1. **Auth and credentials:** Databricks CLI profile in `~/.databrickscfg` plus `mlflow.set_tracking_uri("databricks")` is enough. Keep secrets out of `.env`; keep `.env` gitignored.
2. **Use workspace-native models:** a Databricks FM endpoint removes the external-key dependency and still produces full autolog spans.
3. **Instrument at the application boundary:** an outer `@mlflow.trace` span records end-to-end I/O and gives a stable place for tags (`lab_book`, `scenario`, `session_id`, `turn`, `model_endpoint`). Don't re-wrap nodes autolog already covers.
4. **Capture evidence at run time:** flush and print IDs/trace links, and record them in the experiment writeup. A misattributed ID invalidates an otherwise good run.
5. **Group conversations, don't merge them:** one trace per turn + shared `session_id`; record `history_messages_before` to make context growth measurable.
6. **Treat errors as first-class traces:** design intentional failure cases; distinguish unhandled (trace ERROR) from handled (span ERROR) and keep partial spans.
7. **Validate scorers before trusting metrics:** inspect row-level values, rationales, and error columns; test known-good and known-bad inputs; don't rely on a high mean or a green run alone.
8. **Mix deterministic and LLM scorers:** cheap checks catch text-normalization bugs; the judge covers semantic relevance that code can't.
9. **Segment before aggregating:** scenario and status splits prevent fast-failing error traces from distorting latency/cost summaries.
10. **Reuse the harness:** `analyze_trace_metrics.py` and `evaluate_traces.py` are the standing measurement tools for later A/B and monitoring work.
11. **Small samples limit claims:** all lab answers are short weather replies from one toy agent; 11/11 passes demonstrate the pipeline works, not that the agent is production-ready.
12. **Plant known-bad controls:** a clean 1.0 means nothing without a demonstrated catch rate; add controls to the harness and report clean vs. control rows separately.
13. **Relevance is not truth:** if the expected fact is known, check it directly; a relevance or fluency judge will happily pass a confident, on-topic hallucination.
14. **Scope a rubric judge to one property:** a judge told to "check consistency" will judge relevance too unless you tell it what to ignore. Name the property, list what to ignore, and give it a pass rule for answers with nothing to check.
15. **Verify evidence before judging it:** fetch traces back by ID and assert names, arguments, counts, outcomes, and advertised schemas before writing a manifest; a downstream judge can only be trusted if the span underneath it is trusted. (exp 011)
16. **Keep scorer properties separate and join results by trace ID:** correctness and efficiency answer different questions, and a multi-run comparison must join on `trace_id` (with a scenario tag re-check) rather than row order. Normalize `error`/`missing` separately from `no`. (exp 012)

---

## 4. Related source material

| Topic | Writeup |
| --- | --- |
| Baseline trace, auth, trace ID capture | [001-first-trace.md](experiments/001-first-trace.md) |
| FM endpoint, dependency fix, deprecation | [002-foundation-model.md](experiments/002-foundation-model.md) |
| Manual spans and trace tags | [003-manual-spans.md](experiments/003-manual-spans.md) |
| Multi-turn sessions and ID-capture bug | [004-multi-turn-tracing.md](experiments/004-multi-turn-tracing.md) |
| Error signatures and `status` filtering | [005-error-tracing.md](experiments/005-error-tracing.md) |
| Latency/token/cost findings | [006-latency-cost-analysis.md](experiments/006-latency-cost-analysis.md) |
| Evaluation scorers, pilot fixes, results | [007-genai-evaluation.md](experiments/007-genai-evaluation.md) |
| Known-bad controls, alias fix | [008-scorer-controls.md](experiments/008-scorer-controls.md) |
| Right-city-wrong-fact control, factuality check | [009-factuality-check.md](experiments/009-factuality-check.md) |
| Self-contradiction rubric judge, no expected facts | [010-self-consistency-judge.md](experiments/010-self-consistency-judge.md) |
| Tool-call tracing, five verified span patterns | [011-tool-call-tracing.md](experiments/011-tool-call-tracing.md) |
| Tool-call judges: two correctness modes + efficiency, two repetitions | [012-tool-call-judges.md](experiments/012-tool-call-judges.md) |
| Register, backlog, decision log | [LAB_BOOK.md](LAB_BOOK.md) |

## 5. Still open

- Harden the environment: pin dependency versions so the `--no-deps` recipe is reproducible (F-012).
- Move the known-bad controls from the pilot into the full run and keep them as a standing regression set (F-014); add an LLM `Correctness` check with `expected_facts` for paraphrase robustness and compare it against the deterministic check (deterministic check landed in exp 009, consistency judge in exp 010).
- Standardize tags across every script (F-010), then use the suite for A/B comparisons (F-014) and monitoring (F-013).
- Add a legitimate failure-plus-retry control so the efficiency judge can be checked for false positives on recovery (F-015).
- Promote the exp 011/012 tool-call cases and three verdicts into F-014's standing A/B regression set.
- [x] Decide on Unity Catalog trace storage and shared vs project-specific experiment paths → resolved in [LAB_BOOK.md](LAB_BOOK.md) §7: keep the shared demo path with an env override, defer UC storage (F-011).
