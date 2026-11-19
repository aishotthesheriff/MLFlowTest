# MLFlowTest Demo — GenAI tracing you can prove

About **7 minutes** (~9 with the optional bug-hunt beat). Everything runs from this repo against the Databricks workspace in `~/.databrickscfg`. No external LLM key, no local server.

**Story shape:** show the result first, explain it second, prove it third. The demo is a sequence of real traces already in `/Shared/my-first-trace`, with two short live runs.

| Act | What the audience sees | Time |
| --- | --- | --- |
| 1 | Cold open: one question, one live trace, no API key | ~1.5 min |
| 2 | "What you just saw": autolog + manual spans in one waterfall | ~1 min |
| 3 | Multi-turn: three traces, one session, cross-turn recall | ~1.5 min |
| 4 | Failure signatures: trace `ERROR` vs span `ERROR` | ~1 min |
| 5 | Proof: latency/cost + an evaluation run over stored traces | ~2 min |
| 5B (opt.) | The controls the old suite missed: wrong fact and self-contradiction | ~2.5 min |

## 1. Set up (before the demo)

One command verifies auth, the experiment, the eight evidence traces, and the scorer suite, then opens the deck and the Databricks experiment:

```sh
./start_demo.sh                 # preflight + open tabs
./start_demo.sh --check-only    # verification only, opens nothing
```

Manual steps if you prefer:

```sh
source .venv/bin/activate
python -c 'import mlflow; mlflow.set_tracking_uri("databricks"); print(mlflow.get_experiment_by_name("/Shared/my-first-trace"))'
open DEMO_DECK.html
```

Open **Tab 1** at `https://dbc-5c7ff528-845c.cloud.databricks.com/ml/experiments/1675992194464286/traces` (the **Traces** tab) and zoom to ~125% so the back of the room can read span names.

## 2. Companion artifacts

| File | Use it for |
| --- | --- |
| `DEMO_SCRIPT.md` | Full run-of-show: pre-flight, acts, exact commands, troubleshooting |
| `DEMO_SUMMARY_AND_TALK_TRACK.md` | One-page executive summary + 2–3 minute talk track |
| `DEMO_DECK.html` | 7-slide deck with real MLflow UI screenshots (keys: `→` next, `N` notes, `F` full screen); images live in `docs/demo/screenshots/` |
| `start_demo.sh` | Read-only preflight and tab opener (`--check-only`) |

## 3. If something goes wrong

See the troubleshooting card at the end of `DEMO_SCRIPT.md`. Most issues are auth (`~/.databrickscfg`), the wrong experiment, or a stale trace ID — the preflight catches all three before you start.

**Honest limit to say out loud:** the clean evaluation scores are 1.0 across 11 short weather answers from one toy agent; the pilot's six planted controls are caught 6/6 — including a right-city-wrong-fact hallucination and a self-contradictory answer that the original three-scorer suite passed — which proves the harness discriminates but not that an agent is production-ready. The lab writeups say the same.
