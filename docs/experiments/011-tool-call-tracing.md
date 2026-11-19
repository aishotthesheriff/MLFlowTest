# Experiment 011 — Tool-call tracing: prove what the agent did

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-015 (tool-call tracing and validation), F-014 (A/B regression set), F-010 (tag conventions)
- **Prior experiment(s):** 002 (the real `TOOL` span), 004 (session/tag pattern), 009–010 (the validation arc)

## 1. Objective & hypothesis
**Question:** Can we capture tool-call behavior — including injected failure modes — as queryable traces, and verify it without any LLM judge?
**Hypothesis:** Yes. Drive the real LangGraph agent with scripted model decisions and a fake weather service; keep the user request and advertised tool catalog identical in all cases; then fetch each trace back and assert its spans directly.
**Success criteria:** five traces with the expected `TOOL` span names, arguments, counts, and OK outcomes; both tools advertised on every case; zero judge calls; fail closed on any mismatch; write the manifest only after all five pass.

## 2. Setup
- **Code/script:** new `trace_tool_calls.py` (no edits to `trace_example.py`, `trace_multi_turn.py`, or `evaluate_traces.py`)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_tool_calls.py
  ```
- **Environment:** Python 3.15.2, MLflow 3.18.0, LangChain 1.5.1 / core 1.8.2, LangGraph 1.2.22
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Runtime:** `langchain.agents.create_agent` + `mlflow.langchain.autolog()` — the real agent loop, not a hand-built span tree
- **Scripted model:** `GenericFakeChatModel` subclass whose `bind_tools()` returns a `RunnableBinding` carrying OpenAI tool schemas; it emits deterministic `AIMessage(tool_calls=[...])` decisions followed by a final answer. No endpoint is called, so the decisions cannot drift.
- **Fake service:** `get_weather(city)` → `"It might be cloudy in {city}"`; `get_temperature(city)` → `"It is 20C in {city}"`
- **Constant in every case:** request `"What is the current weather and cloud cover in SF?"`; advertised catalog `[get_weather, get_temperature]`
- **Tags:** `scenario=tool_calls`, `tool_case`, `session_id=lab-f011-…`, `lab_book=F-015`
- **Manifest:** `docs/demo/tool_call_manifest.json` (written only after all assertions pass)

## 3. Procedure
1. Prototyped locally against a SQLite tracking store to confirm that one scripted tool call yields one `TOOL` span, three separate tool-call messages yield three `TOOL` spans, and `RunnableBinding` makes autolog record `mlflow.chat.tools`.
2. Ran all five cases on Databricks with autolog enabled; each case got a manual root span carrying the request and tags, with the agent nested underneath.
3. Fetched all five traces back by ID and asserted: root request, advertised schemas, `TOOL` span names/arguments/counts, OK status, non-empty tool output, and tags.
4. Read advertised schemas from the `mlflow.chat.tools` attribute on `CHAT_MODEL` spans; fall back to the catalog recorded at `bind_tools()` time if the attribute is absent. No judge is invoked on either path.
5. Wrote the manifest only after every assertion passed.

## 4. Results
- **Outcome:** success — all five cases verified, five traces exported, zero judge calls, manifest written.
- **Session:** `lab-f011-1795112059` (see manifest for full IDs).

| Case | Trace ID | Spans | Expected TOOL spans | Observed TOOL spans | Advertised tools |
| --- | --- | ---: | --- | --- | --- |
| `tool_happy` | `tr-218c33b979b86c0e958d546aefa23a64` | 8 | `get_weather(city="SF")` × 1 | `get_weather(city='SF',OK)` × 1 | both |
| `tool_no_call` | `tr-8f166650ff924e86b7726829d3c81911` | 4 | none | none | both |
| `tool_wrong_tool` | `tr-1dd34cbcfd3fd9b4fa0231314015da11` | 8 | `get_temperature(city="SF")` × 1 | `get_temperature(city='SF',OK)` × 1 | both |
| `tool_wrong_args` | `tr-9f9dab49618b133d824747d8515b0104` | 8 | `get_weather(city="NYC")` × 1 | `get_weather(city='NYC',OK)` × 1 | both |
| `tool_retry_storm` | `tr-ba8b262cff37fa530c2d4a7291b87d82` | 16 | `get_weather(city="SF")` × 3 | `get_weather(city='SF',OK)` × 3 | both |

- Every `TOOL` span has `status=OK` and a non-empty `content`; every root request matches the constant string.
- Every `CHAT_MODEL` span carries `mlflow.chat.tools` with both function schemas, including the no-call case.
- The retry case produced **three distinct `TOOL` spans**, all successful — the condition the efficiency judge needs in exp 012.
- Experiment trace count rose from 110 to 115 after this run (exactly five new tagged traces).

## 5. Analysis
- **The user request is constant; the defect is injected in the decision, not the prompt.** Every case asks for SF weather and cloud cover and advertises both tools. That isolates the tool behavior as the only variable.
- **Wrong arguments must be injected before the traced call.** LangChain records arguments at tool entry, so rewriting `city` inside the tool body would leave `SF` in the span. The scripted `AIMessage` carries `{"city": "NYC"}` directly, so the span truthfully shows the defect.
- **Duplicate calls must cross the traced boundary.** Three internal service requests inside one tool body collapse into one `TOOL` span. Three separate tool-call messages produce three spans, which is what a redundancy judge can actually inspect.
- **All retries succeed on purpose.** The efficiency rubric permits retrying after a transient failure; a retry storm is only a defect when nothing failed. No errors are injected here.
- **Schema inspection is direct and free.** `mlflow.chat.tools` on each model span gives the advertised catalog; the fake model's recorded bindings are the fallback. Neither path calls a judge, so 011 is pure evidence.

## 6. Learnings & decisions
- A scripted `BaseChatModel` inside a real `create_agent` loop gives deterministic tool traces without a live endpoint or prompt luck.
- `bind_tools()` returning a `RunnableBinding` with OpenAI schemas is what makes autolog record `mlflow.chat.tools`; returning `self` silently loses the advertised catalog.
- "Tool behavior" has three independent axes: selection (which tool), arguments (what city), and cardinality (how many calls). Each needs its own injected case.
- Fail closed: verify traces before writing the manifest, so a downstream evaluator can never consume half-checked evidence.

## 7. Next actions
- [ ] Experiment 012: judge these same five traces with two correctness modes and an efficiency judge.
- [x] Add the five tool-call cases to F-014's standing A/B regression set alongside the six output-level controls (2026-11-19).
- [ ] Explore a failure-plus-retry case, where retries are legitimate, as an efficiency-judge control (F-016).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Five trace IDs and manifest path recorded (`docs/demo/tool_call_manifest.json`)
- [x] Expected-vs-observed span table published
- [x] No existing script modified; eight demo evidence traces untouched
- [x] Follow-up idea added to lab book backlog (F-015)
