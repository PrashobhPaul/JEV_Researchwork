"""Two query families with objective ground truth — no LLM judge anywhere.

typed: built from oracle facet combinations ("bugs about the terminal on windows"); truth = every
       record whose oracle facets match. This is what named facets are for.
open:  a record's own title as the query; truth = that record. Titles never enter any index, so
       this is an honest open-world retrieval test. This is what dense vectors are for."""
from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass, field

from ..corpus.github_issues import Record


@dataclass
class Query:
    id: str
    family: str  # "typed" | "open"
    text: str
    truth: set[int]
    intent: dict[str, str] = field(default_factory=dict)  # facet -> option, typed only


_SLOT = re.compile(r"\{(\w+)\}")


def build_typed(recs: list[Record], cfg: dict, seed: int = 11) -> list[Query]:
    rng = random.Random(seed)
    phrases: dict[str, dict[str, list[str]]] = cfg["phrases"]
    templates: list[str] = cfg["templates"]
    min_truth = cfg.get("min_truth", 3)
    max_frac = cfg.get("max_truth_fraction", 0.5)
    per_template = cfg.get("per_template", 6)
    out: list[Query] = []
    seen: set[tuple] = set()
    for tpl in templates:
        slots = _SLOT.findall(tpl)
        combos = list(itertools.product(*[list(phrases[s].keys()) for s in slots]))
        rng.shuffle(combos)
        made = 0
        for combo in combos:
            intent = dict(zip(slots, combo))
            key = tuple(sorted(intent.items()))
            if key in seen:
                continue
            truth = {r.id for r in recs if all(r.oracle.get(f) == o for f, o in intent.items())}
            if len(truth) < min_truth or len(truth) > max_frac * len(recs):
                continue
            text = tpl
            for s, o in intent.items():
                text = text.replace("{" + s + "}", rng.choice(phrases[s][o]))
            text = re.sub(r"\s+", " ", text).strip()
            seen.add(key)
            out.append(Query(f"typed-{len(out)+1:02d}", "typed", text, truth, intent))
            made += 1
            if made >= per_template:
                break
    return out


def build_open(recs: list[Record], n: int, seed: int = 13, min_words: int = 4) -> list[Query]:
    rng = random.Random(seed)
    pool = [r for r in recs if len(r.title.split()) >= min_words]
    rng.shuffle(pool)
    return [Query(f"open-{i+1:02d}", "open", r.title, {r.id}) for i, r in enumerate(pool[:n])]
