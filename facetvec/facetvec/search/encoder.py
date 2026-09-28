"""Query understanding: for every vocabulary question, decide whether the query filters on it,
prefers it, or ignores it (Truffler's three roles), and which option it wants.

The model encoder asks the decision model with the query as the state. The oracle encoder reads
the intent a typed evaluation query was built from; it is the ceiling, not a system anyone can run."""
from __future__ import annotations

from dataclasses import dataclass

from ..decision.base import DecisionModel
from ..schema import Answer, Choice, Noul, Question, Score, Vocabulary

NOT_MENTIONED = "not mentioned"


@dataclass(frozen=True)
class Intent:
    mode: str  # "filter" | "prefer" | "ignore"
    option: str | None = None
    weight: float = 1.0


QueryIntent = dict[str, Intent]


def _query_question(q: Question) -> Question:
    """Re-phrase an index-time question as a question about a search query."""
    if isinstance(q, Noul):
        return Noul(q.name, f"The document is a search query. The query asks only for items where: {q.question}")
    opts = tuple(q.options) + (NOT_MENTIONED,)
    text = (
        f"The document is a search query. Which of these does the query ask for, regarding {q.name.replace('_', ' ')}? "
        f"If the query does not say, answer '{NOT_MENTIONED}'."
    )
    return Choice(q.name, text, opts)


class ModelEncoder:
    def __init__(self, dm: DecisionModel, vocab: Vocabulary, filter_at: float = 0.6, prefer_at: float = 0.4):
        self.dm, self.vocab, self.filter_at, self.prefer_at = dm, vocab, filter_at, prefer_at
        self.qqs = [_query_question(q) for q in vocab.questions]

    def encode(self, query: str) -> QueryIntent:
        answers = self.dm.evaluate(query, self.qqs)
        intent: QueryIntent = {}
        for q, qq in zip(self.vocab.questions, self.qqs):
            a: Answer = answers[qq.name]
            if isinstance(q, Noul):
                p = a.p_yes
                if p >= self.filter_at:
                    intent[q.name] = Intent("filter", "yes")
                elif p >= self.prefer_at:
                    intent[q.name] = Intent("prefer", "yes", p)
                else:
                    intent[q.name] = Intent("ignore")
                continue
            top, p = a.top, a.probs[a.top]
            if top == NOT_MENTIONED or p < self.prefer_at:
                intent[q.name] = Intent("ignore")
            elif p >= self.filter_at:
                intent[q.name] = Intent("filter", top)
            else:
                intent[q.name] = Intent("prefer", top, p)
        return intent


class OracleEncoder:
    """Turns the {facet: option} a typed query was generated from into filters."""

    def __init__(self, vocab: Vocabulary):
        self.vocab = vocab

    def encode_from(self, truth_intent: dict[str, str]) -> QueryIntent:
        intent: QueryIntent = {q.name: Intent("ignore") for q in self.vocab.questions}
        for facet, option in truth_intent.items():
            intent[facet] = Intent("filter", option)
        return intent


def intent_accuracy(pred: QueryIntent, truth: dict[str, str], vocab: Vocabulary) -> tuple[int, int]:
    """(correct, total) over the facets in the truth: correct when the predicted mode is filter/prefer
    with the right option. Facets not in the truth count as correct only if ignored."""
    correct = total = 0
    for q in vocab.questions:
        total += 1
        p = pred.get(q.name, Intent("ignore"))
        if q.name in truth:
            correct += p.mode != "ignore" and p.option == truth[q.name]
        else:
            correct += p.mode == "ignore"
    return correct, total
