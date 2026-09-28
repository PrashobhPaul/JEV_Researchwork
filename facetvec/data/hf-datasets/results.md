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
