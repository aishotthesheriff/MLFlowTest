#!/usr/bin/env python3
"""
Minimal MLflow 3 GenAI tracing example for Databricks.

Uses a Databricks Foundation Model API endpoint (no external LLM key required)
and sends traces to a Databricks workspace using MLflow autologging.

Based on:
https://docs.databricks.com/aws/en/mlflow3/genai/tracing/overview

Prereqs:
- Databricks auth configured (DATABRICKS_HOST + DATABRICKS_TOKEN, or ~/.databrickscfg)
- A reachable Foundation Model serving endpoint (default: databricks-gpt-oss-20b)

Usage:
  python trace_example.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    if not (os.getenv("DATABRICKS_HOST") or os.path.exists(os.path.expanduser("~/.databrickscfg"))):
        print(
            "Missing Databricks config. Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env "
            "(see .env.example) or configure ~/.databrickscfg.",
            file=sys.stderr,
        )
        return 2

    import mlflow
    from databricks_langchain import ChatDatabricks
    from langchain.agents import create_agent
    from langchain_core.tools import tool

    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    endpoint = os.getenv("DATABRICKS_MODEL_ENDPOINT", "databricks-gpt-oss-20b")

    mlflow.langchain.autolog()  # LangGraph/LangChain uses LangChain's autolog
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_name)

    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"It might be cloudy in {city}"

    model = ChatDatabricks(model=endpoint, temperature=0.1, max_tokens=500)
    agent = create_agent(model, [get_weather])
    result = agent.invoke({"messages": [("user", "What is the weather in SF?")]})

    # Flush the async trace queue so this run is persisted before we capture its ID.
    mlflow.flush_trace_async_logging()
    trace_id = mlflow.get_last_active_trace_id()

    print(f"Model endpoint: {endpoint}")
    print("Agent response:")
    print(result["messages"][-1].content)
    print()
    print(f"Tracing enabled. View traces in Databricks Experiments UI for: {experiment_name}")
    print("Open: Experiments -> select experiment -> Traces tab")
    if trace_id:
        print(f"Trace ID for this run: {trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
