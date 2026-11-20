# Demo at a Glance — Steps and Systems

A one-page reference for the MLFlowTest tracing demo. Full walkthrough: `DEMO_SCRIPT.md`; evidence and talk track: `DEMO_SUMMARY_AND_TALK_TRACK.md`.

## Systems involved

| System | Role |
| --- | --- |
| Databricks CLI profile (`~/.databrickscfg`) | Only credential — no OpenAI key |
| Databricks FM endpoints via `ChatDatabricks` | `databricks-gpt-oss-20b`; `llama-4-maverick` for the A/B |
| LangGraph weather agent + stub `get_weather` | The subject being traced |
| MLflow 3 Tracing | Autolog spans + manual `@mlflow.trace` spans, sessions, `TraceInfo` metrics |
| Experiment `/Shared/my-first-trace` (`1675992194464286`) | Shared store + Traces UI |
| MLflow GenAI Evaluation | Precomputed mode; 2 managed LLM judges + 3 deterministic scorers + 3 tool-call configs = 8 registered scorers |
| Databricks AI Search | Delta Sync index `workspace.mlflow_lab.weather_docs_index`, `databricks-gte-large-en` embeddings; typed `RETRIEVER` spans |
| Repeatability layer | `start_demo.sh --check-only`, `lab_tags.py`, `regression_suite.py`, manifests, pinned venv |

## Steps

0. `./start_demo.sh --check-only` — verify auth, experiment, evidence traces, 8 scorers.
1. **Act 1** — `trace_example.py`: ask about San Francisco weather; one trace, 7 spans, keyless.
2. **Act 2** — `trace_manual_spans.py`: 7 → 10 spans; manual spans nest with autolog.
3. **Act 3** — `trace_multi_turn.py`: 3 traces, 1 session; turn 3 recalls San Francisco with no tool call.
4. **Act 4** — `trace_errors.py`: unhandled → trace `ERROR`; handled → child span `ERROR`, trace `OK`.
5. **Act 5** — `analyze_trace_metrics.py`, then `evaluate_traces.py --pilot --with-controls`: latency/tokens/cost from the trace; 6/6 planted controls caught.
6. **Act 5B** (optional) — the two hard controls: right-city-wrong-fact and self-contradiction, each caught by exactly one scorer.
7. **Act 5C** (optional) — `trace_tool_calls.py` → `evaluate_tool_calls.py`: prove the tool spans, then judge them; efficiency says `yes` where correctness says `no`.
8. **Extensions** — experiment 013 endpoint A/B; experiment 014 RAG (`setup_rag_index.py` once, then `trace_rag.py`).

## Through-line and limit

**Trace → inspect → measure → evaluate → document.** The honest limit stays attached: toy agent, short answers, scripted tool cases, one clean A/B record per arm, one small RAG corpus.
