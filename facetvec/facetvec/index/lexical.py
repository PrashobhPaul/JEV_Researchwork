"""Lexical baseline: BM25 over a simple tokenisation."""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from ..corpus.github_issues import Record

_TOK = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOK.findall(text.lower())


class LexicalIndex:
    def __init__(self, recs: list[Record]):
        self.ids = [r.id for r in recs]
        self.bm25 = BM25Okapi([tokenize(r.text) for r in recs])

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(self.ids[i], float(scores[i])) for i in order if scores[i] > 0]
