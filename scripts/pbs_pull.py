#!/usr/bin/env python
"""Pull the PBS Public API v3 tables needed for the AMT brand link, at the public tier's pace.

Public tier: no registration; the shared public Subscription-Key is published in the PBS docs and
the MIT reference client (matthewdcage/pbs-mcp-server). Rate limit 1 request / 20 s, shared. The
copyright statement in _meta is retained in the output (redistribute-OK, no-modify).

Tables (latest schedule only):
  amt-items : li_item_id, concept_type_code (MP/MPUU/MPP/TP/TPUU/TPP/CTPP...), amt_code, preferred_term
  items     : li_item_id, pbs_code, li_drug_name, brand_name, li_form, ...
Output: cache/pbs/<table>.json  {"schedule_code", "copyright", "rows": [...]}"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

KEY = "2384af7c667342ceb5a736fe29f1dc6b"   # public tier key (published openly)
BASE = "https://data-api.health.gov.au/pbs/api/v3"
OUT = Path("cache/pbs"); OUT.mkdir(parents=True, exist_ok=True)
SLEEP = 21


def get(path: str, **params) -> dict:
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"Subscription-Key": KEY, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as fh:  # noqa: S310
                return json.loads(fh.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", "25")) + 1
                print(f"    429 — waiting {wait}s", flush=True); time.sleep(wait); continue
            raise
    raise RuntimeError("gave up after repeated 429s")


def pull(table: str, limit: int) -> None:
    rows, page, copyright_ = [], 1, None
    while True:
        d = get(table, get_latest_schedule_only="true", limit=limit, page=page)
        meta = d["_meta"]; data = d.get("data", [])
        copyright_ = copyright_ or meta.get("info", {}).get("messages")
        rows.extend(data)
        total = meta.get("total_records"); eff = meta.get("limit")
        print(f"  {table}: page {page} -> {len(rows):,}/{total:,} (server limit {eff})", flush=True)
        if not data or len(rows) >= total:
            break
        page += 1
        time.sleep(SLEEP)
    sched = rows[0].get("schedule_code") if rows else None
    (OUT / f"{table}.json").write_text(json.dumps({"schedule_code": sched, "copyright": copyright_, "rows": rows}))
    print(f"  wrote {OUT / f'{table}.json'}: {len(rows):,} rows", flush=True)


if __name__ == "__main__":
    pull("amt-items", 10000)
    time.sleep(SLEEP)
    pull("items", 10000)
    print("PBS pull complete", flush=True)
