# data-analyst — a self-driving data analyst on open models, scored against planted root causes

Give it a dataset and a broad objective — *"revenue fell; why?"* — and it decides what to check, writes
the SQL, reads the result, updates its hypotheses, and keeps going until it can name the cause:

```
objective + table → hypotheses → next check → SQL → result → update hypotheses → … → report
                     (planner)                 (coder)                     (planner)
```

The idea comes from Sumanth's
[self-driving data analyst](https://github.com/Sumanth077/Hands-On-AI-Engineering/tree/main/ai_agents/self_driving_data_analyst),
which runs the same loop on the Liner Model API and lets Liner's router send each call to the cheapest
adequate model. This is a fresh implementation with two changes that matter here:

1. **Open models only.** The routing idea stays — a larger *planner* owns the hypotheses and the decision
   to stop; a smaller *coder* only turns one concrete check into one SQL query — but both are open-weights
   models run on the free GitHub runner (or any self-hosted OpenAI-compatible server). No paid API.
2. **A score, not a demo.** Every dataset has a **planted** root cause, so the report's answer is checked
   exactly — no LLM judge — and compared against a no-model baseline that an analyst would try first.

## Results

<!-- results:start -->
<!-- results:end -->

<!-- results:open-models:start -->
**Planner:** Qwen/Qwen2.5-1.5B-Instruct. **Coder:** Qwen/Qwen2.5-Coder-0.5B-Instruct. **Budget:** 6 checks per scenario. **Run:** 2026-09-29 17:00 UTC on Linux / 4 cpu.

| Scenario | Planted cause | Baseline (largest drop) | Agent | Agent steps |
|---|---|---|---|---:|
| region_closure | region=West | ✓ region=West | ✗ broad-based | 6 |
| price_increase | category=Electronics | ✓ category=Electronics | ✗ broad-based | 6 |
| channel_outage | channel=Online | ✓ channel=Online | ✗ broad-based | 6 |
| wholesale_churn | customer_type=Wholesale | ✓ customer_type=Wholesale | ✗ broad-based | 6 |
| stockout | product=ELE-01 | ✓ product=ELE-01 | ✗ broad-based | 6 |
| interaction | region=West & channel=Online | ½ region=West | ✗ broad-based | 6 |
| broad_decline | broad-based | ✗ customer_type=Wholesale | ✓ broad-based | 6 |

**Exact root cause:** baseline 5/7, agent 1/7. **Mean overlap (Jaccard):** baseline 0.786, agent 0.143.

**Usage by tier:** planner 49 calls, 51,022 in / 11,333 out tokens; coder 49 calls, 23,947 in / 2,072 out tokens.
<!-- results:open-models:end -->

The numbers above are written by the `data-analyst-evaluate` workflow; nothing is typed by hand.

## The benchmark

Seven scenarios share one seasonal baseline — 16 weeks of orders across region, channel, category,
product and customer type — and change one thing in the last 8 weeks:

| Scenario | Planted cause | What changed |
|---|---|---|
| region_closure | region=West | West lost 70% of orders |
| price_increase | category=Electronics | prices +40%, units per order −60% |
| channel_outage | channel=Online | online lost 85% of orders |
| wholesale_churn | customer_type=Wholesale | wholesale orders −75% |
| stockout | product=ELE-01 | the best-selling product went out of stock |
| **interaction** | region=West **&** channel=Online | only online orders in the West dropped (−90%) |
| **broad_decline** | *none — broad-based* | every slice lost ~25% |

**Scoring.** The agent must end with a `root_cause`: a list of `dimension=value` conditions, or `[]` for
"broad-based". *Exact* means the same set as the planted one; *overlap* is the Jaccard index, so naming
only West in `interaction` scores 0.5. A reply with no usable answer scores zero — it never counts as
"broad-based".

**Baseline.** One query per dimension, blame the value with the largest absolute revenue drop
(`analyst/baseline.py`). On a single-slice cause it is hard to beat — it gets all five. It cannot find an
interaction and cannot say "broad-based", which is exactly where an agent that reasons over evidence
should earn its keep. If the agent does not beat this baseline, the loop is not worth its tokens.

## Run it yourself

1. **Actions → data-analyst-evaluate → Run workflow.** Pick a config and, optionally, a comma-separated
   subset of scenarios. The run commits `results/<name>.json` and this README's results section.
2. Locally: `pip install torch transformers accelerate && python -m analyst --config configs/open-models.json`.
3. Bigger models on your own machine: start Ollama (or any OpenAI-compatible server), set
   `LOCAL_LLM_BASE_URL`, and use `configs/ollama-example.json`.

`python -m pytest` runs the fast tests with scripted models — no download.

## What this is not

* **Synthetic data.** The causes are planted so the answer is checkable; real data has several causes at
  once and no answer key. This measures whether the loop can find a cause that is there, not whether it
  finds the right one in the wild.
* **Small models on a CPU.** The default pair (1.5B planner, 0.5B coder) is what fits the free runner's
  16 GB. It is a floor, not a ceiling; the configs make a bigger pair a one-line change.
* **SQL only.** The original also runs Python; one read-only SQL tool keeps the sandbox trivial and is
  enough for these questions.
* **Seven scenarios, one seed.** Differences of one scenario are anecdotes. Add seeds before drawing
  conclusions.

## Layout

```
analyst/data.py       scenarios, the planted causes, the orders table
analyst/tools.py      read-only SQL, capped output
analyst/baseline.py   the no-model "largest drop" baseline
analyst/llm.py        open-model backends (transformers, OpenAI-compatible self-hosted, scripted)
analyst/agent.py      the loop, the parsers, the scoring
analyst/evaluate.py   runs baseline + agent on every scenario, writes results
configs/              model pairs
results/              written by CI
```

## Credits

Loop and framing: [Hands-On-AI-Engineering / self_driving_data_analyst](https://github.com/Sumanth077/Hands-On-AI-Engineering/tree/main/ai_agents/self_driving_data_analyst).
Models: [Qwen2.5](https://huggingface.co/Qwen) (Apache-2.0).
