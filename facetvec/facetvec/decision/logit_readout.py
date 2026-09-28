"""A decision model made from any local causal LLM, by reading option probabilities off the logits.

This is the AnyJev recipe (Zheng et al.), reimplemented minimally:

* the answer is read from the next-token distribution over option letters, never generated;
* option order is rotated and the distributions averaged in option space, which removes most of
  the position bias small models have ("always A");
* a label prior, measured with an empty document, is divided out, so a model that likes saying
  "bug" regardless of content is corrected.

The document is encoded once (KV cache) and every question is a short suffix on that cache, so
labelling a document with N questions costs one long pass plus N short ones.

Nothing here is specific to the model; the default is Qwen2.5-0.5B-Instruct because it runs on a
CPU-only CI runner in reasonable time. Swap `model_name` for anything with a chat template.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass

from ..schema import Answer, Noul, Question, Score

MARK = "\u241e"  # record separator, used only to split the chat text into prefix/suffix

SYSTEM = (
    "You are a precise labeller. You will read a document and answer one question about it "
    "by replying with a single letter."
)


@dataclass
class ReadoutConfig:
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    max_state_tokens: int = 640
    rotations: int = 2  # option-order rotations averaged per question (K = all rotations)
    prior_alpha: float = 1.0  # 0 = no prior correction, 1 = full division by the empty-document prior
    threads: int = 0  # 0 = torch default


class LogitReadoutModel:
    def __init__(self, cfg: ReadoutConfig | None = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.cfg = cfg or ReadoutConfig()
        self.name = f"logit-readout:{self.cfg.model_name.split('/')[-1]}:r{self.cfg.rotations}:a{self.cfg.prior_alpha}"
        if self.cfg.threads:
            torch.set_num_threads(self.cfg.threads)
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(self.cfg.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.cfg.model_name, dtype=torch.float32)
        self.model.eval()
        self.letters = [chr(ord("A") + i) for i in range(26)]
        self.letter_ids = [self.tok.encode(L, add_special_tokens=False)[0] for L in self.letters]
        self._prior: dict[str, dict[str, float]] = {}
        self._prefix_cache: tuple[str, object, object] | None = None

    # ----- prompt construction -------------------------------------------------------------

    def _truncate(self, state: str) -> str:
        ids = self.tok.encode(state, add_special_tokens=False)
        if len(ids) <= self.cfg.max_state_tokens:
            return state
        return self.tok.decode(ids[: self.cfg.max_state_tokens]) + " …"

    @staticmethod
    def _question_text(q: Question, options: list[str]) -> str:
        if isinstance(q, Noul):
            head = f"Statement: {q.question}\nIs the statement true for this document?"
        elif isinstance(q, Score):
            head = f"Question: {q.question}\nPick the rung of the scale that fits best."
        else:
            head = f"Question: {q.question}"
        lines = [f"{chr(ord('A') + i)}. {o}" for i, o in enumerate(options)]
        return head + "\n" + "\n".join(lines) + "\nAnswer:"

    def _split_chat(self, state: str, suffix: str) -> tuple[str, str]:
        msgs = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Document:\n{state}\n\n{MARK}{suffix}"},
        ]
        text = self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        pre, suf = text.split(MARK, 1)
        return pre, suf

    # ----- inference ------------------------------------------------------------------------

    def _prefix(self, state: str):
        """Encode the document prefix once per state; reuse across questions and rotations."""
        pre, _ = self._split_chat(state, "Question:")
        if self._prefix_cache and self._prefix_cache[0] == pre:
            return self._prefix_cache[1], self._prefix_cache[2]
        ids = self.tok(pre, return_tensors="pt", add_special_tokens=False).input_ids
        with self.torch.no_grad():
            out = self.model(ids, use_cache=True)
        self._prefix_cache = (pre, ids, out.past_key_values)
        return ids, out.past_key_values

    def _letter_probs(self, state: str, suffix: str, n: int) -> list[float]:
        pre, suf = self._split_chat(state, suffix)
        pre_ids, cache = self._prefix(state)
        full = self.tok(pre + suf, return_tensors="pt", add_special_tokens=False).input_ids
        with self.torch.no_grad():
            if full[0, : pre_ids.shape[1]].tolist() == pre_ids[0].tolist():
                suf_ids = full[:, pre_ids.shape[1]:]
                out = self.model(suf_ids, past_key_values=copy.deepcopy(cache), use_cache=True)
            else:  # tokenizer merged across the boundary; fall back to a full pass
                out = self.model(full)
            logits = out.logits[0, -1, self.letter_ids[:n]].float()
            return self.torch.softmax(logits, dim=-1).tolist()

    def _raw(self, state: str, q: Question) -> dict[str, float]:
        """Rotation-averaged probabilities over q.options for one state."""
        opts = list(q.options)
        n = len(opts)
        rots = min(self.cfg.rotations, n) if n > 2 else min(self.cfg.rotations, 2)
        acc = {o: 0.0 for o in opts}
        for r in range(rots):
            shift = (r * n) // rots
            rotated = opts[shift:] + opts[:shift]
            probs = self._letter_probs(state, self._question_text(q, rotated), n)
            for o, p in zip(rotated, probs):
                acc[o] += p / rots
        return acc

    def _prior_for(self, q: Question) -> dict[str, float]:
        key = f"{q.kind}|{q.name}|{q.question}|{q.options}"
        if key not in self._prior:
            saved = self._prefix_cache
            self._prior[key] = self._raw("(no document)", q)
            self._prefix_cache = saved
        return self._prior[key]

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        state = self._truncate(state.strip() or "(empty)")
        out: dict[str, Answer] = {}
        for q in questions:
            raw = self._raw(state, q)
            if self.cfg.prior_alpha > 0:
                prior = self._prior_for(q)
                corrected = {o: raw[o] / max(prior[o], 1e-6) ** self.cfg.prior_alpha for o in raw}
            else:
                corrected = raw
            z = sum(corrected.values()) or 1.0
            probs = {o: v / z for o, v in corrected.items()}
            srt = sorted(probs.values(), reverse=True)
            conf = srt[0] - (srt[1] if len(srt) > 1 else 0.0)
            out[q.name] = Answer(probs, conf)
        return out

    def describe(self) -> dict:
        return {
            "adapter": "logit-readout (AnyJev-style)",
            "model": self.cfg.model_name,
            "rotations": self.cfg.rotations,
            "prior_alpha": self.cfg.prior_alpha,
            "max_state_tokens": self.cfg.max_state_tokens,
        }


def entropy(probs: dict[str, float]) -> float:
    """Normalised Shannon entropy in [0, 1]; 1 = uniform."""
    n = len(probs)
    if n < 2:
        return 0.0
    h = -sum(p * math.log(p) for p in probs.values() if p > 0)
    return h / math.log(n)
