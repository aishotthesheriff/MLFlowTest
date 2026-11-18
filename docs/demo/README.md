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
on copy. `trace_map.json` records `old_id` → `new_id` for all 34 traces, so each
screenshot can be traced back to the Databricks original cited in
[LAB_BOOK.md](../LAB_BOOK.md). The six cited mappings are:

| Screenshot | Databricks original | Local copy |
| --- | --- | --- |
| 02 baseline | `tr-054cbbc9de1d27ba20aec517e6cda4eb` | `tr-ee8cf68fbe82ea628f5bc5599b2526d1` |
| 03 manual spans | `tr-0cb5f6d26d3dad7fc32c9da9cad10131` | `tr-c2c963345996b3b8829870f55e0c48d9` |
| 04 turn 3 | `tr-6f99921de8fc0c0f8f0271392f7bb606` | `tr-30fe163b1895fbf03ffc30ee189fd380` |
| 05 tool error | `tr-cbd09f84a14aa356cfffb614bb4583c0` | `tr-651bee5671295a29be3a4c6b2ec8729f` |
| 06 unhandled | `tr-3dbea41e598c727874df4a43ed18e897` | `tr-f53de5648d3b7f9ceed011b4c70b702e` |
| 07 handled | `tr-193c937a2ab7790e06969f4bb3730a85` | `tr-1c0d8c12605f1c535f474129f66387cb` |

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

All captures are 3200 × 1800 (1600 × 900 viewport at 2× device scale).

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
runs elsewhere or the copied experiment gets a different ID.

The deck references these files with relative paths, so open
`DEMO_DECK.html` from the repository root (or serve the repo over HTTP) —
do not move the `screenshots/` directory.
