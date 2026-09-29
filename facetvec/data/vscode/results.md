**Corpus:** microsoft/vscode — 400 real issues, labelled with 6 questions. 
**Decision model:** logit-readout:Qwen2.5-0.5B-Instruct:r2:a1.0. **Dense model:** BAAI/bge-small-en-v1.5. **Run:** 2026-09-28 22:03 UTC on Linux / 4 cpu.

| System | typed P@10 | typed R@10 | typed nDCG@10 | open R@10 | open MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 (lexical) | 0.110 | 0.091 | 0.128 | 0.833 | 0.713 |
| Dense (embeddings) | 0.150 | 0.122 | 0.199 | 0.917 | 0.806 |
| **Facets** (model labels + model query encoding) | 0.135 | 0.079 | 0.167 | 0.050 | 0.036 |
| **Fused** RRF(BM25 + dense + facets) | 0.205 | 0.186 | 0.250 | 0.900 | 0.734 |
| Facets — oracle labels (ceiling) | 0.745 | 0.792 | 1.000 | 0.017 | 0.008 |
| Fused — oracle labels (ceiling) | 0.470 | 0.485 | 0.677 | 0.883 | 0.774 |

20 typed queries (truth from the repository's own labels) and 60 open queries (a record's title → that record; titles are never indexed).

**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):

| Facet | n | accuracy | majority-class baseline |
|---|---:|---:|---:|
| kind | 400 | 0.743 | 0.693 |
| area | 400 | 0.090 | 0.448 |
| platform | 400 | 0.333 | 0.973 |
| regression | 400 | 0.172 | 0.950 |
| crash | 400 | 0.372 | 0.978 |

**Query encoder accuracy** on typed queries (right facet role and option, per facet): 0.408

**Matched because** — top fused results for a typed query, with the facet evidence:

- *requests for new features*
  - ✓ #42880 Have a history for recently edited editors — kind=feature (0.94), regression=yes (0.63), crash=yes (0.65), has_repro=yes (0.51)
  - ✓ #330671 Surface failing CI sessions in Omni Chat — kind=feature (1.00), regression=yes (0.65), crash=yes (0.59), has_repro=yes (0.47)
  - ✓ #338225 Agents Window: Populate New Session drafts from product protocol links — kind=feature (0.99), regression=yes (0.45), crash=yes (0.38), has_repro=yes (0.59)
- *engineering debt*
  - ✓ #329106 Restrict terminal auto-approval settings in untrusted workspaces — kind=debt (0.86), regression=yes (0.43), crash=yes (0.37), has_repro=yes (0.46)
  - ✓ #329042 Harden PowerShell terminal auto-approval parsing and default rules — kind=debt (0.89), regression=yes (0.60), crash=yes (0.30), has_repro=yes (0.62)
  - ✗ #336500 Long-running Agent Host sessions accumulate issue and pull-request references without clea — kind=debt (0.28), regression=yes (0.51), crash=yes (0.38), has_repro=yes (0.35)

Timing: labelling 0.0 min for 400 records; decision cache 3867 entries; model calls this run 80.
