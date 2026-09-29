"""The Part 2 renderer embeds GitHub issue titles and queries in HTML; they must never become markup."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "part2"))
import render  # noqa: E402


def test_matched_because_escapes_issue_text():
    pri = json.loads((Path(__file__).resolve().parent.parent / "data" / "vscode" / "results.json").read_text())
    pri["examples"][0]["query"] = "<b>q</b>"
    pri["examples"][0]["top"][0]["title"] = "evil </div><script>alert(1)</script> & co"
    out = render.matched_html(pri, render.context(pri, None, "repo"))
    assert "<script>" not in out and "&lt;/div&gt;&lt;script&gt;" in out
    assert "&amp; co" in out and "&lt;b&gt;q&lt;/b&gt;" in out
