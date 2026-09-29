"""Laya (Convai Innovations): a non-autoregressive System 1 decision engine — a BERT-family encoder
that answers every typed question about a state in one forward pass, with calibrated
probabilities. It speaks the `/v1/systemone` question format natively, so this adapter is a thin
wrapper around `laya.load(...).system_one(...)`.

Checkpoints (one hub repo, picked by `subfolder`): the English root (ModernBERT-large, 421M,
512 tokens), `multilingual` (mmBERT-base, 322M, 1024 tokens) and `typed-decisions`. Pin
`revision` to a commit so the answers — and the cache keyed by this adapter's name — are
reproducible.

Input length: Laya caps each input itself, deterministically. `laya.common.build_sequence` (pinned
by `laya==0.3.21`) lays out `[CLS] question [SEP] options [SEP] state [SEP]` within the checkpoint's
`max_len` (512 tokens for the English root) and keeps the *first* tokens of the state that fit
after the question head. A second cap here would either repeat that cut or change it, so the
adapter passes the full state and records the rule in `describe()`."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import Answer, Question
from .systemone import from_systemone, to_systemone


DEFAULT_REPO = "convaiinnovations/laya"


@dataclass
class LayaConfig:
    model_name: str = DEFAULT_REPO
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
        resolved = getattr(self.agent, "revision", None) or self.cfg.revision
        rev = resolved[:7] if resolved else "unpinned"
        # The name is the answer-cache key, so it must change whenever the loaded weights can.
        # Any repo other than the default is spelled out; the default keeps its short name.
        repo = "" if self.cfg.model_name == DEFAULT_REPO else f"[{self.cfg.model_name}]"
        self.name = f"laya{repo}:{self.cfg.subfolder or 'english'}@{rev}"

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        raw = self.agent.system_one(state.strip() or "(empty)", to_systemone(questions, self.cfg.descriptions))
        return from_systemone(raw, questions)

    def describe(self) -> dict:
        return {"adapter": "laya (native system_one)", "model": self.cfg.model_name,
                "subfolder": self.cfg.subfolder, "revision": self.cfg.revision,
                "input_cap": "laya.common.build_sequence: question head first, then the first state "
                             "tokens that fit the checkpoint's max_len"}
