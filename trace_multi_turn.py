#!/usr/bin/env python3
"""
F-005: Multi-turn conversation tracing.

Runs a 3-turn conversation with shared message history, groups all turns under
one MLflow session_id, and captures per-turn inputs/outputs. Verifies:
- session/thread grouping of traces
- per-turn I/O and context growth
- cross-turn recall (turn 3 references turn 1)

Usage:
  python trace_multi_turn.py
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv


TURNS = [
    "What is the weather in SF?",
    "What about NYC?",                    # relies on turn 1 context (weather)
    "Which city did I ask about first?",  # relies on conversation history
]


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
    session_id = f"lab-f005-{int(time.time())}"

    mlflow.langchain.autolog()
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_name)

    model = ChatDatabricks(model=endpoint, temperature=0.1, max_tokens=500)

    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"It might be cloudy in {city}"

    agent = create_agent(model, [get_weather])
    history: list[tuple[str, str]] = []
    trace_ids: list[str] = []

    for turn_number, user_text in enumerate(TURNS, start=1):
        history.append(("user", user_text))
        with mlflow.start_span(name=f"turn_{turn_number}", span_type="CHAIN") as span:
            mlflow.update_current_trace(
                session_id=session_id,
                tags={
                    "lab_book": "F-005",
                    "scenario": "multi_turn",
                    "session_id": session_id,
                    "turn": str(turn_number),
                },
            )
            result = agent.invoke({"messages": history})
            answer = result["messages"][-1].content
            history.append(("assistant", answer))

            span.set_inputs({
                "turn": turn_number,
                "user": user_text,
                "history_messages_before": len(history) - 2,
            })
            span.set_outputs({"answer": answer})
            span.set_attributes({
                "component": "conversation_turn",
                "session_id": session_id,
                "turn": turn_number,
            })
            # Capture the ID from the live span; get_last_active_trace_id() only
            # returns completed traces and would be off by one inside the span.
            trace_id = span.trace_id

        mlflow.flush_trace_async_logging()
        trace_ids.append(trace_id)

        print(f"Turn {turn_number}: {user_text}")
        print(f"  -> {answer}")
        print(f"  trace: {trace_id}")
        print()

    print(f"Session ID: {session_id}")
    print(f"Traces captured: {len(trace_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
