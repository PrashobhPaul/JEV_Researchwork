**Part 2 — Embeddings you can read.**

Part 1 put a decision model in front of retrieval. This one puts it inside the index.

An embedding answers "what is this like?"
A facet vector answers "what is this?"

**The idea (Kieran Klaassen's, from Truffler — not mine)**
Ask a decision model a handful of typed questions about every record: kind, area, platform, "is this a regression". Store the answers as a vector where every dimension has a name. Encode the query the same way — filter, prefer or ignore each facet — and fuse the facet score with BM25 and a dense vector.

Every result can say why it matched.

**What I measured**
$n_records real closed GitHub issues from $corpus. $n_questions questions. Ground truth from the repository's own labels. No LLM judge.
• $n_typed typed queries ("bug reports in the terminal") — what facets are for
• $n_open open queries (an issue's title, against an index that never saw titles) — what dense vectors are for

**What the numbers said** (typed nDCG@$k / open MRR@$k)
→ BM25: $bm25_typed_ndcg / $bm25_open_mrr
→ Dense (bge-small): $dense_typed_ndcg / $dense_open_mrr
→ Facets alone: $facets_typed_ndcg / $facets_open_mrr
→ **Fused: $fused_typed_ndcg / $fused_open_mrr**
→ Facets with perfect labels (ceiling): $oracle_typed_ndcg

The uncomfortable part: facets alone lost to dense on typed queries. A 0.5B chat model, read through its logits (AnyJev's recipe, no training), got "area" right $area_acc_pct of the time.

Same index, perfect labels: $oracle_typed_ndcg.

The idea isn't the bottleneck. The labeller is.

Fused won the typed queries — and paid for it on open ones ($fused_open_mrr vs dense's $dense_open_mrr).

**Fuse, never replace. Then measure what fusing costs.**

**The surprise**
Lumma-Fev, a purpose-built 0.6B decision model, labelled the same issues worse: facets alone $secondary_typed_ndcg, "kind" right only $secondary_kind_acc_pct of the time.

But it read the queries far better: $secondary_encoder_acc_pct intent accuracy vs $encoder_acc_pct.

Long, code-heavy issue bodies are far from ticket-shaped states, and I did not tune its prompts. A search query is exactly that shape.

A benchmark chart is not your corpus.

**Where it stops**
• Closed-world: a facet only retrieves what a question anticipated.
• The vocabulary is the schema. The repo's labels drifted mid-experiment and I had to add an area. Reword a question, re-label the corpus.
• The model that reads documents best and the model that reads queries best were different models. Pick per job, and test both.
• Labeller accuracy on "kind": $kind_acc against a $kind_majority majority baseline. The oracle ceiling shows how much is the small model, not the idea.
• Scores rank. They are not calibrated probabilities.

Code, corpus snapshot, cached answers, and the CI runs that wrote every number: $repo_url

A vector you cannot read is a vector you cannot argue with.

Which of your retrieval questions are actually typed — and do you know what your labeller gets wrong?

#GenAI #RAG #AgenticAI #LLMOps #AIQuality
