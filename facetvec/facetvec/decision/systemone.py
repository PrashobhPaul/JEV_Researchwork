"""Shared mapping between facetvec questions and the `/v1/systemone` question format that TypeSafe
Jev, Lumma-Fev's `decide()` and `lumma-fev-serve`, and Laya served through Unsloth all speak.

    Choice -> {"type": "choice", "instructions": ..., "criteria": {option: description}}
    Noul   -> {"type": "noul",   "instructions": ...}
    Score  -> {"type": "score",  "instructions": ..., "criteria": [rung, ...]}   (low -> high)

The response is {name: {"type", "choice", "probabilities": {option: p}}}."""
from __future__ import annotations

from ..schema import Answer, Choice, Noul, Question, Score


def to_systemone(questions: list[Question], descriptions: dict[str, dict[str, str]] | None = None) -> dict:
    descriptions = descriptions or {}
    out: dict = {}
    for q in questions:
        if isinstance(q, Noul):
            out[q.name] = {"type": "noul", "instructions": q.question}
        elif isinstance(q, Score):
            out[q.name] = {"type": "score", "instructions": q.question, "criteria": list(q.scale)}
        else:
            desc = descriptions.get(q.name, {})
            out[q.name] = {"type": "choice", "instructions": q.question, "criteria": {o: desc.get(o, o) for o in q.options}}
    return out


def from_systemone(raw: dict, questions: list[Question]) -> dict[str, Answer]:
    """Accepts either {name: result} or {"answers": {name: result}}; normalises probabilities so
    every option in the question is present and the vector sums to 1."""
    body = raw.get("answers", raw) if isinstance(raw, dict) else {}
    out: dict[str, Answer] = {}
    for q in questions:
        res = body.get(q.name, {}) or {}
        probs_in = dict(res.get("probabilities") or {})
        if isinstance(q, Noul) and "yes" not in probs_in:
            p = res.get("noul", res.get("p", res.get("probability")))
            if p is not None:
                probs_in = {"yes": float(p), "no": 1.0 - float(p)}
        if isinstance(q, Score) and probs_in and not any(o in probs_in for o in q.options):
            # Lumma-Fev keys score probabilities by rung index and ships the legend alongside
            legend = res.get("legend") or {str(i): o for i, o in enumerate(q.scale)}
            probs_in = {legend.get(str(k), k): v for k, v in probs_in.items()}
        probs = {o: float(probs_in.get(o, 0.0)) for o in q.options}
        z = sum(probs.values())
        probs = {o: v / z for o, v in probs.items()} if z > 0 else {o: 1.0 / len(q.options) for o in q.options}
        srt = sorted(probs.values(), reverse=True)
        out[q.name] = Answer(probs, srt[0] - (srt[1] if len(srt) > 1 else 0.0))
    return out
