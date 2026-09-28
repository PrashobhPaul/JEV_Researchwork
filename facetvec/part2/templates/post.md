**Part 2 — Embeddings you can read.** Part 1 put a decision model in front of retrieval. This one puts it in front of the index.

An embedding answers "what is this like?". A facet vector answers "what is this?".

**The idea (Kieran Klaassen's, not mine)**
Ask a decision model a handful of typed questions about every record. Store the answers as a vector where every dimension has a name: kind, area, platform, "is this a regression". Encode the query the same way — filter, prefer or ignore each facet — and fuse the facet score with BM25 and a dense vector. Every result can say why it matched.

**What I measured** — $n_records real GitHub issues from $corpus, $n_questions questions, ground truth from the repository's own labels, no LLM judge. Two query families:
• typed ("bug reports about the terminal on windows") — what facets are for
• open (a record's title, against an index that never saw titles) — what dense vectors are for

**What the numbers said** (nDCG@$k typed / MRR@$k open)
• BM25 — $bm25_typed_ndcg / —
• Dense (bge-small) — $dense_typed_ndcg / $dense_open_mrr
• **Facets — $facets_typed_ndcg / $facets_open_mrr**
• Fused — $fused_typed_ndcg / $fused_open_mrr
• Facets with perfect labels (ceiling) — $oracle_typed_ndcg

Facets beat dense on typed queries by ${typed_multiple}×. Facets alone collapse on open queries. Fused holds dense's open score. **The failure column is the design decision: fuse, never replace.**

**The surprise**
A purpose-built 0.6B decision model ($secondary_model) scored $secondary_typed_ndcg on the same typed queries; a 0.5B chat model read through its logits (AnyJev's recipe, no training) scored $facets_typed_ndcg. Long, code-heavy issue bodies are far from ticket-shaped states, and I did not tune its prompts. A benchmark chart is not your corpus.

**Where it stops**
• Closed-world. A facet only retrieves what a question anticipated.
• The vocabulary is the schema: reword a question, re-label the corpus.
• Labeller accuracy on "kind": $kind_acc against a $kind_majority majority baseline. The oracle ceiling shows how much is the small model, not the idea.
• Scores rank; they are not calibrated probabilities until you fit thresholds on your traffic.

Everything is public — code, corpus snapshot, cached answers, the CI run that wrote the table: $repo_url

**A vector you cannot read is a vector you cannot argue with.** Which of your retrieval questions are actually typed?

#GenAI #RAG #AgenticAI #LLMOps
