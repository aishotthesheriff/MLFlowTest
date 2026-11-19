# MLflow GenAI Tracing (Databricks) quickstart

Minimal local setup to produce a traced LangGraph agent run and send traces to a Databricks workspace, following the [Databricks tracing overview](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/overview).

The example agent uses a Databricks Foundation Model API endpoint (`databricks-gpt-oss-20b` by default), so no external LLM key is needed — only Databricks workspace auth.

## Setup

```bash
./rebuild_venv.sh        # exact versions from requirements.lock.txt + smoke check
cp .env.example .env
# Option A: set DATABRICKS_HOST/TOKEN in .env, or use ~/.databrickscfg (no external LLM key)
```

Do not use plain `pip install -r requirements.txt` to rebuild on Python 3.15 — see [Environment notes](#environment-notes--troubleshooting). An existing `.venv` is updated in place, never deleted; pass a different path (`./rebuild_venv.sh /tmp/check-venv`) to verify without touching it.

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
- [DEMO_DECK.html](DEMO_DECK.html) — 8-slide companion deck with real MLflow UI screenshots ([provenance](docs/demo/README.md))

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

### Standing A/B regression set (F-014)

```bash
python regression_suite.py --summary    # the 6 output controls + 5 tool cases + 3 verdicts
python regression_suite.py              # offline: check artifacts cover the set and match baseline
python regression_suite.py --run baseline        # re-score the frozen scripted cases (judge calls)
```

The case lists come from `evaluate_traces.py` and `evaluate_tool_calls.py`, so the suite has no duplicate copy to drift. `--validate` fails if coverage or the exp-012 verdict baseline changes.

#### Real endpoint/prompt A/B (exp 013)

`--run` re-scores the same stored traces, so it cannot compare endpoints or prompts. Use `--ab` to generate a freshly tagged trace for each arm, score it with the 6 standing controls, and snapshot structured results + trace metrics:

```bash
python regression_suite.py --ab gpt-oss-20b --endpoint databricks-gpt-oss-20b
python regression_suite.py --ab llama-4-maverick --endpoint databricks-llama-4-maverick
python regression_suite.py --compare \
  docs/demo/regression/gpt-oss-20b.output.json \
  docs/demo/regression/llama-4-maverick.output.json
```

`--ab` also accepts `--prompt "..."` to hold the endpoint fixed and vary the message. Each generated trace carries `variant` and `model_endpoint` tags, and `evaluate_traces.py --variant` isolates that arm so untagged evaluation traces do not leak into the score. The five scripted tool cases are arm-independent and are deliberately not re-judged. The worked example and results are in [exp 013](docs/experiments/013-endpoint-ab.md).

## Notes

- **Databricks auth:** set `DATABRICKS_HOST` + `DATABRICKS_TOKEN` in `.env`, or configure a profile in `~/.databrickscfg` (used here).
- **LLM:** the sample uses `ChatDatabricks` against a Foundation Model endpoint (`databricks-gpt-oss-20b` by default). Change it via `DATABRICKS_MODEL_ENDPOINT` in `.env`. No external LLM key needed.
- `mlflow.set_tracking_uri("databricks")` sends traces to your Databricks workspace (not a local MLflow server).
- **Trace tags:** every experiment script sets `lab_book`, `scenario`, `env` (default `local`; override with `LAB_ENV`) and `git_sha` via `lab_tags.py`. Scenario-specific tags (`tool_case`, `case`, `turn`, `session_id`, `model_endpoint`) are kept. Filter in the Traces UI with e.g. `tags.scenario = 'tool_calls'`.
- **Dependencies are pinned (F-012, done 2026-11-19).** `requirements.txt` pins the six direct dependencies; `requirements.lock.txt` pins the full 160-package working set. `./rebuild_venv.sh` installs the lock with `--no-deps` and smoke-checks imports/versions. Verified on a fresh Python 3.15.2 venv. Details and known warnings are below.

## Environment notes & troubleshooting

| Symptom | Cause | What to do |
| --- | --- | --- |
| `pip install databricks-langchain` (or `pip install -r requirements.txt`) tries to build scipy and fails with "Unknown compiler(s): gfortran" on Python 3.15 | Resolver follows `unitycatalog-langchain[databricks]` into `databricks-connect`, backtracks, and picks a scipy sdist without a cp315 wheel | Use `./rebuild_venv.sh` — the exact lock with `--no-deps` bypasses resolution. Do not install `databricks-connect` to "fix" it. |
| `pip check` reports missing `tabulate`, `nest-asyncio`, `unitycatalog-client`, `langchain-community`, `openai-agents` and version conflicts (`cloudpickle`, `typing-extensions`, `langchain`, `openai`) | The lock intentionally keeps the known-working stack; those declarations belong to unused optional branches | Expected — the working venv and a clean lock rebuild produce the *same* warnings. Do not resolve them; installing those packages downgrades LangChain/OpenAI and breaks the traced agent. |
| PyYAML builds from source during a clean install | No cp315 wheel is published | Needs Xcode Command Line Tools (`xcode-select --install`); no Fortran compiler is required with the lock. |
| `INFO mlflow.agent.hint: Load the mlflow-trace-instrumentation skill...` on import | Informational hint from MLflow 3.18 | Harmless; set `MLFLOW_DISABLE_AGENT_HINT=1` to silence (the rebuild script does). |
| `npx gitnexus` crashes with `node.target is null` on npm 11 | Upstream npx/[issue #1939](https://github.com/abhigyanpatwari/GitNexus/issues/1939) | Use `node .gitnexus/run.cjs <command>`; if the runner is absent, bootstrap with `bunx gitnexus@latest analyze` or a global install. |
| Local MLflow UI logs a 500 on `/assistant/config` (circular import) during screenshot capture | MLflow UI assistant-endpoint issue in the local replay server | Harmless — traces and screenshots render correctly; see [demo provenance](docs/demo/README.md). |
| Accidentally edited `.env`? | It holds workspace PAT / endpoint config | `.env` is gitignored — never commit it; track only `.env.example`.
