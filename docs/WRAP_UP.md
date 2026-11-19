# MLFlowTest Wrap-Up — Databricks MLflow 3 GenAI Tracing Lab

**Date:** 2026-11-19 · **Final commit:** `8ef34f6` · **Experiment:** `/Shared/my-first-trace` (`1675992194464286`)

## 1. Summary

MLFlowTest is a two-day local lab that turns a Databricks LangGraph agent's execution into queryable evidence in MLflow, then measures and scores that evidence — without an external LLM key or a separate observability vendor. Fourteen experiments (001–014, 2026-11-18/19) built a repeatable loop: **trace → inspect → measure → evaluate → document**. The lab proves the mechanics end to end — autolog plus manual spans, session and error traces, first-class latency/token/cost fields, eight registered scorers, planted known-bad controls, a standing A/B regression set, and traced RAG over Databricks AI Search. It does not prove production quality: short weather answers, scripted tool cases, one clean A/B record per arm, and a 12-document RAG corpus.

## 2. Why it exists / goal order

Original mission: produce a traced agent run from a local Python 3.15 venv into a Databricks workspace and measure/score the stored traces, using only workspace auth and a Databricks FM endpoint. With the mission complete, priorities needed an explicit goal; on 2026-11-19 the lab set **reusable demo → learning breadth → judge trust**. High = demo repeatability, Medium = lab breadth, Low = scorer confidence; lower effort first. This order decided what shipped (F-010, F-012, F-014, F-006) and what was dropped (F-004).

## 3. What was built

| Layer | Concrete artifacts |
| --- | --- |
| Tracing | `trace_example.py`, `trace_manual_spans.py`, `trace_multi_turn.py`, `trace_errors.py`, `trace_tool_calls.py`, `trace_rag.py` (CHAIN/EMBEDDING/RETRIEVER/LLM spans) |
| Measurement | `analyze_trace_metrics.py` (latency/token/cost over 17 traces) |
| Evaluation | `evaluate_traces.py` (5 output scorers), `evaluate_tool_calls.py` (3 tool-call configs) — 8 registered scorers |
| Repeatability | `lab_tags.py` (canonical tags), `regression_suite.py` (validate/run/ab/compare), `requirements.txt` (6 pins) + `requirements.lock.txt` (160 packages) + `rebuild_venv.sh` |
| Evidence | 14 writeups in `docs/experiments/`, LAB_BOOK, FINDINGS, manifests in `docs/demo/`, 8-slide `DEMO_DECK.html`, `start_demo.sh --check-only` |

## 4. Evidence ledger — all 14 experiments

| ID | Result (artifact-backed) |
| --- | --- |
| 001 | First trace exported; response "The weather in San Francisco might be cloudy." (OpenAI baseline) |
| 002 | Keyless FM: trace `tr-054cbbc9de1d27ba20aec517e6cda4eb`, 7 spans incl. `ChatDatabricks` + `get_weather`; deprecation fixed |
| 003 | Manual + autolog spans: `tr-0cb5f6d26d3dad7fc32c9da9cad10131`, 10 spans |
| 004 | 3 traces, session `lab-f005-1795028845`; context 0→2→4 msgs; turn 3 recalled SF |
| 005 | 3 error traces: unhandled → trace ERROR + exception events; handled → span ERROR only |
| 006 | 17 traces aggregated; slowest `tr-983651f7eb6bf22274142b9362c21858` (4304 ms); priciest `tr-66e408aab933cac6feb63ec91b042abe` ($0.000121) |
| 007 | Eval run `345d6069efe64933a8d04e350a264381`: 11 records × 3 scorers, all 1.0, 0 errored |
| 008 | Run `a4809bf5e16a42fcaca5ed77f2d38120`: clean 3/3, controls 4/4, means 0.57/0.57/0.86 |
| 009 | Run `d4e336016b264b8c84720015f550dd3a`: clean 3/3, controls 5/5; right-city-wrong-fact caught only by `answers_expected_fact` |
| 010 | Pilot `30eabe1d8fdf4540a8ef9c8ee5dae368`: controls 6/6, contradiction caught only by `self_consistent`; full `99060446d0004248a3f0acab278408d6`: 16 records, 0 failed, 3 skipped |
| 011 | 5 traces in `lab-f011-1795112059`; tool names/args/counts/outcomes asserted from fetched spans, zero judge calls; manifest verified |
| 012 | 4 runs (`bf9d9e0a…`, `6661dc37…`, `3c0ad95e…`, `bbbb4b81…`); verdicts `yes,no,no,no,no` in both reps, zero flips; efficiency says `yes` on `tool_no_call` where correctness says `no` |
| 013 | `gpt-oss-20b` vs `llama-4-maverick`: 1 clean + 6 controls per arm, 6/6 caught both, 0 verdict changes; maverick ~13% faster, ~7.5× cost |
| 014 | 3/3 RAG traces verified, expected top doc first with 0.13–0.17 score gap; retrieval I/O and canonical tags asserted; `docs/demo/rag_manifest.json` |

## 5. Key decisions (with reasoning)

- **Keyless default:** `databricks-gpt-oss-20b` via `ChatDatabricks` (exp 002) — one credential, full spans.
- **Shared demo path** `/Shared/my-first-trace` with `MLFLOW_EXPERIMENT_NAME` override; UC storage deferred (F-011) — ~120 traces, no governance problem.
- **Manual spans at the application boundary** nest with autolog (exp 003); multi-turn grouped by `session_id`, not merged (exp 004).
- **Control-driven evaluation:** uniform 1.0 is not evidence (exp 007); plant known-bad records (008), check ground truth because relevance is not truth (009), scope the rubric judge to one property (010), keep correctness and efficiency separate (012).
- **Pin, don't resolve:** full resolution pulls `databricks-connect` and a scipy sdist needing Fortran on Python 3.15; lock + `--no-deps` rebuild verified (F-012). Expected `pip check` warnings are documented, not fixed.
- **One helper for tags** (F-010) and **one source of truth for regression cases** (F-014): copy-pasted lists drift.
- **A/B needs variant identity + structured output**; arm-independent scripted tool evidence is excluded (exp 013). Equal verdicts still yield an operational result via trace metrics.
- **F-004 abandoned:** a second autolog integration adds dependencies without a new tracing concept; breadth budget went to F-006.
- **F-006 on Databricks, not Snowflake:** the trial Snowflake account blocks both `EMBED_TEXT_*` and `AI_EMBED_*`; Direct Access AI Search is unsupported in this workspace, so a Delta Sync index with `databricks-gte-large-en` managed embeddings is the working design.

## 6. Proven vs not proven

**Proven:** the loop works end to end from a pinned venv; traces were fetched and asserted before manifests; scorers discriminate (4/4, 5/5, 6/6 controls); tool spans are exact and stable over two repetitions; the A/B harness diffs isolated arms; retrieval evidence comes from a real vector store.

**Not proven:** production quality (11 short weather answers, five clean tool traces); endpoint ranking (one question, one clean record per arm, single-trace latency/cost with cold start); judge stability on borderline cases (two repetitions is a smoke test); cross-turn or implied contradictions; safety (no scorer); retrieval quality versus a benchmark (one small static corpus); UC storage (deferred). Judge calls are non-deterministic; the billable `mlflow_lab_vec` endpoint remains.

## 7. Latest work — reproduce exp 014 (F-006)

One-time `python setup_rag_index.py`: UC schema/Delta table with change data feed, AI Search endpoint `mlflow_lab_vec`, and Delta Sync index `workspace.mlflow_lab.weather_docs_index` with `content` as the managed embedding source. Then `python trace_rag.py`: for each case in `rag_corpus.QUERY_CASES`, embed the query, retrieve top 3, build a grounded prompt, answer with `databricks-gpt-oss-20b`; each stage is a typed span. It flushes, fetches each trace by ID, asserts tags/span types/retriever I/O/top document, and writes the manifest only if all three pass. Overrides: `RAG_ENDPOINT`, `RAG_INDEX`, `RAG_EMBEDDING_ENDPOINT`, `RAG_CHAT_ENDPOINT`.

| Case | Trace ID | Latency | Top doc (score) |
| --- | --- | --- | --- |
| `sf_current` | `tr-e754080659cb22bee921db7192242ac1` | 5557 ms (warm-up) | sf-current (0.7657) |
| `nyc_snow` | `tr-de009be8f86449f0cae96e555ed0c73c` | 979 ms | nyc-snow (0.7099) |
| `tokyo_weather` | `tr-66cb5bafe7c710a681e5203cfc51ce92` | 1110 ms | tokyo-storms (0.7294) |

Gates: `py_compile`, manifest JSON parse, `git diff --check`, `start_demo.sh --check-only`, GitNexus `detect-changes` low risk/no truncation.

## 8. Prioritized next steps (goal order)

1. **Reusable demo (High):** F-010, F-012, F-014 are complete; keep `start_demo.sh --check-only` green and tear down the billable `mlflow_lab_vec` endpoint at retirement. F-013 stays parked.
2. **Learning breadth (Medium): extend F-006.** Add a retrieval-relevance scorer over RETRIEVER outputs, then an embedding A/B (`gte-large-en` vs `bge-large-en`). Corpus identified but not loaded: BEIR/SciFact (5,183 abstracts, 1,109 queries, 339 qrels) downloads as Parquet/TSV with installed `pyarrow`, no new deps. Propose a backlog item first.
3. **Judge trust (Low): F-016 first.** Probe efficiency false positives with a legitimate failure-plus-retry control; then add an LLM `Correctness` check with `expected_facts` and compare it to the deterministic check using human-labeled examples. F-011 stays deferred.
