**Part 2 — Embeddings you can read.**

Part 1 put a decision model in front of retrieval. This one puts it inside the index.

An embedding answers "what is this like?"
A facet vector answers "what is this?"

**The idea (Kieran Klaassen's, from Truffler — not mine)**
Ask a decision model a handful of typed questions about every record: kind, area, platform, "is this a regression". Store the answers as a vector where every dimension has a name. Encode the query the same way — filter, prefer or ignore each facet — and fuse the facet score with BM25 and a dense vector.

Every result can say why it matched.

**What I measured**
400 real closed GitHub issues from microsoft/vscode. 6 questions. Ground truth from the repository's own labels. No LLM judge.
• 20 typed queries ("bug reports in the terminal") — what facets are for
• 60 open queries (an issue's title, against an index that never saw titles) — what dense vectors are for

**What the numbers said** (typed nDCG@10 / open MRR@10)
→ BM25: 0.128 / 0.713
→ Dense (bge-small): 0.199 / 0.806
→ Facets alone: 0.167 / 0.036
→ **Fused: 0.250 / 0.734**
→ Facets with perfect labels (ceiling): 1.000

The uncomfortable part: facets alone lost to dense on typed queries. A 0.5B chat model, read through its logits (AnyJev's recipe, no training), got "area" right 9% of the time.

Same index, perfect labels: 1.000.

The idea isn't the bottleneck. The labeller is.

Fused won the typed queries — and paid for it on open ones (0.734 vs dense's 0.806).

**Fuse, never replace. Then measure what fusing costs.**

**The surprise**
Lumma-Fev, a purpose-built 0.6B decision model, labelled the same issues worse: facets alone 0.094, "kind" right only 30% of the time.

But it read the queries far better: 80% intent accuracy vs 41%.

Long, code-heavy issue bodies are far from ticket-shaped states, and I did not tune its prompts. A search query is exactly that shape.

A benchmark chart is not your corpus.

**Where it stops**
• Closed-world: a facet only retrieves what a question anticipated.
• The vocabulary is the schema. The repo's labels drifted mid-experiment and I had to add an area. Reword a question, re-label the corpus.
• The model that reads documents best and the model that reads queries best were different models. Pick per job, and test both.
• Labeller accuracy on "kind": 0.743 against a 0.693 majority baseline. The oracle ceiling shows how much is the small model, not the idea.
• Scores rank. They are not calibrated probabilities.

Code, corpus snapshot, cached answers, and the CI runs that wrote every number: github.com/PrashobhPaul/JEV_Researchwork

A vector you cannot read is a vector you cannot argue with.

Which of your retrieval questions are actually typed — and do you know what your labeller gets wrong?

#GenAI #RAG #AgenticAI #LLMOps #AIQuality
