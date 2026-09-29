# JEV_Researchwork — working notes for Claude Code

Research experiments about decision models (TypeSafe Jev and open alternatives) in an enterprise
knowledge platform. One self-contained project per folder. Owner works phone-only: every result
must be produced by a GitHub Actions workflow and committed, never by a local run on the owner's
machine. Never ask the owner to run a command.

## Projects

- `facetvec/` — named facet vectors from a decision model, evaluated against BM25 and dense
  retrieval on real GitHub issues. Ground truth comes from the repository's own labels; no LLM
  judge. Two labellers per corpus: `configs/<name>.json` (Qwen 0.5B logit readout, AnyJev-style)
  and `configs/<name>-lumma.json` (Lumma-Fev-0.6B, native `decide()`).
  - `python -m facetvec all --config configs/vscode.json` runs fetch → label → embed → eval → report.
  - `facetvec/part2/render.py` turns `data/<name>/results.json` into the LinkedIn Part 2 assets.

## Rules

1. Numbers in any post, image or README come from `results.json`. Never type a metric by hand.
2. Honest by default: report where facets lose (open queries) as prominently as where they win.
   Keep the oracle-ceiling rows and the labeller-accuracy table.
3. No company, client or colleague names anywhere in the repo or the post. "An enterprise
   knowledge platform" is the only description of the platform.
4. Do not weaken or remove the "Where it stops" / limits sections to make results look better.
5. Keep `data/<corpus>/decisions.sqlite` committed; it is the answer cache that makes CI re-runs free.
6. Workflows: `facetvec-tests` runs on push; `facetvec-evaluate` is manual (workflow_dispatch) and
   commits `facetvec/data/**` plus the README results section. Do not turn evaluate into a push trigger.
7. Small, reviewable commits with plain-English messages. Open a PR for anything that changes
   metrics or the post; merge only after tests pass.

## Part 2 — definition of done

- `facetvec-evaluate` has run for `configs/vscode.json` AND `configs/vscode-lumma.json`
  (400 records each), and both results sections are in `facetvec/README.md`.
- `facetvec/part2/out/` contains `explainer.png`, `explainer_animated.mp4`, `explainer_animated.gif`,
  `results_card.png`, `matched_because.png`, `post.md`, all rendered from the vscode results.
- `post.md` is under 3,000 characters, credits Kieran Klaassen (idea, Truffler), AnyJev, Lumma-Fev,
  links this repo, and keeps the "surprise" paragraph only if the Lumma row actually lost.
- A short `facetvec/part2/README.md` says which commit and workflow run produced the numbers.
