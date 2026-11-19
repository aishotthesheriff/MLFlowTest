# Experiment 013 — Endpoint A/B on the standing regression set

- **Date:** 2026-11-19
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Depends on:** [012-tool-call-judges.md](012-tool-call-judges.md) (F-014 standing set), F-010 tags (variant identification)
- **Related idea(s):** F-014 (prompt/version comparison), F-016 (judge trust), F-008 (latency/cost lens)
- **Prior experiment(s):** 002 (FM endpoint), 007–010 (evaluation and controls)

## 1. Objective & hypothesis

**Question:** With the F-014 harness, can a real endpoint A/B be executed and measured — and does changing the agent endpoint change scorer outcomes on the same prompt and standing controls?

**Hypothesis:** Both ready chat endpoints will produce an on-topic, factually consistent answer to the toy weather question and pass all five scorers. The planted controls will be caught equally (they are identical in both arms). Any difference will therefore be operational (latency/tokens/cost), not a quality-verdict difference.

**Success criteria:** one freshly generated, variant-tagged trace per arm; exactly one clean record selected per arm (no mixing with the experiment's other 129 traces); 6/6 controls caught per arm; structured artifacts that `--compare` can diff; no overwrite of the exp-012 tool-call evidence.

## 2. Setup

**Harness changes (this experiment):**

| Change | Purpose |
| --- | --- |
| `trace_example.py --variant/--endpoint/--prompt` | Generate one tagged A/B arm; tags `variant` and `model_endpoint` via `lab_tags.base_tags()` |
| `evaluate_traces.py --variant` | Restrict `records_from_traces()` to one arm, excluding untagged evaluation artifacts |
| `evaluate_traces.py --output/--endpoint` | Persist row-level verdicts + arm label as a JSON artifact |
| `regression_suite.py --ab LABEL [--endpoint] [--prompt]` | Generate → score → snapshot one arm |
| `regression_suite.py --compare A.output.json B.output.json` | Diff clean + control scorer values and print trace metrics |

Tool-call judging was deliberately **excluded** from `--ab`: the five tool traces are scripted (F-015), so they cannot vary with the agent endpoint, and re-judging them would overwrite the checked-in exp-012 evidence with judge noise.

**Commands:**

```bash
source .venv/bin/activate
python regression_suite.py --ab gpt-oss-20b --endpoint databricks-gpt-oss-20b
python regression_suite.py --ab llama-4-maverick --endpoint databricks-llama-4-maverick
python regression_suite.py --compare \
  docs/demo/regression/gpt-oss-20b.output.json \
  docs/demo/regression/llama-4-maverick.output.json
```

- **Environment:** MLflow 3.18.0, Python 3.15.2, Databricks tracking URI `databricks`
- **Experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Prompt (identical in both arms):** `What is the weather in SF?`
- **Scorers:** the five from `evaluate_traces.py` (2 deterministic + relevance + consistency judge + length)

## 3. Execution and evidence

| Arm | Endpoint | Generated trace | Clean answer |
| --- | --- | --- | --- |
| A | `databricks-gpt-oss-20b` | `tr-e96d66aa28e03574a1d499b46c6f9036` | "It might be cloudy in SF." |
| B | `databricks-llama-4-maverick` | `tr-72afbaf93bf8de56b550a856e9ebf9d3` | "The weather in San Francisco is expected to be cloudy." |

- `--variant` selected exactly 1 usable record per arm from 121/129 total traces (untagged eval `root_span` records excluded).
- Structured artifacts: `docs/demo/regression/gpt-oss-20b.output.json`, `docs/demo/regression/llama-4-maverick.output.json`, plus `.meta.json` per arm.
- MLflow evaluation runs: `f3f01564f78b4d12bf814a8fa0a78cdc` (A), `d6f3b463c14144a38afef425102c217e` (B).

## 4. Results

**Scorer outcome: no difference.** Both arms: clean record 5/5 passed; planted controls 6/6 caught, with the same three controls caught by a single scorer (`over_length` → length, `right_city_wrong_fact` → fact, `self_contradiction` → consistency). `--compare` reported **0 scorer value changes** across the clean record and six controls.

**Operational difference: meaningful.**

| Metric | gpt-oss-20b (A) | llama-4-maverick (B) | B vs A |
| --- | --- | --- | --- |
| Clean answer latency | 2341 ms | 2041 ms | ~13% faster |
| Total tokens | 461 | 876 | ~1.9× more |
| Total cost | $0.0000608 | $0.0004580 | ~7.5× more |

## 5. Learnings

- **A/B needs variant identity first.** Without a `variant` tag and a `--variant` filter, both arms are scored from one mixed trace pool; `--run` alone cannot do endpoint/prompt comparison.
- **Scorer ties are still a result.** Identical verdicts with identical controls mean the harness is stable across endpoints on this prompt; the differentiator here is cost/latency, so attach trace metrics to each arm.
- **Don't re-judge arm-independent evidence.** Scripted tool cases add judge variance and can overwrite canonical evidence; `--ab` intentionally excludes them.
- **This is one clean record per arm.** Enough to prove the loop works, not to claim an endpoint quality ranking — see honest limits below.

## 6. Honest limits / next steps

- One toy question, one clean record per arm; no statistical claim about endpoint quality.
- Endpoint calls are non-deterministic; a repeated arm could flip a borderline judge verdict.
- Latency/cost come from one trace each and include cold-start effects.
- Next: repeat each arm (F-014 `--ab`) for a stability check, or run a prompt A/B with `--prompt` at a fixed endpoint; F-016 remains the separate retry/judge-trust probe.

## 7. Checklist

- [x] Extend harness with variant tagging, filtering, structured output, and comparison
- [x] Run both endpoint arms with the 6 standing controls
- [x] Verify 1 clean record per arm and 6/6 controls caught
- [x] Compare scorer verdicts and capture latency/token/cost
- [x] Preserve exp-012 tool-call evidence unchanged
- [x] Preflight `start_demo.sh --check-only` still passes (8/8 evidence traces, 8 scorers)
