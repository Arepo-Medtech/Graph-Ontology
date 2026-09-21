#!/usr/bin/env python
"""Pull the PBS Public API v3 tables used by the compendium.

The public tier is rate limited to one request every 20 seconds. The shared public
subscription key is published by PBS. Every cached file retains the source schedule
and copyright message so downstream builds can reject mixed schedules.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KEY = "2384af7c667342ceb5a736fe29f1dc6b"
BASE = "https://data-api.health.gov.au/pbs/api/v3"
OUT = Path("cache/pbs")
SLEEP = 21
TABLES = {
    "amt-items": 10_000,
    "items": 10_000,
    "atc-codes": 10_000,
    "item-atc-relationships": 10_000,
    "restrictions": 10_000,
}


def get(path: str, **params: object) -> dict:
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    for _attempt in range(6):
        req = urllib.request.Request(
            url,
            headers={"Subscription-Key": KEY, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            wait = int(exc.headers.get("Retry-After", "25")) + 1
            print(f"    429 - waiting {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("gave up after repeated PBS API rate-limit responses")


def _write_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, separators=(",", ":")))
    temporary.replace(path)


def pull(table: str, limit: int) -> str | None:
    rows: list[dict] = []
    page = 1
    copyright_message = None
    while True:
        response = get(table, get_latest_schedule_only="true", limit=limit, page=page)
        meta = response["_meta"]
        data = response.get("data", [])
        copyright_message = copyright_message or meta.get("info", {}).get("messages")
        rows.extend(data)
        total = int(meta.get("total_records", len(rows)))
        effective_limit = meta.get("limit")
        print(
            f"  {table}: page {page} -> {len(rows):,}/{total:,} "
            f"(server limit {effective_limit})",
            flush=True,
        )
        if not data or len(rows) >= total:
            break
        page += 1
        time.sleep(SLEEP)

    schedules = {row.get("schedule_code") for row in rows if row.get("schedule_code")}
    if len(schedules) > 1:
        raise RuntimeError(f"{table} returned mixed schedules: {sorted(schedules)}")
    schedule = next(iter(schedules), None)
    destination = OUT / f"{table}.json"
    _write_atomic(
        destination,
        {"schedule_code": schedule, "copyright": copyright_message, "rows": rows},
    )
    print(f"  wrote {destination}: {len(rows):,} rows", flush=True)
    return schedule


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=tuple(TABLES),
        default=list(TABLES),
        help="PBS tables to refresh (default: all compendium tables)",
    )
    args = parser.parse_args()

    schedules: dict[str, str | None] = {}
    for index, table in enumerate(args.tables):
        if index:
            time.sleep(SLEEP)
        schedules[table] = pull(table, TABLES[table])

    populated = {value for value in schedules.values() if value}
    if len(populated) > 1:
        raise RuntimeError(f"PBS tables came from different schedules: {schedules}")
    print(f"PBS pull complete (schedule {next(iter(populated), 'unknown')})", flush=True)


if __name__ == "__main__":
    main()
