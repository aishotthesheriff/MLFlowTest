# Phase Closeout — Demo Packaging & Orientation (2026-11-19 → 20)

**State:** demo kit complete and green; working tree clean. This doc closes the *packaging/orientation* phase that followed the 14-experiment lab. The experiment ledger, decisions and lab-level next steps stay in [`WRAP_UP.md`](WRAP_UP.md) — this doc covers what was added since and what to do next.

## 1. What this phase was for

The lab itself was already done. This phase turned it into something presentable and navigable: a short narrated video with the real evidence on screen, a one-page reference for the steps and systems, and a map a newcomer can read like a system diagram. Nothing in the tracing or evaluation code changed.

## 2. What shipped

| Deliverable | Where | State |
| --- | --- | --- |
| 30-second 3D infographic script, **v2** | `DEMO_VIDEO_SCRIPT.md`, commit `98beb41` | Replaced v1 (`855104d`, "too abstract, no real subject") with six concrete scenes naming the San Francisco question, `ChatDatabricks` / `get_weather` / `preprocess` / `postprocess`, `7 → 10 spans`, session `lab-f005-1795028845`, `4,304 ms`, `$0.000121`, `6/6 caught`, the five scorer means and the gpt-oss-20b vs llama-4-maverick footer. Honest limits retained. |
| Raea composition + render | `~/Documents/raea/mlflowtest/projects/mlflow-tracing-infographic/` | Brief, storyboard, `plan.org` and composition rebuilt to match v2. `out/mlflow-tracing-infographic-v2.mp4`: 30 s, 900 frames, **0 errors / 0 warns**; stills in `out/stills-v2/`. v1 kept beside it. |
| One-page demo reference | `docs/DEMO_AT_A_GLANCE.md`, commit `68f0355` | Systems table, steps 0–8 with commands, through-line and limit; links to the full script and talk track. |
| Architecture map | `floorplan/index.html`, served at **http://127.0.0.1:4378** | Six chips — Trace the weather agent, Measure and score, Search the weather notes, Run and repeat the demo, plus MLflow 3 and Databricks externals. 18/18 code files described, 0 unassigned, 31 links, two guided flows, five-stop tour. Ask bar works through the Claude Code CLI. Map and `CLAUDE.local.md` note are local-only (self-gitignored / locally excluded). |

## 3. Verification done

- **Video:** full 900-frame render clean; `raea check` 0 errors, all text fits and clears the UI safe area. On-screen text OCR'd from downscaled stills with macOS Vision — all six scenes and all four extruded 3D span labels read correctly. The 6/6-known-controls scene was fixed to show six green gates, not two red ones.
- **Docs:** `git diff --check` clean; GitNexus change analysis showed no affected processes for the doc edits.
- **Floorplan:** build clean — 0 unassigned, no plain-language warnings, health found nothing. The endpoint sign-in check had nothing to inspect (this repo has no server routes), so that dimension is untested, not passed.
- **Git:** all three repo deliverables committed on `main`; `git status` clean.

## 4. Known limits — carry these forward

1. **The video has not been seen by a human.** OCR verifies text, not colour, layout or motion. The raea app is not installed, so no reviewable item was posted; open `out/mlflow-tracing-infographic-v2.mp4` directly and judge it by eye.
2. **The map shows code only.** 33 docs, 17 assets, 8 data and 3 config files are deliberately off the board — add `docs` to `include` in `floorplan/architecture.json` if the experiment write-ups should appear.
3. **The map can go stale.** It is a local artifact, rebuilt on request; re-run the floorplan skill after code changes.
4. **Two stale artifacts remain by design:** the v1 video and the v1 script commit. Do not present either as current.

## 5. Roadmap

### Near term — finish the packaging
1. **Review the v2 video by eye.** If it reads well, promote it to the canonical output name and link it from `DEMO.md` and the README; if not, iterate on the composition while the six-scene storyboard stays fixed.
2. **Wire up the new docs.** `DEMO.md` line 42 still describes the video script generically and neither `DEMO.md` nor `README.md` links `DEMO_AT_A_GLANCE.md`. Add both links so the one-pager and video are discoverable from the kit's entry points.
3. **Keep the kit green.** `./start_demo.sh --check-only` before any demo; refresh the floorplan after any code change.

### Medium — learning breadth (from `WRAP_UP.md` §8)
4. **Extend F-006.** Add a retrieval-relevance scorer over `RETRIEVER` spans, then an embedding A/B (`gte-large-en` vs `bge-large-en`). BEIR/SciFact is the identified corpus (5,183 abstracts, 1,109 queries); propose a backlog item before loading it.
5. **F-016 — judge trust.** Add a legitimate failure-plus-retry control to probe efficiency false positives, then compare an LLM `Correctness` check with `expected_facts` against the deterministic check on human-labelled examples. F-011 (UC storage) stays deferred; F-013 stays parked.

### Retirement hygiene
6. Tear down the billable `mlflow_lab_vec` endpoint when the lab is retired. Keep the honest limits attached to every presentation: toy agent, short answers, scripted tool cases, one clean A/B record per arm, one small RAG corpus.
