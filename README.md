# JEV Research Work

Research experiments, one self-contained project per folder. Each project has its own README,
dependencies, tests, and committed results; CI workflows live in `.github/workflows/` and are
scoped to their project's folder.

| Project | What it tests | CI |
|---|---|---|
| [`facetvec/`](facetvec/) | Named facet vectors from a decision model (logit readout), evaluated against BM25 and dense retrieval on real GitHub issues, with ground truth from the repo's own labels | `facetvec-tests` (push/PR), `facetvec-evaluate` (manual) |
| [`data-analyst/`](data-analyst/) | A self-driving data analyst (planner + coder open models, investigate → SQL → update hypotheses) scored exactly against planted root causes, against a no-model baseline | `data-analyst-tests` (push/PR), `data-analyst-evaluate` (manual) |
