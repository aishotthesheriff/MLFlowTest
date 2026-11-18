# Experiment 005 — Error/failure tracing (F-007)

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-007 (also informs F-010)
- **Prior experiment(s):** 003-manual-spans, 004-multi-turn-tracing

## 1. Objective & hypothesis
**Question:** Do tool errors, unhandled exceptions, and explicitly recorded errors produce diagnosable traces with error status, exception details, and retained partial spans?  
**Hypothesis:** Unhandled exceptions (tool or application) will set trace/span status to ERROR with exception events; handled/manually-recorded errors will mark individual spans ERROR while leaving the trace OK.  
**Success criteria:** Each failure case yields a persisted trace; error spans include exception type/message/stacktrace; partial successful spans remain visible; error traces are filterable via `search_traces`.

## 2. Setup
- **Code/script/notebook:** `trace_errors.py` (workspace root)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_errors.py
  ```
- **Environment:** same venv as exp 004 (Python 3.15.2, MLflow 3.18.0, `databricks-langchain` 0.22.0, `langchain` 1.5.1)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Model:** `ChatDatabricks(model="databricks-gpt-oss-20b", temperature=0.1, max_tokens=500)`
- **Config/params:** `mlflow.langchain.autolog()` on; session `lab-f007-1795033547`; tags `lab_book/scenario/session_id/case`; APIs used: `span.record_exception()`, `span.set_status(SpanStatusCode.ERROR)`, `@mlflow.trace` auto-exception capture
- **Data/inputs:** three failure cases (below)

## 3. Procedure
1. Created `trace_errors.py` with three cases, each in its own `@mlflow.trace` root span:
   - **A:** tool `get_weather` raises `RuntimeError`; prompt explicitly requires tool use.
   - **B:** manual traced function raises unhandled `ValueError`.
   - **C:** manual child span calls `record_exception(TimeoutError(...))` + `set_status(ERROR)` without raising.
2. Ran the script, captured per-case trace IDs, inspected each trace's state/span statuses/events via `mlflow.get_trace`.
3. Verified filtering by `tags.case`, `tags.lab_book`, and `status` via `mlflow.search_traces`.
4. First exploratory run (session `lab-f007-1795033478`) is superseded: case A's tool description said "deliberately broken", so the model refused to call it and no tool-error span was produced. Renamed/described the tool normally and forced tool use in the final run.

## 4. Results
- **Outcome:** Success (exit 0; exceptions are intentional and caught by the harness)
- **Trace(s):** final run session `lab-f007-1795033547`:

  | Case | Trace ID | Trace status | Spans | Error detail |
  | --- | --- | --- | --- | --- |
  | A: tool error | `tr-cbd09f84a14aa356cfffb614bb4583c0` | ERROR | 6 | `RuntimeError: Weather service unavailable for SF` on root, `LangGraph`, `tools`, and `get_weather` (TOOL) spans |
  | B: unhandled exception | `tr-3dbea41e598c727874df4a43ed18e897` | ERROR | 1 | `ValueError: intentional unhandled failure for F-007` on root span, with exception event + stacktrace |
  | C: explicit error recorded | `tr-193c937a2ab7790e06969f4bb3730a85` | OK | 2 | `TimeoutError: simulated downstream timeout` on child `manual_failure` span only; trace/root stay OK |

- **Observations:**
  - Case A retained partial successful spans (`model`, `ChatDatabricks` both OK) alongside ERROR spans — the failed tool call is fully diagnosable in context.
  - Case C demonstrates handled errors: span-level ERROR with `exception.type`, `exception.message`, `exception.stacktrace` in the span event, while the overall trace remains OK.
  - `@mlflow.trace` automatically records unhandled exceptions (type, message, stacktrace) and sets span/trace status ERROR.
  - **Search:** `filter_string="status = 'ERROR'"` returned 3 traces; `"status = 'OK' AND tags.lab_book = 'F-007'"` returned 3; `tags.case = 'A_tool_error'` also works. Note the filter column is `status` (not `state`) — `state = 'ERROR'` is invalid.
  - Tags `lab_book=F-007`, `scenario=error_tracing`, `session_id`, `case` were present on all traces.

## 5. Analysis
- **What happened:** Unhandled failures propagate to trace-level ERROR with rich exception events on every affected span; explicitly recorded/handled failures stay at span level and do not fail the trace.
- **Why (interpretation):** `@mlflow.trace` wraps the function and records exceptions automatically; LangChain autolog propagates tool errors through `tools`/`get_weather` spans to the graph boundary. `span.record_exception()` + `set_status(ERROR)` are the explicit API for handled failures.
- **Surprises / risks:** An LLM may refuse to call a tool whose name/description signals failure — error-injection scripts must keep failing tools looking legitimate. `mlflow.search_traces` filter uses `status`, not `state`.
- **Comparison to prior runs:** Exps 003/004 produced only OK traces; exp 007 adds ERROR traces and span-level error evidence.

## 6. Learnings & decisions
- Three distinct error signatures are observable: unhandled tool error (trace ERROR, multi-span), unhandled app error (trace ERROR, single span), handled error (trace OK, child span ERROR).
- Always include exception details in error cases; `@mlflow.trace` already captures type/message/stacktrace for unhandled exceptions.
- Use tags (`lab_book`, `case`, `scenario`, `session_id`) + `status` to find error traces later.

## 7. Next actions
- [ ] Apply error-pattern tags consistently across future scripts (F-010).
- [ ] Build a latency/token/cost summary across OK and ERROR traces (F-008).
- [ ] Consider alerting on `status = 'ERROR'` traces as a monitoring signal (F-013).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Trace/run identifiers recorded (3 trace IDs + session `lab-f007-1795033547`)
- [x] Relevant code changes noted (`trace_errors.py`)
- [x] Follow-up ideas added to lab book backlog
