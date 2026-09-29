# Task for Claude Code — finish Part 2 in PrashobhPaul/JEV_Researchwork

Read CLAUDE.md first. Then, in this order, on a branch `part2`, opening a PR at the end:

1. **Repo hygiene.** Confirm `facetvec/` has: `facetvec/part2/` (render.py, templates/, this task
   kit), `configs/vscode.json`, `configs/vscode-lumma.json`, `configs/hf-datasets*.json`,
   `.github/workflows/facetvec-tests.yml` and `facetvec-evaluate.yml` scoped to the folder
   (`working-directory: facetvec`). Run the tests. Fix paths if the monorepo move broke any.

2. **Run the evaluation twice via the workflow, not locally.** Trigger `facetvec-evaluate` with
   `config=configs/vscode.json`, `max_records=400`, `refresh=true`; when it has committed, trigger
   it again with `config=configs/vscode-lumma.json`, `refresh=false` (reuse the snapshot).
   If the fetch step fails with "only N usable records", the vscode label mapping has drifted:
   inspect the label frequencies in the job log, correct `oracle.map` in both vscode configs,
   re-run. Do not lower `min_records` below 150.

3. **Check the run before trusting it.** In `facetvec/data/vscode/results.json`: typed queries ≥ 20,
   open queries = 60, every system present, labeller accuracy table present. If query-encoder
   accuracy is below 0.5, try one change only — rephrase `_query_question` in
   `facetvec/search/encoder.py` to a shorter, ticket-style instruction — re-run the lumma config
   only if the change affects it, and keep whichever encoder scores higher. Record what you tried
   in `facetvec/part2/README.md`.

4. **Render Part 2.** `pip install playwright && playwright install chromium`, ensure ffmpeg, then
   `python facetvec/part2/render.py --primary vscode --secondary vscode-lumma`. Inspect every PNG
   (open them) for overflow or clipped text; fix the template, not the numbers. Commit `part2/out/`.

5. **Post.** Edit `facetvec/part2/out/post.md` only for wording and length (< 3,000 chars). Do not
   change any number. If Lumma-Fev did NOT lose on vscode, replace the "surprise" paragraph with
   one honest sentence comparing the two labellers.

6. **PR.** Title "Part 2: facet vectors on vscode issues — results, assets, post". Body: the results
   table from README, the workflow run URLs, and the list of rendered files. Stop there; the owner
   reviews and merges from the phone.

Do not: add a paid API, add a Jev key, run on a GPU, rename metrics, or touch Part 1 assets.
