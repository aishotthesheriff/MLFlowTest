# 30-Second 3D Infographic — MLflow GenAI Tracing

**Runtime:** 0:30 exactly · **Format:** 16:9, 30 fps (900 frames) · **Voiceover:** 66 words, ~26 s spoken + ~4 s pauses

**Source:** the MLFlowTest demo kit — `DEMO_SCRIPT.md` (Acts 1–5C), `DEMO_SUMMARY_AND_TALK_TRACK.md`, `DEMO_DECK.html` (10 slides), experiments 001–014.

**Story:** one question becomes one trace; the trace becomes evidence; the evidence becomes a repeatable loop. Show the result first, prove it second, end on the loop — no terminal footage, no UI screenshots, no talking head.

---

## Visual system

- **Stage:** horizonless dark slate plane with a faint dot grid. One glowing **trace spine** stays on stage for all six scenes and accumulates meaning.
- **Palette:** background `#0A0E1A` · model spans amber `#FFB347` · tool spans violet `#A78BFA` · manual spans frosted white · data chips cyan `#38BDF8` · error red `#EF4444` · passing gates green `#34D399`.
- **Camera:** three-quarter view, ~25° above, slow continuous dolly-in; Scene 5 pushes closer to the gates; Scene 6 pulls back for the loop. No whip pans.
- **Motion grammar:** build → nest → split → pulse → emit → sort → lock. No bounce, no confetti.
- **Type:** extruded sans labels; numerals large, captions small, one line of on-screen text at a time.

---

## Scene 1 — The question (0:00–0:04)

**Voiceover:** "One question. One trace. No external key."

**On screen:** `ONE QUESTION → ONE TRACE`, then `NO API KEY`

**3D action:** A white query tile drops onto the plane. On impact it extrudes into a horizontal spine; seven short segments click into place along it. Camera begins its slow drift in.

**Sound:** soft click, low hum begins.

---

## Scene 2 — Spans nest (0:04–0:09)

**Voiceover:** "Model and tool spans appear; manual spans nest around them. Seven becomes ten."

**On screen:** `7 → 10 SPANS`

**3D action:** Amber blocks (model) and violet blocks (tool) light up on the spine. Translucent white hoops (manual spans) sweep in and wrap the blocks — they parent the autolog spans rather than sitting beside them. Counter ticks 7 → 10.

**Sound:** two warm pings, counter tick.

---

## Scene 3 — Turns group (0:09–0:13)

**Voiceover:** "Three turns, one session. Each keeps its own inputs."

**On screen:** `3 TURNS / 1 SESSION`

**3D action:** The spine duplicates into three parallel traces orbiting a thin session ring. A cyan memory thread runs from trace 1 to trace 3; trace 3's tool block stays dark — the answer came from history, not a tool call.

**Sound:** three light ticks, ring chime.

---

## Scene 4 — Failure signatures (0:13–0:18)

**Voiceover:** "Unhandled error: the whole trace turns red. Handled: one child span."

**On screen:** `TRACE ERROR ≠ SPAN ERROR`

**3D action:** Two copies of the spine, separated in depth. Left: a red pulse floods the entire trace. Right: only one child block flashes red while the outer spine holds its color and stamps a small `OK` badge.

**Sound:** low alert on the left, muted tick on the right.

---

## Scene 5 — Measure and score (0:18–0:24)

**Voiceover:** "Latency, tokens, cost ride on the trace. Six planted defects, six caught."

**On screen:** `6 / 6 CONTROL DEFECTS CAUGHT`

**3D action:** Three cyan chips — `ms`, `tokens`, `$` — lift off the spine and settle into a readout panel. The trace then flows through six gates. Four ordinary answers pass; two bad ones stop at dedicated gates labelled `FACT` and `CONSISTENCY`. Gate counter flashes 6/6.

**Sound:** crisp gate clicks, two distinct stop tones.

---

## Scene 6 — Behavior, then the loop (0:24–0:30)

**Voiceover:** "Judge what the agent did: efficient can still be wrong. Trace, inspect, measure, evaluate."

**On screen:** `EFFICIENT ≠ CORRECT` → `TRACE → INSPECT → MEASURE → EVALUATE`

**3D action:** Tool-call tokens snap into a sequence on the floor. On the no-call case, a correctness gate says `no` while an efficiency gate says `yes`. Camera pulls back as four nodes — trace, inspect, measure, evaluate — rise and lock into a closed loop above the spine. End card footer: `MLFlowTest · experiments 001–014`.

**Sound:** two opposing tones, one resolving chord, hum fades out.

---

## Accuracy guardrails

Every claim in the voiceover is backed by the demo kit:

| Claim | Source |
| --- | --- |
| "No external key" — the only credential is the Databricks CLI profile | `DEMO_SCRIPT.md` Act 1 |
| Seven spans become ten when manual spans wrap autolog spans | Acts 1–2 |
| Three turns, one session, each turn with its own inputs | Act 3 |
| Trace `ERROR` vs child-span `ERROR` with trace `OK` | Act 4 |
| Latency, tokens and cost are `TraceInfo` fields; no re-run | Act 5 |
| Six planted controls, 6/6 caught, including right-city-wrong-fact and self-contradiction | Act 5B |
| Efficiency says `yes` on the no-call trace where correctness says `no` | Act 5C |

Do **not** add "production-ready", a 1.0 mean as proof, or a claim that the judges are deterministic. The toy-agent limit stays in the speaker notes, not the 30-second cut.

---

## Optional 15-second cutdown

| Time | Voiceover | On screen |
| --- | --- | --- |
| 0:00–0:03 | "One question. One trace. No external key." | `ONE TRACE / NO API KEY` |
| 0:03–0:08 | "Spans nest; three turns group under one session." | `7 → 10 SPANS · 3 TURNS` |
| 0:08–0:12 | "Latency, tokens, cost from the trace. Six planted defects, six caught." | `6 / 6` |
| 0:12–0:15 | "Trace, inspect, measure, evaluate. Repeat." | the closed loop |

---

## Implementation note

Built as a single raea composition (React/TSX, `Camera3d`/`Mesh3d`) on one clock: 900 frames, one persistent spine mesh, scenes as time-keyed components, instanced gates. Send storyboard stills and the script to review with `raea show`.
