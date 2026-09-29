"""The Laya adapter with a stand-in `laya` module: questions go out in the /v1/systemone shape and
answers come back as facetvec Answers, with the pinned revision in the adapter's name."""
import sys
import types

from facetvec.decision.laya import LayaConfig, LayaModel
from facetvec.schema import Choice, Noul


class _FakeAgent:
    revision = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"

    def __init__(self):
        self.calls = []

    def system_one(self, state, questions):
        self.calls.append((state, questions))
        return {"model": "laya-rl-agent", "answers": {
            "kind": {"choice": "bug", "probabilities": {"bug": 0.8, "feature": 0.2}},
            "crash": {"noul": 0.7},
        }}


def test_laya_adapter_round_trip(monkeypatch):
    agent = _FakeAgent()
    loaded = {}

    def load(model, device=None, subfolder=None, revision=None):
        loaded.update(model=model, device=device, subfolder=subfolder, revision=revision)
        return agent

    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(load=load))
    m = LayaModel(LayaConfig(revision=_FakeAgent.revision, descriptions={"kind": {"bug": "something is broken"}}))
    qs = [Choice("kind", "What kind of issue?", ("bug", "feature")), Noul("crash", "This reports a crash.")]
    out = m.evaluate("  editor crashes on paste  ", qs)

    assert loaded == {"model": "convaiinnovations/laya", "device": "cpu", "subfolder": None,
                      "revision": _FakeAgent.revision}
    assert m.name.startswith("laya:english@55cf4c4+d")
    state, sent = agent.calls[0]
    assert state == "editor crashes on paste"
    assert sent["kind"] == {"type": "choice", "instructions": "What kind of issue?",
                            "criteria": {"bug": "something is broken", "feature": "feature"}}
    assert sent["crash"] == {"type": "noul", "instructions": "This reports a crash."}
    assert out["kind"].probs == {"bug": 0.8, "feature": 0.2}
    assert abs(out["crash"].probs["yes"] - 0.7) < 1e-9


def test_laya_name_separates_other_repos(monkeypatch):
    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(load=lambda *a, **k: types.SimpleNamespace()))
    default = LayaModel(LayaConfig(revision=_FakeAgent.revision))
    other = LayaModel(LayaConfig(model_name="someone/laya-finetune", revision=_FakeAgent.revision))
    unpinned = LayaModel(LayaConfig(model_name="someone/laya-finetune"))
    assert default.name == "laya:english@55cf4c4"  # the default repo is not spelled out
    assert other.name == "laya[someone/laya-finetune]:english@55cf4c4"
    assert unpinned.name == "laya[someone/laya-finetune]:english@unpinned"
    assert len({default.name, other.name, unpinned.name}) == 3


def test_laya_name_tracks_descriptions(monkeypatch):
    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(load=lambda *a, **k: types.SimpleNamespace()))
    a = LayaModel(LayaConfig(revision=_FakeAgent.revision, descriptions={"kind": {"bug": "broken"}}))
    b = LayaModel(LayaConfig(revision=_FakeAgent.revision, descriptions={"kind": {"bug": "something is broken"}}))
    a2 = LayaModel(LayaConfig(revision=_FakeAgent.revision, descriptions={"kind": {"bug": "broken"}}))
    assert a.name != b.name and a.name == a2.name
