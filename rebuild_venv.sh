#!/usr/bin/env bash
# Reproducibly build (or repair) the MLFlowTest environment from requirements.lock.txt.
# Usage: ./rebuild_venv.sh [VENV_PATH]   (default: .venv)
# An existing venv is updated in place; it is never deleted. Use a different path
# (e.g. /tmp/verify-venv) to verify the lock without touching the working venv.
set -euo pipefail

cd "$(dirname "$0")"
VENV="${1:-.venv}"

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating $VENV with $(python3 --version)"
  python3 -m venv "$VENV"
fi

echo "Installing exact versions from requirements.lock.txt (--no-deps is intentional)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet --no-deps -r requirements.lock.txt

echo "Smoke-checking imports and versions"
MLFLOW_DISABLE_AGENT_HINT=1 "$VENV/bin/python" - <<'PY'
from importlib.metadata import version

import mlflow  # noqa: F401
import langchain  # noqa: F401
import langgraph  # noqa: F401
import langchain_openai  # noqa: F401
from databricks_langchain import ChatDatabricks  # noqa: F401
from langchain.agents import create_agent  # noqa: F401

expected = {
    "mlflow": "3.18.0",
    "langgraph": "1.2.22",
    "langchain": "1.5.1",
    "langchain-openai": "1.8.1",
    "databricks-langchain": "0.22.0",
    "python-dotenv": "1.2.4",
    "numpy": "2.5.5",
    "scipy": "1.18.1",
    "PyYAML": "6.0.3",
}
for name, want in expected.items():
    got = version(name)
    assert got == want, f"{name}: expected {want}, got {got}"
print("OK:", ", ".join(f"{k}=={v}" for k, v in expected.items()))
PY

echo "Environment ready at $VENV"
echo "Next: cp .env.example .env (if needed), then ./start_demo.sh --check-only"
