# Experiment 001 — First traced LangGraph agent run

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-001, F-002
- **Prior experiment(s):** None (baseline)

## 1. Objective & hypothesis
**Question:** Can we produce and export a GenAI trace from a local Python script to a Databricks workspace using MLflow 3 autologging?  
**Hypothesis:** Following the Databricks tracing overview quickstart (LangGraph + LangChain OpenAI + `mlflow.langchain.autolog()`, `tracking_uri="databricks"`) will create an experiment/trace visible in the Databricks Experiments UI.  
**Success criteria:** Script runs end-to-end without auth/export errors, returns an agent response, and flushes traces to the configured Databricks experiment.

## 2. Setup
- **Code/script/notebook:** `trace_example.py` (workspace root)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_example.py
  ```
- **Environment:** macOS (darwin), Python 3.15.2, `.venv`
  - `mlflow[databricks]` 3.18.0, `langgraph` 1.2.22, `langchain-openai` 1.8.1, `python-dotenv`
- **Databricks:** `https://dbc-5c7ff528-845c.cloud.databricks.com` (AWS, workspace `7474660896957932`), auth via `~/.databrickscfg` DEFAULT PAT profile (valid), `mlflow.set_tracking_uri("databricks")`
- **MLflow experiment:** `/Shared/my-first-trace` (`MLFLOW_EXPERIMENT_NAME` from `.env`; experiment created if missing)
- **Model(s)/endpoint(s):** OpenAI `gpt-4o-mini` via `ChatOpenAI` (`OPENAI_API_KEY` from `.env`)
- **Config/params:** LangChain autolog enabled (`mlflow.langchain.autolog()`); single user message; one tool `get_weather`
- **Data/inputs:** User prompt: `"What is the weather in SF?"`; tool returns fixed string `"It might be cloudy in {city}"`

## 3. Procedure
1. Created project scaffold (`requirements.txt`, `.env.example`, `trace_example.py`, `README.md`) and installed dependencies into `.venv`.
2. Verified Databricks CLI/auth (`databricks auth profiles/describe`) and ensured `.env` provided required LLM key (Databricks auth resolved from `~/.databrickscfg`).
3. Ran `python trace_example.py` and observed agent output and trace flush on exit.

## 4. Results
- **Outcome:** Success (exit code 0)
- **Agent/model outputs (summary):** "The weather in San Francisco might be cloudy."
- **Trace(s):** Exported to Databricks experiment `/Shared/my-first-trace` (experiment ID `1675992194464286`, new experiment created during run).  
  - **Trace ID (original baseline run):** `tr-983651f7eb6bf22274142b9362c21858` (state: OK; retrieved via `mlflow.search_traces` on 2026-11-18)  
  - **Trace ID (verification run after adding in-script trace ID logging):** `tr-efb8425cc9c44452521a84f94a49c744` (2026-11-18; response: "The weather in San Francisco is likely to be cloudy.")  
  - View in Databricks UI: **Experiments** → `/Shared/my-first-trace` → **Traces** → open the trace. You can also copy the trace ID from the trace details/header in the UI.
- **Metrics/observations:** Async trace logging queue flushed before program exit (`mlflow.tracing.export.async_export_queue`). Token/latency details to review in trace UI.
- **Artifacts:** Local script/config in workspace; terminal run log showed successful completion.

**Notable runtime messages (non-blocking):**
- MLflow info: suggested loading installed `mlflow-trace-instrumentation` skill; noted Unity Catalog trace storage option.
- LangGraph deprecation warning: `create_react_agent` moved to `langchain.agents.create_agent` (LangGraph V1.0 → remove in V2.0).

## 5. Analysis
- **What happened:** Local run authenticated to Databricks, created/selected the target experiment, executed a LangGraph ReAct agent with a tool call, and exported trace data successfully.
- **Why (interpretation):** Autologging captured LangChain/LangGraph execution; Databricks tracking URI routed trace storage to the workspace using existing CLI PAT configuration.
- **Surprises / risks:** Deprecation warning indicates API drift to address; Python 3.15 is very new but dependencies installed and ran for this case. Trace ID not recorded locally—future runs should capture/link IDs explicitly.
- **Comparison to prior runs:** N/A (baseline).
- **Trace ID capture:** The original run did not print a trace ID; it was retrieved after the fact from Databricks with `mlflow.search_traces(...)`. `trace_example.py` now calls `mlflow.flush_trace_async_logging()` and `mlflow.get_last_active_trace_id()` after the agent invocation, so the trace ID is printed automatically for future runs (verified by `tr-efb8425cc9c44452521a84f94a49c744`).

## 6. Learnings & decisions
- A minimal local `.venv` + `~/.databrickscfg` is sufficient to send traces to Databricks without embedding host/token in `.env`.
- Baseline example is a good template for future tracing experiments; document trace IDs/links as part of each run.

## 7. Next actions
- [x] Capture trace ID/link for this run and append here (`tr-983651f7eb6bf22274142b9362c21858`).
- [ ] Update `trace_example.py` to `langchain.agents.create_agent` (F-002) and re-verify trace.
- [ ] Try Databricks Foundation Model endpoint to remove external OpenAI dependency (F-001).
- [ ] Add manual span instrumentation experiment (F-003).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Trace/run identifiers recorded (`tr-983651f7eb6bf22274142b9362c21858`, experiment `1675992194464286`)
- [x] Relevant code changes noted (baseline scaffold in workspace)
- [x] Follow-up ideas added to lab book backlog (F-001, F-002, etc.)
