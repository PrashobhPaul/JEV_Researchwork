"""Fast tests with scripted models: the data, the SQL guard, the loop, and the scoring. Real runs
come from the data-analyst-evaluate workflow."""
import json

import pytest

from analyst.agent import Analyst, clean_root_cause, parse_json, parse_sql, score
from analyst.baseline import largest_drop
from analyst.data import BY_NAME, SCENARIOS, generate, load_sqlite, objective
from analyst.llm import ScriptedLLM
from analyst.tools import SQLError, run_sql


def con_for(name):
    return load_sqlite(generate(BY_NAME[name]))


def test_generation_is_deterministic_and_plants_the_cause():
    assert generate(BY_NAME["stockout"]) == generate(BY_NAME["stockout"])
    con = con_for("stockout")
    after = con.execute("SELECT COUNT(*) FROM orders WHERE product='ELE-01' AND order_date >= '2026-04-27'").fetchone()[0]
    assert after == 0


def test_baseline_gets_single_slices_and_misses_the_hard_ones():
    got = {s.name: score(largest_drop(con_for(s.name))["root_cause"], s.truth)["exact"] for s in SCENARIOS}
    assert all(got[n] for n in ("region_closure", "price_increase", "channel_outage", "wholesale_churn", "stockout"))
    assert not got["interaction"] and not got["broad_decline"]


def test_sql_tool_is_read_only_and_capped():
    con = con_for("region_closure")
    for bad in ("DELETE FROM orders", "SELECT 1; DROP TABLE orders", "PRAGMA table_info(orders)"):
        with pytest.raises(SQLError):
            run_sql(con, bad)
    cols, rows, truncated = run_sql(con, "SELECT order_id FROM orders", max_rows=5)
    assert cols == ["order_id"] and len(rows) == 5 and truncated


def test_parsers_tolerate_chatter():
    assert parse_json('Sure!\n```json\n{"done": true, "root_cause": []}\n```') == {"done": True, "root_cause": []}
    assert parse_json('Thinking... {"a": {"b": 1}} trailing') == {"a": {"b": 1}}
    assert parse_json("no json here") is None
    assert parse_sql("Here you go:\n```sql\nSELECT region FROM orders;\n```") == "SELECT region FROM orders"


def test_no_answer_never_counts_as_broad_based():
    assert clean_root_cause(None) is None
    assert clean_root_cause([{"dimension": "colour", "value": "red"}]) is None
    assert clean_root_cause([]) == []
    assert score(None, []) == {"exact": False, "overlap": 0.0}
    assert score([], []) == {"exact": True, "overlap": 1.0}
    two = [{"dimension": "region", "value": "West"}, {"dimension": "channel", "value": "Online"}]
    assert score([{"dimension": "region", "value": "west"}], two) == {"exact": False, "overlap": 0.5}


def test_loop_investigates_retries_bad_sql_and_concludes():
    planner = ScriptedLLM([
        json.dumps({"hypotheses": [{"text": "one region collapsed", "status": "open"}],
                    "next_check": "revenue by region before vs after", "done": False}),
        json.dumps({"hypotheses": [{"text": "one region collapsed", "status": "supported"}],
                    "done": True, "root_cause": [{"dimension": "region", "value": "West"}],
                    "explanation": "West revenue fell ~70% while other regions held"}),
    ], name="planner")
    coder = ScriptedLLM([
        "```sql\nSELECT regoin FROM orders\n```",  # typo: fails, gets one retry with the error
        "```sql\nSELECT region, SUM(revenue) FROM orders GROUP BY region\n```",
    ], name="coder")
    rep = Analyst(planner, coder, max_steps=4).investigate(objective(), con_for("region_closure"))
    assert rep.concluded and rep.root_cause == [{"dimension": "region", "value": "West"}]
    assert len(rep.steps) == 1 and not rep.steps[0].error and "West" in rep.steps[0].result
    assert "no such column" in coder.prompts[1][-1]["content"]
    assert rep.usage["planner"]["calls"] == 2 and rep.usage["coder"]["calls"] == 2
    assert score(rep.root_cause, BY_NAME["region_closure"].truth)["exact"]


def test_budget_forces_a_conclusion():
    keep_going = json.dumps({"next_check": "revenue by channel", "done": False})
    planner = ScriptedLLM([keep_going, keep_going, json.dumps({"done": True, "root_cause": []})])
    coder = ScriptedLLM(["SELECT channel, SUM(revenue) FROM orders GROUP BY channel"] * 2)
    rep = Analyst(planner, coder, max_steps=2).investigate(objective(), con_for("broad_decline"))
    assert len(rep.steps) == 2 and not rep.concluded and rep.root_cause == []
    assert "conclude now" in planner.prompts[-1][-1]["content"]
