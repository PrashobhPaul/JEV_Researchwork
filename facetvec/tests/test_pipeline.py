"""Fast tests that need no model: schema fingerprints, cache, oracle mapping, ranking, metrics, and the
query builders on a tiny synthetic corpus. Real results come from the evaluate workflow."""
import json
from pathlib import Path

from facetvec.corpus.github_issues import Record, normalise
from facetvec.decision.base import CachedModel, DecisionCache
from facetvec.decision.fake import KeywordModel
from facetvec.eval.metrics import mrr_at, ndcg_at, precision_at, recall_at
from facetvec.eval.queries import build_open, build_typed
from facetvec.index.facets import label_accuracy, label_corpus, oracle_facets
from facetvec.index.lexical import LexicalIndex
from facetvec.schema import Choice, Noul, Vocabulary
from facetvec.search.encoder import Intent, OracleEncoder
from facetvec.search.rank import explain, facet_search, rrf

CFG = {
    "min_body_chars": 10,
    "oracle": {
        "kind": {"required": True, "map": {"bug": ["bug"], "feature": ["feature-request"]}},
        "crash": {"default": "no", "map": {"yes": ["freeze-slow-crash-leak"]}},
    },
}
VOCAB = Vocabulary(
    [
        Choice("kind", "What kind of issue is this?", ("bug", "feature")),
        Noul("crash", "This reports a crash."),
    ]
)


def raw(n, title, body, labels):
    return {"number": n, "title": title, "body": body, "labels": [{"name": l} for l in labels], "state": "closed", "html_url": "", "created_at": ""}


def corpus():
    return normalise(
        [
            raw(1, "Editor crash when pasting", "The editor crashes and freezes on paste, bug every time", ["bug", "freeze-slow-crash-leak"]),
            raw(2, "Add a dark theme option", "It would be a great feature to have a darker theme", ["feature-request"]),
            raw(3, "Terminal loses colours", "terminal output has no colours after update, bug", ["bug"]),
            raw(4, "Support vertical tabs", "feature request: vertical tabs please", ["feature-request"]),
            raw(5, "Untriaged thing", "no kind label on this one", []),
            raw(1, "duplicate id", "should be dropped as a duplicate", ["bug"]),
        ],
        CFG,
    )


def test_normalise_oracle_and_dedupe():
    recs = corpus()
    assert [r.id for r in recs] == [1, 2, 3, 4]
    assert recs[0].oracle == {"kind": "bug", "crash": "yes"}
    assert recs[1].oracle == {"kind": "feature", "crash": "no"}


def test_fingerprint_changes_with_wording():
    a = Vocabulary.fingerprint_of(Choice("kind", "What kind?", ("bug", "feature")))
    b = Vocabulary.fingerprint_of(Choice("kind", "What type?", ("bug", "feature")))
    c = Vocabulary.fingerprint_of(Choice("kind", "What kind?", ("bug", "feature", "debt")))
    assert len({a, b, c}) == 3


def test_cache_serves_second_call(tmp_path: Path):
    dm = CachedModel(KeywordModel(), DecisionCache(tmp_path / "c.sqlite"))
    q = VOCAB.questions
    first = dm.evaluate("a bug that crashes", q)
    second = dm.evaluate("a bug that crashes", q)
    assert first == second and dm.model_calls == 1 and dm.cache.count() == 2


def test_label_and_oracle_shapes(tmp_path: Path):
    recs = corpus()
    dm = CachedModel(KeywordModel(), DecisionCache(tmp_path / "c.sqlite"))
    f = label_corpus(recs, VOCAB, dm, log=lambda *_: None)
    o = oracle_facets(recs, VOCAB)
    assert set(f) == set(o) == {1, 2, 3, 4}
    assert abs(sum(f[1]["kind"].values()) - 1) < 1e-6
    assert o[1]["crash"] == {"yes": 1.0, "no": 0.0}
    acc = label_accuracy(f, o, VOCAB)
    assert set(acc) == {"kind", "crash"} and 0 <= acc["kind"]["accuracy"] <= 1


def test_facet_search_filters_and_explains():
    recs = corpus()
    o = oracle_facets(recs, VOCAB)
    intent = OracleEncoder(VOCAB).encode_from({"kind": "bug", "crash": "yes"})
    hits = facet_search(intent, o)
    assert [h for h, _ in hits] == [1]
    assert explain(1, intent, o) == [
        {"facet": "kind", "option": "bug", "mode": "filter", "p": 1.0},
        {"facet": "crash", "option": "yes", "mode": "filter", "p": 1.0},
    ]
    assert facet_search({"kind": Intent("ignore")}, o) == []


def test_rrf_and_metrics():
    fused = rrf([(1, 1.0), (2, 0.5)], [(2, 1.0), (3, 0.5)])
    assert fused[0][0] == 2
    ranked = [3, 1, 2]
    assert precision_at(ranked, {1, 2}, 2) == 0.5
    assert recall_at(ranked, {1, 2}, 3) == 1.0
    assert mrr_at(ranked, {1}, 10) == 0.5
    assert 0 < ndcg_at(ranked, {1, 2}, 3) < 1


def test_query_builders():
    recs = corpus()
    typed = build_typed(
        recs,
        {"templates": ["{kind}"], "per_template": 5, "min_truth": 1, "max_truth_fraction": 1.0, "phrases": {"kind": {"bug": ["bugs"], "feature": ["feature requests"]}}},
    )
    assert {q.text for q in typed} == {"bugs", "feature requests"}
    assert all(len(q.truth) == 2 for q in typed)
    opened = build_open(recs, 10, min_words=3)
    assert len(opened) == 4 and all(len(q.truth) == 1 for q in opened)
    idx = LexicalIndex(recs)
    assert idx.search("vertical tabs")[0][0] == 4
