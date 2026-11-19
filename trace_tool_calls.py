#!/usr/bin/env python3
"""
F-011: Tool-call tracing — prove what the agent did, not just what it said.

Runs five scenarios through the *real* LangGraph agent runtime with autologging
enabled. Model decisions are scripted (a fake chat model emits AIMessage tool
calls) so every failure mode is deterministic; the weather service is a stub.
The user request and the advertised tool catalog are identical in all five
cases — only the scripted decision and the tool wrapper change.

After export, each trace is fetched by ID and asserted directly against its
spans. No LLM judge is called: advertised schemas are read from the
`mlflow.chat.tools` span attribute, with in-process tool discovery as fallback.
A trace-ID manifest is written only if all five cases pass.

Usage:
  python trace_tool_calls.py
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

USER_REQUEST = "What is the current weather and cloud cover in SF?"
EXPECTED_TOOLS = ("get_weather", "get_temperature")
MANIFEST_PATH = Path("docs/demo/tool_call_manifest.json")

# Manifest order is significant: experiment 012 asserts the exact-match
# acceptance sequence yes, no, no, no, no against this order.
CASES = (
    "tool_happy",
    "tool_no_call",
    "tool_wrong_tool",
    "tool_wrong_args",
    "tool_retry_storm",
)

EXPECTED_CALLS = {
    "tool_happy": [("get_weather", {"city": "SF"})],
    "tool_no_call": [],
    "tool_wrong_tool": [("get_temperature", {"city": "SF"})],
    "tool_wrong_args": [("get_weather", {"city": "NYC"})],
    "tool_retry_storm": [("get_weather", {"city": "SF"})] * 3,
}


def _tool_call(name: str, args: dict, call_id: str):
    from langchain_core.messages import AIMessage

    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _final_answer() -> object:
    from langchain_core.messages import AIMessage

    return AIMessage(content="It might be cloudy in SF.")


def _script(case: str) -> list:
    """Scripted model decisions for one case; the final message ends the agent loop."""
    if case == "tool_happy":
        return [_tool_call("get_weather", {"city": "SF"}, "h1"), _final_answer()]
    if case == "tool_no_call":
        # Answer from memory: no tool call, but both tools stay advertised.
        return [_final_answer()]
    if case == "tool_wrong_tool":
        return [_tool_call("get_temperature", {"city": "SF"}, "w1"), _final_answer()]
    if case == "tool_wrong_args":
        # Inject NYC into the tool-call arguments *before* the traced invocation.
        # LangChain records args at tool entry, so rewriting the city inside the
        # tool body would leave "SF" in the span. The decision itself must carry NYC.
        return [_tool_call("get_weather", {"city": "NYC"}, "a1"), _final_answer()]
    if case == "tool_retry_storm":
        # Three distinct tool-call messages -> three TOOL spans. Calling the fake
        # service three times inside one tool body would produce a single span.
        # All three succeed on purpose: the efficiency rubric permits retries
        # after transient failures, so only redundant success is a defect.
        calls = [_tool_call("get_weather", {"city": "SF"}, f"r{i}") for i in range(3)]
        return calls + [_final_answer()]
    raise ValueError(f"unknown case: {case}")


def _parse_chat_tools(raw) -> list[dict]:
    """Normalize the mlflow.chat.tools attribute (JSON string or Python literal)."""
    if not raw:
        return []
    if isinstance(raw, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(raw)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, SyntaxError):
                continue
        return []
    return raw if isinstance(raw, list) else []


def _schema_names(schemas: list[dict]) -> list[str]:
    names = []
    for schema in schemas:
        if isinstance(schema, dict):
            fn = schema.get("function") or schema
            if isinstance(fn, dict) and fn.get("name"):
                names.append(fn["name"])
    return names


def _user_text(inputs) -> str | None:
    """Extract the first user message from a root/LangGraph span's inputs."""
    if not isinstance(inputs, dict):
        return None
    messages = inputs.get("messages") or []
    for msg in messages:
        if isinstance(msg, (list, tuple)) and len(msg) > 1 and msg[0] in {"user", "human"}:
            return str(msg[1])
        if isinstance(msg, dict) and msg.get("role") in {"user", "human"}:
            return str(msg.get("content"))
    if inputs.get("user"):
        return str(inputs["user"])
    return None


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
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.runnables import RunnableBinding
    from langchain_core.tools import tool
    from langchain_core.utils.function_calling import convert_to_openai_tool
    from pydantic import Field

    class ScriptedChatModel(GenericFakeChatModel):
        """Real chat-model interface, deterministic decisions, recorded tool catalog."""

        advertised: list = Field(default_factory=list)

        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            schemas = [convert_to_openai_tool(t) for t in tools]
            self.advertised = schemas
            # Returning a RunnableBinding passes `tools` into invocation_params,
            # so autolog records the advertised schemas as mlflow.chat.tools.
            return RunnableBinding(bound=self, kwargs={"tools": schemas})

    def fake_weather_service(city: str) -> str:
        return f"It might be cloudy in {city}"

    def fake_temperature_service(city: str) -> str:
        return f"It is 20C in {city}"

    @tool
    def get_weather(city: str) -> str:
        """Get current weather and cloud cover for a city."""
        return fake_weather_service(city)

    @tool
    def get_temperature(city: str) -> str:
        """Get the current temperature for a city."""
        return fake_temperature_service(city)

    tools = [get_weather, get_temperature]
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")
    session_id = f"lab-f011-{int(time.time())}"

    mlflow.langchain.autolog()
    mlflow.set_tracking_uri("databricks")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        print(f"Experiment not found: {experiment_name}", file=sys.stderr)
        return 2
    mlflow.set_experiment(experiment_name)

    generated: dict[str, dict] = {}
    for case in CASES:
        model = ScriptedChatModel(messages=iter(_script(case)))
        agent = create_agent(model, tools)
        with mlflow.start_span(name=f"tool_case_{case}", span_type="CHAIN") as root:
            mlflow.update_current_trace(tags={
                "lab_book": "F-015",
                "scenario": "tool_calls",
                "tool_case": case,
                "session_id": session_id,
            })
            result = agent.invoke({"messages": [("user", USER_REQUEST)]})
            answer = result["messages"][-1].content
            root.set_inputs({"tool_case": case, "user": USER_REQUEST})
            root.set_outputs({"answer": answer})
            trace_id = root.trace_id
        mlflow.flush_trace_async_logging()
        generated[case] = {
            "trace_id": trace_id,
            "answer": answer,
            "fallback_schemas": model.advertised,
        }
        print(f"{case:<18} trace={trace_id} answer={answer!r}")

    # --- Fetch every trace back by ID and verify it before writing the manifest ---
    manifest_cases = []
    problems = []
    for case in CASES:
        info = generated[case]
        trace_id = info["trace_id"]
        try:
            trace = mlflow.get_trace(trace_id)
        except Exception as exc:  # noqa: BLE001 - a missing trace must fail the script
            problems.append(f"{case}: cannot fetch trace {trace_id}: {type(exc).__name__}: {exc}")
            continue

        tags = trace.info.tags or {}
        for key, expected in (
            ("scenario", "tool_calls"),
            ("tool_case", case),
            ("session_id", session_id),
        ):
            if tags.get(key) != expected:
                problems.append(f"{case}: tag {key}={tags.get(key)!r}, expected {expected!r}")

        spans = trace.data.spans
        root = next((s for s in spans if s.parent_id is None), None)
        if root is None:
            problems.append(f"{case}: no root span")
            continue
        observed_request = _user_text(root.inputs)
        if observed_request != USER_REQUEST:
            problems.append(f"{case}: root request {observed_request!r}, expected {USER_REQUEST!r}")

        # Advertised schemas, read directly from the trace. Fallback tool
        # discovery uses the catalog recorded on the fake model at bind time —
        # still zero judge calls.
        observed_tool_names: list[str] = []
        chat_spans = [s for s in spans if s.span_type == "CHAT_MODEL"]
        for span in chat_spans:
            names = _schema_names(_parse_chat_tools(span.attributes.get("mlflow.chat.tools")))
            if not names:
                names = _schema_names(info["fallback_schemas"])
            if set(names) != set(EXPECTED_TOOLS):
                problems.append(
                    f"{case}: advertised tools on {span.name}={names}, expected {list(EXPECTED_TOOLS)}"
                )
            observed_tool_names.extend(names)
        if not chat_spans:
            problems.append(f"{case}: no CHAT_MODEL span to verify advertised tools")

        tool_spans = [s for s in spans if s.span_type == "TOOL"]
        observed_calls = []
        for span in tool_spans:
            inputs = span.inputs if isinstance(span.inputs, dict) else {}
            status = span.status.status_code.value if span.status else None
            outputs = span.outputs if isinstance(span.outputs, dict) else {}
            observed_calls.append((span.name, inputs.get("city"), status, bool(outputs.get("content"))))

        expected_calls = EXPECTED_CALLS[case]
        if len(observed_calls) != len(expected_calls):
            problems.append(
                f"{case}: {len(observed_calls)} TOOL spans, expected {len(expected_calls)}"
            )
        for index, ((want_name, want_args), observed) in enumerate(zip(expected_calls, observed_calls)):
            got_name, got_city, status, has_content = observed
            if got_name != want_name or got_city != want_args["city"]:
                problems.append(
                    f"{case} call {index}: got {got_name}(city={got_city!r}), "
                    f"expected {want_name}(city={want_args['city']!r})"
                )
            if status != "OK" or not has_content:
                problems.append(
                    f"{case} call {index}: outcome status={status} content={has_content}, expected OK/content"
                )

        manifest_cases.append({
            "case": case,
            "trace_id": trace_id,
            "advertised_tools": sorted(set(observed_tool_names)),
            "tool_calls": [
                {"name": name, "city": city, "status": status, "has_content": has_content}
                for name, city, status, has_content in observed_calls
            ],
        })

    # --- Expected vs observed table ---
    print("\n=== Experiment 011: expected vs observed spans ===")
    for entry in manifest_cases:
        case = entry["case"]
        expected = EXPECTED_CALLS[case]
        observed = [
            f"{c['name']}(city={c['city']!r},{c['status']})" for c in entry["tool_calls"]
        ] or ["<none>"]
        print(f"  {case:<18} expected={expected!s:<70} observed={observed}")

    if problems:
        print("\nFAIL: tool-call trace verification failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("Manifest was NOT written.", file=sys.stderr)
        return 1

    payload = {
        "experiment": experiment_name,
        "experiment_id": experiment.experiment_id,
        "lab_book": "F-015",
        "session_id": session_id,
        "user_request": USER_REQUEST,
        "advertised_tools": list(EXPECTED_TOOLS),
        "cases": manifest_cases,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nAll 5 cases verified. Manifest written: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
