"""Chat backends, all open or self-hosted — no paid API anywhere.

  TransformersLLM   an open-weights model run locally with transformers (CPU is fine; CI uses it)
  OpenAICompatLLM   any self-hosted server with an OpenAI-style /v1/chat/completions endpoint
                    (Ollama, vLLM, llama.cpp server) — base URL from config, no key by default
  ScriptedLLM       replays fixed replies; for tests

Every backend records calls, tokens and seconds, so a run can report what each tier cost."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0

    def add(self, i: int, o: int, s: float) -> None:
        self.calls += 1
        self.input_tokens += i
        self.output_tokens += o
        self.seconds += s

    def as_dict(self) -> dict:
        return {"calls": self.calls, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "seconds": round(self.seconds, 1)}


@dataclass
class ScriptedLLM:
    replies: list[str]
    name: str = "scripted"
    usage: Usage = field(default_factory=Usage)
    prompts: list[list[dict]] = field(default_factory=list)

    def chat(self, messages: list[dict], max_new_tokens: int = 512) -> str:
        self.prompts.append(messages)
        reply = self.replies.pop(0) if self.replies else ""
        self.usage.add(sum(len(m["content"]) for m in messages) // 4, len(reply) // 4, 0.0)
        return reply


class TransformersLLM:
    def __init__(self, model_name: str, dtype: str = "float32", revision: str | None = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.name = model_name
        self.usage = Usage()
        self.tok = AutoTokenizer.from_pretrained(model_name, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision,
                                                          dtype=getattr(torch, dtype))
        self.model.eval()

    def chat(self, messages: list[dict], max_new_tokens: int = 512) -> str:
        t0 = time.time()
        text = self.tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        ids = self.tok(text, return_tensors="pt").input_ids
        with self.torch.no_grad():
            out = self.model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        new = out[0, ids.shape[1]:]
        self.usage.add(int(ids.shape[1]), int(new.shape[0]), time.time() - t0)
        return self.tok.decode(new, skip_special_tokens=True)


class OpenAICompatLLM:
    def __init__(self, model_name: str, base_url: str | None = None, api_key_env: str = "LOCAL_LLM_API_KEY"):
        self.name = model_name
        self.base_url = (base_url or os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.usage = Usage()

    def chat(self, messages: list[dict], max_new_tokens: int = 512) -> str:
        t0 = time.time()
        body = json.dumps({"model": self.name, "messages": messages, "max_tokens": max_new_tokens,
                           "temperature": 0}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        u = data.get("usage") or {}
        self.usage.add(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), time.time() - t0)
        return data["choices"][0]["message"]["content"]


def make_llm(spec: dict):
    kind = spec.get("backend", "transformers")
    if kind == "transformers":
        return TransformersLLM(spec["model"], spec.get("dtype", "float32"), spec.get("revision"))
    if kind == "openai-compatible":
        return OpenAICompatLLM(spec["model"], spec.get("base_url"))
    raise ValueError(f"unknown backend {kind!r} (transformers | openai-compatible)")
