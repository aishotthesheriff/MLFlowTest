# Experiment 003 — Manual/custom spans for non-autologged logic

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-003
- **Prior experiment(s):** 001-first-trace, 002-foundation-model

## 1. Objective & hypothesis
**Question:** Do manual `@mlflow.trace` spans add useful visibility into pre/post-processing that autologging cannot see, without disrupting the autologged agent/model/tool spans?  
**Hypothesis:** Adding an outer application-boundary span plus explicit preprocessing/postprocessing spans will produce a single coherent trace where manual and autolog spans nest correctly, with captured I/O and custom attributes.  
**Success criteria:** One trace (not fragmented) with manual spans as parents/siblings of autolog spans, inputs/outputs present on manual spans, custom attributes and trace tags visible, script exits 0.

## 2. Setup
- **Code/script/notebook:** `trace_manual_spans.py` (workspace root)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_manual_spans.py
  ```
- **Environment:** same venv/versions as exp 002 (Python 3.15.2, MLflow 3.18.0, `databricks-langchain` 0.22.0, `langchain` 1.5.1)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Model:** `ChatDatabricks(model="databricks-gpt-oss-20b", temperature=0.1, max_tokens=500)`
- **Config/params:** `mlflow.langchain.autolog()` kept on; manual spans added via `@mlflow.trace` and `mlflow.update_current_trace(tags=...)` inside the root span
- **Data/inputs:** `city="SF"`; `build_user_prompt` maps `SF` → `San Francisco`

## 3. Procedure
1. Created `trace_manual_spans.py` with three manual spans:
   - `weather_assistant` (CHAIN) — application boundary, explicit request/response I/O
   - `build_user_prompt` (PARSER) — preprocessing, city-code normalization
   - `format_response` (PARSER) — postprocessing, output prefix/whitespace cleanup
2. Kept autolog on so agent/model/tool spans remain captured; did **not** re-wrap already-autologged nodes (per MLflow guidance).
3. Set trace-level tags (`lab_book`, `scenario`, `model_endpoint`) inside the root span via `mlflow.update_current_trace`.
4. Ran the script, captured the trace ID, and verified the persisted trace/span tree with `mlflow.get_trace`.

## 4. Results
- **Outcome:** Success (exit code 0)
- **Agent/model outputs (summary):** "Answer: The current weather in San Francisco is **cloudy**."
- **Trace(s):** `tr-0cb5f6d26d3dad7fc32c9da9cad10131` — state OK, experiment `1675992194464286`  
  - **10 spans** (vs 7 in exp 002 autolog-only). Tree:
    - `weather_assistant` (CHAIN, root) — inputs `{'city': 'SF'}`, outputs full formatted answer, attrs include `component=application_boundary`, `lab_experiment=F-003`
      - `build_user_prompt` (PARSER) — inputs `{'city': 'SF'}`, outputs `"What is the weather in San Francisco?"`, attrs `component=preprocessing`, `step=prompt_construction`
      - `LangGraph` → `model` → `ChatDatabricks` (CHAT_MODEL), `tools` → `get_weather` (TOOL), second `model` → `ChatDatabricks` (all autologged, unchanged)
      - `format_response` (PARSER) — inputs raw model text, outputs `"Answer: ..."`, attrs `component=postprocessing`, `step=response_formatting`
  - **Trace tags:** `lab_book=F-003`, `scenario=manual_spans`, `model_endpoint=databricks-gpt-oss-20b`
- **Metrics/observations:** Manual and autolog spans share one trace/request ID; nesting is correct. No duplicate or orphan traces.

## 5. Analysis
- **What happened:** Manual spans added three explicit, searchable steps around the agent while autolog continued to capture the internal workflow, yielding a richer single trace.
- **Why (interpretation):** MLflow context propagation attaches autologged spans to the active manual root span; `@mlflow.trace` records function args/return values and custom attributes automatically.
- **Surprises / risks:** None functional. Model formatted "San Francisco" with a narrow no-break space and markdown bold; postprocessing span captured it verbatim. Care needed not to double-wrap autologged nodes (would create duplicate spans).
- **Comparison to prior runs:** Exp 002 had 7 autolog-only spans; exp 003 has 10 spans adding application boundary + two processing steps with I/O and tags. Core agent/tool spans identical.

## 6. Learnings & decisions
- Manual tracing is additive and composes cleanly with `mlflow.langchain.autolog()`.
- An outer application-boundary span is the most useful manual addition: it records end-to-end I/O and gives a stable place for environment/scenario tags.
- Custom attributes + trace tags make traces filterable (e.g. `scenario=manual_spans`).

## 7. Next actions
- [ ] Consider making the application-boundary span/tagging a reusable wrapper across scripts (F-010: tagging/searchability).
- [ ] Apply manual spans to a failure/error scenario (F-007) to confirm error capture on custom spans.

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Trace/run identifiers recorded (`tr-0cb5f6d26d3dad7fc32c9da9cad10131`, experiment `1675992194464286`)
- [x] Relevant code changes noted (`trace_manual_spans.py`)
- [x] Follow-up ideas added to lab book backlog
