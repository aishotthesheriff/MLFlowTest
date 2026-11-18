"""Copy real traces from Databricks into a local SQLite MLflow store.

This exists so the MLflow 3 UI can be screenshotted without a Databricks SSO
session: the local server authenticates with ~/.databrickscfg on our behalf.
Spans, timings, inputs/outputs, tags and metadata are preserved; MLflow assigns
new trace IDs, which are written to docs/demo/trace_map.json alongside the
originals so the screenshot script can resolve them.
"""
import json
import os
import tempfile

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
from mlflow.tracing.utils.copy import copy_trace_to_experiment

WORK = os.path.join(tempfile.gettempdir(), "mlflowtest-demo-shots")
os.makedirs(WORK, exist_ok=True)
DB_PATH = os.path.join(WORK, "mlflow.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
LOCAL_URI = "sqlite:///" + DB_PATH
EXPERIMENT = "/Shared/my-first-trace"

# Read the real traces from Databricks.
mlflow.set_tracking_uri("databricks")
source_exp = mlflow.get_experiment_by_name(EXPERIMENT)
assert source_exp, f"missing source experiment {EXPERIMENT}"
source_traces = mlflow.search_traces(
    locations=[source_exp.experiment_id], max_results=1000, return_type="list"
)
print(f"source traces: {len(source_traces)}")

# Write them into a local store that the MLflow UI can serve read-only.
mlflow.set_tracking_uri(LOCAL_URI)
mlflow.set_experiment(EXPERIMENT)
local_exp = mlflow.get_experiment_by_name(EXPERIMENT)
assert local_exp, "failed to create local experiment"

mapping = []
for t in source_traces:
    old_id = t.info.trace_id
    new_id = copy_trace_to_experiment(t.to_dict(), experiment_id=local_exp.experiment_id)
    mapping.append(
        {
            "old_id": old_id,
            "new_id": new_id,
            "name": t.data.spans[0].name if t.data.spans else "",
            "status": t.info.status,
            "spans": len(t.data.spans),
        }
    )
mlflow.flush_trace_async_logging()

with open(os.path.join(os.path.dirname(__file__), "trace_map.json"), "w") as f:
    json.dump(mapping, f, indent=2)

local_traces = mlflow.search_traces(
    locations=[local_exp.experiment_id], max_results=1000, return_type="list"
)
print(f"local traces: {len(local_traces)}")
print(f"local experiment id: {local_exp.experiment_id}")
print(f"store: {DB_PATH}")
