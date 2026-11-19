# Experiment 008 — Known-bad scorer controls (F-009 follow-up / F-014)

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-009 (evaluation harness), F-014 (known-bad controls, A/B)
- **Prior experiment(s):** 007 (scorer suite and precomputed evaluation)

## 1. Objective & hypothesis
**Question:** Does the scorer suite actually discriminate, or does it return 1.0 for everything?
**Hypothesis:** Appending a small set of planted known-bad records to the precomputed evaluation will produce non-uniform scores, with every control caught by at least one scorer — proving the harness is a real measurement tool, not a green light.
**Success criteria:** One `--pilot --with-controls` run shows the clean sample passing, every control flagged, row-level rationales present, and no unscored or errored records.

## 2. Setup
- **Code/script:** `evaluate_traces.py` (new `--with-controls` flag, `build_controls()`, clean-vs-controls report)
- **Commands:**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python evaluate_traces.py --pilot --with-controls
  ```
- **Environment:** same venv as exps 001-007 (Python 3.15.2, MLflow 3.18.0)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Judge model:** `databricks` (managed Databricks judge, no external key)
- **Data/inputs:** 3 clean multi-turn pilot records + 4 planted controls (wrong city, off-topic, over-length, refusal)

## 3. Procedure
1. Fixed the deterministic city scorer's alias gap: `NYC` now matches "New York City"/"New York", and `San Francisco` matches "SF", using whole-word matching after whitespace normalization.
2. Added `build_controls()` with four planted known-bad records; each is expected to fail at least one scorer.
3. Added `--with-controls` to append the controls to a pilot or full evaluation, plus a clean-vs-controls summary and a per-control "caught" table.
4. Ran `evaluate_traces.py --pilot --with-controls` against the experiment.

## 4. Results
- **Outcome:** Success — evaluation run `gaudy-colt-173` / `a4809bf5e16a42fcaca5ed77f2d38120` FINISHED.
- **URL:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=a4809bf5e16a42fcaca5ed77f2d38120`
- **Records:** 7 (3 clean + 4 controls); 0 unscored; 0 errored.

| Group | n | answers_expected_city | relevance_to_query | response_length |
| --- | ---: | ---: | ---: | ---: |
| Clean sample | 3 | 3/3 passed | 3/3 passed | 3/3 passed |
| Planted controls | 4 | 3/4 flagged | 3/4 flagged | 1/4 flagged |

| Control | Answer | Caught | By |
| --- | --- | :---: | --- |
| `wrong_city` | "The current weather in New York City is cloudy." | yes | city, relevance |
| `off_topic` | "I can help you write a Python function to sort a list." | yes | city, relevance |
| `over_length` | SF weather update repeated to 590 chars | yes | length |
| `refusal` | "I'm sorry, but I can't help with weather questions." | yes | city, relevance |

- **Controls caught:** 4/4.
- **Aggregate means:** `answers_expected_city` 0.571, `relevance_to_query` 0.571, `response_length` 0.857 — non-uniform by design.
- **Alias-fix evidence:** turn 2 ("What about NYC?" → "The weather in New York City is currently cloudy.") now scores `answers_expected_city=True`; before the alias map it scored `False`.

## 5. Analysis
- **The harness discriminates.** The clean records stay green while every planted defect is flagged — the missing evidence from exp 007's uniform 1.0.
- **The checks are complementary.** The deterministic city check caught 3/4 controls; the length check caught the one the city check could not (over-length); the LLM judge independently flagged the same 3 semantic failures.
- **The alias fix closes a real false negative.** The model expands "NYC" to "New York City", so literal token matching was wrong. Whole-word aliases fix it without weakening the check.
- **Known blind spot:** a plausible hallucination that names the right city with a wrong fact would pass the current deterministic checks (and may pass the relevance judge). That needs a factuality scorer or human labels — [exp 009](009-factuality-check.md) closes it with a reference-based fact check and proves the gap with a fifth control.

## 6. Learnings & decisions
- A high mean is not evidence; planted known-bad controls turn "all 1.0" into a demonstrated capability.
- Deterministic scorers need alias/normalization coverage for the model's natural paraphrases, not just punctuation and Unicode.
- Report clean and control rows separately so a reviewer can see both the pass rate and the catch rate.

## 7. Next actions
- [ ] Add the controls to the full run and keep them as a standing regression set (F-014).
- [x] Add a factuality/hallucination check for right-city-wrong-fact answers. → completed in [experiment 009](009-factuality-check.md).
- [ ] Use the suite for prompt/model A/B comparisons (F-014).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Evaluation run ID and URL recorded
- [x] Row-level counts, metrics, and rationales inspected
- [x] Relevant code changes noted (`evaluate_traces.py`)
- [x] Follow-up ideas added to lab book backlog (F-014)
