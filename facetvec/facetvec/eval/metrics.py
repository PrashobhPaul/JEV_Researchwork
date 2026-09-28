from __future__ import annotations

import math


def precision_at(ranked: list[int], truth: set[int], k: int) -> float:
    top = ranked[:k]
    return sum(1 for r in top if r in truth) / k if top else 0.0


def recall_at(ranked: list[int], truth: set[int], k: int) -> float:
    return sum(1 for r in ranked[:k] if r in truth) / len(truth) if truth else 0.0


def mrr_at(ranked: list[int], truth: set[int], k: int) -> float:
    for i, r in enumerate(ranked[:k], 1):
        if r in truth:
            return 1.0 / i
    return 0.0


def ndcg_at(ranked: list[int], truth: set[int], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, r in enumerate(ranked[:k], 1) if r in truth)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(truth), k) + 1))
    return dcg / ideal if ideal else 0.0
