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
