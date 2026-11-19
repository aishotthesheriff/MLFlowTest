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

import argparse
import os
import sys

from dotenv import load_dotenv

from lab_tags import base_tags


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", help="A/B arm label; tags the generated trace with it")
    parser.add_argument("--endpoint", help="Foundation Model endpoint (overrides env/default)")
    parser.add_argument("--prompt", help="User message (default: the lab's weather question)")
    args = parser.parse_args()

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
    endpoint = args.endpoint or os.getenv("DATABRICKS_MODEL_ENDPOINT", "databricks-gpt-oss-20b")
    prompt = args.prompt or "What is the weather in SF?"

    mlflow.langchain.autolog()  # LangGraph/LangChain uses LangChain's autolog
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_name)

    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"It might be cloudy in {city}"

    model = ChatDatabricks(model=endpoint, temperature=0.1, max_tokens=500)
    agent = create_agent(model, [get_weather])
    result = agent.invoke({"messages": [("user", prompt)]})

    # Flush the async trace queue so this run is persisted before we capture its ID.
    mlflow.flush_trace_async_logging()
    trace_id = mlflow.get_last_active_trace_id()
    if trace_id:
        # Autolog owns the root span here, so tag the finished trace by ID
        # instead of adding a wrapper span that would change its structure.
        extras = {"model_endpoint": endpoint}
        if args.variant:
            extras["variant"] = args.variant
        for key, value in base_tags("F-001", "baseline", **extras).items():
            mlflow.set_trace_tag(trace_id, key, value)

    print(f"Model endpoint: {endpoint}")
    if args.variant:
        print(f"Variant: {args.variant}")
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
