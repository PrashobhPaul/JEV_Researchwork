"""Synthetic retail orders with one planted root cause per scenario.

Every scenario starts from the same seasonal baseline — 16 weeks of orders across regions, channels,
categories, products and customer types — and then changes exactly one slice in the last 8 weeks.
Revenue falls because of that slice and nothing else, so the question "why did revenue decline?"
has one right answer that can be checked without a judge: the (dimension, value) pairs that were
planted — or none, for the scenario where every slice declines together.
Random noise keeps the other slices moving a little, so the answer is not the only thing that
changed — it is the thing that explains the decline."""
from __future__ import annotations

import datetime as dt
import random
import sqlite3
from dataclasses import dataclass

REGIONS = ["North", "South", "East", "West"]
CHANNELS = ["Online", "Store", "Partner"]
CATEGORIES = {"Electronics": 180.0, "Home": 60.0, "Apparel": 35.0, "Grocery": 12.0}
CUSTOMER_TYPES = ["Retail", "Wholesale"]
PRODUCTS = {c: [f"{c[:3].upper()}-{i:02d}" for i in range(1, 6)] for c in CATEGORIES}
START = dt.date(2026, 3, 2)
WEEKS = 16
CHANGE_WEEK = 8  # the planted change applies from this week on

COLUMNS = ["region", "channel", "category", "product", "customer_type"]


@dataclass(frozen=True)
class Scenario:
    name: str
    slice: tuple[tuple[str, str], ...]  # (dimension, value) pairs the change applies to; () = every order
    effect: str  # what the planted change does, for the report
    volume: float = 1.0  # multiplier on order count in the slice
    price: float = 1.0  # multiplier on unit price in the slice
    units: float = 1.0  # multiplier on units per order in the slice

    @property
    def truth(self) -> list[dict]:
        """The root cause as a list of {dimension, value}; empty means no single slice — broad-based."""
        return [{"dimension": d, "value": v} for d, v in self.slice]


SCENARIOS = [
    Scenario("region_closure", (("region", "West"),), "West stores lost 70% of orders (closures)", volume=0.3),
    Scenario("price_increase", (("category", "Electronics"),), "Electronics prices +40%, units per order down 60%",
             price=1.4, units=0.4),
    Scenario("channel_outage", (("channel", "Online"),), "the online channel lost 85% of orders (checkout outage)",
             volume=0.15),
    Scenario("wholesale_churn", (("customer_type", "Wholesale"),), "wholesale customers placed 75% fewer orders",
             volume=0.25),
    Scenario("stockout", (("product", "ELE-01"),), "the best-selling electronics product went out of stock",
             volume=0.0),
    # Harder: the cause is an interaction of two dimensions, so any single-slice answer is half right.
    Scenario("interaction", (("region", "West"), ("channel", "Online")),
             "online orders in the West dropped 90% (a regional payment-provider failure)", volume=0.1),
    # Harder: nothing to blame — every slice lost about a quarter of its orders. The right answer is
    # "broad-based", and blaming the largest slice is wrong.
    Scenario("broad_decline", (), "orders fell ~25% evenly across every slice (market-wide demand drop)",
             volume=0.75),
]
BY_NAME = {s.name: s for s in SCENARIOS}


def generate(scenario: Scenario, seed: int = 7, orders_per_day: int = 60) -> list[tuple]:
    """Rows of (order_id, order_date, region, channel, category, product, customer_type, units,
    unit_price, revenue). Deterministic for a given scenario and seed."""
    rng = random.Random(f"{scenario.name}:{seed}")
    region_w = [0.3, 0.25, 0.2, 0.25]
    channel_w = [0.45, 0.4, 0.15]
    cat_w = [0.3, 0.3, 0.25, 0.15]
    cust_w = [0.7, 0.3]
    product_w = [0.4, 0.2, 0.15, 0.15, 0.1]  # product 01 is each category's best seller
    rows = []
    oid = 0
    for day in range(WEEKS * 7):
        date = START + dt.timedelta(days=day)
        week = day // 7
        season = 1.0 + 0.15 * (1 if date.weekday() >= 5 else 0) + rng.uniform(-0.05, 0.05)
        for _ in range(int(orders_per_day * season)):
            region = rng.choices(REGIONS, region_w)[0]
            channel = rng.choices(CHANNELS, channel_w)[0]
            category = rng.choices(list(CATEGORIES), cat_w)[0]
            product = rng.choices(PRODUCTS[category], product_w)[0]
            cust = rng.choices(CUSTOMER_TYPES, cust_w)[0]
            units = rng.randint(1, 3) * (4 if cust == "Wholesale" else 1)
            price = CATEGORIES[category] * rng.uniform(0.9, 1.1)
            dims = {"region": region, "channel": channel, "category": category, "product": product,
                    "customer_type": cust}
            slice_hit = week >= CHANGE_WEEK and all(dims[d] == v for d, v in scenario.slice)
            if slice_hit:
                if rng.random() > scenario.volume:
                    continue
                price *= scenario.price
                units = max(1, round(units * scenario.units))
            oid += 1
            rows.append((oid, date.isoformat(), region, channel, category, product, cust, units,
                         round(price, 2), round(units * price, 2)))
    return rows


def load_sqlite(rows: list[tuple]) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute(
        "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, order_date TEXT, region TEXT, channel TEXT, "
        "category TEXT, product TEXT, customer_type TEXT, units INTEGER, unit_price REAL, revenue REAL)"
    )
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return con


def periods() -> tuple[tuple[str, str], tuple[str, str]]:
    """(before, after) date ranges, inclusive ISO strings: the 8 weeks before and after the change."""
    b0, b1 = START, START + dt.timedelta(days=CHANGE_WEEK * 7 - 1)
    a0, a1 = START + dt.timedelta(days=CHANGE_WEEK * 7), START + dt.timedelta(days=WEEKS * 7 - 1)
    return (b0.isoformat(), b1.isoformat()), (a0.isoformat(), a1.isoformat())


SCHEMA = """orders(order_id INTEGER, order_date TEXT 'YYYY-MM-DD', region TEXT, channel TEXT, category TEXT,
       product TEXT, customer_type TEXT, units INTEGER, unit_price REAL, revenue REAL)
Dimensions: region, channel, category, product, customer_type. Measures: units, unit_price, revenue."""


def objective() -> str:
    (b0, b1), (a0, a1) = periods()
    return (f"Revenue from {a0} to {a1} is lower than from {b0} to {b1}. Find the root cause: the slice of "
            f"orders (one or more dimension=value conditions) whose change explains the decline, or say that "
            f"the decline is broad-based if no single slice explains it.")
