# Experiment 009 — Right city, wrong fact: a reference-based factuality check

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-009 (evaluation harness), F-014 (known-bad controls, A/B)
- **Prior experiment(s):** 007 (scorer suite), 008 (known-bad controls + city aliases)

## 1. Objective & hypothesis
**Question:** Would the current scorer suite catch a hallucination that names the right city but states the wrong weather fact?
**Hypothesis:** No. The deterministic city check only asks whether the city appears, the length check only measures size, and the relevance judge only asks whether the answer is on topic — so a plausible wrong-fact answer would pass all three. Adding a reference-based fact check against the tool's ground truth should catch it, and only it.
**Success criteria:** A planted `right_city_wrong_fact` control passes city, relevance, and length, fails the new fact scorer, and is reported as caught only by the fact check; clean records keep passing; 5/5 controls caught.

## 2. Setup
- **Code/script:** `evaluate_traces.py` (new `answers_expected_fact` scorer, `fact_stated()`, `expected_fact` ground truth, fifth control)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python evaluate_traces.py --register --pilot          # persist the 4th scorer
  python evaluate_traces.py --pilot --with-controls     # 3 clean + 5 controls
  ```
- **Environment:** same venv as exps 001-008 (Python 3.15.2, MLflow 3.18.0)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Judge model:** `databricks` (managed Databricks judge, no external key)
- **Ground truth:** the lab weather tool is a stub — `get_weather` always returns `It might be cloudy in {city}` — so `cloudy` is the expected fact for every weather turn. The cross-turn recall turn ("Which city did I ask about first?") has no tool-derived fact and is skipped by the fact check.
- **Data/inputs:** 3 clean multi-turn pilot records + 5 planted controls (wrong city, off-topic, over-length, refusal, right-city-wrong-fact)

## 3. Procedure
1. Added `expected_fact` to each record's expectations: `cloudy` for weather turns, absent for the recall turn.
2. Added the deterministic `answers_expected_fact` scorer: normalize whitespace/case, then whole-word match against `FACT_ALIASES["cloudy"] = ("cloudy", "clouds", "overcast")`. It returns `None` (no assessment) when a record has no known fact, so the recall turn is skipped rather than failed.
3. Made the shared `_normalize()` helper lowercase and collapse whitespace inside `city_mentioned()` and `fact_stated()`, so both matchers are case- and U+202F-insensitive by construction.
4. Added the fifth control: `"The weather in San Francisco is sunny and 75F with clear skies."`
5. Registered the 4th scorer and ran the pilot with controls. The report now shows skipped counts and flags controls caught only by the fact check.

## 4. Results
- **Outcome:** Success — evaluation run `able-foal-755` / `d4e336016b264b8c84720015f550dd3a` FINISHED.
- **URL:** `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/evaluation-runs?selectedRunUuid=d4e336016b264b8c84720015f550dd3a`
- **Records:** 8 (3 clean + 5 controls); 0 unscored; 0 errored; 1 fact-check skip (recall turn).

| Group | n | answers_expected_city | answers_expected_fact | relevance_to_query | response_length |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clean sample | 3 | 3/3 passed | 2/2 passed (1 skipped) | 3/3 passed | 3/3 passed |
| Planted controls | 5 | 3/5 flagged | 3/5 flagged | 3/5 flagged | 1/5 flagged |

| Control | City | Fact | Relevance | Length | Caught by |
| --- | :---: | :---: | :---: | :---: | --- |
| `wrong_city` | ✗ | ✓ | ✗ | ✓ | city, relevance |
| `off_topic` | ✗ | ✗ | ✗ | ✓ | city, fact, relevance |
| `over_length` | ✓ | ✓ | ✓ | ✗ | length |
| `refusal` | ✗ | ✗ | ✗ | ✓ | city, fact, relevance |
| `right_city_wrong_fact` | ✓ | **✗** | ✓ | ✓ | **fact only** |

- **Controls caught:** 5/5.
- **Aggregate means:** `answers_expected_city` 0.625, `answers_expected_fact` 0.571, `relevance_to_query` 0.625, `response_length` 0.875.
- **The key row:** `control:right_city_wrong_fact` → city `True`, relevance `yes`, length `yes`, fact `False`. The original three-scorer suite would have passed it.
- **Alias fix still holds:** turn 2 ("What about NYC?" → "The weather in New York City is currently cloudy.") scores `answers_expected_city=True` and `answers_expected_fact=True`.

**Full run (all usable records, 4 scorers):** `amusing-goose-170` / `6c408d499a794bacbc42b842ecfac352` — 16 records, 0 failed, 0 errored, 3 skipped (the recall turns with no tool-derived fact), every mean 1.0. The deterministic fact check produces no false negatives on the real answers, and the three skips are reported as skipped rather than unscored.

## 5. Analysis
- **The gap was real.** The managed relevance judge did not flag "San Francisco is sunny and 75F" — it is on topic, just wrong. City and length checks cannot see the error either. A semantic judge asks "is this relevant?", not "is this true?".
- **Reference-based checks close it cheaply.** Because the lab tool is a stub, the ground truth is known exactly, so a deterministic whole-word check is enough. No extra judge call, no key.
- **Skip semantics matter.** Returning `None` from the scorer is treated by MLflow as an empty assessment, so the recall turn is skipped instead of counted as a failure. The report prints `skipped=1` to keep that visible.
- **Residual blind spot:** an answer that states the expected fact *and* contradicts it — "cloudy, but also 95F and sunny" — still passes the deterministic check. Catching contradictions needs an LLM correctness judge (MLflow's `Correctness` with `expected_facts`) or human labels.
- **Comparison to exp 008:** 4/4 → 5/5 controls, and the fifth is the first control the original suite provably could not catch.

## 6. Learnings & decisions
- Relevance and factuality are different questions; a relevance judge is not a factuality check.
- Plant the defect the current harness cannot catch, then add the check — that is the demonstration, not a claim.
- When ground truth is known, a deterministic reference check is cheaper and more explainable than another LLM judge.
- Keep skip semantics explicit (`None` + `skipped` count) so "not applicable" never reads as "failed" or "unscored".

## 7. Next actions
- [ ] Add an LLM `Correctness` check with `expected_facts` for paraphrase and contradiction robustness, and compare it against the deterministic check.
- [ ] Move all five controls into the full run as a standing regression set (F-014).
- [ ] Use the suite for prompt/model A/B comparisons (F-014).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Evaluation run ID and URL recorded
- [x] Row-level counts, metrics, and rationales inspected
- [x] Relevant code changes noted (`evaluate_traces.py`)
- [x] Follow-up ideas added to lab book backlog (F-014)
