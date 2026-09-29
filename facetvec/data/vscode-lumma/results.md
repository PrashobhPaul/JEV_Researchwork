**Corpus:** microsoft/vscode — 400 real issues, labelled with 6 questions. 
**Decision model:** lumma-fev:Lumma-fev-0.6b. **Dense model:** BAAI/bge-small-en-v1.5. **Run:** 2026-09-29 04:24 UTC on Linux / 4 cpu.

| System | typed P@10 | typed R@10 | typed nDCG@10 | open R@10 | open MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 (lexical) | 0.110 | 0.091 | 0.128 | 0.833 | 0.713 |
| Dense (embeddings) | 0.150 | 0.122 | 0.199 | 0.917 | 0.806 |
| **Facets** (model labels + model query encoding) | 0.080 | 0.053 | 0.094 | 0.017 | 0.002 |
| **Fused** RRF(BM25 + dense + facets) | 0.185 | 0.164 | 0.227 | 0.883 | 0.697 |
| Facets — oracle labels (ceiling) | 0.745 | 0.792 | 1.000 | 0.017 | 0.002 |
| Fused — oracle labels (ceiling) | 0.470 | 0.485 | 0.677 | 0.883 | 0.757 |

20 typed queries (truth from the repository's own labels) and 60 open queries (a record's title → that record; titles are never indexed).

**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):

| Facet | n | accuracy | majority-class baseline |
|---|---:|---:|---:|
| kind | 400 | 0.302 | 0.693 |
| area | 400 | 0.175 | 0.448 |
| platform | 400 | 0.973 | 0.973 |
| regression | 400 | 0.728 | 0.950 |
| crash | 400 | 0.552 | 0.978 |

**Query encoder accuracy** on typed queries (right facet role and option, per facet): 0.800

**Matched because** — top fused results for a typed query, with the facet evidence:

- *requests for new features*
  - ✓ #42880 Have a history for recently edited editors — kind=feature (0.98)
  - ✗ #335752 Agents: Keep new-session input stable while switching workspaces — kind=feature (0.94)
  - ✓ #338026 Announce new-session welcome phrases to screen readers — kind=feature (0.90)
- *requests for new features about the integrated terminal*
  - ✗ #327561 feat: Standardized Chat Panel Extension API (transcript access, scroll state, overlay deco — kind=feature (1.00)
  - ✗ #42880 Have a history for recently edited editors — kind=feature (0.98)
  - ✓ #327326 API: Provide a stable terminal session ID across window reloads — kind=feature (0.33)

Timing: labelling 87.4 min for 400 records; decision cache 2880 entries; model calls this run 332.
