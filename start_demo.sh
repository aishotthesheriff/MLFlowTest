#!/usr/bin/env bash
# MLFlowTest demo launcher: read-only preflight, then open the deck and Databricks Traces tab.
# Usage: ./start_demo.sh [--check-only] [--no-open]
set -euo pipefail
cd "$(dirname "$0")"

CHECK_ONLY=0
NO_OPEN=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    --no-open) NO_OPEN=1 ;;
    -h|--help) echo "usage: ./start_demo.sh [--check-only] [--no-open]"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "FAIL: .venv/bin/python missing — create the venv first (see README.md)" >&2
  exit 1
fi

echo "== MLFlowTest demo preflight =="
MLFLOW_DISABLE_AGENT_HINT=1 "$PY" - <<'PY'
import sys
import mlflow

EXPERIMENT = "/Shared/my-first-trace"
EXPECTED_TRACES = [
    "054cbbc9", "0cb5f6d2", "e07c3271", "66e408aa", "6f99921d",
    "cbd09f84", "3dbea41e", "193c937a",
]
EXPECTED_SCORERS = {"relevance_to_query", "answers_expected_city", "response_length"}

failures = []
try:
    mlflow.set_tracking_uri("databricks")
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if not exp:
        failures.append(f"experiment not found: {EXPERIMENT}")
    else:
        print(f"OK  experiment: {EXPERIMENT} ({exp.experiment_id})")
        mlflow.set_experiment(EXPERIMENT)
        traces = mlflow.search_traces(locations=[exp.experiment_id], max_results=1000, return_type="list")
        ids = {t.info.trace_id for t in traces}
        missing = [s for s in EXPECTED_TRACES if not any(i.startswith("tr-" + s) for i in ids)]
        if missing:
            failures.append("missing evidence traces: " + ", ".join(missing))
        else:
            print(f"OK  evidence traces: {len(EXPECTED_TRACES)}/{len(EXPECTED_TRACES)} present (experiment has {len(traces)} traces)")
        scorers = {getattr(s, "name", "") for s in mlflow.genai.list_scorers()}
        absent = EXPECTED_SCORERS - scorers
        if absent:
            failures.append("unregistered scorers: " + ", ".join(sorted(absent)) + " (run: python evaluate_traces.py --register)")
        else:
            print("OK  scorers: " + ", ".join(sorted(EXPECTED_SCORERS)))
except Exception as exc:  # noqa: BLE001 - preflight should report any auth/API failure
    failures.append(f"{type(exc).__name__}: {exc}")

if failures:
    for f in failures:
        print("FAIL: " + f, file=sys.stderr)
    sys.exit(1)
print("PREFLIGHT PASSED")
PY

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Check-only: no tabs opened."
  exit 0
fi

if [ "$NO_OPEN" -eq 0 ]; then
  open DEMO_DECK.html
  open "https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/traces"
  echo "Opened: DEMO_DECK.html and the Databricks Traces tab."
else
  echo "Skipped opening tabs (--no-open). Open DEMO_DECK.html manually."
fi

cat <<'EOF'

Ready. Run of show (see DEMO_SCRIPT.md):
  1  .venv/bin/python trace_example.py          # live baseline trace
  2  .venv/bin/python trace_manual_spans.py     # manual spans (or show tr-0cb5f6d2...)
  3  .venv/bin/python trace_multi_turn.py       # one session, three turns
  4  .venv/bin/python trace_errors.py           # error signatures
  5  .venv/bin/python analyze_trace_metrics.py  # latency / tokens / cost
     .venv/bin/python evaluate_traces.py --pilot --with-controls  # clean + planted controls
EOF
