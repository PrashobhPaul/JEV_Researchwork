"""Lumma-Fev (FrontiersMind): an open decision model with the same three primitives as Jev,
loaded through transformers and called with `model.decide(state, questions)`. One forward pass
scores every question — no rotations, no prior correction, no parsing.

Sizes: 0.1B, 0.6B, 4B, 9B. The 0.6B runs on a CPU-only CI runner; the larger ones want a GPU."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import Answer, Question
from .systemone import from_systemone, to_systemone


@dataclass
class LummaFevConfig:
    model_name: str = "FrontiersMind/Lumma-fev-0.6b"
    dtype: str = "float32"  # bfloat16 on GPU; float32 is safer on CPU
    max_state_chars: int = 3000
    revision: str | None = None
    descriptions: dict[str, dict[str, str]] = field(default_factory=dict)  # optional option descriptions per question


class LummaFevModel:
    def __init__(self, cfg: LummaFevConfig | None = None):
        import torch
        from transformers import AutoModel

        self.cfg = cfg or LummaFevConfig()
        self.name = f"lumma-fev:{self.cfg.model_name.split('/')[-1]}"
        dtype = getattr(torch, self.cfg.dtype)
        self.model = AutoModel.from_pretrained(self.cfg.model_name, trust_remote_code=True, dtype=dtype, revision=self.cfg.revision)
        self.model.eval()

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        state = (state.strip() or "(empty)")[: self.cfg.max_state_chars]
        raw = self.model.decide(state=state, questions=to_systemone(questions, self.cfg.descriptions))
        return from_systemone(raw, questions)

    def describe(self) -> dict:
        return {"adapter": "lumma-fev (native decide())", "model": self.cfg.model_name, "dtype": self.cfg.dtype}
