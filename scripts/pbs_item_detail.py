#!/usr/bin/env python
"""Cache complete PBS item-overview evidence for selected PBS item codes.

The schedule-wide tables remain the reproducible bulk source. This command is an
on-demand evidence collector for ingredient wording, ATC ancestry, restrictions and
prescribing text that PBS exposes through its assembled item-overview endpoint.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from pbs_pull import SLEEP, _write_atomic, get

OUT = Path("cache/pbs/item-overview")
PBS_CODE = re.compile(r"^[0-9]{1,5}[A-Z]$")


def normalise_pbs_code(value: str) -> str:
    code = value.strip().upper()
    if not PBS_CODE.fullmatch(code):
        raise argparse.ArgumentTypeError(
            f"invalid PBS item code {value!r}; expected digits followed by one letter"
        )
    return code


def pull_item(code: str) -> None:
    response = get(
        "item-overview",
        pbs_code=code,
        get_latest_schedule_only="true",
        limit=1_000,
        page=1,
    )
    rows = response.get("data", [])
    if not rows:
        raise RuntimeError(f"PBS returned no item-overview rows for {code}")
    schedules = {
        row.get("schedule_code") or (row.get("schedule") or {}).get("schedule_code")
        for row in rows
        if row.get("schedule_code") or (row.get("schedule") or {}).get("schedule_code")
    }
    if len(schedules) > 1:
        raise RuntimeError(f"{code} returned mixed schedules: {sorted(schedules)}")
    schedule = next(iter(schedules), None)
    copyright_message = response.get("_meta", {}).get("info", {}).get("messages")
    destination = OUT / f"{code}.json"
    _write_atomic(
        destination,
        {
            "pbs_code": code,
            "schedule_code": schedule,
            "source_url": f"https://www.pbs.gov.au/medicine/item/{code}",
            "copyright": copyright_message,
            "rows": rows,
        },
    )
    print(f"wrote {destination}: {len(rows):,} rows (schedule {schedule})", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbs_codes", nargs="+", type=normalise_pbs_code)
    args = parser.parse_args()
    for index, code in enumerate(dict.fromkeys(args.pbs_codes)):
        if index:
            time.sleep(SLEEP)
        pull_item(code)


if __name__ == "__main__":
    main()
