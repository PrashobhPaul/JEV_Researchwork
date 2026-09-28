"""A keyword heuristic that satisfies the DecisionModel interface. The test suite uses it so CI runs
in seconds without a model. It is never used for reported results."""
from __future__ import annotations

import re

from ..schema import Answer, Noul, Question


class KeywordModel:
    name = "keyword-heuristic"

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        text = state.lower()
        out: dict[str, Answer] = {}
        for q in questions:
            opts = list(q.options)
            counts = [
                len(re.findall(r"\b" + re.escape(o.replace("-", " ").split()[0]) + r"\w*", text)) for o in opts
            ]
            if isinstance(q, Noul):
                counts = [counts[0], 1]
            total = float(sum(counts))
            if total == 0:
                probs = {o: 1.0 / len(opts) for o in opts}
            else:
                probs = {o: c / total for o, c in zip(opts, counts)}
            srt = sorted(probs.values(), reverse=True)
            out[q.name] = Answer(probs, srt[0] - (srt[1] if len(srt) > 1 else 0.0))
        return out
