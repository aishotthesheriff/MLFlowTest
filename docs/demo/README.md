# Demo screenshot provenance

The [deck](../../DEMO_DECK.html) uses real screenshots of the MLflow 3 UI — not
mockups. This directory explains where they came from and how to regenerate
them.

## Why a local store?

The in-app browser has no Databricks SSO session, so opening the hosted
experiment redirects to `accounts.cloud.databricks.com/login`. Instead, the
real traces from `/Shared/my-first-trace` are copied into a local SQLite MLflow
store, and the real MLflow 3 UI is served against that store from `localhost`.
The screenshots therefore show genuine MLflow UI rendering of genuine traces —
spans, timings, inputs/outputs, tags and error events all came from Databricks.

## What is preserved

`copy_traces.py` uses MLflow's `copy_trace_to_experiment` helper, which copies
the full trace data. Timings, token usage, tags and metadata are intact.

What it **does not** preserve: the original trace IDs. MLflow assigns new IDs
on copy. `trace_map.json` records `old_id` → `new_id` for every copied trace, so each
screenshot can be traced back to the Databricks original cited in
[LAB_BOOK.md](../LAB_BOOK.md). The six original mappings are:

| Screenshot | Databricks original | Local copy |
| --- | --- | --- |
| 02 baseline | `tr-054cbbc9de1d27ba20aec517e6cda4eb` | `tr-ee8cf68fbe82ea628f5bc5599b2526d1` |
| 03 manual spans | `tr-0cb5f6d26d3dad7fc32c9da9cad10131` | `tr-c2c963345996b3b8829870f55e0c48d9` |
| 04 turn 3 | `tr-6f99921de8fc0c0f8f0271392f7bb606` | `tr-30fe163b1895fbf03ffc30ee189fd380` |
| 05 tool error | `tr-cbd09f84a14aa356cfffb614bb4583c0` | `tr-651bee5671295a29be3a4c6b2ec8729f` |
| 06 unhandled | `tr-3dbea41e598c727874df4a43ed18e897` | `tr-f53de5648d3b7f9ceed011b4c70b702e` |
| 07 handled | `tr-193c937a2ab7790e06969f4bb3730a85` | `tr-1c0d8c12605f1c535f474129f66387cb` |

The five tool-call cases from experiment 011 use the same path, with these
additional mappings:

| Screenshot | Databricks original | Local copy |
| --- | --- | --- |
| 09 tool happy | `tr-218c33b979b86c0e958d546aefa23a64` | `tr-f76443b19357764359d2537bdb103a0c` |
| 10 tool no-call | `tr-8f166650ff924e86b7726829d3c81911` | `tr-e6eff0d8b7be76965f9e3c45210ff02d` |
| 11 tool wrong-tool | `tr-1dd34cbcfd3fd9b4fa0231314015da11` | `tr-b13225c85a997f5330367df7daab202e` |
| 12 tool wrong-args | `tr-9f9dab49618b133d824747d8515b0104` | `tr-ba4e062f61a4a44599fafa0169cac55d` |
| 13 tool retry-storm | `tr-ba8b262cff37fa530c2d4a7291b87d82` | `tr-859f09b6f20a080fa18ffc15af15586a` |

The RAG tracing (experiment 014) and endpoint A/B (experiment 013) work adds
these mappings. Shots 14 and 15 use the same RAG trace; 16 and 17 are the two
A/B arms.

| Screenshot | Databricks original | Local copy |
| --- | --- | --- |
| 14 / 15 rag waterfall + retriever | `tr-e754080659cb22bee921db7192242ac1` | `tr-3868764f15a607d277c50ac291ad3e3b` |
| 16 A/B gpt-oss-20b | `tr-e96d66aa28e03574a1d499b46c6f9036` | `tr-dc278d594e4f0e52c42e8a48b0966f07` |
| 17 A/B llama-4-maverick | `tr-72afbaf93bf8de56b550a856e9ebf9d3` | `tr-630eb3933feed389c701c428ed2aaca2` |

The JSON map deliberately excludes trace tags because they include an
individual's email address.

## Screenshots

| File | Shows |
| --- | --- |
| `01-traces-list.png` | Traces tab: inputs, outputs, session, duration, state, tokens, tags |
| `02-baseline-waterfall.png` | 7 spans / 3.12 s — autologged ChatDatabricks + `get_weather` |
| `03-manual-spans.png` | 10 spans / 2.69 s — manual spans nesting the autolog spans |
| `04-multiturn-turn3.png` | Turn 3 recalling the first city from session history |
| `05-tool-error.png` | Tool failure: trace `ERROR`, exception type and stacktrace |
| `06-unhandled-error.png` | Unhandled exception: trace `ERROR`, one span |
| `07-handled-error.png` | Handled failure: child span `ERROR`, trace still `OK` |
| `08-error-rows.png` | Error and session rows in the traces list |
| `09-tool-happy.png` | One `get_weather(city=SF)` TOOL span, inputs panel open |
| `10-tool-no-call.png` | No TOOL span; both tools still advertised on the model span |
| `11-tool-wrong-tool.png` | `get_temperature(city=SF)` TOOL span with its inputs |
| `12-tool-wrong-args.png` | `get_weather(city=NYC)` TOOL span — the injected defect, visible in inputs |
| `13-tool-retry-storm.png` | Three `get_weather(city=SF)` TOOL spans, all OK |
| `14-rag-waterfall.png` | RAG trace: CHAIN → EMBEDDING → RETRIEVER → LLM spans, 5.56 s |
| `15-rag-retriever.png` | RETRIEVER span Inputs/Outputs: query, top_k=3, index, ranked docs with scores |
| `16-ab-gpt-oss.png` | A/B arm `variant=gpt-oss-20b`, 7 spans, 461 tokens |
| `17-ab-maverick.png` | A/B arm `variant=llama-4-maverick`, 7 spans, 876 tokens |

All captures are 3200 × 1800 (1600 × 900 viewport at 2× device scale). The
tool-call shots select the tool span before capture so the Inputs/Outputs panel
shows the real arguments; `shoot.js` does this via each target's `selectSpan`.
Shot 15 selects the `retrieve_docs` span so the ranked-doc outputs are visible.
`shoot.js` forces a full document reload between targets — hash-only navigation
left the previous trace selected in the MLflow SPA, which produced shots of the
wrong run.

## Regenerate

```bash
# 1. Replay the current Databricks traces into a local store.
.venv/bin/python docs/demo/copy_traces.py

# 2. Serve the local store (use the exact `store:` path printed by step 1;
#    Python's tempfile directory is not /tmp on macOS).
.venv/bin/mlflow ui \
  --backend-store-uri "sqlite:///<store path from step 1>" \
  --host 127.0.0.1 --port 5123

# 3. Re-capture (in another shell). PLAYWRIGHT_MODULE is only needed if
#    Playwright is not installed in the current Node project.
PLAYWRIGHT_MODULE=/path/to/node_modules/playwright node docs/demo/shoot.js
```

`shoot.js` resolves each target's original trace prefix through
`trace_map.json`, so a fresh copy does not require editing the script.
`MLFLOW_UI_URL` and `MLFLOW_EXPERIMENT_ID` can override the defaults if the UI
runs elsewhere or the copied experiment gets a different ID. To recapture only
a subset, pass comma-separated trace prefixes via `SHOOT_ONLY`:

```bash
# The five tool-call shots:
SHOOT_ONLY=218c33b9,8f166650,1dd34cbc,9f9dab49,ba8b262c node docs/demo/shoot.js
# The four new RAG + A/B shots (three trace prefixes; 14 and 15 share one):
SHOOT_ONLY=e7540806,e96d66aa,72afbaf9 node docs/demo/shoot.js
```

The deck references these files with relative paths, so open
`DEMO_DECK.html` from the repository root (or serve the repo over HTTP) —
do not move the `screenshots/` directory.
