"""The investigation loop: objective + data -> hypothesise -> query -> observe -> update -> repeat
-> report. Nothing about the path is scripted; the planner decides every next check from what the
previous ones returned.

Two model tiers, the way a cost router would split the work: the planner (the larger model) owns
the hypotheses and the decision to stop; the coder (the smaller model) only turns one concrete
check into one SQL query. The report records each tier's calls and tokens separately."""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

from .data import COLUMNS, SCHEMA, periods
from .tools import SQLError, format_result, run_sql

PLANNER_SYSTEM = """You are a data analyst investigating a business question with SQL. You never see the
raw data; you plan checks, read their results, and update your hypotheses.
Reply with ONE JSON object and nothing else:
{"hypotheses": [{"text": "...", "status": "open" | "supported" | "rejected"}],
 "next_check": "one concrete question the next SQL query should answer",
 "done": false,
 "root_cause": [{"dimension": "...", "value": "..."}],
 "explanation": "..."}
Set "done": true only when the evidence supports a conclusion. "root_cause" lists the dimension=value
conditions that together define the slice whose change explains the decline (one condition, or two for
an interaction); use [] if the decline is broad-based and no slice explains it. Dimensions must be
from: region, channel, category, product, customer_type."""

CODER_SYSTEM = """You write SQLite queries. Reply with exactly one SELECT statement in a ```sql block
and nothing else. Only the table below exists."""


@dataclass
class Step:
    check: str
    sql: str
    result: str
    error: bool = False


@dataclass
class Report:
    root_cause: list[dict] | None  # None = no usable answer
    explanation: str
    hypotheses: list[dict]
    steps: list[Step]
    concluded: bool  # False when the step budget forced the conclusion
    sql_errors: int
    usage: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"root_cause": self.root_cause, "explanation": self.explanation, "hypotheses": self.hypotheses,
                "concluded": self.concluded, "sql_errors": self.sql_errors, "usage": self.usage,
                "steps": [s.__dict__ for s in self.steps]}


def parse_json(text: str) -> dict | None:
    """The first JSON object in a model reply, tolerating fences and chatter around it."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            depth += ch == "{"
            depth -= ch == "}"
            if depth == 0:
                candidates.append(text[start:i + 1])
                break
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def parse_sql(text: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = fenced.group(1) if fenced else text
    m = re.search(r"\b(with|select)\b.*", sql, re.S | re.I)
    return (m.group(0) if m else sql).strip().rstrip(";").strip()


def clean_root_cause(raw) -> list[dict] | None:
    """The concluded slice, [] for an explicit "broad-based", or None when the model gave no usable
    answer — which must never score as "broad-based"."""
    if not isinstance(raw, list):
        return None
    out = []
    for item in raw:
        if isinstance(item, dict) and str(item.get("dimension", "")).strip() in COLUMNS and item.get("value") is not None:
            out.append({"dimension": str(item["dimension"]).strip(), "value": str(item["value"]).strip()})
    return out if out or not raw else None  # a non-empty list with no valid entries is not "broad-based"


def dimension_values(con: sqlite3.Connection) -> str:
    return "\n".join(f"{d}: " + ", ".join(v for (v,) in con.execute(f"SELECT DISTINCT {d} FROM orders ORDER BY 1"))
                     for d in COLUMNS)


class Analyst:
    def __init__(self, planner, coder, max_steps: int = 6):
        self.planner, self.coder, self.max_steps = planner, coder, max_steps

    def _context(self, objective: str, con: sqlite3.Connection) -> str:
        (b0, b1), (a0, a1) = periods()
        return (f"Objective: {objective}\n\nTable:\n{SCHEMA}\n\nValues:\n{dimension_values(con)}\n\n"
                f"Period before: {b0} to {b1}. Period after: {a0} to {a1}.")

    def _plan(self, context: str, steps: list[Step], hypotheses: list[dict], force: bool) -> dict:
        history = "\n\n".join(f"Check {i}: {s.check}\nSQL: {s.sql}\nResult:\n{s.result}" for i, s in enumerate(steps, 1))
        ask = ("You have used your budget of checks: conclude now with done=true."
               if force else "Decide the next check, or conclude if the evidence is sufficient.")
        user = (f"{context}\n\nHypotheses so far: {json.dumps(hypotheses)}\n\n"
                f"Evidence so far:\n{history or '(none yet)'}\n\n{ask}")
        reply = self.planner.chat([{"role": "system", "content": PLANNER_SYSTEM}, {"role": "user", "content": user}],
                                  max_new_tokens=400)
        return parse_json(reply) or {}

    def _query(self, context: str, check: str, con: sqlite3.Connection) -> Step:
        user = f"{context}\n\nWrite one query that answers: {check}"
        messages = [{"role": "system", "content": CODER_SYSTEM}, {"role": "user", "content": user}]
        sql = ""
        for attempt in range(2):
            sql = parse_sql(self.coder.chat(messages, max_new_tokens=300))
            try:
                return Step(check, sql, format_result(*run_sql(con, sql)))
            except SQLError as e:
                if attempt == 0:
                    messages += [{"role": "assistant", "content": f"```sql\n{sql}\n```"},
                                 {"role": "user", "content": f"That failed: {e}. Reply with a corrected query."}]
                else:
                    return Step(check, sql, f"ERROR: {e}", error=True)
        return Step(check, sql, "ERROR: no query", error=True)

    def investigate(self, objective: str, con: sqlite3.Connection) -> Report:
        context = self._context(objective, con)
        steps: list[Step] = []
        hypotheses: list[dict] = []
        plan: dict = {}
        concluded = False
        for i in range(self.max_steps + 1):
            force = i == self.max_steps
            plan = self._plan(context, steps, hypotheses, force)
            if isinstance(plan.get("hypotheses"), list):
                hypotheses = [h for h in plan["hypotheses"] if isinstance(h, dict)]
            if plan.get("done") or force:
                concluded = bool(plan.get("done")) and not force
                break
            check = str(plan.get("next_check") or "").strip()
            if not check:
                check = "Revenue before and after the change for each value of each dimension"
            steps.append(self._query(context, check, con))
        return Report(
            root_cause=clean_root_cause(plan.get("root_cause")),
            explanation=str(plan.get("explanation", "")),
            hypotheses=hypotheses,
            steps=steps,
            concluded=concluded,
            sql_errors=sum(s.error for s in steps),
            usage={"planner": {"model": self.planner.name, **self.planner.usage.as_dict()},
                   "coder": {"model": self.coder.name, **self.coder.usage.as_dict()}},
        )


def score(pred: list[dict] | None, truth: list[dict]) -> dict:
    """exact: same set of dimension=value conditions (values case-insensitive); overlap: Jaccard.
    No answer (None) scores zero on both, even against a broad-based truth."""
    if pred is None:
        return {"exact": False, "overlap": 0.0}
    key = lambda xs: {(x["dimension"], str(x["value"]).lower()) for x in xs}
    p, t = key(pred), key(truth)
    exact = p == t
    overlap = 1.0 if not p and not t else len(p & t) / len(p | t) if p | t else 0.0
    return {"exact": exact, "overlap": round(overlap, 3)}
