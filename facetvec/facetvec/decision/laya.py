"""Laya (Convai Innovations): a non-autoregressive System 1 decision engine — a BERT-family encoder
that answers every typed question about a state in one forward pass, with calibrated
probabilities. It speaks the `/v1/systemone` question format natively, so this adapter is a thin
wrapper around `laya.load(...).system_one(...)`.

Checkpoints (one hub repo, picked by `subfolder`): the English root (ModernBERT-large, 421M,
512 tokens), `multilingual` (mmBERT-base, 322M, 1024 tokens) and `typed-decisions`. Pin
`revision` to a commit so the answers — and the cache keyed by this adapter's name — are
reproducible."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import Answer, Question
from .systemone import from_systemone, to_systemone


@dataclass
class LayaConfig:
    model_name: str = "convaiinnovations/laya"
    subfolder: str | None = None  # None = English root checkpoint; "multilingual", "typed-decisions"
    revision: str | None = None  # hub commit; the name (and so the cache key) records it
    device: str = "cpu"
    descriptions: dict[str, dict[str, str]] = field(default_factory=dict)  # optional option descriptions per question


class LayaModel:
    def __init__(self, cfg: LayaConfig | None = None):
        import laya

        self.cfg = cfg or LayaConfig()
        self.agent = laya.load(self.cfg.model_name, device=self.cfg.device, subfolder=self.cfg.subfolder,
                               revision=self.cfg.revision)
        resolved = getattr(self.agent, "revision", None) or self.cfg.revision or "unpinned"
        self.name = f"laya:{self.cfg.subfolder or 'english'}@{resolved[:7]}"

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        raw = self.agent.system_one(state.strip() or "(empty)", to_systemone(questions, self.cfg.descriptions))
        return from_systemone(raw, questions)

    def describe(self) -> dict:
        return {"adapter": "laya (native system_one)", "model": self.cfg.model_name,
                "subfolder": self.cfg.subfolder, "revision": self.cfg.revision}
