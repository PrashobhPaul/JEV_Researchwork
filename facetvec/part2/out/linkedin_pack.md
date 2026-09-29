# Part 2 — LinkedIn pack

**Post:** `post.md` (2,872 characters, every number filled from `data/vscode*/results.json`).
**Images, in posting order:** `explainer.png` (or `explainer_animated.mp4`) → `results_card.png` → `matched_because.png`.
`companion.png` is the single-image alternative for a text-first post.
**Final-results screenshots (from the repo README on github.com):** `github_results_vscode.png`, `github_results_vscode-lumma.png`.
**When:** Tue–Thu, 08:30–10:30 IST or 17:30–19:00 IST. Reply to every substantive comment in the first 3 hours.

Numbers below are quoted from the two committed `results.json` files; nothing in a reply should go beyond them.

## Comment-anticipation matrix

| # | Archetype | Predicted comment | Prepared reply | Risk |
|---|---|---|---|---|
| 1 | Skeptic | "This is just faceted search from 2005." | Fair — faceted search is old, and the ranking side here is deliberately boring. What's new is who fills the facets: a decision model at index time, and another read of the query at search time. The numbers show that's exactly where it breaks — perfect labels hit 1.000 typed nDCG, model labels 0.167. The old idea was never the problem; the labelling is. | ✅ |
| 2 | Skeptic | "Facets lost to dense. So the idea failed?" | Facets *alone* lost (0.167 vs 0.199). Same index with correct labels scores 1.000, and the fused ranking won the typed queries (0.250). That's a labeller-quality result, not a representation result — and because every dimension has a name, you can see which facet is failing (area: 9% vs a 45% majority baseline). Try doing that with 384 unnamed dimensions. | ⚠️ |
| 3 | Technical prober | "Why RRF and not a weighted sum?" | Because the scores aren't on the same scale — cosine, BM25 and facet probabilities aren't comparable, and none of them is calibrated. RRF only uses ranks, so it needs no tuning to be fair. A learned fusion is the obvious next step once there's a query log to fit it on. | ✅ |
| 4 | Technical prober | "How did you get ground truth without an LLM judge?" | From the repository's own labels. A config maps vscode labels to facet options (bug/feature/debt, area, platform…); typed queries are built from those combinations, and truth is every issue that carries them. Open queries are issue titles, and titles are never indexed. No model grades anything. | ✅ |
| 5 | Senior peer | "Only 20 typed queries — isn't that too small to conclude anything?" | Agreed, it's small, and I'd read the gaps as directional. The typed set is bounded by the labels themselves: a query needs at least 3 true results and can't match more than half the corpus. The per-query results are in results.json, and the whole run re-executes in CI — a bigger, better-labelled corpus is one config file away. | ⚠️ |
| 6 | Senior peer | "Why a 0.5B model? A frontier model would label this easily." | Deliberate: open weights, CPU-only, zero API cost, so anyone can re-run it. The labeller is a swappable adapter, and the oracle row is the upper bound whatever model you plug in. The trade worth measuring is quality per labelled record — you pay it once at index time, not per query. | ✅ |
| 7 | Technical prober | "Isn't Lumma-Fev unfair here? You said you didn't tune it." | Yes — and I said so in the post. Worth adding: it read *queries* at 80% intent accuracy vs 41% for the Qwen readout. Short, ticket-shaped text is its home ground; long code-heavy issue bodies aren't. The honest takeaway is "pick the model per job", not "model X is worse". | ✅ |
| 8 | Beginner | "What do nDCG and MRR mean?" | nDCG@10: did the right items show up in the top 10, and how high? 1.0 is perfect ordering. MRR@10: for a query with one right answer, how close to the top was it? 1.0 means first place every time. Typed queries use the first, open queries the second. | ✅ |
| 9 | Tangent-rider | "Would this work for images / PDFs / our knowledge base?" | Different failure surface, same discipline: pick the questions your users actually filter on, get gold labels for a sample, and measure accuracy per facet before trusting the index. The questions change by domain; the gate doesn't. | ✅ |
| 10 | Danger | "Is this running in production where you work?" | This repo is the experiment, and everything in it is public. The pattern I'd take into any enterprise knowledge platform is the gate, not the model: named facets for the filters people actually use, fused ranking, and per-facet labeller accuracy as a release check. | ⚠️ |
| 11 | Danger | "Which company/platform is this for?" | Can't discuss the who — happy to go deep on the how. The repo has everything needed to reproduce every number in the post. | ⚠️ |
| 12 | Praise | "Great post!" / "Very insightful 👏" | Thanks, {name}! If you try it on your own corpus, I'd love to know which facet breaks first. | ✅ |

## Danger comments — deeper replies

**#2 — "So the idea failed?"**
- *Round 2* ("but facets alone still lost"): "They did, on this corpus with this labeller. That's the point of keeping the oracle row: it separates 'the representation can't express this' from 'the model filled it in wrong'. Here it's the second. The fix is a better labeller for the facets that fail — which you can only target because each one has a name."
- *Exit:* "Enjoyed this — the repo has the per-facet numbers if you want to dig into which ones fail."

**#5 — "Too small to conclude anything"**
- *Round 2* ("then why post it?"): "Because the method matters more than the leaderboard: repository labels as ground truth, an oracle ceiling, per-facet accuracy, and everything reproducible in CI. The numbers are small-sample; the discipline isn't."
- *Exit:* "Fair challenge — if you have a well-labelled public corpus in mind, I'll point the rig at it."

**#10 — "Is this in production?"**
- Never answer yes or no. *Round 2* ("yes, but are *you* using it?"): "What I can share is the decision rule: no facet goes into the index until its labeller beats the majority-class baseline on a gold sample. Here, 'kind' passed (0.743 vs 0.693) and 'area' failed badly (0.090 vs 0.448) — so area would ship as a preference, not a filter."
- *Exit:* "DMs open if you want to compare notes on the gating."

## Pre-publish checks

- [x] Every number traces to `data/vscode/results.json` or `data/vscode-lumma/results.json`
- [x] Losses stated as prominently as wins (facets alone < dense; fused pays on open queries)
- [x] Oracle ceiling and labeller accuracy kept; "Where it stops" intact
- [x] Credits: Kieran Klaassen (idea, Truffler), AnyJev, Lumma-Fev; repo linked
- [x] No company, client or colleague names
- [x] Under 3,000 characters
