# MLflow GenAI Tracing (Databricks) quickstart

Minimal local setup to produce a traced LangGraph agent run and send traces to a Databricks workspace, following the [Databricks tracing overview](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/overview).

The example agent uses a Databricks Foundation Model API endpoint (`databricks-gpt-oss-20b` by default), so no external LLM key is needed — only Databricks workspace auth.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Option A: set DATABRICKS_HOST/TOKEN in .env, or use ~/.databrickscfg (no external LLM key)
```

## Run

```bash
source .venv/bin/activate
python trace_example.py
```

Then in Databricks: **Experiments** → open the experiment (default `/Shared/my-first-trace`) → **Traces** tab.

## Demo kit

A ~7-minute live demo of the tracing, failure, metrics, and evaluation experiments. Follows the same pattern as the other demo stacks (`DEMO_SCRIPT.md`, `DEMO_SUMMARY_AND_TALK_TRACK.md`, `DEMO_DECK.html`, launcher).

```bash
./start_demo.sh --check-only   # read-only preflight: auth, experiment, evidence traces, scorers
./start_demo.sh                # preflight + open the deck and the Databricks Traces tab
```

- [DEMO.md](DEMO.md) — overview and quick start
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — full run-of-show with pre-flight and troubleshooting
- [DEMO_SUMMARY_AND_TALK_TRACK.md](DEMO_SUMMARY_AND_TALK_TRACK.md) — one-page summary and 2–3 minute talk track
- [DEMO_DECK.html](DEMO_DECK.html) — 7-slide companion deck with real MLflow UI screenshots ([provenance](docs/demo/README.md))

## Lab book

- [docs/LAB_BOOK.md](docs/LAB_BOOK.md) — experiment log, environment snapshot, ideas/backlog for future experiments
- [docs/FINDINGS_AND_LEARNINGS.md](docs/FINDINGS_AND_LEARNINGS.md) — consolidated fixes, findings, and learnings across all experiments
- [docs/experiments/](docs/experiments/) — per-experiment writeups and template ([001-first-trace.md](docs/experiments/001-first-trace.md), [002-foundation-model.md](docs/experiments/002-foundation-model.md), [003-manual-spans.md](docs/experiments/003-manual-spans.md), [004-multi-turn-tracing.md](docs/experiments/004-multi-turn-tracing.md), [005-error-tracing.md](docs/experiments/005-error-tracing.md), [006-latency-cost-analysis.md](docs/experiments/006-latency-cost-analysis.md), [007-genai-evaluation.md](docs/experiments/007-genai-evaluation.md), [008-scorer-controls.md](docs/experiments/008-scorer-controls.md), [009-factuality-check.md](docs/experiments/009-factuality-check.md), [010-self-consistency-judge.md](docs/experiments/010-self-consistency-judge.md), [011-tool-call-tracing.md](docs/experiments/011-tool-call-tracing.md), [012-tool-call-judges.md](docs/experiments/012-tool-call-judges.md))

### Optional experiments
```bash
python trace_manual_spans.py   # @mlflow.trace boundary + pre/post-processing spans
python trace_multi_turn.py     # 3-turn conversation grouped by a shared session_id
python trace_errors.py         # tool errors, unhandled exceptions, handled error spans
python trace_tool_calls.py     # 5 scripted tool-call cases; verified spans + manifest (exp 011)
python evaluate_tool_calls.py --register  # register 3 tool-call scorer configs (exp 012)
python evaluate_tool_calls.py  # judge the 011 traces: 2 reps x 2 passes, no predict_fn (exp 012)
python analyze_trace_metrics.py  # latency/token/cost summary over persisted traces
python evaluate_traces.py --pilot --with-controls  # pilot + planted known-bad controls
python evaluate_traces.py --pilot # 3-record scorer pilot (use --register to persist scorers)
python evaluate_traces.py        # full GenAI evaluation over persisted traces
```

## Notes

- **Databricks auth:** set `DATABRICKS_HOST` + `DATABRICKS_TOKEN` in `.env`, or configure a profile in `~/.databrickscfg` (used here).
- **LLM:** the sample uses `ChatDatabricks` against a Foundation Model endpoint (`databricks-gpt-oss-20b` by default). Change it via `DATABRICKS_MODEL_ENDPOINT` in `.env`. No external LLM key needed.
- `mlflow.set_tracking_uri("databricks")` sends traces to your Databricks workspace (not a local MLflow server).
- **Dependency note (Python 3.15):** `databricks-langchain` and its Databricks/Unity Catalog transitive deps were installed with `pip install --no-deps ...` because full resolution attempts to build an old scipy that needs a Fortran compiler. If you rebuild the venv, install `mlflow[databricks] langgraph langchain langchain-openai python-dotenv` normally, then add the Databricks integration packages with `--no-deps` (see experiment 002 for the list).
