# Part 2 kit

`render.py` fills `templates/` from `../data/<name>/results.json` and writes `out/`:
explainer (4:5 PNG + animated MP4/GIF with directional flow), results card (16:9), matched-because
card (16:9), and `post.md`. Every number in the outputs is read from results.json.

    pip install playwright && playwright install chromium   # plus ffmpeg on PATH
    python part2/render.py --primary vscode --secondary vscode-lumma

## Provenance of the published numbers

All numbers come from `facetvec-evaluate` runs on branch `part2` (GitHub-hosted runner, 4 CPU),
400 closed `microsoft/vscode` issues, one snapshot shared by both labellers.

| Labeller | Config | Workflow run | Results commit |
|---|---|---|---|
| Qwen2.5-0.5B-Instruct, logit readout | `configs/vscode.json` | [run 3](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36489233976) | `40ee9bc` |
| Lumma-Fev-0.6B, native `decide()`, float32 | `configs/vscode-lumma.json` | [run 6](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36514366131) | `d190f86` |

`out/` was rendered from those two `results.json` files at commit `c70bf08`:
`explainer.png` + `explainer_animated.mp4/.gif`, `results_card.png`, `matched_because.png`,
`companion.png` (single-image feed card), `post.md`, and `linkedin_pack.md` (posting order and a
prepared reply for every likely comment). `github_results_vscode.png` and
`github_results_vscode-lumma.png` are the README results sections as GitHub renders them on `part2`.

## What was tried before those runs, and why

1. **[Run 1](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36474575812)**
   (`63c546d`, fresh fetch) failed the sanity check: 12 typed queries (bar: ≥ 20). The vscode
   label mapping had drifted — recent vscode issues are mostly chat/agent work, so `area` was
   `other` for 352/400 issues, and `regression` missed the `recent-regression` label.
2. **Config fix** (`33aef99`, both vscode configs): `area` gains a `chat` option (mapped last, so
   a specific area label still wins); `workbench` also takes `file-explorer`, `titlebar`, `layout`;
   `regression` also takes `recent-regression`; three single-facet typed templates (`{area}`,
   `{regression}`, `{crash}`). Oracle facets are now re-derived from the snapshot's stored labels
   on every run (`679128b`), so the fix applied without re-fetching. `min_records` unchanged (150).
3. **[Run 2](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36484397092)**
   (`993ca85`): 20 typed + 60 open queries. Query-encoder accuracy with the original wording: see
   `query_encoder_accuracy` in that commit's `data/vscode/results.json`.
4. **Encoder change — the one allowed** (`9c113d1`): `_query_question` rephrased to a shorter,
   ticket-style instruction (`Search query. Field: <facet>. Which value does it ask for? …`).
   [Run 3](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36489233976) (`40ee9bc`)
   scored higher on the same 20 queries (0.383 → 0.408), so it was kept. Still below
   0.5; no further encoder changes were made.
5. **Lumma-Fev on the CPU runner.**
   [Run 4](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36490617457) loaded the
   model in `bfloat16` and labelled at 104–135 s per record (75/400 after 169 min — it would have
   needed ~15 h); cancelled. `configs/vscode-lumma.json` now uses `float32` (`c1e8922`), the
   adapter's own CPU default: same model, same questions, ~37 s per record in
   [run 5](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36506869848). Run 5 was
   cancelled deliberately at 148/400 to read its pace; the workflow now commits the answer cache on
   any failure (`b8b1765`), so the float32 answers were kept (`10214fb`) and
   [run 6](https://github.com/PrashobhPaul/JEV_Researchwork/actions/runs/36514366131) resumed from
   them. Every Lumma answer in the published numbers is a float32 answer.

## Known gaps

- The Lumma-Fev model code is fetched from the Hugging Face Hub at the latest revision on every run
  (`trust_remote_code`). Pin it with `decision_model.revision` in `configs/vscode-lumma.json` to make
  the Lumma row exactly reproducible.
- The Qwen query encoder stayed below 0.5 accuracy after the one allowed change (step 4). The Lumma-Fev encoder scored far higher on the same queries — `query_encoder_accuracy` in `data/vscode-lumma/results.json` — which makes a Qwen-labels + Lumma-encoder split the obvious next run.
