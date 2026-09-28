"""Facet scoring, reciprocal-rank fusion, and the "matched because" explanation."""
from __future__ import annotations

from ..index.facets import Facets
from .encoder import Intent, QueryIntent

Ranked = list[tuple[int, float]]


def facet_search(intent: QueryIntent, facets: Facets, k: int = 50, min_score: float = 0.02) -> Ranked:
    """score = Π P(filter options) × (1 + Σ w·P(preferred options)). Empty when the intent has no
    filter and no preference: facets then have nothing to say, and fusion falls back to text."""
    filters = [(n, i) for n, i in intent.items() if i.mode == "filter" and i.option]
    prefers = [(n, i) for n, i in intent.items() if i.mode == "prefer" and i.option]
    if not filters and not prefers:
        return []
    scored: Ranked = []
    for rid, row in facets.items():
        s = 1.0
        for name, it in filters:
            s *= row.get(name, {}).get(it.option, 0.0)
            if s < min_score:
                break
        if s < min_score:
            continue
        boost = sum(it.weight * row.get(name, {}).get(it.option, 0.0) for name, it in prefers)
        scored.append((rid, s * (1.0 + boost)))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def rrf(*lists: Ranked, k: int = 60, top: int = 50) -> Ranked:
    acc: dict[int, float] = {}
    for lst in lists:
        for rank, (rid, _) in enumerate(lst, 1):
            acc[rid] = acc.get(rid, 0.0) + 1.0 / (k + rank)
    return sorted(acc.items(), key=lambda x: -x[1])[:top]


def explain(rid: int, intent: QueryIntent, facets: Facets) -> list[dict]:
    """Why a record matched: one line per facet the query cared about."""
    row = facets.get(rid, {})
    out = []
    for name, it in intent.items():
        if it.mode == "ignore" or not it.option:
            continue
        out.append({"facet": name, "option": it.option, "mode": it.mode, "p": round(row.get(name, {}).get(it.option, 0.0), 2)})
    return out
