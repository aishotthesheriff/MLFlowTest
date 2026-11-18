#!/usr/bin/env python3
"""
F-007: Error/failure tracing.

Exercises three failure modes and verifies how MLflow records them:
  A. Tool raises an exception, agent handles it and responds.
  B. Manual @mlflow.trace function raises an unhandled exception.
  C. Manual span explicitly records an exception + ERROR status without raising.

Usage:
  python trace_errors.py
"""

from __future__ import annotations

import os
import sys
import time

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
    from mlflow.entities import SpanStatusCode

    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    endpoint = os.getenv("DATABRICKS_MODEL_ENDPOINT", "databricks-gpt-oss-20b")
    session_id = f"lab-f007-{int(time.time())}"

    mlflow.langchain.autolog()
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_name)

    model = ChatDatabricks(model=endpoint, temperature=0.1, max_tokens=500)

    def tag_trace(case: str) -> None:
        mlflow.update_current_trace(tags={
            "lab_book": "F-007",
            "scenario": "error_tracing",
            "session_id": session_id,
            "case": case,
        })

    # --- Case A: tool raises, agent handles it ---
    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        raise RuntimeError(f"Weather service unavailable for {city}")

    @mlflow.trace(name="case_a_tool_error", span_type="CHAIN")
    def case_a() -> str:
        tag_trace("A_tool_error")
        agent = create_agent(model, [get_weather])
        result = agent.invoke({
            "messages": [("user", "Use the get_weather tool to check the weather in SF.")]
        })
        return result["messages"][-1].content

    # --- Case B: unhandled exception in a manual traced function ---
    @mlflow.trace(name="case_b_unhandled_exception", span_type="CHAIN")
    def case_b() -> str:
        tag_trace("B_unhandled_exception")
        raise ValueError("intentional unhandled failure for F-007")

    # --- Case C: explicit record_exception + ERROR status, no raise ---
    @mlflow.trace(name="case_c_explicit_error", span_type="CHAIN")
    def case_c() -> str:
        tag_trace("C_explicit_error")
        with mlflow.start_span(name="manual_failure", span_type="CHAIN") as span:
            span.set_inputs({"operation": "simulated_payment"})
            span.record_exception(TimeoutError("simulated downstream timeout"))
            span.set_status(SpanStatusCode.ERROR)
            span.set_outputs({"result": None, "error": "timeout"})
        return "handled simulated failure"

    cases = [
        ("A_tool_error", case_a),
        ("B_unhandled_exception", case_b),
        ("C_explicit_error", case_c),
    ]
    for name, fn in cases:
        print(f"--- {name} ---")
        trace_id = None
        try:
            result = fn()
            trace_id = mlflow.get_last_active_trace_id()
            print(f"  result: {result}")
        except Exception as exc:
            trace_id = mlflow.get_last_active_trace_id()
            print(f"  raised: {type(exc).__name__}: {exc}")
        mlflow.flush_trace_async_logging()
        print(f"  trace: {trace_id}")
        print()

    print(f"Session ID: {session_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
