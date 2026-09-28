from facetvec.decision.systemone import from_systemone, to_systemone
from facetvec.schema import Choice, Noul, Score


def test_round_trip_mapping():
    qs = [Choice("team", "Which team?", ("billing", "shipping")), Noul("urgent", "Is it urgent?"), Score("sev", "How severe?", ("low", "high"))]
    sent = to_systemone(qs, {"team": {"billing": "Payments and refunds"}})
    assert sent["team"] == {"type": "choice", "instructions": "Which team?", "criteria": {"billing": "Payments and refunds", "shipping": "shipping"}}
    assert sent["urgent"] == {"type": "noul", "instructions": "Is it urgent?"}
    assert sent["sev"]["criteria"] == ["low", "high"]
    raw = {"answers": {"team": {"choice": "billing", "probabilities": {"billing": 0.9, "shipping": 0.1}}, "urgent": {"probabilities": {"yes": 0.7, "no": 0.3}}, "sev": {"probabilities": {"low": 0.2, "high": 0.8}}}}
    got = from_systemone(raw, qs)
    assert got["team"].top == "billing" and abs(got["team"].confidence - 0.8) < 1e-9
    assert abs(got["urgent"].p_yes - 0.7) < 1e-9
    assert got["sev"].top == "high"


def test_missing_option_is_handled():
    qs = [Choice("k", "?", ("a", "b", "c"))]
    got = from_systemone({"k": {"probabilities": {"a": 0.5, "b": 0.5}}}, qs)
    assert got["k"].probs["c"] == 0.0 and abs(sum(got["k"].probs.values()) - 1) < 1e-9


def test_lumma_fev_native_shapes():
    qs = [Noul("tb", "has traceback"), Score("sev", "severity", ("low", "medium", "high"))]
    raw = {"tb": {"type": "noul", "noul": 0.066}, "sev": {"type": "score", "score": 1.09, "legend": {"0": "low", "1": "medium", "2": "high"}, "probabilities": {"0": 0.21, "1": 0.48, "2": 0.30}}}
    got = from_systemone(raw, qs)
    assert abs(got["tb"].p_yes - 0.066) < 1e-9
    assert got["sev"].top == "medium" and abs(sum(got["sev"].probs.values()) - 1) < 1e-9
