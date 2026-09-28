"""Run every retrieval system over both query families and write results.json + results.md.

Systems
  bm25            lexical only
  dense           embedding only
  facets          model labels + model query encoding          (the thing being tested)
  fused           RRF(bm25, dense, facets)                      (the recommended shape)
  facets-oracle   oracle labels + oracle query encoding          (ceiling of the method)
  fused-oracle    RRF(bm25, dense, facets-oracle)                (ceiling of the shape)

For open queries there is no oracle intent, so the oracle rows use oracle labels with the model's
own query encoding."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..corpus.github_issues import Record
from ..index.dense import DenseIndex
from ..index.facets import Facets, label_accuracy
from ..index.lexical import LexicalIndex
from ..schema import Vocabulary
from ..search.encoder import ModelEncoder, OracleEncoder, QueryIntent, intent_accuracy
from ..search.rank import explain, facet_search, rrf
from .metrics import mrr_at, ndcg_at, precision_at, recall_at
from .queries import Query

SYSTEMS = ["bm25", "dense", "facets", "fused", "facets-oracle", "fused-oracle"]


def run_eval(
    recs: list[Record],
    vocab: Vocabulary,
    queries: list[Query],
    facets_model: Facets,
    facets_oracle: Facets,
    dense: DenseIndex,
    lexical: LexicalIndex,
    encoder: ModelEncoder,
    k: int = 10,
    log=print,
) -> dict:
    oracle_enc = OracleEncoder(vocab)
    per_query: list[dict] = []
    enc_correct = enc_total = 0
    examples: list[dict] = []
    t0 = time.time()
    for qi, q in enumerate(queries, 1):
        bm = lexical.search(q.text, 50)
        de = dense.search(q.text, 50)
        intent_m: QueryIntent = encoder.encode(q.text)
        if q.family == "typed":
            intent_o = oracle_enc.encode_from(q.intent)
            c, t = intent_accuracy(intent_m, q.intent, vocab)
            enc_correct += c
            enc_total += t
        else:
            intent_o = intent_m
        fa = facet_search(intent_m, facets_model)
        fo = facet_search(intent_o, facets_oracle)
        # facets join the fusion only when the query actually filters on something; a preference alone
        # is too weak a signal to let a small labeller re-order the text rankers
        fuse_m = fa if any(i.mode == "filter" for i in intent_m.values()) else []
        fuse_o = fo if any(i.mode == "filter" for i in intent_o.values()) else []
        ranked = {
            "bm25": bm,
            "dense": de,
            "facets": fa,
            "fused": rrf(bm, de, fuse_m) if fuse_m else rrf(bm, de),
            "facets-oracle": fo,
            "fused-oracle": rrf(bm, de, fuse_o) if fuse_o else rrf(bm, de),
        }
        row = {"id": q.id, "family": q.family, "text": q.text, "n_truth": len(q.truth), "intent_model": {n: [i.mode, i.option] for n, i in intent_m.items() if i.mode != "ignore"}, "metrics": {}}
        for name, lst in ranked.items():
            ids = [r for r, _ in lst]
            row["metrics"][name] = {
                "p": precision_at(ids, q.truth, k),
                "r": recall_at(ids, q.truth, k),
                "ndcg": ndcg_at(ids, q.truth, k),
                "mrr": mrr_at(ids, q.truth, k),
            }
        per_query.append(row)
        if q.family == "typed" and len(examples) < 3 and fa:
            by_id = {r.id: r for r in recs}
            examples.append(
                {
                    "query": q.text,
                    "top": [
                        {"id": rid, "title": by_id[rid].title[:90], "in_truth": rid in q.truth, "because": explain(rid, intent_m, facets_model)}
                        for rid, _ in ranked["fused"][:3]
                    ],
                }
            )
        if qi % 10 == 0 or qi == len(queries):
            log(f"  evaluated {qi}/{len(queries)} queries ({(time.time()-t0)/60:.1f} min)")

    def agg(family: str, system: str, metric: str) -> float:
        vals = [r["metrics"][system][metric] for r in per_query if r["family"] == family]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    summary = {
        s: {
            "typed": {m: agg("typed", s, m) for m in ("p", "r", "ndcg")},
            "open": {m: agg("open", s, m) for m in ("r", "mrr")},
        }
        for s in SYSTEMS
    }
    return {
        "k": k,
        "n_queries": {"typed": sum(r["family"] == "typed" for r in per_query), "open": sum(r["family"] == "open" for r in per_query)},
        "summary": summary,
        "label_accuracy": label_accuracy(facets_model, facets_oracle, vocab),
        "query_encoder_accuracy": round(enc_correct / enc_total, 3) if enc_total else None,
        "examples": examples,
        "per_query": per_query,
    }


def to_markdown(res: dict, meta: dict) -> str:
    k = res["k"]
    s = res["summary"]
    lines = []
    lines.append(f"**Corpus:** {meta['corpus']} — {meta['n_records']} real issues, labelled with {meta['n_questions']} questions. ")
    lines.append(f"**Decision model:** {meta['decision_model']}. **Dense model:** {meta['dense_model']}. **Run:** {meta['run_at']} on {meta['runner']}.")
    lines.append("")
    lines.append(f"| System | typed P@{k} | typed R@{k} | typed nDCG@{k} | open R@{k} | open MRR@{k} |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    names = {
        "bm25": "BM25 (lexical)",
        "dense": "Dense (embeddings)",
        "facets": "**Facets** (model labels + model query encoding)",
        "fused": "**Fused** RRF(BM25 + dense + facets)",
        "facets-oracle": "Facets — oracle labels (ceiling)",
        "fused-oracle": "Fused — oracle labels (ceiling)",
    }
    for sys_ in SYSTEMS:
        t, o = s[sys_]["typed"], s[sys_]["open"]
        lines.append(f"| {names[sys_]} | {t['p']:.3f} | {t['r']:.3f} | {t['ndcg']:.3f} | {o['r']:.3f} | {o['mrr']:.3f} |")
    lines.append("")
    lines.append(f"{res['n_queries']['typed']} typed queries (truth from the repository's own labels) and {res['n_queries']['open']} open queries (a record's title → that record; titles are never indexed).")
    lines.append("")
    lines.append("**Labeller accuracy vs the repository's labels** (argmax, or P(yes) > 0.5 for yes/no):")
    lines.append("")
    lines.append("| Facet | n | accuracy | majority-class baseline |")
    lines.append("|---|---:|---:|---:|")
    for name, a in res["label_accuracy"].items():
        lines.append(f"| {name} | {a['n']} | {a['accuracy']:.3f} | {a['majority_baseline']:.3f} |")
    lines.append("")
    if res["query_encoder_accuracy"] is not None:
        lines.append(f"**Query encoder accuracy** on typed queries (right facet role and option, per facet): {res['query_encoder_accuracy']:.3f}")
        lines.append("")
    if res["examples"]:
        lines.append("**Matched because** — top fused results for a typed query, with the facet evidence:")
        lines.append("")
        for ex in res["examples"][:2]:
            lines.append(f"- *{ex['query']}*")
            for t in ex["top"]:
                because = ", ".join(f"{b['facet']}={b['option']} ({b['p']:.2f})" for b in t["because"])
                mark = "✓" if t["in_truth"] else "✗"
                lines.append(f"  - {mark} #{t['id']} {t['title']} — {because}")
        lines.append("")
    lines.append(f"Timing: labelling {meta['label_minutes']:.1f} min for {meta['n_records']} records; decision cache {meta['cache_entries']} entries; model calls this run {meta['model_calls']}.")
    return "\n".join(lines)


def write_results(res: dict, meta: dict, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, **res}, f, indent=1)
    with open(out / "results.md", "w", encoding="utf-8") as f:
        f.write(to_markdown(res, meta) + "\n")
