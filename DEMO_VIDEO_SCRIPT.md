# 30-Second 3D Infographic — What an MLflow Trace Actually Catches

**Runtime:** 0:30 exactly · **Format:** 16:9, 30 fps (900 frames) · **Voiceover:** 62 words, ~30 s at a measured pace with pauses
**Source:** `DEMO_SCRIPT.md` (Acts 1–5C), `DEMO_SUMMARY_AND_TALK_TRACK.md`, `docs/experiments/001`–`014`.

**Subject:** a real LangGraph weather agent answering "What's the weather in San Francisco?" on `databricks-gpt-oss-20b`, traced in Databricks MLflow 3. Nothing on screen is a generic stand-in: span names, counts, trace IDs, timings and verdicts are the ones from the demo kit.

**Story:** ask a concrete question → see the real waterfall → watch it catch what a score hides. The 3D is a readable waterfall, not an abstract sculpture.

---

## On-screen assets (all literal)

- The question tile reads **"What's the weather in San Francisco?"** — not "ONE QUESTION".
- Span blocks carry their real names: **`ChatDatabricks`** (CHAT_MODEL), **`get_weather`** (TOOL), **`preprocess`** / **`postprocess`** (manual), and the app boundary span.
- Numerals are the measured ones: **7 → 10 spans**, **3 traces / 1 session**, **4,304 ms**, **$0.000121**, **6 planted / 6 caught**, the **0.67 / 0.63 / 0.67 / 0.89 / 0.89** means.
- Session and trace IDs appear verbatim: **`lab-f005-1795028845`**, **`tr-054cbbc9…`**, **`tr-0cb5f6d2…`**, **`tr-6f99921d…`**.
- Judge names are literal: **`relevance_to_query`**, **`answers_expected_city`**, **`answers_expected_fact`**, **`self_consistent`**, **`response_length`**.
- Palette: background `#0A0E1A` · model spans amber `#FFB347` · tool spans violet `#A78BFA` · manual spans frosted white · data chips cyan `#38BDF8` · error red `#EF4444` · passing gates green `#34D399`.
- Camera: three-quarter view, slow continuous dolly, no whip pans. One line of on-screen text at a time; no motion-grammar jargon, no confetti.

---

## Scene 1 — The real question (0:00–0:04)

**Voiceover:** "San Francisco weather. One MLflow trace. No API key."

**On screen:** `"What's the weather in San Francisco?"` → `ChatDatabricks · get_weather()` → `1 TRACE · NO API KEY`

**3D action:** A query tile with the literal question drops onto the plane. On impact it extrudes into a waterfall containing two named blocks — an amber `ChatDatabricks` (CHAT_MODEL) and a violet `get_weather` (TOOL). Camera begins its slow drift in.

**Sound:** soft click, low hum begins.

---

## Scene 2 — Autolog plus your code (0:04–0:09)

**Voiceover:** "Autolog sees ChatDatabricks and get_weather. Manual spans take seven to ten."

**On screen:** `AUTOLOG: CHAT_MODEL + TOOL` / `MANUAL: @mlflow.trace` / `7 → 10 SPANS`

**3D action:** The two named autolog blocks light up. A frosted-white app-boundary span wraps them; `preprocess` and `postprocess` slots in around the model call. Counter ticks from the baseline `tr-054cbbc9…` (7) to `tr-0cb5f6d2…` (10). The manual spans parent the autolog spans; they do not sit beside them.

**Sound:** two warm pings, counter tick.

---

## Scene 3 — Turn three (0:09–0:13)

**Voiceover:** "Three turns, one session. Turn three: recall, no tool call."

**On screen:** `3 TRACES · 1 SESSION · lab-f005-1795028845` / `TURN 3: NO TOOL CALL`

**3D action:** The waterfall duplicates into three traces around a session ring labelled `lab-f005-1795028845`. Turn 2 changes city to NYC; turn 3 (`tr-6f99921d…`) has an empty tool slot — a cyan thread from turn 1 carries "San Francisco" forward. Fewer spans, recall intact.

**Sound:** three light ticks, ring chime.

---

## Scene 4 — Two failure signatures (0:13–0:17)

**Voiceover:** "Unhandled: trace ERROR. Handled: span ERROR, trace OK."

**On screen:** `UNHANDLED → TRACE ERROR` / `HANDLED → SPAN ERROR · TRACE OK`

**3D action:** Two copies of the waterfall, separated in depth. Left: an unhandled exception floods the whole trace red with an exception badge. Right: only the `get_weather` child block flashes red; the outer trace holds its colour and stamps `OK`. The caption is the distinction a pager acts on.

**Sound:** low alert on the left, muted tick on the right.

---

## Scene 5 — Measure, then catch (0:17–0:23)

**Voiceover:** "Latency, tokens, cost straight from the trace. Six planted bad answers, six caught."

**On screen:** `4,304 MS · $0.000121 · TOKENS ON TRACE` → `6 PLANTED CONTROLS · 6/6 CAUGHT` / `right city, wrong fact · self-contradiction`

**3D action:** Three cyan chips — `ms`, `tokens`, `$` — lift off the waterfall and settle into a readout showing `4,304 ms` and `$0.000121`. Six labelled control cards file past a bank of gates named after the five registered scorers. Every card gets a red `CAUGHT` stamp. The last two stop specifically at `answers_expected_fact` ("sunny and 75F" for a cloudy stub) and `self_consistent` ("cloudy, but sunny and 95F"). A strip below reads `0.67 / 0.63 / 0.67 / 0.89 / 0.89` — a high mean is not the evidence; a caught control is.

**Sound:** crisp gate clicks, two distinct stop tones, stamp thuds.

---

## Scene 6 — What it did, then repeat (0:23–0:30)

**Voiceover:** "Efficient can still be wrong. Trace, inspect, measure, evaluate — then repeat."

**On screen:** `get_weather(city='SF'): EFFICIENCY YES · CORRECTNESS NO` → `TRACE → INSPECT → MEASURE → EVALUATE` / footer `gpt-oss-20b vs llama-4-maverick · identical verdicts`

**3D action:** Tool-call tokens snap into the literal sequence `get_weather(city='SF')`. A no-call card splits into two verdict chips: efficiency `YES`, correctness `NO`. Camera pulls back as four nodes — trace, inspect, measure, evaluate — lock into a closed loop above the waterfall. End-card footer names the real endpoint A/B and the 14 experiments.

**Sound:** two opposing tones, one resolving chord, hum fades out.

---

## Accuracy guardrails

| Claim on screen | Source |
| --- | --- |
| "What's the weather in San Francisco?" · no external key; only the Databricks CLI profile | `DEMO_SCRIPT.md` Act 1 |
| `ChatDatabricks` (CHAT_MODEL), `get_weather` (TOOL) captured by autolog | Act 1 |
| 7 spans → 10 with one app boundary + two manual spans | Acts 1–2; `tr-054cbbc9…`, `tr-0cb5f6d2…` |
| 3 traces, 1 session `lab-f005-…`; turn 3 recalls from history with no tool call | Act 3; `tr-6f99921d…` |
| Unhandled → trace `ERROR`; handled → child span `ERROR`, trace `OK` | Act 4; `tr-193c937a…` |
| 4,304 ms slowest; $0.000121 most expensive; usage is a `TraceInfo` field | Act 5 |
| 3 clean + 6 controls, 6/6 caught; right-city-wrong-fact caught only by `answers_expected_fact`, self-contradiction by `self_consistent`; means 0.67/0.63/0.67/0.89/0.89 | Act 5B |
| No-call trace: efficiency `yes`, correctness `no`; exact match `yes,no,no,no,no` twice | Act 5C |
| gpt-oss-20b vs llama-4-maverick: identical verdicts, ~13% faster, ~7.5× cost, one trace per arm | experiment 013 |

Do **not** add "production-ready", present a 1.0 mean as proof, call the LLM judges deterministic, or imply the A/B is a stability guarantee. Keep the toy-agent limit out of the 30-second cut; it lives in the speaker notes and `docs/FINDINGS_AND_LEARNINGS.md`.

---

## Optional 15-second cutdown

| Time | Voiceover | On screen |
| --- | --- | --- |
| 0:00–0:03 | "San Francisco weather. One MLflow trace, no API key." | `"What's the weather in SF?"` → `1 TRACE` |
| 0:03–0:08 | "Autolog sees the model and tool; manual spans take seven to ten." | `ChatDatabricks · get_weather` · `7 → 10 SPANS` |
| 0:08–0:12 | "Six planted bad answers, six caught — not a 1.0 mean." | `6/6 CONTROLS CAUGHT` |
| 0:12–0:15 | "Efficient can still be wrong. Trace, inspect, measure, evaluate." | the closed loop |

---

## Implementation note

Single raea composition (React/TSX, `Camera3d`/`Mesh3d`) on one clock: 900 frames, one persistent waterfall, scenes as time-keyed components. Span names, IDs and numerals render as actual on-screen text — the 3D is never allowed to stand in for the subject. Send storyboard stills and the script to review with `raea show`.
