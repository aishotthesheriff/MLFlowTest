#!/usr/bin/env python3
"""F-006: provision and seed the Databricks AI Search vector store.

Creates, idempotently:

* UC schema ``workspace.mlflow_lab`` (via the workspace SQL warehouse)
* standard AI Search endpoint ``mlflow_lab_vec`` (if absent)
* Delta table ``workspace.mlflow_lab.weather_docs`` with change data feed
* Delta Sync index ``workspace.mlflow_lab.weather_docs_index``; Databricks
  computes the embeddings from ``content`` with ``databricks-gte-large-en``

Using a managed-embedding Delta Sync index keeps the whole vector store on
Databricks: no locally generated vectors and no external vector service.
Re-running the script re-seeds the same documents from ``rag_corpus.DOCS`` and
syncs the index.

Usage:
  python setup_rag_index.py
"""

from __future__ import annotations

import argparse
import os
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn,
    EndpointType,
    PipelineType,
    VectorIndexType,
)

from rag_corpus import DOCS

DEFAULT_ENDPOINT = "mlflow_lab_vec"
DEFAULT_INDEX = "workspace.mlflow_lab.weather_docs_index"
DEFAULT_EMBEDDING_ENDPOINT = "databricks-gte-large-en"
SCHEMA_NAME = "workspace.mlflow_lab"
TABLE_NAME = "workspace.mlflow_lab.weather_docs"


def _sql(ws: WorkspaceClient, statement: str) -> None:
    warehouses = list(ws.warehouses.list())
    if not warehouses:
        raise RuntimeError("no SQL warehouse available for the lab schema/table")
    warehouse_id = os.getenv("MLFLOW_LAB_WAREHOUSE_ID") or warehouses[0].id
    response = ws.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s"
    )
    state = str(getattr(response.status.state, "value", response.status.state))
    if state != "SUCCEEDED":
        raise RuntimeError(f"SQL failed ({state}): {getattr(response.status, 'error', None)}")


def _ensure_endpoint(ws: WorkspaceClient, name: str) -> None:
    if name in {e.name for e in ws.vector_search_endpoints.list_endpoints()}:
        print(f"endpoint already exists: {name}")
        return
    try:
        # The SDK sometimes raises KeyError while parsing the create response
        # although the endpoint was created; the list check is authoritative.
        ws.vector_search_endpoints.create_endpoint(name, EndpointType.STANDARD)
    except KeyError:
        pass
    if name not in {e.name for e in ws.vector_search_endpoints.list_endpoints()}:
        raise RuntimeError(f"endpoint was not created: {name}")
    ws.vector_search_endpoints.wait_get_endpoint_vector_search_endpoint_online(name)
    print(f"endpoint ready: {name}")


def _seed_table(ws: WorkspaceClient) -> None:
    _sql(ws, f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
    _sql(
        ws,
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
              doc_id STRING NOT NULL,
              title STRING,
              content STRING
            )
            TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')""",
    )
    _sql(ws, f"DELETE FROM {TABLE_NAME}")
    values = ",\n".join(
        "('{}', '{}', '{}')".format(
            doc["doc_id"].replace("'", "''"),
            doc["title"].replace("'", "''"),
            doc["content"].replace("'", "''"),
        )
        for doc in DOCS
    )
    _sql(ws, f"INSERT INTO {TABLE_NAME} (doc_id, title, content) VALUES\n{values}")
    print(f"seeded {len(DOCS)} weather documents into {TABLE_NAME}")


def _index_exists(ws: WorkspaceClient, name: str) -> bool:
    try:
        ws.vector_search_indexes.get_index(name)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("RAG_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--index", default=os.getenv("RAG_INDEX", DEFAULT_INDEX))
    parser.add_argument(
        "--embedding-endpoint",
        default=os.getenv("RAG_EMBEDDING_ENDPOINT", DEFAULT_EMBEDDING_ENDPOINT),
    )
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    ws = WorkspaceClient()

    _ensure_endpoint(ws, args.endpoint)
    _seed_table(ws)

    created = not _index_exists(ws, args.index)
    if created:
        ws.vector_search_indexes.create_index(
            name=args.index,
            endpoint_name=args.endpoint,
            primary_key="doc_id",
            index_type=VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
                source_table=TABLE_NAME,
                columns_to_sync=["doc_id", "title", "content"],
                embedding_source_columns=[
                    EmbeddingSourceColumn(
                        name="content",
                        embedding_model_endpoint_name=args.embedding_endpoint,
                    )
                ],
                pipeline_type=PipelineType.TRIGGERED,
            ),
        )
        print(f"index created: {args.index}")
    ws.vector_search_indexes.sync_index(args.index)
    print(f"index synced: {args.index}")

    print(f"endpoint: {args.endpoint} | embedding model: {args.embedding_endpoint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
