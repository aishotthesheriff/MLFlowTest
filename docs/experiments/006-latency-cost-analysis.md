# Experiment 006 — Latency, token & cost analysis (F-008)

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-008 (also informs F-013 monitoring, F-014 A/B comparison)
- **Prior experiment(s):** 001-005 (analysis spans all traces in the experiment)

## 1. Objective & hypothesis
**Question:** Does persisted trace metadata contain enough latency, token, and cost detail to identify slow and expensive runs and explain why?
**Hypothesis:** `TraceInfo` exposes latency and usage/cost fields directly, so a read-only script can rank traces and attribute hotspots to specific spans without re-running the agent.
**Success criteria:** A reusable script aggregates all traces by scenario, reports latency percentiles + token/cost totals, and drills into the slowest trace's span breakdown.

## 2. Setup
- **Code/script:** `analyze_trace_metrics.py` (workspace root)
- **Command:**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python analyze_trace_metrics.py
  ```
- **Environment:** same venv as exps 001-005 (Python 3.15.2, MLflow 3.18.0)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Scope:** 17 persisted traces from exps 001-005 (baseline, manual spans, multi-turn, error tracing)
- **No new LLM calls:** analysis-only; reads existing traces via `mlflow.search_traces(return_type="list")`

## 3. Procedure
1. Inspected `mlflow.search_traces` signature and `TraceInfo` fields; confirmed `execution_time_ms`, `token_usage`, and `cost` are first-class attributes (usage/cost are `None` when no LLM call completed).
2. Wrote `analyze_trace_metrics.py` to: group traces by the `scenario` tag (default `baseline/unlabeled`), compute mean/p50/p95 latency (linear-interpolation percentile), sum tokens and cost, rank slowest and most expensive traces, and break down the slowest trace by span duration (`end_time_ns - start_time_ns`).
3. Ran the script against the live experiment and recorded the output below.

## 4. Results
- **Outcome:** Success (17 traces analyzed, exit 0)

**Per-scenario summary** (latency in ms; cost in USD):

| Scenario | n | avg latency | p50 | p95 | tokens | cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline/unlabeled | 4 | 3499 | 3543 | 4253 | 1194 | 0.000180 |
| error_tracing | 6 | 990 | 46 | 3593 | 508 | 0.000080 |
| manual_spans | 1 | 2693 | 2693 | 2693 | 432 | 0.000051 |
| multi_turn | 6 | 2319 | 2427 | 3833 | 2542 | 0.000343 |

**Slowest traces:**

| Trace ID | Latency | Scenario |
| --- | ---: | --- |
| `tr-983651f7eb6bf22274142b9362c21858` | 4304 ms | baseline/unlabeled (exp 001, first run) |
| `tr-c493b6bfc032907e1acf21abc0b6ebc5` | 4266 ms | error_tracing (superseded case A) |
| `tr-97e685894b849324a42efc5aa0ddeaab` | 4173 ms | multi_turn, turn 2 |
| `tr-efb8425cc9c44452521a84f94a49c744` | 3964 ms | baseline/unlabeled (exp 001 verification) |
| `tr-054cbbc9de1d27ba20aec517e6cda4eb` | 3122 ms | baseline/unlabeled (exp 002) |

**Most expensive traces:**

| Trace ID | Cost | Tokens | In / out cost |
| --- | ---: | ---: | --- |
| `tr-66e408aab933cac6feb63ec91b042abe` | $0.000121 | 692 | 0.000026 / 0.000095 |
| `tr-1f0fff95ffe0e97f5434e1c4584f3211` | $0.000060 | 458 | 0.000024 / 0.000036 |
| `tr-c493b6bfc032907e1acf21abc0b6ebc5` | $0.000058 | 316 | 0.000011 / 0.000047 |
| `tr-c7233a38c42ab292a331272756e8e819` | $0.000054 | 438 | 0.000024 / 0.000030 |
| `tr-97e685894b849324a42efc5aa0ddeaab` | $0.000054 | 473 | 0.000027 / 0.000027 |

**Span breakdown of slowest trace** `tr-983651f7eb6bf22274142b9362c21858` (4304 ms):

| Duration | Span | Type |
| ---: | --- | --- |
| 4304.4 ms | LangGraph | CHAIN |
| 2754.0 ms | agent | CHAIN |
| 2747.7 ms | call_model | CHAIN |
| 2746.8 ms | RunnableSequence | CHAIN |
| 2742.0 ms | ChatOpenAI | CHAT_MODEL |
| 1539.5 ms | agent | CHAIN |
| 1535.1 ms | call_model | CHAIN |
| 1533.4 ms | RunnableSequence | CHAIN |
| 1530.3 ms | ChatOpenAI | CHAT_MODEL |
| 3.9 ms | should_continue | CHAIN |

## 5. Analysis
- **Where time goes:** the slowest trace is a two-LLM-call ReAct loop; nearly all latency is in the two `ChatOpenAI` spans (2742 ms + 1530 ms ≈ 99% of total). Graph/tool overhead is negligible (~4 ms). This is expected for an LLM-bound agent.
- **Why the slowest trace uses ChatOpenAI:** it is the original exp 001 baseline (`gpt-4o-mini`), before the Databricks FM switch in exp 002. Later Databricks FM traces are faster (multi-turn avg 2319 ms). Comparing these directly is confounded by model change, so treat it as a historical baseline, not a like-for-like benchmark.
- **Why error_tracing latency/cost looks low:** only 2 of the 6 error traces completed an LLM call; the others fail fast, yielding `execution_time_ms` of 2-81 ms and `token_usage`/`cost` of `None`. Aggregating errors with successful runs drags the mean down and makes p50 (46 ms) misleading. Error and OK traces should be segmented before drawing latency conclusions.
- **Cost driver:** cost scales with tokens, and output tokens dominate (e.g. the most expensive trace: $0.000095 out vs $0.000026 in). The multi-turn scenario has the highest total cost ($0.000343) because it has 6 traces with growing context.
- **Surprise/risk:** request metadata also carries `mlflow.trace.tokenUsage` and `mlflow.trace.cost` for traces with model calls, but the first-class `TraceInfo` fields are simpler and consistent; prefer those. Traces with no LLM call legitimately report null usage/cost — the script must handle `None`.

## 6. Learnings & decisions
- `TraceInfo.execution_time_ms`, `TraceInfo.token_usage`, and `TraceInfo.cost` are the reliable, read-only source for latency/token/cost analysis — no re-run or extra API needed.
- Latency percentiles should be computed per scenario/status; mixing fast-failing error traces with successful LLM traces distorts averages.
- Span duration = `end_time_ns - start_time_ns`; sorting spans this way instantly exposes LLM-bound hotspots.
- Cost is output-token-heavy for this workload; context growth in multi-turn is the main cost lever so far.

## 7. Next actions
- [ ] Add a `status` split (OK vs ERROR) to the summary to avoid mixing fast failures with successful runs (informs F-013).
- [ ] Use this script as the measurement harness for prompt/model A/B comparisons (F-014).
- [ ] Capture per-span token/cost (not just trace totals) if finer attribution is needed.
- [ ] Standardize scenario/status tags across all scripts so every trace is groupable (F-010).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Scope recorded (17 traces in `/Shared/my-first-trace`); key trace IDs listed
- [x] Relevant code changes noted (`analyze_trace_metrics.py`)
- [x] Follow-up ideas added to lab book backlog (F-010, F-013, F-014)
