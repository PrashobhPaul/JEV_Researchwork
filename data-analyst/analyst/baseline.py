"""The baseline the agent has to beat: no model, one query per dimension. For every dimension value,
compare revenue before and after the change date and blame the value with the largest absolute
drop. It is what an analyst would try first, and on a single-slice cause it is hard to beat. Its
blind spots are structural: it always names exactly one slice, so it cannot find a two-dimension
interaction and cannot say "broad-based"; and a product-level cause shows up almost as large at
its category, so it can pick the wrong granularity."""
from __future__ import annotations

import sqlite3

from .data import COLUMNS, periods


def revenue_drops(con: sqlite3.Connection) -> list[tuple[str, str, float, float]]:
    """(dimension, value, revenue_before, revenue_after) for every value of every dimension."""
    (b0, b1), (a0, a1) = periods()
    out = []
    for dim in COLUMNS:
        q = (f"SELECT {dim}, "
             f"SUM(CASE WHEN order_date BETWEEN ? AND ? THEN revenue ELSE 0 END), "
             f"SUM(CASE WHEN order_date BETWEEN ? AND ? THEN revenue ELSE 0 END) "
             f"FROM orders GROUP BY {dim}")
        for value, before, after in con.execute(q, (b0, b1, a0, a1)):
            out.append((dim, value, before or 0.0, after or 0.0))
    return out


def largest_drop(con: sqlite3.Connection) -> dict:
    dim, value, before, after = min(revenue_drops(con), key=lambda r: r[3] - r[2])
    return {"root_cause": [{"dimension": dim, "value": value}],
            "explanation": f"{dim}={value}: revenue {before:,.0f} -> {after:,.0f}"}
