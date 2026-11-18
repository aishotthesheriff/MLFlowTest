# Experiment 002 — Switch agent to Databricks Foundation Model (no external LLM key)

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-001, F-002
- **Prior experiment(s):** 001-first-trace

## 1. Objective & hypothesis
**Question:** Can the agent use a Databricks Foundation Model API endpoint instead of OpenAI, so tracing works with only Databricks workspace auth and no external API key?  
**Hypothesis:** Swapping `ChatOpenAI` for `ChatDatabricks` (databricks-langchain) preserves tool-calling and MLflow autolog span capture, producing an equivalent trace without `OPENAI_API_KEY`.  
**Success criteria:** Script runs end-to-end using only `~/.databrickscfg`, the tool is called, trace exports to Databricks with LangGraph/CHAT_MODEL/TOOL spans, and no deprecation warning remains.

## 2. Setup
- **Code/script/notebook:** `trace_example.py` (workspace root)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_example.py
  ```
- **Environment:** macOS, Python 3.15.2, `.venv`; added `databricks-langchain` 0.22.0 + transitive deps and `langchain` 1.5.1 (installed `--no-deps` to avoid an incompatible scipy source build on Py 3.15; existing scipy 1.18.1 retained)
- **Databricks:** `https://dbc-5c7ff528-845c.cloud.databricks.com` (AWS, workspace `7474660896957932`), auth via `~/.databrickscfg` DEFAULT PAT profile
- **MLflow experiment:** `/Shared/my-first-trace` (experiment ID `1675992194464286`)
- **Model(s)/endpoint(s):** `ChatDatabricks(model="databricks-gpt-oss-20b", temperature=0.1, max_tokens=500)` — a ready FM endpoint in the workspace; configurable via `DATABRICKS_MODEL_ENDPOINT`
- **Config/params:** `mlflow.langchain.autolog()`; `langchain.agents.create_agent` (replaces deprecated `langgraph.prebuilt.create_react_agent`); one tool `get_weather`
- **Data/inputs:** User prompt `"What is the weather in SF?"`; tool returns fixed `"It might be cloudy in {city}"`

## 3. Procedure
1. Listed ready FM serving endpoints via `databricks serving-endpoints list` / `WorkspaceClient().serving_endpoints.list()` (11 ready).
2. Installed `databricks-langchain` and its missing transitive deps (`--no-deps`) into `.venv`.
3. Verified `ChatDatabricks` import and a direct invoke, then verified tool calling with `create_agent`.
4. Rewrote `trace_example.py` to use `ChatDatabricks` + `langchain.agents.create_agent`, keeping trace-ID printing.
5. Ran the script; captured trace ID and verified the persisted trace and spans via `mlflow.get_trace`.

## 4. Results
- **Outcome:** Success (exit code 0); no deprecation warning
- **Agent/model outputs (summary):** "The current weather in San Francisco is cloudy."
- **Trace(s):** `tr-054cbbc9de1d27ba20aec517e6cda4eb` — state OK, experiment `1675992194464286`; verified 7 spans:
  - `LangGraph` (CHAIN), `model` (CHAIN), `ChatDatabricks` (CHAT_MODEL), `tools` (CHAIN), `get_weather` (TOOL), `model` (CHAIN), `ChatDatabricks` (CHAT_MODEL)
- **Metrics/observations:** Tool was called; LLM spans captured with model name. (Latency/token details available in trace UI.)
- **Artifacts:** Updated `trace_example.py`, `requirements.txt`, `.env.example`, `README.md`.

## 5. Analysis
- **What happened:** The agent answered using the Databricks-hosted model and produced a fully traced run with no OpenAI key present.
- **Why (interpretation):** `ChatDatabricks` authenticates through the Databricks SDK/profile; `mlflow.langchain.autolog()` instruments the LangGraph execution including the ChatDatabricks model spans.
- **Surprises / risks:** Installing `databricks-langchain` with full dependency resolution fails on Python 3.15 because an older scipy needs a Fortran compiler; using `--no-deps` with the already-installed modern stack works. `--no-deps` installs are version-sensitive and should be revisited if the venv is rebuilt.
- **Comparison to prior runs:** Same task/tools as exp 001; span structure adds explicit `ChatDatabricks` CHAT_MODEL spans and removes the OpenAI dependency. Response wording differs (model-dependent).

## 6. Learnings & decisions
- Databricks FM endpoints can fully replace OpenAI for this lab, using workspace auth only.
- `mlflow.langchain.autolog()` covers `ChatDatabricks`/LangGraph without extra configuration.
- Default endpoint chosen: `databricks-gpt-oss-20b` (fast, tool-capable); overridable via `DATABRICKS_MODEL_ENDPOINT`.

## 7. Next actions
- [ ] Compare response quality/latency across other endpoints (e.g. `databricks-llama-4-maverick`, `databricks-meta-llama-3-3-70b-instruct`) — F-014
- [ ] Address dependency install fragility (pin versions / document `--no-deps` recipe) — F-012
- [ ] Add manual spans around custom logic (F-003)

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Trace/run identifiers recorded (`tr-054cbbc9de1d27ba20aec517e6cda4eb`, experiment `1675992194464286`)
- [x] Relevant code changes noted (`trace_example.py`, `requirements.txt`, `.env.example`, `README.md`)
- [x] Follow-up ideas added to lab book backlog
