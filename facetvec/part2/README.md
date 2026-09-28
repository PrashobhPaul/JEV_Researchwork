# Part 2 kit

`render.py` fills `templates/` from `../data/<name>/results.json` and writes `out/`:
explainer (4:5 PNG + animated MP4/GIF with directional flow), results card (16:9), matched-because
card (16:9), and `post.md`. Every number in the outputs is read from results.json.

    pip install playwright && playwright install chromium   # plus ffmpeg on PATH
    python part2/render.py --primary vscode --secondary vscode-lumma

Provenance of the numbers used for the published assets: _pending — filled in after the evaluate runs._
