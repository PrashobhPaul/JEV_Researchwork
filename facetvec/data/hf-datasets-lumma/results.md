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
