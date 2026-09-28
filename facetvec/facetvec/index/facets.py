"""Index-time labelling: ask the decision model every vocabulary question about every record and
store the probabilities. Also builds the oracle facet table (from the repository's labels) in the
same shape, so both can be searched by the same code."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..corpus.github_issues import Record
from ..decision.base import DecisionModel
from ..schema import Answer, Noul, Vocabulary

# facets: {record_id: {question_name: {option: prob}}}
Facets = dict[int, dict[str, dict[str, float]]]


def label_corpus(recs: list[Record], vocab: Vocabulary, dm: DecisionModel, log=print, every: int = 25) -> Facets:
    out: Facets = {}
    t0 = time.time()
    for i, r in enumerate(recs, 1):
        answers = dm.evaluate(r.text, vocab.questions)
        out[r.id] = {name: a.probs for name, a in answers.items()}
        if i % every == 0 or i == len(recs):
            el = time.time() - t0
            log(f"  labelled {i}/{len(recs)}  ({el/ i:.1f}s per record, {el/60:.1f} min elapsed)")
    return out


def oracle_facets(recs: list[Record], vocab: Vocabulary) -> Facets:
    """One-hot facets from the oracle labels, for the questions that have a ground truth."""
    out: Facets = {}
    for r in recs:
        row: dict[str, dict[str, float]] = {}
        for q in vocab.questions:
            truth = r.oracle.get(q.name)
            if truth is None:
                continue
            row[q.name] = {o: (1.0 if o == truth else 0.0) for o in q.options}
        out[r.id] = row
    return out


def save_facets(f: Facets, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in f.items()}, fh)


def load_facets(path: str | Path) -> Facets:
    with open(path, encoding="utf-8") as fh:
        return {int(k): v for k, v in json.load(fh).items()}


def label_accuracy(pred: Facets, truth: Facets, vocab: Vocabulary) -> dict[str, dict]:
    """Per question: accuracy of argmax (choice/score) or of P(yes)>0.5 (noul) against the oracle,
    plus the majority-class baseline so a lazy labeller is visible."""
    out: dict[str, dict] = {}
    for q in vocab.questions:
        ids = [i for i in truth if q.name in truth[i] and i in pred and q.name in pred[i]]
        if not ids:
            continue
        correct = 0
        counts: dict[str, int] = {}
        for i in ids:
            t = max(truth[i][q.name], key=truth[i][q.name].get)
            counts[t] = counts.get(t, 0) + 1
            p = pred[i][q.name]
            guess = ("yes" if p.get("yes", 0) > 0.5 else "no") if isinstance(q, Noul) else max(p, key=p.get)
            correct += guess == t
        out[q.name] = {
            "n": len(ids),
            "accuracy": round(correct / len(ids), 3),
            "majority_baseline": round(max(counts.values()) / len(ids), 3),
            "truth_distribution": counts,
        }
    return out
