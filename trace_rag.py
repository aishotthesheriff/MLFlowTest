#!/usr/bin/env python3
"""F-006: traced RAG retrieval over a Databricks AI Search index.

Each query produces one trace with four explicit spans:

  rag_query (CHAIN) ← embed_query (EMBEDDING) ← retrieve_docs (RETRIEVER)
                    ← generate_answer (LLM)

The retrieval span records the query, top_k, ranked document ids and scores,
so relevance failures can be debugged from the trace alone. No autolog wrapper
is applied: every span here covers work that an integration would not capture
(the embedding call, the vector-store query, and the prompt assembly).

After export, each trace is fetched by ID and asserted against its spans. A
manifest is written only when all cases pass.

Usage:
  python setup_rag_index.py          # once, to provision + seed the index
  python trace_rag.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from dotenv import load_dotenv
from mlflow.entities import SpanType

from lab_tags import base_tags
from rag_corpus import QUERY_CASES

MANIFEST_PATH = Path("docs/demo/rag_manifest.json")
DEFAULT_ENDPOINT = "mlflow_lab_vec"
DEFAULT_INDEX = "workspace.mlflow_lab.weather_docs_index"
DEFAULT_EMBEDDING_ENDPOINT = "databricks-gte-large-en"
DEFAULT_CHAT_ENDPOINT = "databricks-gpt-oss-20b"
TOP_K = 3
READBACK_DEADLINE_S = 60

PROMPT_TEMPLATE = (
    "Answer the question using only the context below. If the context does not "
    "contain the answer, say you do not know.\n\n"
    "Context:\n{context}\n\nQuestion: {query}\n"
)


def _rows(response: object) -> list[dict]:
    """Turn a query_index response into plain dicts using its result manifest."""
    columns = [c.name for c in (response.manifest.columns or [])]
    rows = response.result.data_array or []
    return [dict(zip(columns, row)) for row in rows]


def _embed(ws: WorkspaceClient, query: str) -> list[float]:
    embedded = ws.serving_endpoints.query(
        name=os.getenv("RAG_EMBEDDING_ENDPOINT", DEFAULT_EMBEDDING_ENDPOINT),
        input=[query],
    )
    return list(embedded.data[0].embedding)


def _search(ws: WorkspaceClient, index: str, vector: list[float]) -> list[dict]:
    response = ws.vector_search_indexes.query_index(
        index,
        columns=["doc_id", "title", "content"],
        query_vector=vector,
        num_results=TOP_K,
    )
    return _rows(response)


def _answer(ws: WorkspaceClient, prompt: str) -> str:
    response = ws.serving_endpoints.query(
        name=os.getenv("RAG_CHAT_ENDPOINT", DEFAULT_CHAT_ENDPOINT),
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        max_tokens=128,
        temperature=0,
    )
    return response.choices[0].message.content or ""


def _run_case(ws: WorkspaceClient, case: dict, index: str) -> dict:
    query = case["query"]
    with mlflow.start_span(name="rag_query", span_type=SpanType.CHAIN) as root:
        mlflow.update_current_trace(
            tags=base_tags(
                "F-006",
                "rag_retrieval",
                query_case=case["case"],
                model_endpoint=os.getenv("RAG_CHAT_ENDPOINT", DEFAULT_CHAT_ENDPOINT),
                index=index,
            )
        )
        root.set_inputs({"query": query})

        with mlflow.start_span(name="embed_query", span_type=SpanType.EMBEDDING) as embed:
            embed.set_inputs(
                {"text": query, "model": os.getenv("RAG_EMBEDDING_ENDPOINT", DEFAULT_EMBEDDING_ENDPOINT)}
            )
            vector = _embed(ws, query)
            embed.set_outputs({"dimension": len(vector)})

        with mlflow.start_span(name="retrieve_docs", span_type=SpanType.RETRIEVER) as retrieve:
            retrieve.set_inputs({"query": query, "top_k": TOP_K, "index": index})
            rows = _search(ws, index, vector)
            retrieve.set_outputs(
                {
                    "documents": [
                        {"doc_id": row.get("doc_id"), "score": row.get("score")}
                        for row in rows
                    ],
                    "count": len(rows),
                }
            )

        prompt = PROMPT_TEMPLATE.format(
            context="\n".join(f"- {row['title']}: {row['content']}" for row in rows),
            query=query,
        )
        with mlflow.start_span(name="generate_answer", span_type=SpanType.LLM) as generate:
            generate.set_inputs({"prompt": prompt, "doc_ids": [row.get("doc_id") for row in rows]})
            answer = _answer(ws, prompt)
            generate.set_outputs({"answer": answer})

        root.set_outputs(
            {
                "answer": answer,
                "retrieved_doc_ids": [row.get("doc_id") for row in rows],
            }
        )
        trace_id = root.trace_id

    mlflow.flush_trace_async_logging()
    return {
        "case": case["case"],
        "query": query,
        "expected_doc": case["expected_doc"],
        "retrieved_doc_ids": [row.get("doc_id") for row in rows],
        "answer": answer,
        "trace_id": trace_id,
    }


def _verify(record: dict) -> list[str]:
    """Fetch the persisted trace and assert the retrieval evidence it contains."""
    problems = []
    trace = mlflow.get_trace(record["trace_id"])
    tags = trace.info.tags or {}
    for key, expected in (
        ("lab_book", "F-006"),
        ("scenario", "rag_retrieval"),
        ("query_case", record["case"]),
    ):
        if tags.get(key) != expected:
            problems.append(f"{record['case']}: tag {key}={tags.get(key)!r} != {expected!r}")

    spans = trace.data.spans
    by_type = {span.span_type: span for span in spans}
    for span_type in ("EMBEDDING", "RETRIEVER", "LLM"):
        if span_type not in by_type:
            problems.append(f"{record['case']}: missing {span_type} span")

    retriever = by_type.get("RETRIEVER")
    if retriever is not None:
        inputs = retriever.inputs if isinstance(retriever.inputs, dict) else {}
        outputs = retriever.outputs if isinstance(retriever.outputs, dict) else {}
        if inputs.get("query") != record["query"]:
            problems.append(f"{record['case']}: retriever query {inputs.get('query')!r} differs")
        if inputs.get("top_k") != TOP_K:
            problems.append(f"{record['case']}: retriever top_k={inputs.get('top_k')!r}")
        documents = outputs.get("documents") or []
        if not documents:
            problems.append(f"{record['case']}: retriever returned no documents")
        top_doc = documents[0].get("doc_id") if documents else None
        if top_doc != record["expected_doc"]:
            problems.append(
                f"{record['case']}: top doc {top_doc!r}, expected {record['expected_doc']!r}"
            )

    embedding = by_type.get("EMBEDDING")
    if embedding is not None:
        outputs = embedding.outputs if isinstance(embedding.outputs, dict) else {}
        if outputs.get("dimension") != 1024:
            problems.append(f"{record['case']}: embedding dimension={outputs.get('dimension')!r}")

    answer_span = by_type.get("LLM")
    if answer_span is not None:
        outputs = answer_span.outputs if isinstance(answer_span.outputs, dict) else {}
        if not outputs.get("answer"):
            problems.append(f"{record['case']}: empty LLM span answer")
    return problems


def main() -> int:
    load_dotenv()
    index = os.getenv("RAG_INDEX", DEFAULT_INDEX)
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/my-first-trace")

    mlflow.set_tracking_uri("databricks")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        print(f"Experiment not found: {experiment_name}", file=sys.stderr)
        return 2
    mlflow.set_experiment(experiment_name)

    ws = WorkspaceClient()
    records = []
    for case in QUERY_CASES:
        record = _run_case(ws, case, index)
        records.append(record)
        print(
            f"{record['case']:<14} trace={record['trace_id']} "
            f"docs={record['retrieved_doc_ids']} answer={record['answer']!r}"
        )

    # Backend verification is bounded: one flush already happened per case, so
    # readback should be quick. Stop at the deadline rather than retrying forever.
    started = time.monotonic()
    problems = []
    for record in records:
        if time.monotonic() - started > READBACK_DEADLINE_S:
            problems.append("readback deadline exceeded before all traces were verified")
            break
        try:
            problems.extend(_verify(record))
        except Exception as exc:  # noqa: BLE001 - verification must fail the script
            problems.append(f"{record['case']}: cannot fetch trace: {type(exc).__name__}: {exc}")

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps({"index": index, "cases": records}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"VERIFIED {len(records)} traces; manifest={MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
