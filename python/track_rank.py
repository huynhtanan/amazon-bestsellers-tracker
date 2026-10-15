"""Track Amazon Best Sellers daily: rank changes, price changes, new entries.

Run this file every day (cron, Task Scheduler, or Apify Scheduler). Each run calls the
actor for your (marketplace, listType, category), stores one row per ASIN in SQLite,
and prints how the chart moved versus the previous observation.

    pip install "apify-client>=3"
    export APIFY_TOKEN=...
    python track_rank.py
"""
import os
import sqlite3
from datetime import date
from pathlib import Path

from apify_client import ApifyClient

MARKETPLACE = "com"
LIST_TYPE = "bestsellers"
CATEGORY = "electronics"
TOP_N = 100

DB = Path(__file__).with_name("amazon_rank.sqlite3")


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def fetch():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/amazon-best-sellers-scraper").call(run_input={
        "marketplace": MARKETPLACE,
        "listType": LIST_TYPE,
        "categorySlugs": [CATEGORY],
        "maxItemsPerCategory": TOP_N,
        "pagesPerCategory": (TOP_N + 29) // 30,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    return list(client.dataset(dataset_id).iterate_items())


def store(con, run_date, items):
    con.execute("""CREATE TABLE IF NOT EXISTS ranks (
        run_date    TEXT NOT NULL,
        marketplace TEXT NOT NULL,
        list_type   TEXT NOT NULL,
        category    TEXT NOT NULL,
        rank        INTEGER NOT NULL,
        asin        TEXT NOT NULL,
        title       TEXT,
        price       REAL,
        currency    TEXT,
        rating      REAL,
        reviews     INTEGER,
        PRIMARY KEY (run_date, marketplace, list_type, category, asin))""")
    for it in items:
        con.execute("INSERT OR REPLACE INTO ranks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (run_date, MARKETPLACE, LIST_TYPE, CATEGORY,
                     it["rank"], it["asin"], it["title"],
                     it.get("price"), it.get("currency"),
                     it.get("rating"), it.get("reviewsCount")))
    con.commit()


def report(con, run_date):
    rows_today = con.execute(
        """SELECT rank, asin, title, price, currency FROM ranks
           WHERE run_date = ? AND marketplace = ? AND list_type = ? AND category = ?
           ORDER BY rank""",
        (run_date, MARKETPLACE, LIST_TYPE, CATEGORY),
    ).fetchall()
    today = {asin: (rank, title, price, cur) for rank, asin, title, price, cur in rows_today}

    prev = con.execute(
        """SELECT MAX(run_date) FROM ranks
           WHERE run_date < ? AND marketplace = ? AND list_type = ? AND category = ?""",
        (run_date, MARKETPLACE, LIST_TYPE, CATEGORY),
    ).fetchone()[0]

    print(f"\nAmazon.{MARKETPLACE} {LIST_TYPE} / {CATEGORY} on {run_date}")
    print(f"({len(today)} products tracked)\n")

    if not prev:
        for rank, _, title, price, cur in rows_today[:10]:
            tag = f"{price:.2f} {cur}" if price else "    --"
            print(f"  #{rank:>3}  {title[:62]:62}  {tag:>10}")
        print(f"\n  (first run — rerun tomorrow to see rank/price changes)")
        return

    prev_rows = con.execute(
        """SELECT asin, rank, price FROM ranks
           WHERE run_date = ? AND marketplace = ? AND list_type = ? AND category = ?""",
        (prev, MARKETPLACE, LIST_TYPE, CATEGORY),
    ).fetchall()
    prev_map = {asin: (rank, price) for asin, rank, price in prev_rows}

    climbers, droppers, newcomers, left = [], [], [], []
    for asin, (rank, title, price, cur) in today.items():
        if asin not in prev_map:
            newcomers.append((rank, title, price, cur))
            continue
        prev_rank, prev_price = prev_map[asin]
        delta = prev_rank - rank
        price_delta = None
        if price and prev_price:
            price_delta = (price - prev_price) / prev_price * 100
        if delta >= 3:
            climbers.append((rank, prev_rank, title, price_delta))
        elif delta <= -3:
            droppers.append((rank, prev_rank, title, price_delta))

    for asin, (prev_rank, _) in prev_map.items():
        if asin not in today:
            left.append((prev_rank, asin))

    def _p(section, items, fmt):
        print(f"  {section}:")
        if not items:
            print("    (none)")
            return
        for row in items[:5]:
            print("    " + fmt(row))
        print()

    _p("New in the chart", newcomers,
       lambda r: f'#{r[0]:>3}  {r[1][:60]:60}  {(f"{r[2]:.2f} {r[3]}" if r[2] else ""):>10}')
    _p("Climbers (3+ positions up)", climbers,
       lambda r: f'#{r[0]:>3} (was #{r[1]})  {r[2][:50]:50}  {(f"price {r[3]:+.1f}%" if r[3] is not None else "")}')
    _p("Fallers (3+ positions down)", droppers,
       lambda r: f'#{r[0]:>3} (was #{r[1]})  {r[2][:50]:50}  {(f"price {r[3]:+.1f}%" if r[3] is not None else "")}')
    _p("Dropped out", left,
       lambda r: f'(was #{r[0]:>3})  {r[1]}')


if __name__ == "__main__":
    items = fetch()
    run_date = date.today().isoformat()
    with sqlite3.connect(DB) as con:
        store(con, run_date, items)
        report(con, run_date)
