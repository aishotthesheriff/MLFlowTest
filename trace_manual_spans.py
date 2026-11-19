#!/usr/bin/env python3
"""
F-003: Manual/custom MLflow spans for non-autologged pre/post-processing.

Adds an outer application-boundary span plus explicit preprocessing and
postprocessing spans around the same Databricks-FM agent used in the
autolog-only baseline (trace_example.py). Autolog still captures the agent,
model, and tool spans; manual spans cover work autolog cannot see.

Based on:
https://docs.databricks.com/aws/en/mlflow3/genai/tracing/manual-tracing

Usage:
  python trace_manual_spans.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from lab_tags import base_tags


CITY_NAMES = {"SF": "San Francisco", "NYC": "New York"}


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

    mlflow.langchain.autolog()  # agent / model / tool spans
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_name)

    model = ChatDatabricks(model=endpoint, temperature=0.1, max_tokens=500)

    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"It might be cloudy in {city}"

    agent = create_agent(model, [get_weather])

    # --- Manual spans: work that autologging cannot see ---

    @mlflow.trace(name="build_user_prompt", span_type="PARSER",
                  attributes={"component": "preprocessing", "step": "prompt_construction"})
    def build_user_prompt(city: str) -> str:
        """Normalize the city code and construct the user prompt."""
        display_name = CITY_NAMES.get(city.upper(), city)
        return f"What is the weather in {display_name}?"

    @mlflow.trace(name="format_response", span_type="PARSER",
                  attributes={"component": "postprocessing", "step": "response_formatting"})
    def format_response(text: str) -> str:
        """Apply presentation formatting to the agent output."""
        return "Answer: " + text.strip()

    @mlflow.trace(name="weather_assistant", span_type="CHAIN",
                  attributes={"component": "application_boundary", "lab_experiment": "F-003"})
    def run_weather_assistant(city: str) -> str:
        """Application boundary: capture the full request/response explicitly."""
        mlflow.update_current_trace(tags=base_tags(
            "F-003", "manual_spans", model_endpoint=endpoint,
        ))
        prompt = build_user_prompt(city)
        result = agent.invoke({"messages": [("user", prompt)]})
        answer = result["messages"][-1].content
        return format_response(answer)

    final_answer = run_weather_assistant("SF")

    # Flush the async trace queue so this run is persisted before we capture its ID.
    mlflow.flush_trace_async_logging()
    trace_id = mlflow.get_last_active_trace_id()

    print(f"Model endpoint: {endpoint}")
    print("Agent response:")
    print(final_answer)
    print()
    print(f"Tracing enabled. View traces in Databricks Experiments UI for: {experiment_name}")
    print("Open: Experiments -> select experiment -> Traces tab")
    if trace_id:
        print(f"Trace ID for this run: {trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
