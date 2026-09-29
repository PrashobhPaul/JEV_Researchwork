"""python -m analyst --config configs/open-models.json [--scenarios a,b] [--fake]

Runs the no-model baseline and the agent on every planted scenario, scores both against the planted
root cause (exact match of the dimension=value set, no judge), and writes results/<name>.json, a
markdown table, and the README results section."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import time
from pathlib import Path

from .agent import Analyst, score
from .baseline import largest_drop
from .data import BY_NAME, SCENARIOS, generate, load_sqlite, objective
from .llm import ScriptedLLM, make_llm

ROOT = Path(__file__).resolve().parent.parent


def fmt_cause(rc: list[dict] | None) -> str:
    if rc is None:
        return "no answer"
    return " & ".join(f"{x['dimension']}={x['value']}" for x in rc) if rc else "broad-based"


def run(cfg: dict, scenario_names: list[str], fake: bool = False, log=print) -> dict:
    if fake:
        planner = ScriptedLLM([], name="fake-planner")
        coder = ScriptedLLM([], name="fake-coder")
    else:
        planner, coder = make_llm(cfg["planner"]), make_llm(cfg["coder"])
    rows = []
    for name in scenario_names:
        s = BY_NAME[name]
        con = load_sqlite(generate(s, seed=cfg.get("seed", 7)))
        base = largest_drop(con)
        t0 = time.time()
        before = {k: m.usage.as_dict() for k, m in (("planner", planner), ("coder", coder))}
        rep = Analyst(planner, coder, max_steps=cfg.get("max_steps", 6)).investigate(objective(), con)
        after = rep.usage
        usage = {k: {f: after[k][f] - before[k][f] for f in ("calls", "input_tokens", "output_tokens")}
                 for k in ("planner", "coder")}
        row = {
            "scenario": name, "effect": s.effect, "truth": s.truth,
            "baseline": {"root_cause": base["root_cause"], **score(base["root_cause"], s.truth)},
            "agent": {"root_cause": rep.root_cause, **score(rep.root_cause, s.truth), "concluded": rep.concluded,
                      "steps": len(rep.steps), "sql_errors": rep.sql_errors, "usage": usage,
                      "minutes": round((time.time() - t0) / 60, 1), "explanation": rep.explanation,
                      "hypotheses": rep.hypotheses, "trace": [st.__dict__ for st in rep.steps]},
        }
        rows.append(row)
        log(f"{name:16s} truth={fmt_cause(s.truth):32s} baseline={fmt_cause(base['root_cause']):28s} "
            f"agent={fmt_cause(rep.root_cause):28s} exact={row['agent']['exact']} steps={len(rep.steps)} "
            f"({row['agent']['minutes']} min)")
    n = len(rows)
    summary = {k: {"exact": sum(r[k]["exact"] for r in rows), "overlap": round(sum(r[k]["overlap"] for r in rows) / n, 3)}
               for k in ("baseline", "agent")}
    return {
        "meta": {"name": cfg.get("name", "run"), "planner": planner.name, "coder": coder.name,
                 "max_steps": cfg.get("max_steps", 6), "seed": cfg.get("seed", 7),
                 "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                 "runner": os.environ.get("RUNNER_OS", platform.system()) + f" / {os.cpu_count()} cpu"},
        "n": n, "summary": summary, "scenarios": rows,
        "usage": {k: {f: sum(r["agent"]["usage"][k][f] for r in rows) for f in ("calls", "input_tokens", "output_tokens")}
                  for k in ("planner", "coder")},
    }


def markdown(res: dict) -> str:
    m, s, n = res["meta"], res["summary"], res["n"]
    lines = [
        f"**Planner:** {m['planner']}. **Coder:** {m['coder']}. **Budget:** {m['max_steps']} checks per scenario. "
        f"**Run:** {m['run_at']} on {m['runner']}.",
        "",
        "| Scenario | Planted cause | Baseline (largest drop) | Agent | Agent steps |",
        "|---|---|---|---|---:|",
    ]
    for r in res["scenarios"]:
        mark = lambda x: "✓" if x["exact"] else ("½" if x["overlap"] > 0 else "✗")
        lines.append(f"| {r['scenario']} | {fmt_cause(r['truth'])} | {mark(r['baseline'])} {fmt_cause(r['baseline']['root_cause'])} "
                     f"| {mark(r['agent'])} {fmt_cause(r['agent']['root_cause'])} | {r['agent']['steps']} |")
    lines += [
        "",
        f"**Exact root cause:** baseline {s['baseline']['exact']}/{n}, agent {s['agent']['exact']}/{n}. "
        f"**Mean overlap (Jaccard):** baseline {s['baseline']['overlap']:.3f}, agent {s['agent']['overlap']:.3f}.",
        "",
        "**Usage by tier:** " + "; ".join(f"{k} {v['calls']} calls, {v['input_tokens']:,} in / {v['output_tokens']:,} out tokens"
                                          for k, v in res["usage"].items()) + ".",
    ]
    return "\n".join(lines)


def inject_readme(name: str, body: str, readme: Path) -> None:
    start, end = f"<!-- results:{name}:start -->", f"<!-- results:{name}:end -->"
    text = readme.read_text(encoding="utf-8")
    section = f"{start}\n{body}\n{end}"
    if start in text:
        text = re.sub(f"{re.escape(start)}.*?{re.escape(end)}", lambda _: section, text, flags=re.S)
    else:
        if "<!-- results:end -->" not in text:
            raise SystemExit("README.md is missing the <!-- results:end --> anchor")
        text = text.replace("<!-- results:end -->", f"<!-- results:end -->\n\n{section}", 1)
    readme.write_text(text, encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="analyst")
    ap.add_argument("--config", required=True)
    ap.add_argument("--scenarios", default=",".join(s.name for s in SCENARIOS))
    ap.add_argument("--fake", action="store_true", help="scripted models that return nothing (plumbing check only)")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text())
    res = run(cfg, [x for x in a.scenarios.split(",") if x], fake=a.fake)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    name = cfg.get("name", "run")
    (out / f"{name}.json").write_text(json.dumps(res, indent=1))
    md = markdown(res)
    (out / f"{name}.md").write_text(md + "\n")
    if not a.fake:
        inject_readme(name, md, ROOT / "README.md")
    print("\n" + md)
