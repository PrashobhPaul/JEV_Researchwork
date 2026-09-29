"""Render the Part 2 assets from real results.

    python part2/render.py --primary vscode --secondary vscode-lumma

Reads data/<primary>/results.json (the labeller the post leads with) and, if present,
data/<secondary>/results.json (the comparison labeller), then writes to part2/out/:

    explainer.png                 4:5 infographic (numbers filled in)
    explainer_animated.mp4/.gif   same, with directional flow along the pipeline
    results_card.png              landscape results table
    matched_because.png           a result list with "matched because" chips
    post.md                       the post, numbers filled in, ready to edit

Needs: pip install playwright && playwright install chromium ; ffmpeg on PATH for the animation.
Every number in the outputs comes from results.json; nothing is typed by hand.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent  # the facetvec project folder
TPL = Path(__file__).resolve().parent / "templates"
OUT = Path(__file__).resolve().parent / "out"

NAMES = {
    "bm25": "BM25 (lexical)",
    "dense": "Dense (bge-small)",
    "facets": "Facets — model labels, model encoding",
    "fused": "Fused — RRF(BM25 + dense + facets)",
    "facets-oracle": "Facets — oracle labels (ceiling)",
    "fused-oracle": "Fused — oracle labels (ceiling)",
}


def load(name: str) -> dict | None:
    p = ROOT / "data" / name / "results.json"
    return json.loads(p.read_text()) if p.exists() else None


def f3(x: float) -> str:
    return f"{x:.3f}"


def result_rows(res: dict) -> str:
    s = res["summary"]
    rows = []
    best_typed = max(s[k]["typed"]["ndcg"] for k in ("bm25", "dense", "facets", "fused"))
    for key in ("bm25", "dense", "facets", "fused", "facets-oracle", "fused-oracle"):
        t, o = s[key]["typed"], s[key]["open"]
        cls = ""
        if key == "facets":
            cls = "win" if t["ndcg"] >= best_typed else "lose"
        rows.append(
            f'<tr class="{cls}"><td>{NAMES[key]}</td><td class="n">{f3(t["ndcg"])}</td><td class="n">{f3(t["r"])}</td>'
            f'<td class="n">{f3(o["mrr"])}</td><td class="n">{f3(o["r"])}</td></tr>'
        )
    return "\n".join(rows)


def facet_rows(res: dict) -> str:
    """One bar per facet, taken from the first 'matched because' example if present, else from
    label_accuracy names with neutral values."""
    ex = res.get("examples") or []
    rows = []
    if ex and ex[0]["top"]:
        for b in ex[0]["top"][0]["because"][:6]:
            rows.append(f'<div class="row"><span class="k">{b["facet"]}</span><span class="bar"><i style="width:{int(b["p"]*100)}%"></i></span><span class="v">{b["option"]} {b["p"]:.2f}</span></div>')
    for name in list(res["label_accuracy"].keys())[:6]:
        if len(rows) >= 6:
            break
        if not any(name in r for r in rows):
            rows.append(f'<div class="row"><span class="k">{name}</span><span class="bar"><i style="width:0%"></i></span><span class="v">—</span></div>')
    return "\n".join(rows)


def label_acc_line(res: dict) -> str:
    return " · ".join(f'{n} {a["accuracy"]:.2f} (majority {a["majority_baseline"]:.2f})' for n, a in res["label_accuracy"].items())


def headline(s: dict) -> str:
    """The results card's claim, chosen by the numbers so it can never contradict the table."""
    facets, dense, fused = (s[k]["typed"]["ndcg"] for k in ("facets", "dense", "fused"))
    if facets >= max(dense, fused):
        return "Facets win the typed queries. Facets alone <span>collapse</span> on open ones. Fuse."
    if fused > dense:
        return "Fused wins the typed queries. Facets alone trail dense, and <span>collapse</span> on open ones."
    return "Dense wins the typed queries here. Facets alone <span>collapse</span> on open ones."


def secondary_line(sec: dict | None) -> str:
    if not sec:
        return "not run"
    s = sec["summary"]
    return f'{sec["meta"]["decision_model"].split(":")[1]}: typed nDCG {f3(s["facets"]["typed"]["ndcg"])}, open MRR fused {f3(s["fused"]["open"]["mrr"])}'


def fill(template: str, ctx: dict) -> str:
    return Template(template).safe_substitute(ctx)


def context(pri: dict, sec: dict | None, repo_url: str) -> dict:
    m = pri["meta"]
    s = pri["summary"]
    n_typed, n_open = pri["n_queries"]["typed"], pri["n_queries"]["open"]
    facet_ndcg, dense_ndcg, bm25_ndcg = s["facets"]["typed"]["ndcg"], s["dense"]["typed"]["ndcg"], s["bm25"]["typed"]["ndcg"]
    ctx = {
        "corpus": m["corpus"],
        "n_records": m["n_records"],
        "n_questions": m["n_questions"],
        "decision_model": m["decision_model"],
        "decision_model_short": m["decision_model"].split(":")[1] if ":" in m["decision_model"] else m["decision_model"],
        "dense_model": m["dense_model"],
        "k": pri["k"],
        "n_typed": n_typed,
        "n_open": n_open,
        "result_rows": result_rows(pri),
        "facet_rows": facet_rows(pri),
        "label_acc_line": label_acc_line(pri),
        "secondary_line": secondary_line(sec),
        "note_top": 862 + 40 + 6 * 38 + 14,
        "list_top": 862 + 40 + 6 * 38 + 84,  # clears a three-line note
        "repo_url": repo_url,
        # post numbers
        "facets_typed_ndcg": f3(facet_ndcg),
        "dense_typed_ndcg": f3(dense_ndcg),
        "bm25_typed_ndcg": f3(bm25_ndcg),
        "fused_typed_ndcg": f3(s["fused"]["typed"]["ndcg"]),
        "oracle_typed_ndcg": f3(s["facets-oracle"]["typed"]["ndcg"]),
        "facets_open_mrr": f3(s["facets"]["open"]["mrr"]),
        "dense_open_mrr": f3(s["dense"]["open"]["mrr"]),
        "fused_open_mrr": f3(s["fused"]["open"]["mrr"]),
        "typed_multiple": f"{facet_ndcg / max(dense_ndcg, 1e-9):.1f}",
        "encoder_acc": f3(pri["query_encoder_accuracy"] or 0.0),
        "secondary_model": (sec["meta"]["decision_model"].split(":")[1] if sec else "n/a"),
        "secondary_typed_ndcg": f3(sec["summary"]["facets"]["typed"]["ndcg"]) if sec else "n/a",
        "bm25_open_mrr": f3(s["bm25"]["open"]["mrr"]),
        "secondary_fused_typed_ndcg": f3(sec["summary"]["fused"]["typed"]["ndcg"]) if sec else "n/a",
        "area_acc": f3(pri["label_accuracy"].get("area", {}).get("accuracy", 0.0)),
        "area_majority": f3(pri["label_accuracy"].get("area", {}).get("majority_baseline", 0.0)),
        "kind_acc": f3(pri["label_accuracy"].get("kind", {}).get("accuracy", 0.0)),
        "kind_majority": f3(pri["label_accuracy"].get("kind", {}).get("majority_baseline", 0.0)),
        "example_query": (pri["examples"][0]["query"] if pri.get("examples") else ""),
        "example_because": (", ".join(f'{b["facet"]}={b["option"]} ({b["p"]:.2f})' for b in pri["examples"][0]["top"][0]["because"]) if pri.get("examples") else ""),
        "headline": headline(s),
        "run_at": m["run_at"],
        "runner": m["runner"],
    }
    return ctx


def matched_html(pri: dict, ctx: dict) -> str:
    cards = []
    for ex in (pri.get("examples") or [])[:2]:
        items = []
        for t in ex["top"]:
            chips = "".join(
                f'<span class="chip {b["mode"]}">{b["facet"]} = {b["option"]} <b>{b["p"]:.2f}</b></span>' for b in t["because"]
            )
            mark = "✓" if t["in_truth"] else "✗"
            title = t["title"] + ("…" if len(t["title"]) >= 90 else "")  # results.json keeps 90 chars
            items.append(f'<div class="item"><div class="t"><span class="m {"y" if t["in_truth"] else "n"}">{mark}</span> #{t["id"]} {title}</div><div class="chips">{chips}</div></div>')
        cards.append(f'<div class="q">query: <b>{ex["query"]}</b></div>' + "".join(items))
    return fill((TPL / "matched_because.html").read_text(), {**ctx, "cards": "\n".join(cards)})


def screenshot(html: str, out: Path, w: int, h: int, scale: float = 2.0) -> None:
    from playwright.sync_api import sync_playwright

    tmp = Path(tempfile.mkdtemp()) / "page.html"
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(1800)
        pg.screenshot(path=str(out))
        b.close()


def animate(html: str, out_mp4: Path, out_gif: Path, w: int, h: int, fps: int = 15, dur: float = 3.8) -> None:
    from playwright.sync_api import sync_playwright

    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; skipping animation")
        return
    frames = Path(tempfile.mkdtemp())
    (frames / "page.html").write_text(html, encoding="utf-8")
    n = int(fps * dur)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto((frames / "page.html").as_uri())
        pg.wait_for_timeout(1800)
        for i in range(n):
            pg.evaluate(f"render({i / fps})")
            pg.screenshot(path=str(frames / f"f{i:04d}.png"))
        b.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out_mp4)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "f%04d.png"), "-vf", "scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3", "-loop", "0", str(out_gif)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default="vscode")
    ap.add_argument("--secondary", default="vscode-lumma")
    ap.add_argument("--repo-url", default="github.com/PrashobhPaul/JEV_Researchwork")
    ap.add_argument("--no-animation", action="store_true")
    a = ap.parse_args()
    pri = load(a.primary)
    if not pri:
        raise SystemExit(f"no results for {a.primary}; run the evaluate workflow first")
    sec = load(a.secondary)
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = context(pri, sec, a.repo_url)

    expl = fill((TPL / "explainer.html").read_text(), ctx)
    screenshot(expl, OUT / "explainer.png", 1200, 1500)
    if not a.no_animation:
        animate(expl, OUT / "explainer_animated.mp4", OUT / "explainer_animated.gif", 1200, 1500)
    screenshot(fill((TPL / "results_card.html").read_text(), ctx), OUT / "results_card.png", 1200, 675)
    screenshot(matched_html(pri, ctx), OUT / "matched_because.png", 1200, 675)
    screenshot(fill((TPL / "companion.html").read_text(), ctx), OUT / "companion.png", 1200, 1500, scale=1.0)
    (OUT / "post.md").write_text(fill((TPL / "post.md").read_text(), ctx), encoding="utf-8")
    (OUT / "context.json").write_text(json.dumps({k: v for k, v in ctx.items() if not k.endswith("_rows")}, indent=1))
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
