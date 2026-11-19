# Experiment 014 — RAG retrieval tracing on Databricks AI Search (F-006)

- **Date:** 2026-11-19
- **Owner:** lab
- **Status:** Completed
- **Related idea(s):** F-006
- **Prior experiment(s):** 013 (harness patterns), 003 (manual spans), 010 (canonical tags)

## 1. Objective & hypothesis

**Question:** Do retrieval steps appear as trace spans with enough input/output detail to debug relevance, when the vector store and embeddings both live on Databricks?

**Hypothesis:** A manually traced RAG path (embed → vector search → generate) produces a RETRIEVER span whose inputs carry the query/top_k and whose outputs carry ranked doc ids and scores, so a wrong retrieval is diagnosable from the trace alone.

**Success criteria:** Three query cases export and persist; each trace has CHAIN/EMBEDDING/RETRIEVER/LLM spans with canonical tags; the expected top document is first for each case; a manifest is written only after all traces verify.

## 2. Setup

- **Code/scripts:** `rag_corpus.py`, `setup_rag_index.py`, `trace_rag.py`
- **Commands:**
  ```bash
  python setup_rag_index.py
  python trace_rag.py
  ```
- **Environment:** Python 3.15.2 venv, `databricks-sdk`, MLflow 3.18.0
- **Databricks:** workspace auth from `~/.databrickscfg`; SQL warehouse for schema/table DDL
- **MLflow experiment:** `/Shared/my-first-trace` (`MLFLOW_EXPERIMENT_NAME` overrides)
- **Embedding endpoint:** `databricks-gte-large-en`
- **Chat endpoint:** `databricks-gpt-oss-20b`
- **Vector store:** AI Search endpoint `mlflow_lab_vec`; UC index `workspace.mlflow_lab.weather_docs_index` (Delta Sync, managed embeddings, TRIGGERED pipeline)
- **Corpus:** 12 weather documents in `rag_corpus.DOCS`; 3 query cases in `rag_corpus.QUERY_CASES`
- **Tags:** `lab_book=F-006`, `scenario=rag_retrieval`, plus `query_case`, `model_endpoint`, `index`

## 3. Procedure

1. Provision the UC schema and weather-doc Delta table via the SQL warehouse; enable change data feed.
2. Create (or reuse) the standard AI Search endpoint and the Delta Sync index with `content` as the embedding source column.
3. For each query case: embed the query, search the index for the top 3 docs, build a grounded prompt, generate an answer — each stage in its own typed span.
4. Flush each trace, fetch it back by ID, and assert tags, span types, retrieval I/O, and the expected top document.
5. Write `docs/demo/rag_manifest.json` only when all cases pass.

## 4. Results

- **Outcome:** success — 3/3 traces persisted and verified; 3/3 expected top documents retrieved.
- **Traces** (all in `/Shared/my-first-trace`, experiment id `1675992194464286`):

| Case | Trace ID | Latency | Ranked docs (score) |
| --- | --- | --- | --- |
| `sf_current` | `tr-e754080659cb22bee921db7192242ac1` | 5557 ms | sf-current (0.7657), sf-rain (0.6827), sf-wind (0.6581) |
| `nyc_snow` | `tr-de009be8f86449f0cae96e555ed0c73c` | 979 ms | nyc-snow (0.7099), nyc-current (0.5760), sf-rain (0.5500) |
| `tokyo_weather` | `tr-66cb5bafe7c710a681e5203cfc51ce92` | 1110 ms | tokyo-storms (0.7294), london-fog (0.5639), nyc-current (0.5393) |

- **Span shape (verified on every trace):** one `CHAIN` root `rag_query`, with `EMBEDDING` (`embed_query`), `RETRIEVER` (`retrieve_docs`) and `LLM` (`generate_answer`) children.
- **Retriever span inputs:** `{"query": "...", "top_k": 3, "index": "workspace.mlflow_lab.weather_docs_index"}`; **outputs:** ranked `doc_id`/`score` pairs plus `count: 3`.
- **Embedding span outputs:** `{"dimension": 1024}` — confirms the managed embedding model without storing a 1024-float blob in the trace.
- **Tags:** `lab_book=F-006`, `scenario=rag_retrieval`, `query_case`, `model_endpoint`, `index`, plus the canonical `env`/`git_sha`.
- **Answers:** grounded in the retrieved docs; e.g. SF returned "cloudy ... near 14C, high coastal humidity" from `sf-current`.
- **Artifacts:** `docs/demo/rag_manifest.json` (written only after all verifications passed).

## 5. Analysis

- **What happened:** the first query cost 5557 ms because it included endpoint/index compute warm-up; the next two settled under 1.2 s. All three queries ranked the intended document first with a clear score gap to the runner-up (0.08–0.17; the warm-up `sf_current` case was the narrowest), so the corpus and embedding model are well separated for these cases.
- **Why it worked:** a Delta Sync index with a managed embedding source keeps ingestion and query embeddings on the same model (`databricks-gte-large-en`), avoiding train/serve skew. Storing the query, top_k and ranked scores on the RETRIEVER span makes a future relevance mistake attributable to retrieval (wrong docs) versus generation (right docs, wrong answer).
- **Surprises / risks:** endpoint provisioning took several minutes after the endpoint reported ONLINE; queries are rejected until the index reports `ready`. The AI Search endpoint is billable and remains in the workspace. Scores are from one small static corpus, not a relevance benchmark.
- **Comparison to prior runs:** unlike exps 011–012 (scripted tool spans), these retrieval spans are produced by a real external vector store, so the evidence is not a fixture.

## 6. Learnings & decisions

- Direct Access AI Search indexes are unsupported in this workspace (`Vector index type DIRECT_ACCESS is not supported for this workspace`); a Delta Sync index with a managed embedding source is the working design.
- No integration wrapper is enabled: embedding, vector search and prompt assembly are not autologged, so all four spans are explicit `mlflow.start_span` calls — meaningful application work, not re-wrapped framework nodes.
- A `RETRIEVER` span should carry both the query/top_k inputs and the ranked doc ids/scores outputs; that is what turns a trace into a relevance debugging artifact.
- Snowflake was evaluated first and rejected: the trial account blocks legacy `EMBED_TEXT_*` (new accounts) and current `AI_EMBED_*` (trial accounts), and the user chose to keep both embedding and storage on Databricks. No Snowflake lab objects were created.

## 7. Next actions

- [ ] Add a retrieval-relevance scorer that reads the RETRIEVER span outputs and flag a query whose expected doc is missing.
- [ ] Compare embedding models (`gte-large-en` vs `bge-large-en`) by re-pointing `RAG_EMBEDDING_ENDPOINT` and rebuilding the index.
- [ ] Delete the billable `mlflow_lab_vec` endpoint and index when the lab is retired.

## 8. Reproducibility checklist

- [x] Commands and config recorded
- [x] Trace/run identifiers recorded
- [x] Relevant code changes noted (commit/hash if applicable)
- [x] Follow-up ideas added to lab book backlog (if any)
