# facetvec — embeddings you can read

An embedding answers *"what is this like?"*. A facet vector answers *"what is this?"*.

`facetvec` asks a decision model a handful of typed questions about every record in a corpus and
stores the answers as a vector whose every dimension has a name:

```
#5628  fix(ui): open terminal links from session-less login shells
       kind      bug .91 · feature .05 · debt .03 · question .01
       area      terminal .84 · workbench .09 · …
       platform  any .77 · linux .12 · …
       regression yes .31        crash yes .08        has_repro yes .88
```

A search query is encoded the same way — for each facet the query either **filters** on an option,
**prefers** it, or **ignores** it — and the facet score is fused with BM25 and a dense embedding.
Every result can say *why* it matched.

This repository is the experiment behind the post, not a library. It evaluates the idea on real
GitHub issues, against real dense and lexical baselines, with ground truth that comes from the
repository's own labels — no LLM judge anywhere. The numbers below are written by the CI run.

## Results

<!-- results:start -->
<!-- results:end -->

<!-- results:hf-datasets:start -->
### hf-datasets — `configs/hf-datasets.json`

**Corpus:** huggingface/datasets — 60 real issues, labelled with 3 questions. 
**Decision model:** logit-readout:Qwen2.5-0.5B-Instruct:r2:a1.0. **Dense model:** BAAI/bge-small-en-v1.5. **Run:** 2026-09-28 18:46 UTC on Linux / 1 cpu.

| System | typed P@10 | typed R@10 | typed nDCG@10 | open R@10 | open MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 (lexical) | 0.240 | 0.145 | 0.251 | 0.982 | 0.886 |
| Dense (embeddings) | 0.360 | 0.170 | 0.391 | 1.000 | 0.960 |
| **Facets** (model labels + model query encoding) | 0.540 | 0.429 | 0.645 | 0.036 | 0.022 |
| **Fused** RRF(BM25 + dense + facets) | 0.480 | 0.342 | 0.521 | 1.000 | 0.932 |
| Facets — oracle labels (ceiling) | 0.700 | 0.744 | 1.000 | 0.055 | 0.036 |
| Fused — oracle labels (ceiling) | 0.660 | 0.686 | 0.867 | 0.982 | 0.929 |

5 typed queries (truth from the repository's own labels) and 55 open queries (a record's title → that record; titles are never indexed).

**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):

| Facet | n | accuracy | majority-class baseline |
|---|---:|---:|---:|
| kind | 60 | 0.700 | 0.500 |
| area | 60 | 0.583 | 0.800 |

**Query encoder accuracy** on typed queries (right facet role and option, per facet): 0.467

**Matched because** — top fused results for a typed query, with the facet evidence:

- *bug reports*
  - ✓ #2470 Crash when `num_proc` > dataset length for `map()` on a `datasets.Dataset`. — kind=bug (0.96), traceback=yes (0.53)
  - ✓ #2645 load_dataset processing failed with OS error after downloading a dataset — kind=bug (0.96), traceback=yes (0.40)
  - ✓ #2643 Enum used in map functions will raise a RecursionError with dill. — kind=bug (0.93), traceback=yes (0.53)
- *enhancement requests*
  - ✗ #1064 Not support links with 302 redirect — kind=enhancement (0.09), traceback=yes (0.36)
  - ✗ #2262 NewsPH NLI dataset script fails to access test data. — kind=enhancement (0.09), traceback=yes (0.71)
  - ✓ #2736 Add Microsoft Building Footprints dataset — kind=enhancement (0.71), traceback=yes (0.08)

Timing: labelling 0.0 min for 60 records; decision cache 714 entries; model calls this run 0.
<!-- results:hf-datasets:end -->

<!-- results:hf-datasets-lumma:start -->
### hf-datasets-lumma — `configs/hf-datasets-lumma.json`

**Corpus:** huggingface/datasets — 60 real issues, labelled with 3 questions. 
**Decision model:** lumma-fev:Lumma-fev-0.6b. **Dense model:** BAAI/bge-small-en-v1.5. **Run:** 2026-09-28 18:44 UTC on Linux / 1 cpu.

| System | typed P@10 | typed R@10 | typed nDCG@10 | open R@10 | open MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 (lexical) | 0.240 | 0.145 | 0.251 | 0.982 | 0.886 |
| Dense (embeddings) | 0.360 | 0.170 | 0.391 | 1.000 | 0.960 |
| **Facets** (model labels + model query encoding) | 0.100 | 0.081 | 0.145 | 0.109 | 0.061 |
| **Fused** RRF(BM25 + dense + facets) | 0.440 | 0.306 | 0.443 | 0.927 | 0.843 |
| Facets — oracle labels (ceiling) | 0.700 | 0.744 | 1.000 | 0.036 | 0.011 |
| Fused — oracle labels (ceiling) | 0.660 | 0.686 | 0.867 | 0.927 | 0.792 |

5 typed queries (truth from the repository's own labels) and 55 open queries (a record's title → that record; titles are never indexed).

**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):

| Facet | n | accuracy | majority-class baseline |
|---|---:|---:|---:|
| kind | 60 | 0.450 | 0.500 |
| area | 60 | 0.733 | 0.800 |

**Query encoder accuracy** on typed queries (right facet role and option, per facet): 0.400

**Matched because** — top fused results for a typed query, with the facet evidence:

- *enhancement requests*
  - ✗ #1064 Not support links with 302 redirect — area=other (1.00)
  - ✗ #2262 NewsPH NLI dataset script fails to access test data. — area=other (1.00)
  - ✓ #883 Downloading/caching only a part of a datasets' dataset. — area=other (0.04)
- *things that are broken about a specific dataset*
  - ✗ #1992 `datasets.map` multi processing much slower than single processing — traceback=yes (0.54)
  - ✗ #1593 Access to key in DatasetDict map — traceback=yes (0.88)
  - ✗ #797 Token classification labels are strings and we don't have the list of labels — traceback=yes (0.22)

Timing: labelling 3.8 min for 60 records; decision cache 714 entries; model calls this run 119.
<!-- results:hf-datasets-lumma:end -->

### How to read the table

* **typed** queries are what facets are for: *"bug reports about the terminal on windows"*. Truth is
  every record whose repository labels match. Facets should win here; if they don't, the labeller is
  the problem (see the accuracy table).
* **open** queries are what dense vectors are for: a record's own title, against an index that never
  saw titles. Facets alone should lose badly here — that is the point, not a bug. Fused should stay
  close to dense.
* **oracle** rows use the repository's labels as if the decision model had been perfect. They are the
  ceiling of the method and show how much of the gap is the small model rather than the idea.
* Two labellers run on every corpus (`<name>` = Qwen logit readout, `<name>-lumma` = Lumma-Fev-0.6B).
  Same corpus, same queries, same baselines; only the decision model changes.

## How it works

```
corpus.jsonl ─► labeller  (decision model, N typed questions per record) ─► facets.json
             ├► embedder (bge-small-en-v1.5, CPU)                         ─► dense.npz
             └► BM25                                                       ─► in memory

query ─► encoder  (decision model: per facet → filter / prefer / ignore)  ─► facet score ─┐
      ├► dense cosine ────────────────────────────────────────────────────────────────────┼─► RRF ─► results + "matched because"
      └► BM25 ────────────────────────────────────────────────────────────────────────────┘
```

* **Decision model — three adapters, one interface.** `evaluate(state, questions) -> {name: Answer}`.
  * `logit-readout` (default in CI): any local chat model turned into a decision model by reading option
    probabilities off the next-token logits — the [AnyJev](https://github.com/nokia-applied-research/AnyJev)
    recipe (option-order rotation, empty-document prior correction), reimplemented minimally with a
    KV-cached document prefix. Default `Qwen/Qwen2.5-0.5B-Instruct`; ~9 s per issue on one core.
  * `lumma-fev`: [Lumma-Fev-0.6B](https://huggingface.co/FrontiersMind/Lumma-fev-0.6b),
    an open (Apache-2.0) decision model with the same three primitives as Jev, called natively through
    `model.decide()`. One forward pass scores every question; ~4 s per issue on one core in bfloat16.
    Configs ending in `-lumma.json` use it, so the two labellers are compared on the same corpus. On
    the first slice it lost to the logit readout (see results) — its prompts were not tuned, and long
    code-heavy issue bodies are far from the ticket-shaped states it was trained on.
  * `systemone-api`: any server that speaks `/v1/systemone` — TypeSafe's hosted Jev,
    `lumma-fev-serve`, or Laya served locally through Unsloth Desktop. Not exercised in CI.
* **Three primitives.** `Choice` (one of N, a probability each), `Score` (an ordered scale),
  `Noul` (a yes/no as a probability). Same vocabulary as Jev, so questions written for one adapter
  run unchanged on another.
* **Cache.** Every answer is cached in SQLite, keyed by adapter, question fingerprint and state hash.
  Rewording a question invalidates only that question's answers. The cache is committed, so re-runs
  in CI are free.
* **Ground truth.** The repository's labels are mapped to oracle facets by a config (`configs/*.json`).
  The model never sees labels. Typed queries are generated from facet combinations with phrase
  banks; open queries are titles.

## Run it yourself

Everything runs in GitHub Actions on the free runner; no keys, no GPU, no cost.

1. Fork the repository.
2. **Actions → facetvec-evaluate → Run workflow.** Config paths are relative to `facetvec/`. Pick a config (`configs/vscode.json` by default — Qwen logit
   readout; `configs/vscode-lumma.json` for the Lumma-Fev-0.6B labeller), the number of records, and
   whether to refresh the corpus snapshot. Each config writes its own results section below.
3. The workflow fetches the issues with the built-in `GITHUB_TOKEN`, labels them, embeds them,
   runs both query families, and commits `data/<corpus>/` and this README's results section.

To point it at another repository, copy a config and edit the `oracle` label mapping and the
`phrases` used to build typed queries. The fetch step fails loudly if fewer than `min_records`
issues survive the mapping.

## What this is not

Honest limits, so the results are read correctly:

* **Scores are not calibrated probabilities out of the box.** FrontiersMind say so about Lumma-Fev
  and it is true of the logit readout too: 0.82 means "more than 0.60", not "82% correct". The
  filter/prefer thresholds in the configs were not tuned on held-out data; a production index would
  fit them on labelled traffic.
* **A 0.6B model is not Jev 1.13.** Labeller accuracy is reported next to the majority-class baseline
  for exactly that reason. The oracle rows show the ceiling; the gap is mostly the model. Swap
  `model_name` for `Lumma-fev-4b` or `-9b` on a GPU runner, or point `systemone-api` at hosted Jev,
  and the pipeline is unchanged.
* **Closed-world.** A facet vector can only retrieve what a question anticipated. Open-world
  questions belong to dense vectors; that is why the recommended system is the fusion, and why the
  open-query column exists.
* **Document-level facets, chunk-level retrieval is the real problem.** Long documents get one
  vector here; a production index needs facets per chunk or per section.
* **The vocabulary is the schema.** Add or reword a question and the corpus is re-labelled (the
  fingerprint makes that safe, not free).
* **Single small corpus, one seed.** A few hundred records and ~100 queries. Directionally useful,
  not a benchmark.
* **A classifier fine-tuned on a stable label set will still beat this** on cost, latency and
  accuracy. The case for a decision model is day one: labels defined at run time, no training data.

## Production path

Chunk-level facets · label fingerprints with a backfill ledger and spend cap (see
[Truffler](https://github.com/kieranklaassen/truffler)'s design) · facets in a real store
(pgvector column or a `facets` table beside the vector index) · `facet_first` as a route the query
router can choose · re-label on entropy rather than on schedule · a labelled query set per corpus,
refreshed as the corpus changes.

## Related work, same instinct

* [Truffler](https://github.com/kieranklaassen/truffler) — labels beside keyword and vector search,
  query roles filter / prefer / ignore, label fingerprints and spend ledgers. The design this borrows.
* [jevgrep](https://github.com/dzhng/jevgrep) — "find code by asking what it does": a repository
  question in, hierarchical Jev classification over files, relevant files and reading leads out.
  The same move, aimed at code. Its release notes report 6/10 and 7/10 SWE-bench-subset tasks against
  an 8/10 baseline at lower Sol cost — honest about the tradeoff, which is the standard to hold to.
* [AnyJev](https://github.com/nokia-applied-research/AnyJev) — decisions from any LLM's logits.
* [Lumma-Fev](https://www.frontiersmind.ai/blog/lumma-fev/index.html) — 0.1B → 9B open decision
  models; their own four-task benchmark puts the 4B and 9B above Jev 1.13 and the 0.6B below it.
  Those are their numbers, on their tasks; this repository reports its own.
* Laya through [Unsloth](https://github.com/unslothai/unsloth) — a Jev-compatible `/v1/systemone`
  server on a 4 GB laptop; the `systemone-api` adapter targets exactly that.

## Credits

The idea of asking a model questions and using the answers as a readable vector is Kieran Klaassen's
(and his Rails gem, Truffler, is the honest implementation of it: labels *beside* text search, not
instead of it). The primitives are TypeSafe AI's Jev. The logit-readout method is AnyJev's; the alternate labeller is FrontiersMind's Lumma-Fev. The
dense baseline is BAAI's bge-small. The corpus belongs to the maintainers and contributors of the
repository it was fetched from.

## Layout

```
facetvec/
  schema.py              Choice / Score / Noul, vocabulary fingerprint
  decision/base.py       DecisionModel interface, SQLite answer cache
  decision/lumma_fev.py  Lumma-Fev adapter (native decide())
  decision/logit_readout.py   any-LLM adapter (AnyJev-style)
  decision/systemone_api.py   /v1/systemone HTTP adapter (Jev, lumma-fev-serve, Laya via Unsloth)
  decision/systemone.py  shared question/answer mapping
  decision/fake.py       keyword heuristic for tests only
  corpus/github_issues.py     GitHub API / JSONL loader, oracle facets from labels
  index/{facets,dense,lexical}.py
  search/{encoder,rank}.py    query → filter/prefer/ignore, facet score, RRF, explanations
  eval/{queries,metrics,run}.py
  cli.py                 fetch · label · embed · eval · report · all
configs/                 one JSON per corpus: source, label mapping, questions, phrase banks
data/<corpus>/           corpus snapshot, facets, cache, results (committed by CI)
.github/workflows/       evaluate.yml (manual), tests.yml (on push)
```

MIT licence.
