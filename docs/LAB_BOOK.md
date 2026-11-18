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
| Key scripts | `trace_example.py`, `trace_manual_spans.py`, `trace_multi_turn.py`, `trace_errors.py`, `.env.example`, `requirements.txt`, `README.md` |

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

**Status legend:** Planned · In progress · Completed · Blocked · Abandoned

---

## 5. Detailed experiment notes

Individual writeups live in [`docs/experiments/`](experiments/):

- [TEMPLATE.md](experiments/TEMPLATE.md) — copy for new experiments
- [001-first-trace.md](experiments/001-first-trace.md) — baseline first trace
- [002-foundation-model.md](experiments/002-foundation-model.md) — Databricks FM endpoint (no OpenAI key), deprecation fix
- [003-manual-spans.md](experiments/003-manual-spans.md) — manual @mlflow.trace spans for pre/post-processing
- [004-multi-turn-tracing.md](experiments/004-multi-turn-tracing.md) — session grouping + per-turn I/O across 3 turns
- [005-error-tracing.md](experiments/005-error-tracing.md) — tool errors, unhandled exceptions, handled errors

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
| F-008 | Latency and token/cost analysis | Trace metadata is sufficient to identify slow/expensive spans. | Medium | S-M | Runs with usage data | Proposed | Compare prompts/models; document where metrics appear in UI. |
| F-009 | MLflow GenAI evaluation on traces | Automated scorers/judges can assess quality from traced runs. | High | M-L | Dataset/scorers setup | Proposed | Define criteria, run evaluation, track scores over iterations. |
| F-010 | Trace tagging, metadata, and searchability | Consistent tags (env, feature, git SHA, scenario) make traces easy to filter/debug. | Medium | S | — | Proposed | Set tags/metadata in code; document naming conventions. Exp 003 set `lab_book`/`scenario`/`model_endpoint` tags — reuse as convention. |
| F-011 | Unity Catalog trace storage | UC-backed trace storage improves governance/queryability for this workflow. | Medium | M | UC permissions/config | Proposed | Follow [trace-unity-catalog](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog); compare limits/capabilities. |
| F-012 | Experiment organization strategy | Separate dev/test/prod experiments and naming conventions reduce clutter and risk. | Medium | S | Team/workspace conventions | Proposed | Propose path scheme, tags, and retention expectations. |
| F-013 | Production-style monitoring/alerting workflow | Traces can feed dashboards/alerts for ongoing quality and performance monitoring. | Medium | L | Production-like workload | Proposed | Identify key signals and Databricks/Lakehouse integration path. |
| F-014 | Prompt/version comparison (A/B) | Side-by-side traced runs make prompt/model changes measurable. | Medium | M | Variant configs | Proposed | Hold inputs constant; compare outputs, traces, and eval scores. |

> Add new ideas freely; include a short hypothesis and dependency so they are actionable.

## 7. Open questions

- [x] Which Databricks Foundation Model serving endpoint should be the default for keyless/local-auth runs? → using `databricks-gpt-oss-20b` (exp 002); revisit if quality/latency favors another.
- [ ] Should traces live in shared experiments (`/Shared/...`) or user/project-specific paths?
- [ ] Do we need Unity Catalog-backed trace storage for this project now?
- [ ] What evaluation criteria/scorers matter first (correctness, tool use, latency, cost, safety)?
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

## 9. Change log

| Date | Change | Author/notes |
| --- | --- | --- |
| 2026-11-18 | Created lab book structure, experiment register, template, and initial backlog | Initialized from first successful trace run |
| 2026-11-18 | Updated `trace_example.py` to print the trace ID after flushing traces | Verified with a successful re-run; lab-book exp 001 records both original and verification trace IDs |
| 2026-11-18 | Added experiment 002; switched agent to Databricks FM, fixed deprecation, updated config/docs | F-001 and F-002 completed; verified persisted trace |
| 2026-11-18 | Added `trace_manual_spans.py` and experiment 003 | F-003 completed; manual + autolog spans verified in one 10-span trace |
| 2026-11-18 | Added `trace_multi_turn.py` and experiment 004 | F-005 completed; 3-turn session grouping and context recall verified |
| 2026-11-18 | Added `trace_errors.py` and experiment 005 | F-007 completed; 3 error signatures verified with exception events and filtering |

---
*Keep entries factual, link to traces/evidence, and prefer small reproducible experiments over large undocumented changes.*