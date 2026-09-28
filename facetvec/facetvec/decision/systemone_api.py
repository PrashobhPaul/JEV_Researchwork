"""Any server that speaks `/v1/systemone`: TypeSafe's hosted Jev, `lumma-fev-serve`, or Laya served
locally through Unsloth Desktop. Point `base_url` at it; set `SYSTEMONE_API_KEY` if the server wants
one. Not exercised in CI (no server there); the request/response mapping is shared with the
Lumma-Fev adapter, which is."""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

from ..schema import Answer, Question
from .systemone import from_systemone, to_systemone


@dataclass
class SystemOneConfig:
    base_url: str = "http://localhost:8000"
    api_key_env: str = "SYSTEMONE_API_KEY"
    timeout: float = 60.0
    max_state_chars: int = 30000
    descriptions: dict[str, dict[str, str]] = field(default_factory=dict)


class SystemOneAPIModel:
    def __init__(self, cfg: SystemOneConfig | None = None):
        self.cfg = cfg or SystemOneConfig()
        host = self.cfg.base_url.replace("https://", "").replace("http://", "").rstrip("/")
        self.name = f"systemone-api:{host}"

    def evaluate(self, state: str, questions: list[Question]) -> dict[str, Answer]:
        payload = {"state": (state.strip() or "(empty)")[: self.cfg.max_state_chars], "questions": to_systemone(questions, self.cfg.descriptions)}
        req = urllib.request.Request(
            self.cfg.base_url.rstrip("/") + "/v1/systemone",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "user-agent": "facetvec"},
            method="POST",
        )
        key = os.environ.get(self.cfg.api_key_env)
        if key:
            req.add_header("authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=self.cfg.timeout) as r:
            return from_systemone(json.loads(r.read()), questions)
