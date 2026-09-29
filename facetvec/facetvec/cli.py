"""python -m facetvec <command> --config configs/<corpus>.json

  fetch    build the corpus snapshot (GitHub API or JSONL) -> data/<name>/corpus.jsonl
  label    ask the decision model every question about every record -> facets.json
  embed    build the dense index -> dense.npz
  eval     run both query families over every system -> results.json / results.md
  report   inject results.md into README.md between the result markers
  all      fetch (if no snapshot) -> label -> embed -> eval -> report
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

from .corpus import github_issues as gh
from .decision.base import CachedModel, DecisionCache
from .eval.queries import build_open, build_typed
from .eval.run import run_eval, write_results
from .index.dense import DenseIndex
from .index.facets import label_corpus, load_facets, oracle_facets, save_facets
from .index.lexical import LexicalIndex
from .schema import Vocabulary
from .search.encoder import ModelEncoder


def log(msg: str) -> None:
    print(msg, flush=True)


def load_cfg(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def data_dir(cfg: dict) -> Path:
    d = Path("data") / cfg["name"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_corpus(cfg: dict) -> list:
    """The snapshot, with oracle facets re-derived from its labels under the current config."""
    recs = gh.load(data_dir(cfg) / "corpus.jsonl")
    kept, changed = gh.reapply_oracle(recs, cfg)
    if changed or len(kept) != len(recs):
        log(f"  oracle mapping re-applied: {changed} records changed, {len(recs) - len(kept)} dropped")
    return kept


def make_model(cfg: dict, fake: bool = False):
    if fake:
        from .decision.fake import KeywordModel

        return KeywordModel()
    rc = dict(cfg.get("decision_model", {}))
    adapter = rc.pop("adapter", "lumma-fev")
    if adapter == "lumma-fev":
        from .decision.lumma_fev import LummaFevConfig, LummaFevModel

        return LummaFevModel(LummaFevConfig(**rc))
    if adapter == "logit-readout":
        from .decision.logit_readout import LogitReadoutModel, ReadoutConfig

        return LogitReadoutModel(ReadoutConfig(**rc))
    if adapter == "systemone-api":
        from .decision.systemone_api import SystemOneAPIModel, SystemOneConfig

        return SystemOneAPIModel(SystemOneConfig(**rc))
    raise SystemExit(f"unknown decision_model.adapter {adapter!r} (lumma-fev | logit-readout | systemone-api)")


# ----- commands ----------------------------------------------------------------------------------


def cmd_fetch(cfg: dict, args) -> None:
    src = cfg["source"]
    if src["type"] == "github_api":
        log(f"fetching issues from github.com/{src['repo']} (state={src.get('state', 'all')})")
        raw = gh.fetch_github_api(src["repo"], src.get("max_fetch", 1500), src.get("state", "all"), log=log)
    elif src["type"] == "jsonl":
        raw = gh.load_jsonl(src["path"])
    elif src["type"] == "jsonl_url":
        cache = data_dir(cfg) / "raw.jsonl"
        if not cache.exists():
            import urllib.request

            log(f"downloading {src['url']}")
            urllib.request.urlretrieve(src["url"], cache)
        raw = gh.load_jsonl(cache)
    else:
        raise SystemExit(f"unknown source type {src['type']}")
    recs = gh.normalise(raw, cfg)
    log(f"  {len(raw)} raw issues -> {len(recs)} usable (body >= {cfg.get('min_body_chars', 80)} chars, required facets present)")
    if len(recs) < cfg.get("min_records", 100):
        raise SystemExit(f"only {len(recs)} usable records; check the oracle label mapping in the config")
    recs = gh.balance(recs, cfg.get("balance_facet", "kind"), src.get("max_records", 400))
    gh.save(recs, data_dir(cfg) / "corpus.jsonl")
    dist = {}
    for r in recs:
        for f, o in r.oracle.items():
            dist.setdefault(f, {}).setdefault(o, 0)
            dist[f][o] += 1
    log(f"  saved {len(recs)} records; oracle distribution: {json.dumps(dist)}")


def cmd_label(cfg: dict, args) -> None:
    d = data_dir(cfg)
    recs = load_corpus(cfg)
    vocab = Vocabulary.from_config(cfg["questions"])
    dm = CachedModel(make_model(cfg, args.fake), DecisionCache(d / "decisions.sqlite"))
    log(f"labelling {len(recs)} records × {len(vocab.questions)} questions with {dm.name} (cache: {dm.cache.count()} entries)")
    t0 = time.time()
    facets = label_corpus(recs, vocab, dm, log=log)
    save_facets(facets, d / "facets.json")
    save_facets(oracle_facets(recs, vocab), d / "facets_oracle.json")
    with open(d / "label_meta.json", "w") as f:
        json.dump({"minutes": (time.time() - t0) / 60, "model": dm.name, "model_calls": dm.model_calls, "vocab_fingerprint": vocab.fingerprint()}, f)
    log(f"  done in {(time.time()-t0)/60:.1f} min; {dm.model_calls} records needed the model, rest from cache")


def cmd_embed(cfg: dict, args) -> None:
    d = data_dir(cfg)
    recs = load_corpus(cfg)
    idx = DenseIndex.build(recs, cfg.get("dense_model", "BAAI/bge-small-en-v1.5"), log=log)
    idx.save(d / "dense.npz")
    log(f"  saved {idx.vectors.shape} vectors")


def cmd_eval(cfg: dict, args) -> None:
    d = data_dir(cfg)
    recs = load_corpus(cfg)
    vocab = Vocabulary.from_config(cfg["questions"])
    facets_m = load_facets(d / "facets.json")
    facets_o = load_facets(d / "facets_oracle.json")
    dense = DenseIndex.load(d / "dense.npz")
    if set(dense.ids) != {r.id for r in recs}:
        raise SystemExit("dense.npz does not match corpus.jsonl — run `embed` again")
    if set(map(int, facets_m)) != {r.id for r in recs}:
        raise SystemExit("facets.json does not match corpus.jsonl — run `label` again")
    lexical = LexicalIndex(recs)
    dm = CachedModel(make_model(cfg, args.fake), DecisionCache(d / "decisions.sqlite"))
    enc_cfg = cfg.get("query_encoder", {})
    encoder = ModelEncoder(dm, vocab, enc_cfg.get("filter_at", 0.6), enc_cfg.get("prefer_at", 0.4))
    typed = build_typed(recs, cfg["typed_queries"])
    open_q = build_open(recs, cfg.get("open_queries", {}).get("n", 60))
    log(f"evaluating {len(typed)} typed + {len(open_q)} open queries over {len(recs)} records")
    res = run_eval(recs, vocab, typed + open_q, facets_m, facets_o, dense, lexical, encoder, k=cfg.get("k", 10), log=log)
    lm = json.load(open(d / "label_meta.json"))
    meta = {
        "corpus": cfg["source"].get("repo") or cfg["source"].get("path"),
        "n_records": len(recs),
        "n_questions": len(vocab.questions),
        "decision_model": lm["model"],
        "dense_model": dense.model_name,
        "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "runner": os.environ.get("RUNNER_OS", platform.system()) + f" / {os.cpu_count()} cpu",
        "label_minutes": lm["minutes"],
        "cache_entries": dm.cache.count(),
        "model_calls": lm["model_calls"] + dm.model_calls,
    }
    write_results(res, meta, d)
    log("\n" + open(d / "results.md").read())


def cmd_report(cfg: dict, args) -> None:
    """Inject data/<name>/results.md into README.md under a per-config marker pair, creating the
    section (right after the generic results block) if it does not exist yet."""
    d = data_dir(cfg)
    readme = Path("README.md")
    body = open(d / "results.md", encoding="utf-8").read().strip()
    name = cfg["name"]
    start, end = f"<!-- results:{name}:start -->", f"<!-- results:{name}:end -->"
    text = readme.read_text(encoding="utf-8")
    section = f"{start}\n### {name} — `configs/{name}.json`\n\n{body}\n{end}"
    if start in text and end in text:
        text = re.sub(f"{re.escape(start)}.*?{re.escape(end)}", section, text, flags=re.S)
    else:
        anchor = "<!-- results:end -->"
        if anchor not in text:
            raise SystemExit("README.md is missing the <!-- results:end --> anchor")
        text = text.replace(anchor, anchor + "\n\n" + section, 1)
    text = re.sub(r"<!-- results:start -->.*?<!-- results:end -->", "<!-- results:start -->\n<!-- results:end -->", text, flags=re.S)
    readme.write_text(text, encoding="utf-8")
    log(f"README.md results section for {name} updated")


def cmd_all(cfg: dict, args) -> None:
    d = data_dir(cfg)
    if args.refresh or not (d / "corpus.jsonl").exists():
        cmd_fetch(cfg, args)
    else:
        log(f"using existing snapshot {d / 'corpus.jsonl'} (pass --refresh to re-fetch)")
    cmd_label(cfg, args)
    cmd_embed(cfg, args)
    cmd_eval(cfg, args)
    cmd_report(cfg, args)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="facetvec", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["fetch", "label", "embed", "eval", "report", "all"])
    p.add_argument("--config", required=True)
    p.add_argument("--fake", action="store_true", help="use the keyword heuristic instead of a model (tests only)")
    p.add_argument("--refresh", action="store_true", help="re-fetch the corpus snapshot")
    p.add_argument("--max-records", type=int, help="override source.max_records")
    args = p.parse_args(argv)
    cfg = load_cfg(args.config)
    if args.max_records:
        cfg["source"]["max_records"] = args.max_records
    {"fetch": cmd_fetch, "label": cmd_label, "embed": cmd_embed, "eval": cmd_eval, "report": cmd_report, "all": cmd_all}[args.command](cfg, args)


if __name__ == "__main__":
    main(sys.argv[1:])
