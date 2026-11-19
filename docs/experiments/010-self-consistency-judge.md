# Experiment 010 — A rubric judge for self-contradiction (no expected facts)

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-009 (evaluation harness), F-014 (known-bad controls, A/B)
- **Prior experiment(s):** 009 (reference-based fact check and its documented blind spot), 008 (known-bad controls)

## 1. Objective & hypothesis
**Question:** Can an LLM judge catch an answer that contradicts itself without maintaining a set of expected facts?
**Hypothesis:** Yes. A rubric judge that only asks "does this answer agree with itself?" should flag "cloudy, but also sunny and 95F" while passing correct answers, irrelevant answers, and answers that are wrong but internally consistent. It should complement — not replace — the deterministic fact check from exp 009.
**Success criteria:** A new planted control `self_contradiction` passes city, fact, relevance, and length, fails only the consistency judge, and is reported as caught by a single scorer; clean records keep passing; 6/6 controls caught.

## 2. Setup
- **Code/script:** `evaluate_traces.py` (new `self_consistent` scorer, `SELF_CONSISTENCY_GUIDELINES`, sixth control)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python evaluate_traces.py --register --pilot          # persist the 5th scorer
  python evaluate_traces.py --pilot --with-controls     # 3 clean + 6 controls
  python evaluate_traces.py                             # full run
  ```
- **Environment:** same venv as exps 001-009 (Python 3.15.2, MLflow 3.18.0)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Judge:** `mlflow.genai.scorers.Guidelines(name="self_consistent", model="databricks")` — the same managed Databricks judge used by `relevance_to_query`, no external key
- **Rubric:** scoped to internal consistency only — ignore relevance, correctness against outside facts, completeness, and tone; if the answer makes no weather claim, pass it
- **Ground truth:** none. That is the point — the judge reads only the answer, so it works where `expected_fact` is unknown
- **Data/inputs:** 3 clean multi-turn pilot records + 6 planted controls (wrong city, off-topic, over-length, refusal, right-city-wrong-fact, self-contradiction)

## 3. Procedure
1. Probed `Guidelines` directly on four texts before touching the harness: a clean answer, the contradiction, the recall turn, and the right-city-wrong-fact control. It returned yes / no / yes / yes as intended.
2. Added `self_consistent` to `build_scorers()` with an initial two-line rubric ("must not contradict itself").
3. Ran the pilot: the contradiction was caught, but the judge also flagged the `off_topic` control — its rationale talked about the answer not addressing the question. The rubric was drifting into relevance.
4. Tightened the rubric to a self-consistency-only scope ("Ignore relevance, correctness against outside facts, completeness, and tone"; "If the answer makes no claim about weather conditions or temperature, pass it"), re-registered, and re-ran.
5. Added the sixth control: `"It might be cloudy in San Francisco, but it's also sunny, 95F, and clear."`
6. Generalized the report's single-scorer callout so any control caught by exactly one scorer is listed with that scorer.

## 4. Results
- **Outcome:** Success — pilot `grandiose-trout-226` / `30eabe1d8fdf4540a8ef9c8ee5dae368`; full run `enthused-kite-512` / `99060446d0004248a3f0acab278408d6`.
- **URL:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=99060446d0004248a3f0acab278408d6`
- **Records:** pilot 9 (3 clean + 6 controls), 0 unscored, 0 errored; full 16, 0 failed, 0 errored, 3 skipped (fact check on recall turns).

| Group | n | city | fact | relevance | self_consistent | length |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Clean sample | 3 | 3/3 passed | 2/2 passed (1 skipped) | 3/3 passed | 3/3 passed | 3/3 passed |
| Planted controls | 6 | 3/6 flagged | 3/6 flagged | 3/6 flagged | 1/6 flagged | 1/6 flagged |

| Control | City | Fact | Relevance | Self-consistent | Length | Caught by |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| `wrong_city` | ✗ | ✓ | ✗ | ✓ | ✓ | city, relevance |
| `off_topic` | ✗ | ✗ | ✗ | ✓ | ✓ | city, fact, relevance |
| `over_length` | ✓ | ✓ | ✓ | ✓ | ✗ | length only |
| `refusal` | ✗ | ✗ | ✗ | ✓ | ✓ | city, fact, relevance |
| `right_city_wrong_fact` | ✓ | **✗** | ✓ | ✓ | ✓ | **fact only** |
| `self_contradiction` | ✓ | ✓ | ✓ | **✗** | ✓ | **self_consistent only** |

- **Controls caught:** 6/6.
- **Aggregate means (pilot):** city 0.667, fact 0.625, relevance 0.667, self_consistent 0.889, length 0.889.
- **The key row:** `control:self_contradiction` → city `True`, fact `True`, relevance `yes`, length `yes`, self_consistent `no`.
- **Clean full run:** every scorer 1.0 on all 16 records; the judge produced no false positives on real answers.
- **First rubric iteration** (`orderly-bass-141` / `cfa3e5ba48914f5ea0d8b4e155166332`): caught the contradiction but also flagged `off_topic` (2/6). Kept as evidence that an unscoped rubric judge leaks into relevance.

## 5. Analysis
- **The blind spot is closed without expected facts.** The deterministic fact check needs a known truth per record; the rubric judge needs none. It sees the contradiction because the two claims are in the same answer.
- **The two checks are complementary, and the control matrix proves it.** `right_city_wrong_fact` is internally consistent, so the judge passes it; `self_contradiction` states the expected fact, so the deterministic check passes it. Each control is caught by exactly one scorer.
- **Rubric scope is the whole game.** The first rubric judged relevance by accident. Adding "ignore relevance/correctness/tone" and "pass answers with no weather claim" made it fire once, on the one intended control.
- **An LLM judge is not free.** It adds a model call per record (~1-2 s in the pilot) and is non-deterministic. Keep the deterministic checks for known ground truth and use the judge where truth is unknown or the defect is internal.
- **Evaluation adds traces too.** The experiment's trace count rose from 76 to 110 while these 34 records were scored (two pilots + one full run); the new traces are untagged `root_span` records from the judge/evaluation path. Filter by scenario or trace name before counting agent runs.
- **Residual blind spot:** a contradiction that is spread across turns or stated as implication ("cloudy, so expect 95F") may still slip. That is the same class of limitation any single-answer rubric has.

## 6. Learnings & decisions
- "Self-consistent" is a separate property from "relevant", "correct", and "short". Name the property, then scope the rubric to it.
- A rubric judge is the right tool when no expected fact exists; a deterministic check is still better when one does.
- Test a judge on a small labelled set before adding it to the suite — the first rubric looked fine in prose and leaked in practice.
- Report single-scorer catches explicitly: that is where a narrower suite would have failed.

## 7. Next actions
- [ ] Compare `Guidelines` against MLflow's `Correctness` with `expected_facts` on paraphrase/contradiction cases.
- [ ] Add a contradiction control with the claims split across two sentences and one with an implication, to probe judge robustness.
- [x] Move all six controls into the full run as a standing regression set (F-014) — exposed as `evaluate_traces.CONTROL_NAMES` for the regression suite (2026-11-19).
- [x] Use the suite for prompt/model A/B comparisons (F-014) — `regression_suite.py --run/--compare` (2026-11-19).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Evaluation run IDs and URLs recorded
- [x] Row-level counts, metrics, and rationales inspected
- [x] Relevant code changes noted (`evaluate_traces.py`)
- [x] Follow-up ideas added to lab book backlog (F-014)
