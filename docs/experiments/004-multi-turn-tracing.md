# Experiment 004 — Multi-turn conversation tracing (F-005)

- **Date:** 2026-11-18
- **Owner:** Casey / local workspace
- **Status:** Completed
- **Related idea(s):** F-005 (also informs F-008, F-010)
- **Prior experiment(s):** 001-first-trace, 002-foundation-model, 003-manual-spans

## 1. Objective & hypothesis
**Question:** Does MLflow capture multi-turn agent behavior clearly — grouping turns into a session, recording per-turn inputs/outputs, and showing context growth — while preserving cross-turn recall?  
**Hypothesis:** Assigning one `session_id` across turns via `mlflow.update_current_trace(session_id=...)` will group separate per-turn traces, and each turn's root span will record its user input and growing history.  
**Success criteria:** 3 distinct traces sharing one session ID; per-turn I/O and history size recorded; turn 3 correctly references turn 1; traces searchable by session.

## 2. Setup
- **Code/script/notebook:** `trace_multi_turn.py` (workspace root)
- **Command(s):**
  ```bash
  cd /Users/yourbabes/dev/Databricks/MLFlowTest
  source .venv/bin/activate
  python trace_multi_turn.py
  ```
- **Environment:** same venv as exp 003 (Python 3.15.2, MLflow 3.18.0, `databricks-langchain` 0.22.0, `langchain` 1.5.1)
- **Databricks:** `~/.databrickscfg` DEFAULT PAT profile; tracking URI `databricks`
- **MLflow experiment:** `/Shared/my-first-trace` (`1675992194464286`)
- **Model:** `ChatDatabricks(model="databricks-gpt-oss-20b", temperature=0.1, max_tokens=500)`
- **Config/params:** `mlflow.langchain.autolog()` on; one `session_id` = `lab-f005-1795028845` applied to all turns; tags `lab_book/scenario/session_id/turn`; shared `history` list passed to `agent.invoke`
- **Data/inputs:** 3 turns:
  1. "What is the weather in SF?"
  2. "What about NYC?" (requires turn-1 context to infer weather)
  3. "Which city did I ask about first?" (requires conversation history)

## 3. Procedure
1. Created `trace_multi_turn.py` with a 3-turn loop, accumulating `(user, assistant)` message history.
2. Wrapped each turn in `mlflow.start_span(name=f"turn_{n}")`, set `session_id` + tags via `mlflow.update_current_trace`, and recorded inputs/outputs/history size on the span.
3. Ran the script, captured per-turn trace IDs, and verified persistence/grouping via `mlflow.get_trace` and `mlflow.search_traces`.
4. Fixed an ID-capture bug (see Analysis) and re-ran cleanly.

## 4. Results
- **Outcome:** Success (exit code 0)
- **Agent/model outputs:**
  1. "It might be cloudy in SF."
  2. "It might be cloudy in NYC."
  3. "You asked about San Francisco first." ✅ (cross-turn recall worked)
- **Trace(s):** session `lab-f005-1795028845`, 3 traces all state OK in experiment `1675992194464286`:

  | Turn | Trace ID | Spans | History messages before | Input tokens | Cost (USD) |
  | --- | --- | --- | --- | --- | --- |
  | 1 | `tr-e07c3271b691ff7adc60f35674d5c03f` | 8 | 0 | 337 | 0.000053 |
  | 2 | `tr-66e408aab933cac6feb63ec91b042abe` | 8 | 2 | 376 | 0.000121 |
  | 3 | `tr-6f99921de8fc0c0f8f0271392f7bb606` | 4 | 4 | 192 | 0.000029 |

  - Each trace has a root span `turn_N` with inputs `{turn, user, history_messages_before}` and output `{answer}`.
  - Session recorded two ways: `request_metadata["mlflow.trace.session"]` **and** tag `session_id`.
  - Turn 3 has fewer spans (no tool call — it answered from history), showing behavior differences per turn.
- **Search verification:** `mlflow.search_traces(locations=["1675992194464286"], filter_string="tags.session_id = 'lab-f005-1795028845'")` returned exactly 3 traces; filtering on `request_metadata.\`mlflow.trace.session\`` also returned 3.

## 5. Analysis
- **What happened:** Each turn produced its own trace (autolog spans + a manual root span), all tied to a shared session; context accumulated correctly and the final turn recalled the first city.
- **Why (interpretation):** `session_id` on `update_current_trace` is stored as trace session metadata; MLflow does not merge turns into one trace but groups them for session-level querying. Passing accumulated `history` to the agent enables cross-turn recall; token usage/cost metadata show context growth effects.
- **Surprises / risks:**
  - **ID-capture bug:** `mlflow.get_last_active_trace_id()` called *inside* an active span returned `None` for turn 1 and shifted IDs for later turns (it returns the last *completed* trace). Fixed by reading `span.trace_id` directly and flushing after the span closes. First exploratory run (`lab-f005-1795028805`, traces `tr-c7233a38...`, `tr-97e68589...`) had misattributed IDs — do not use it as evidence.
  - `TraceInfo` has no `.session_id` attribute; session lives in `request_metadata["mlflow.trace.session"]` and in tags.
  - `mlflow.search_traces` requires `locations=[experiment_id]` (or an active experiment) when filtering.
- **Comparison to prior runs:** Exp 003 was a single turn with one trace; exp 004 shows the multi-turn pattern of one trace per turn grouped by session.

## 6. Learnings & decisions
- Multi-turn tracing = one trace per turn + shared `session_id`; both tag and native session metadata are available for filtering.
- Always capture `span.trace_id` from the live span for per-turn IDs; reserve `get_last_active_trace_id()` for after a trace completes.
- Session-level metadata plus per-turn `history_messages_before` makes context growth visible and quantifiable (tokens/cost already present in `request_metadata`).

## 7. Next actions
- [ ] Use this session pattern for an error/failure scenario (F-007).
- [ ] Build a latency/token/cost summary from `request_metadata` across turns (F-008).
- [ ] Adopt `session_id` + `lab_book`/`scenario`/`turn` tags as a standard tagging convention (F-010).

## 8. Reproducibility checklist
- [x] Commands and config recorded
- [x] Trace/run identifiers recorded (3 trace IDs + session `lab-f005-1795028845`)
- [x] Relevant code changes noted (`trace_multi_turn.py`)
- [x] Follow-up ideas added to lab book backlog
