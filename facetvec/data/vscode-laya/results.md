**Corpus:** microsoft/vscode — 400 real issues, labelled with 6 questions. 
**Decision model:** laya:english@55cf4c4. **Dense model:** BAAI/bge-small-en-v1.5. **Run:** 2026-09-29 17:16 UTC on Linux / 4 cpu.

| System | typed P@10 | typed R@10 | typed nDCG@10 | open R@10 | open MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 (lexical) | 0.110 | 0.091 | 0.128 | 0.833 | 0.713 |
| Dense (embeddings) | 0.150 | 0.122 | 0.199 | 0.917 | 0.806 |
| **Facets** (model labels + model query encoding) | 0.195 | 0.138 | 0.245 | 0.083 | 0.017 |
| **Fused** RRF(BM25 + dense + facets) | 0.200 | 0.176 | 0.231 | 0.833 | 0.490 |
| Facets — oracle labels (ceiling) | 0.745 | 0.792 | 1.000 | 0.050 | 0.029 |
| Fused — oracle labels (ceiling) | 0.470 | 0.485 | 0.677 | 0.883 | 0.710 |

20 typed queries (truth from the repository's own labels) and 60 open queries (a record's title → that record; titles are never indexed).

**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):

| Facet | n | accuracy | majority-class baseline |
|---|---:|---:|---:|
| kind | 400 | 0.800 | 0.693 |
| area | 400 | 0.075 | 0.448 |
| platform | 400 | 0.460 | 0.973 |
| regression | 400 | 0.380 | 0.950 |
| crash | 400 | 0.845 | 0.978 |

**Query encoder accuracy** on typed queries (right facet role and option, per facet): 0.842

**Matched because** — top fused results for a typed query, with the facet evidence:

- *requests for new features*
  - ✓ #42880 Have a history for recently edited editors — kind=feature (0.83)
  - ✓ #338225 Agents Window: Populate New Session drafts from product protocol links — kind=feature (0.86)
  - ✓ #336500 Long-running Agent Host sessions accumulate issue and pull-request references without clea — kind=feature (0.27)
- *engineering debt*
  - ✓ #329106 Restrict terminal auto-approval settings in untrusted workspaces — kind=debt (0.76)
  - ✗ #205598 Invoking deltaDecorations recursively could lead to leaking decorations. — kind=debt (0.15)
  - ✓ #329042 Harden PowerShell terminal auto-approval parsing and default rules — kind=debt (0.57)

Timing: labelling 67.5 min for 400 records; decision cache 2880 entries; model calls this run 480.
