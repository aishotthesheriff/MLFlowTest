# Experiment 012 — Judging the tool calls from experiment 011

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Depends on:** [011-tool-call-tracing.md](011-tool-call-tracing.md) — this experiment judges exactly the five traces and the manifest that 011 verified. It does not generate traces.
- **Related idea(s):** F-015 (tool-call tracing and validation), F-014 (A/B regression set), F-013 (monitoring, deliberately not enabled here)
- **Prior experiment(s):** 007 (precomputed evaluation), 009–010 (judge design and scoping)

## 1. Objective & hypothesis
**Question:** On the five verified tool-call traces from 011, what does each MLflow tool scorer configuration actually report — and do the two correctness modes disagree?
**Hypothesis:** The exact-match correctness scorer will accept only the happy case; the ground-truth-free correctness scorer and the efficiency scorer will judge the same five traces from the request alone. Efficiency is a different property from correctness, so it will part ways on at least one case.
**Success criteria:** load exactly five manifest traces with spans intact; two repetitions of two passes each; five complete scenario rows per repetition with all three verdicts; exact-match sequence `yes, no, no, no, no`; errors/missing results kept distinct from `"no"`; only three scorer configurations registered, no automatic monitoring.

## 2. Setup
- **Code/script:** new `evaluate_tool_calls.py` (no edits to `trace_example.py`, `trace_multi_turn.py`, `evaluate_traces.py`, or the 011 script)
- **Commands:**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python evaluate_tool_calls.py --register   # one-time: register 3 configs, no monitoring
  python evaluate_tool_calls.py              # 2 repetitions x 2 passes
  ```
- **Environment:** MLflow 3.18.0, Python 3.15.2, Databricks tracking URI `databricks`
- **Experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Input:** `docs/demo/tool_call_manifest.json` from 011 — the five trace IDs, `scenario=tool_calls`, one shared session, one shared user request.
- **Evaluation mode:** `mlflow.genai.evaluate(data=<trace column>, scorers=[...])` with **no `predict_fn`** and **no agent re-run**. Each row carries the source `Trace` object plus an `expectations` dict.
- **Scorer configurations (exactly three, registered without monitoring):**

  | Registered name | Class | Config | Expectation passed |
  | --- | --- | --- | --- |
  | `tool_call_correctness` | `ToolCallCorrectness` | `model="databricks"`, `should_exact_match=False`, `should_consider_ordering=False` | `{}` (empty — ground-truth free) |
  | `tool_call_efficiency` | `ToolCallEfficiency` | `model="databricks"` | `{}` (empty) |
  | `tool_call_correctness_exact` | `ToolCallCorrectness` | `model="databricks"`, `should_exact_match=True`, `should_consider_ordering=False` | `{"expected_tool_calls": [{"name": "get_weather", "arguments": {"city": "SF"}}]}` |

- **Why `expectations={}` in pass 1:** when MLflow sees `expected_tool_calls` in a row, it switches the default `tool_call_correctness` scorer into fuzzy matching against that expectation. Keeping the key out of pass 1 preserves the true ground-truth-free mode.

## 3. Procedure
1. Load the 011 manifest and fetch all five traces by ID. Fail on missing/duplicate cases, a wrong `scenario`/`tool_case`/`session_id` tag, or a trace whose spans were lost (no `CHAT_MODEL` span).
2. Run pass 1 (unaided correctness + efficiency) and pass 2 (exact correctness) on the *same five source traces*, twice, with no `predict_fn`.
3. Join each run's `result_df` back to the source traces by `trace_id` (not row position), re-check the `scenario` tag on every result row, and reject duplicate/absent traces.
4. Read each verdict from that run's own `result_df`; normalize to `yes` / `no` / `error` / `missing` so a scorer error or absent result is never silently counted as `"no"`.
5. Assert five complete rows per repetition and the exact-match sequence `yes, no, no, no, no`; report correctness-mode disagreements and cross-repetition flips; write `docs/demo/tool_call_eval_results.json` only after the structure checks pass.

## 4. Results
- **Outcome:** success — 4 evaluation runs (2 repetitions × 2 passes), 5 complete rows each, no scorer errors and no missing results, exact-match sequence correct in both repetitions, zero verdict flips.

### Evaluation runs
| Repetition | Pass | Run ID |
| --- | --- | --- |
| 1 | ground-truth-free correctness + efficiency | `bf9d9e0a1cc44b188d074a4765ca72b8` |
| 1 | exact-match correctness | `6661dc371beb41a889d3452ae61ac5a8` |
| 2 | ground-truth-free correctness + efficiency | `3c0ad95e42e642d39d017785b03e676f` |
| 2 | exact-match correctness | `bbbb4b81beca4ae6a49af77708d47fea` |

### Scenario rows (identical in both repetitions)
| Case (manifest order) | Trace ID | Correctness (no expectations) | Efficiency | Correctness (exact match) |
| --- | --- | --- | --- | --- |
| `tool_happy` | `tr-218c33b979b86c0e958d546aefa23a64` | yes | yes | yes |
| `tool_no_call` | `tr-8f166650ff924e86b7726829d3c81911` | **no** | **yes** | no |
| `tool_wrong_tool` | `tr-1dd34cbcfd3fd9b4fa0231314015da11` | no | no | no |
| `tool_wrong_args` | `tr-9f9dab49618b133d824747d8515b0104` | no | no | no |
| `tool_retry_storm` | `tr-ba8b262cff37fa530c2d4a7291b87d82` | no | no | no |

- **Exact-match sequence:** `yes, no, no, no, no` in both repetitions, matching the manifest order.
- **Correctness-mode disagreements:** none. The ground-truth-free and exact-match correctness scorers returned the same verdict on all five cases. They reached it differently: exact match counted calls ("Expected 1, but got 0/3") and named the missing/unexpected call; the unaided judge read the request and reasoned about tool choice.
- **Cross-scorer disagreement:** `tool_no_call` — both correctness modes say `no`, efficiency says `yes`. Efficiency only sees that no redundant calls were made; it cannot tell that a required call was skipped.
- **Verdict flips between repetitions:** none for any of the three configurations.
- **Errors / missing results:** none; the `error`/`missing` states were exercised by the normalization code and kept distinct from `"no"` in the schema.

## 5. Analysis
- **Two correctness modes agreed on these five clean-cut defects.** The value of the exact-match mode is not a different verdict here but a deterministic, auditable rationale: it states the expected call and the observed calls, which is useful in a regression gate where a model-based verdict needs explanation.
- **Efficiency is not correctness.** The no-call case is the sharpest lesson: doing nothing is maximally efficient and still wrong. A single "tool health" score would hide this; keeping correctness and efficiency as separate scorers surfaces it.
- **The retry storm is caught twice, for two reasons.** Efficiency flags three calls with identical arguments; exact match flags "Expected 1, got 3". That is the intended separation: redundancy versus deviation from expectation.
- **No `predict_fn` means the source traces are the evidence.** Each run's verdicts are read from that run's own `result_df`, joined by trace ID. This avoids attributing an assessment on a linked/copied trace to the wrong run.
- **Stability on this set is a property of the cases, not a guarantee.** These five traces are unambiguous. LLM-judge verdicts on borderline cases can still flip; two repetitions on five cases is a smoke test, not a flakiness study.

## 6. Learnings & decisions
- Passing `expected_tool_calls` changes the *default* correctness scorer's behavior; pass 1 must pass `{}` to stay ground-truth-free.
- `ToolCallEfficiency.__call__` takes only `trace`; `ToolCallCorrectness.__call__` also accepts `expectations`. The evaluator passes `expectations` only where it is supported.
- Joining by `trace_id` (with a `scenario` tag re-check) is safer than trusting `result_df` row order when results from multiple runs are compared.
- Registering a scorer does not enable monitoring — the three configurations are available for repeatable evaluation but no automatic trace evaluation was turned on (F-013 remains open).

## 7. Next actions
- [ ] Add the five tool-call cases and all three verdicts to F-014's standing A/B regression set.
- [ ] Add a legitimate failure-plus-retry control to check that the efficiency judge does not punish recovery (F-016).
- [ ] Run a larger repetition count on borderline cases before treating judge verdicts as a stability guarantee.

## 8. Reproducibility checklist
- [x] Source traces and manifest from exp 011; no traces regenerated here
- [x] Both passes run twice with no `predict_fn`; four run IDs recorded
- [x] Five complete scenario rows per repetition with all three verdicts
- [x] Exact-match sequence `yes, no, no, no, no` verified in both repetitions
- [x] Errors/missing results normalized separately from `no`
- [x] Three scorer configurations registered, no automatic monitoring
- [x] Results file `docs/demo/tool_call_eval_results.json`; eight original evidence traces untouched
