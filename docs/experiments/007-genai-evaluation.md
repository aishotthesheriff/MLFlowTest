# Experiment 007 — MLflow GenAI evaluation on traces (F-009)

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-009 (feeds F-014 A/B comparison, F-013 monitoring)
- **Prior experiment(s):** 001-006 (evaluates traces they produced)

## 1. Objective & hypothesis
**Question:** Can automated scorers/judges assess answer quality from already-traced runs, without re-invoking the agent or creating a new dataset?
**Hypothesis:** MLflow 3.18's precomputed evaluation mode can consume selected existing traces as `inputs`/`outputs`/`expectations` records and produce row-level assessments plus aggregate metrics, using a mix of deterministic and LLM-judge scorers.
**Success criteria:** A reusable script selects usable traces, runs a 3-scorer suite, persists an evaluation run with row-level results for every record, and reports assessed/missing/errored counts.

## 2. Setup
- **Code/script:** `evaluate_traces.py` (workspace root); modes `--pilot`, `--register`, default full run
- **Commands:**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python evaluate_traces.py --pilot       # 3 representative records
  python evaluate_traces.py --register    # register suite, then full run
  python evaluate_traces.py               # full run only
  ```
- **Environment:** same venv as exps 001-006 (Python 3.15.2, MLflow 3.18.0)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Judge model:** `databricks` (MLflow default for Databricks tracking URI) — managed Databricks judge, no external key. Verified with a real direct scorer call before the pilot.
- **Scorer suite:**
  | Scorer | Type | Criterion | Data |
  | --- | --- | --- | --- |
  | `relevance_to_query` | Built-in LLM judge | Response directly addresses the question | inputs + outputs |
  | `answers_expected_city` | Custom `@scorer` (deterministic) | Answer names the city the user asked about (user outcome) | inputs + outputs + expectations |
  | `response_length` | Built-in deterministic | Answer under 300 chars | outputs |

## 3. Procedure
1. Inspected installed scorer catalog and registered scorers/datasets: none registered, no datasets.
2. Selected records from all 17 original traces: 11 had a usable final answer (6 multi-turn, 4 baseline, 1 manual-spans). Excluded 6 `error_tracing` traces (no usable final answer; already covered by exp 005).
3. Normalized each trace's root-span inputs/outputs into precomputed records; set `expectations.expected_city` from the known lab conversation (SF or NYC). No agent call and no stored trace modification.
4. Verified the judge with a direct `RelevanceToQuery()` call and validated the custom scorer on known-good and known-bad answers.
5. **Pilot 1** (`1b5ab86f5f8d4fe78d94589b1c184a91`): failed diagnosis — custom scorer produced false negatives on `"It might be cloudy in SF."` (`sf.` tokenization) and `"You asked about San Francisco first."` (U+202F narrow no-break space); expectations also surfaced as a pseudo-scorer column. Fixed with Unicode whitespace normalization + word-boundary matching and scorer-only verdict counting.
6. **Pilot 2** (`8b39b2373898459b839386360a21e71b`): 3/3 records passed all scorers; every row had valid values and rationales, no errors.
7. Registered all three scorers in the experiment and verified via `mlflow.genai.list_scorers()`.
8. **Full run** (`345d6069efe64933a8d04e350a264381`): 11 records; inspected run status, aggregate metrics, row-level values/rationales/errors, and verdict counts.

## 4. Results
- **Outcome:** Success — evaluation run `FINISHED` (17.1 s), row-level results for all 11 records.
- **Run:** `rumbling-trout-797` / `345d6069efe64933a8d04e350a264381`
- **URL:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=345d6069efe64933a8d04e350a264381`

| Scorer | Mean | Passed | Failed | Unscored | Errored |
| --- | ---: | ---: | ---: | ---: | ---: |
| `answers_expected_city` | 1.0 | 11 | 0 | 0 | 0 |
| `relevance_to_query` | 1.0 | 11 | 0 | 0 | 0 |
| `response_length` | 1.0 | 11 | 0 | 0 | 0 |

- **Coverage:** 11 evaluated; 0 failed; 0 missing/unscored; 0 errored. 6 error-tracing traces deliberately excluded.
- **Composition:** 6 multi-turn (turns 1-3 from two sessions), 4 baseline, 1 manual-spans; expected city SF (9) or NYC (2).
- **Evidence examples:** `tr-e07c3271b691ff7adc60f35674d5c03f` (turn 1, "It might be cloudy in SF."), `tr-66e408aab933cac6feb63ec91b042abe` (turn 2, "It might be cloudy in NYC."), `tr-6f99921de8fc0c0f8f0271392f7bb606` (turn 3 recall, "You asked about San Francisco first.") — all three scorers passed with rationales.
- **Registered scorers verified:** `relevance_to_query`, `answers_expected_city`, `response_length`.

## 5. Analysis
- **Uniform 1.0 scores are genuine for this sample, not a broken scorer.** Every selected record is a known-good weather answer from the lab's happy-path runs. Direct validation confirmed `answers_expected_city` returns `False` for a wrong city and for an unrelated answer, so the scorer can discriminate; the pilot also caught its two false-negative bugs. Still, 11 short synthetic-lab answers from one weather agent are **not** evidence of production quality.
- **Judge worked without new credentials:** on Databricks tracking, `RelevanceToQuery()` defaults to the managed `databricks` judge. A real call succeeded before any evaluation run.
- **Precomputed mode limits:** no predictor is invoked, so there are no new agent traces to inspect; assessments are stored in the evaluation run's row-level results, not attached to the original traces (checked: original trace assessments list is empty).
- **Gotchas recorded:**
  - Model output contains U+202F (narrow no-break space) in "San Francisco" — naive substring checks fail; normalize with `re.sub(r"\s+", " ", ...)`.
  - `sf.` at end of a sentence defeats `"sf" in text.split()` — use word-boundary regex `\bsf\b`.
  - "NYC" is expanded to "New York City" in the answer, so a literal `"nyc"` check is a false negative — use an alias map (fixed in [exp 008](008-scorer-controls.md)).
  - `expectations` become `<key>/value` columns in the result table; MLflow's `result.passed` inspects all such columns and can report `False` because a ground-truth string is not a yes/no rating. The script counts only real scorer verdicts.
  - Each evaluation run adds new traces to the experiment (17 → 23 across pilot/retry/full runs); the record selector still finds exactly 11 usable ones because generated traces lack usable root inputs.
- **Comparison to prior experiments:** exps 001-006 established tracing and measurement; exp 007 adds the first automated quality signal over those traces.

## 6. Learnings & decisions
- MLflow GenAI precomputed evaluation works directly over persisted traces: no re-run, no dataset creation, no new credentials needed here.
- A mix of one LLM judge (semantic relevance) and deterministic checks (expected city, length) gives complementary evidence; deterministic checks are cheaper and caught real text-normalization bugs.
- Validate custom scorers on known-bad inputs and inspect row-level values/rationales/errors — a successful run and 1.0 mean are not sufficient on their own.
- Segment by scenario/status before evaluation: error traces have no final answer and must be excluded or handled by a separate criterion.
- A uniform 1.0 needs planted known-bad controls to mean anything; [exp 008](008-scorer-controls.md) adds them (clean 3/3, controls 4/4 caught) and shows non-uniform means.

## 7. Next actions
- [x] Add a known-bad case set (wrong city, refusal, off-topic) to prove non-uniform scoring in the full harness (F-014). → completed in [experiment 008](008-scorer-controls.md).
- [x] Use this suite as the measurement harness for prompt/model A/B comparisons (F-014) — `regression_suite.py` now orchestrates it (2026-11-19).
- [ ] Consider human-labeled examples and judge alignment before trusting subjective scores (F-009 follow-up).
- [ ] Feed `status = 'ERROR'` traces into a separate error-quality evaluation (F-013).

## 8. Reproducibility checklist
- [x] Commands and config recorded (script, modes, experiment, judge model)
- [x] Evaluation run IDs and URL recorded (pilot 1, pilot 2, full)
- [x] Row-level counts, metrics, and scorer rationales inspected
- [x] Relevant code changes noted (`evaluate_traces.py`)
- [x] Follow-up ideas added to lab book backlog (F-013, F-014)
