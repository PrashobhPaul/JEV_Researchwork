"""Typed questions (the three decision primitives) and the vocabulary a corpus is labelled with.

A vocabulary's fingerprint changes whenever any question's wording or options change, so cached
answers for an old wording are never reused for a new one (the same idea as Truffler's label
fingerprints)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, Union


@dataclass(frozen=True)
class Choice:
    """Pick one of N known options. Answer: a probability per option."""
    name: str
    question: str
    options: tuple[str, ...]
    kind: Literal["choice"] = "choice"


@dataclass(frozen=True)
class Noul:
    """A yes/no statement. Answer: P(yes)."""
    name: str
    question: str
    kind: Literal["noul"] = "noul"

    @property
    def options(self) -> tuple[str, ...]:
        return ("yes", "no")


@dataclass(frozen=True)
class Score:
    """A position on an ordered scale. Answer: a probability per rung."""
    name: str
    question: str
    scale: tuple[str, ...]
    kind: Literal["score"] = "score"

    @property
    def options(self) -> tuple[str, ...]:
        return self.scale


Question = Union[Choice, Noul, Score]


@dataclass(frozen=True)
class Answer:
    """probs: option -> probability (sums to 1). confidence: top-1 minus top-2 probability."""
    probs: dict[str, float]
    confidence: float

    @property
    def top(self) -> str:
        return max(self.probs, key=self.probs.get)

    @property
    def p_yes(self) -> float:
        return self.probs.get("yes", 0.0)


@dataclass
class Vocabulary:
    questions: list[Question] = field(default_factory=list)

    @classmethod
    def from_config(cls, items: list[dict]) -> "Vocabulary":
        qs: list[Question] = []
        for it in items:
            k = it["kind"]
            if k == "choice":
                qs.append(Choice(it["name"], it["question"], tuple(it["options"])))
            elif k == "noul":
                qs.append(Noul(it["name"], it["question"]))
            elif k == "score":
                qs.append(Score(it["name"], it["question"], tuple(it["scale"])))
            else:
                raise ValueError(f"unknown question kind {k!r}")
        return cls(qs)

    def by_name(self, name: str) -> Question:
        for q in self.questions:
            if q.name == name:
                return q
        raise KeyError(name)

    @staticmethod
    def fingerprint_of(q: Question) -> str:
        payload = json.dumps(
            {"kind": q.kind, "name": q.name, "question": q.question, "options": list(q.options)},
            sort_keys=True,
        )
        return hashlib.sha1(payload.encode()).hexdigest()[:12]

    def fingerprint(self) -> str:
        return hashlib.sha1("|".join(self.fingerprint_of(q) for q in self.questions).encode()).hexdigest()[:12]
