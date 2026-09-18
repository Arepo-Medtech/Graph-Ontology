#!/usr/bin/env python
"""Resolve every substance AMT uses as an active/precise ingredient to an RxNorm ingredient (IN/PIN)
by NAME through RxNav (NLM, free, public domain). search=1 = exact or normalised string match, never
approximate. Tries the AU preferred term, then the FSN without its tag, then each active synonym.
Output: cache/rxnorm_substances.json {sctid: {name_tried, rxcui, name, tty}} (unresolved keep rxcui=None).
Run before build_compendium.py (or re-run the build afterwards to fold it in)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT",
                     "/Users/ken-arepo/iCloud Drive (Archive)/Documents/Documents - Citrus-Arepo/ONTOLOGIES/"
                     "SnomedCT_Release_AU1000036_20260731/Snapshot")
REL = "20260731"
OUT = Path("cache/rxnorm_substances.json")
RXNAV = "https://rxnav.nlm.nih.gov/REST"
ING_TYPES = ("127489000", "762949000")


def rxnav(path: str, **params) -> dict:
    req = urllib.request.Request(f"{RXNAV}/{path}?{urllib.parse.urlencode(params)}",
                                 headers={"Accept": "application/json", "User-Agent": "arepo-au-medicines-compendium/0.1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as fh:  # noqa: S310
                return json.loads(fh.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            time.sleep(2 ** attempt)
    return {}


def find_ingredient(name: str) -> dict | None:
    """RxCUI for a name if RxNorm knows it as an ingredient (IN/PIN/MIN)."""
    r = rxnav("rxcui.json", name=name, search=1)
    ids = (r.get("idGroup") or {}).get("rxnormId") or []
    for rxcui in ids[:3]:
        props = (rxnav(f"rxcui/{rxcui}/properties.json").get("properties") or {})
        if props.get("tty") in ("IN", "PIN", "MIN"):
            return {"rxcui": rxcui, "name": props.get("name"), "tty": props.get("tty")}
    return None


def main() -> int:
    con = duckdb.connect()
    con.execute(f"""
    CREATE VIEW dsc AS SELECT * FROM read_csv('{RF2}/Terminology/sct2_Description_Snapshot-en-au_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
    CREATE VIEW rel AS SELECT * FROM read_csv('{RF2}/Terminology/sct2_Relationship_Snapshot_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
    """)
    subs = con.sql(f"""
      WITH used AS (SELECT DISTINCT destinationId AS id FROM rel WHERE active='1' AND typeId IN {ING_TYPES})
      SELECT u.id, list(DISTINCT CASE WHEN d.typeId='900000000000003001' THEN regexp_replace(d.term, ' \\([^()]+\\)$', '') ELSE d.term END) AS names
      FROM used u JOIN dsc d ON d.conceptId=u.id AND d.active='1' GROUP BY 1""").fetchall()
    done = json.load(open(OUT)) if OUT.exists() else {}
    print(f"substances used as ingredients: {len(subs):,}; already resolved/attempted: {len(done):,}", flush=True)
    for i, (sctid, names) in enumerate(subs, 1):
        if sctid in done:
            continue
        hit, tried = None, []
        for n in sorted(set(names), key=len)[:6]:
            tried.append(n)
            hit = find_ingredient(n)
            time.sleep(0.06)
            if hit:
                break
        done[sctid] = {"names_tried": tried, **(hit or {"rxcui": None, "name": None, "tty": None})}
        if i % 200 == 0:
            OUT.write_text(json.dumps(done)); print(f"  {i:,}/{len(subs):,}  resolved so far: {sum(1 for v in done.values() if v['rxcui']):,}", flush=True)
    OUT.write_text(json.dumps(done))
    print(f"done: {sum(1 for v in done.values() if v['rxcui']):,} of {len(done):,} substances have an RxNorm ingredient", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
