"""The one tool the agent gets: read-only SQL over the orders table, with results capped so a
careless query cannot flood the model's context."""
from __future__ import annotations

import re
import sqlite3

MAX_ROWS = 20
_ALLOWED = re.compile(r"^\s*(with|select)\b", re.I)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)


class SQLError(Exception):
    pass


def run_sql(con: sqlite3.Connection, sql: str, max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple], bool]:
    """(columns, rows, truncated). Only a single SELECT/WITH statement is accepted."""
    sql = sql.strip().rstrip(";").strip()
    if not _ALLOWED.match(sql) or _FORBIDDEN.search(sql) or ";" in sql:
        raise SQLError("only a single read-only SELECT/WITH statement is allowed")
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(max_rows + 1)
    except sqlite3.Error as e:
        raise SQLError(str(e)) from e
    cols = [d[0] for d in cur.description or []]
    return cols, rows[:max_rows], len(rows) > max_rows


def format_result(cols: list[str], rows: list[tuple], truncated: bool) -> str:
    def cell(v):
        return f"{v:,.2f}" if isinstance(v, float) else str(v)

    lines = [" | ".join(cols)] + [" | ".join(cell(v) for v in r) for r in rows]
    if truncated:
        lines.append(f"... (first {len(rows)} rows shown)")
    if not rows:
        lines.append("(no rows)")
    return "\n".join(lines)
