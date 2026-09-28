"""Load real GitHub issues (from the REST API or from a JSONL dump in the API's shape) and derive
oracle facets from the repository's own labels.

The oracle facets are the ground truth for two things: how accurate the decision model's labels are,
and which records a typed query should retrieve. They are never shown to the model."""
from __future__ import annotations

import fnmatch
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Record:
    id: int
    title: str
    body: str
    labels: list[str]
    state: str
    url: str
    created_at: str
    oracle: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """The text every index sees. The title is deliberately excluded: it is the open-world query."""
        return self.body


# ----- sources ---------------------------------------------------------------------------------


def _api_get(url: str, token: str | None) -> tuple[list, dict]:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "facetvec"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()), dict(r.headers)


def fetch_github_api(repo: str, max_fetch: int, state: str = "all", token: str | None = None, log=print) -> list[dict]:
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    raw: list[dict] = []
    page = 1
    while len(raw) < max_fetch:
        qs = urllib.parse.urlencode({"state": state, "per_page": 100, "page": page, "sort": "updated", "direction": "desc"})
        batch, headers = _api_get(f"https://api.github.com/repos/{repo}/issues?{qs}", token)
        if not batch:
            break
        raw.extend(b for b in batch if "pull_request" not in b)
        log(f"  page {page}: {len(batch)} items, {len(raw)} issues so far, rate remaining {headers.get('X-RateLimit-Remaining', '?')}")
        page += 1
        time.sleep(0.2)
    return raw[:max_fetch]


def load_jsonl(path: str | Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                if d.get("pull_request") or d.get("is_pull_request"):
                    continue
                out.append(d)
    return out


# ----- normalisation ---------------------------------------------------------------------------

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_WS = re.compile(r"\n{3,}")


def clean_body(body: str | None, max_chars: int) -> str:
    if not body:
        return ""
    b = _HTML_COMMENT.sub("", body)
    b = _IMAGE.sub("", b)
    b = b.replace("\r\n", "\n")
    b = _WS.sub("\n\n", b).strip()
    return b[:max_chars]


def _oracle_for(labels: list[str], spec: dict) -> dict[str, str] | None:
    """Map the issue's labels onto the config's oracle facets. First matching option in map order wins.
    Returns None if a required facet has no match (the record is dropped)."""
    out: dict[str, str] = {}
    lower = [l.lower() for l in labels]
    for facet, fs in spec.items():
        chosen = None
        for option, patterns in fs["map"].items():
            if any(fnmatch.fnmatch(l, p.lower()) for l in lower for p in patterns):
                chosen = option
                break
        if chosen is None:
            if fs.get("required"):
                return None
            chosen = fs.get("default")
        if chosen is not None:
            out[facet] = chosen
    return out


def normalise(raw: list[dict], cfg: dict) -> list[Record]:
    min_chars = cfg.get("min_body_chars", 80)
    max_chars = cfg.get("max_body_chars", 4000)
    recs: list[Record] = []
    seen: set[int] = set()
    for d in raw:
        if int(d["number"]) in seen:
            continue
        seen.add(int(d["number"]))
        body = clean_body(d.get("body"), max_chars)
        if len(body) < min_chars:
            continue
        labels = [l["name"] if isinstance(l, dict) else str(l) for l in d.get("labels", [])]
        oracle = _oracle_for(labels, cfg["oracle"])
        if oracle is None:
            continue
        recs.append(
            Record(
                id=int(d["number"]),
                title=(d.get("title") or "").strip(),
                body=body,
                labels=labels,
                state=d.get("state", ""),
                url=d.get("html_url", ""),
                created_at=d.get("created_at", ""),
                oracle=oracle,
            )
        )
    return recs


def balance(recs: list[Record], facet: str, max_records: int, seed: int = 7) -> list[Record]:
    """Cap the corpus at max_records while keeping every option of `facet` represented in proportion,
    with a floor so rare options are not squeezed out."""
    import random

    rng = random.Random(seed)
    by: dict[str, list[Record]] = {}
    for r in recs:
        by.setdefault(r.oracle.get(facet, "_"), []).append(r)
    for v in by.values():
        rng.shuffle(v)
    total = sum(len(v) for v in by.values())
    if total <= max_records:
        return sorted(recs, key=lambda r: r.id)
    floor = max(8, max_records // (len(by) * 4))
    quota = {k: max(min(len(v), floor), int(max_records * len(v) / total)) for k, v in by.items()}
    out: list[Record] = []
    for k, v in by.items():
        out.extend(v[: quota[k]])
    return sorted(out[:max_records], key=lambda r: r.id)


def save(recs: list[Record], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def load(path: str | Path) -> list[Record]:
    with open(path, encoding="utf-8") as f:
        return [Record(**json.loads(line)) for line in f if line.strip()]
