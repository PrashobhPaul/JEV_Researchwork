"""The one interface every decision-model adapter implements, plus an on-disk answer cache.

The cache is keyed by (adapter name, question fingerprint, state hash). Committed to the repo, it lets
CI re-run the evaluation without re-loading a model, and it never serves an answer for a reworded
question."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Protocol

from ..schema import Answer, Question, Vocabulary


class DecisionModel(Protocol):
    name: str

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        """Evaluate every question against one state. Returns {question.name: Answer}."""
        ...


class DecisionCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS decisions (key TEXT PRIMARY KEY, probs TEXT NOT NULL, confidence REAL NOT NULL)"
        )
        self.con.commit()

    @staticmethod
    def key(model_name: str, q: Question, state: str) -> str:
        h = hashlib.sha1(state.encode()).hexdigest()
        return f"{model_name}|{Vocabulary.fingerprint_of(q)}|{h}"

    def get(self, model_name: str, q: Question, state: str) -> Answer | None:
        row = self.con.execute(
            "SELECT probs, confidence FROM decisions WHERE key=?", (self.key(model_name, q, state),)
        ).fetchone()
        if not row:
            return None
        return Answer(json.loads(row[0]), row[1])

    def put(self, model_name: str, q: Question, state: str, a: Answer) -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?,?,?)",
            (self.key(model_name, q, state), json.dumps(a.probs), a.confidence),
        )

    def commit(self) -> None:
        self.con.commit()

    def count(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]


class CachedModel:
    """Wraps any DecisionModel with the cache; only uncached questions reach the model."""

    def __init__(self, inner: DecisionModel, cache: DecisionCache):
        self.inner, self.cache = inner, cache
        self.name = inner.name
        self.model_calls = 0

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        out: dict[str, Answer] = {}
        missing: list[Question] = []
        for q in questions:
            hit = self.cache.get(self.name, q, state)
            if hit is None:
                missing.append(q)
            else:
                out[q.name] = hit
        if missing:
            fresh = self.inner.evaluate(state, missing)
            self.model_calls += 1
            for q in missing:
                self.cache.put(self.name, q, state, fresh[q.name])
                out[q.name] = fresh[q.name]
            self.cache.commit()
        return out
