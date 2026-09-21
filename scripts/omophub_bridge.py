#!/usr/bin/env python
"""AMT -> OMOP bridge via OMOPHub (Athena vocabulary as an API; needs OMOPHUB_API_KEY).

OMOP carries the Australian Medicines Terminology as its own vocabulary (`AMT`, version v20210630 in Athena
2026.2) and maps every AMT product to a *standard* drug concept (RxNorm Extension / RxNorm) with a `Maps to`
relationship. That is a product-level route to OMOP and RxNorm that never touches ingredient names, and an
independent second verdict on the by-name RxNorm links from rxnorm_enrich/rxnorm_resolve.

  scripts/omophub_bridge.py vocab                 page the whole AMT vocabulary (136,850 concepts, ~700 calls)
                                                  -> cache/omophub_amt_concepts.json  {amt_code: concept}
  scripts/omophub_bridge.py map tpuu|mpuu|mp      `Maps to` for the compendium's products of that level
                                                  -> cache/omophub_amt_maps.json      {amt_code: [standard targets]}
  scripts/omophub_bridge.py substances            SNOMED substance -> OMOP concept -> RxNorm ingredient (`Maps to`)
                                                  -> cache/omophub_substances.json    {sctid: {...}}
  scripts/omophub_bridge.py report                agreement with cache/rxnorm_substances.json -> out/omop_bridge_report.md

Rate limit is 120 requests/min (burst 20 per 10 s); the client paces itself and honours 429 + ratelimit-reset.
Every phase is resumable: results are written every 200 calls and skipped on re-run. Run outside the sandbox
(a sandboxed background job loses its proxy) or in the foreground.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import duckdb

BASE = "https://api.omophub.com/v1"
CACHE = Path("cache")
OUT = Path("out")
DB = OUT / "compendium.duckdb"
VOCAB_CACHE = CACHE / "omophub_amt_concepts.json"
MAP_CACHE = CACHE / "omophub_amt_maps.json"
SUBS_CACHE = CACHE / "omophub_substances.json"
MIN_INTERVAL = 0.55  # just under the 2 req/s sustained + 20/10 s burst limits; a tripped 429 costs a 10 s wait
_last = [0.0]
_calls = [0]


def api_key() -> str:
    k = os.environ.get("OMOPHUB_API_KEY")
    if not k:
        for env in (Path(".env"), Path.home() / "code" / "spine" / ".env"):
            if env.exists():
                for line in env.read_text().splitlines():
                    if line.startswith("OMOPHUB_API_KEY="):
                        k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("OMOPHUB_API_KEY not set (see ~/code/spine/.env.example)")
    return k


def get(path: str, key: str, **params) -> Optional[Dict[str, Any]]:
    """GET with pacing and 429 handling. Returns the JSON body, or None on 404."""
    url = f"{BASE}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    for attempt in range(6):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        _calls[0] += 1
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "User-Agent": "arepo-au-medicines-compendium/0.2 (omophub bridge)",
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                reset = e.headers.get("ratelimit-reset") or e.headers.get("retry-after") or "10"
                time.sleep(min(float(reset) + 1, 60))
                continue
            raise
        except Exception:  # noqa: BLE001
            time.sleep(2 ** attempt)
    return None


def load(p: Path) -> Dict[str, Any]:
    return json.load(open(p)) if p.exists() else {}


def save(p: Path, d: Dict[str, Any]) -> None:
    p.parent.mkdir(exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    tmp.replace(p)


def slim(c: Dict[str, Any]) -> Dict[str, Any]:
    return {k: c.get(k) for k in ("concept_id", "concept_name", "vocabulary_id", "domain_id", "concept_class_id", "standard_concept",
                                   "concept_code", "invalid_reason", "valid_end_date")}


# --- vocab -------------------------------------------------------------------------------------------
def cmd_vocab(args) -> int:
    key = api_key()
    cache = load(VOCAB_CACHE)
    meta = cache.get("_meta", {"next_page": 1, "total_pages": None})
    page = meta["next_page"]
    concepts: Dict[str, Any] = cache.get("concepts", {})
    while meta["total_pages"] is None or page <= meta["total_pages"]:
        d = get("/vocabularies/AMT/concepts", key, page=page, page_size=200)
        if d is None:
            break
        for c in d.get("data", []):
            concepts[str(c["concept_code"])] = slim(c)
        pg = (d.get("meta") or {}).get("pagination") or {}
        meta["total_pages"] = pg.get("total_pages")
        page += 1
        meta["next_page"] = page
        if page % 25 == 0 or not pg.get("has_next"):
            save(VOCAB_CACHE, {"_meta": meta, "concepts": concepts})
            print(f"  page {page - 1}/{meta['total_pages']}  concepts {len(concepts):,}", flush=True)
        if not pg.get("has_next"):
            break
    save(VOCAB_CACHE, {"_meta": meta, "concepts": concepts})
    classes: Dict[str, int] = {}
    for c in concepts.values():
        classes[c["concept_class_id"]] = classes.get(c["concept_class_id"], 0) + 1
    print(f"AMT in OMOP: {len(concepts):,} concepts; classes: {dict(sorted(classes.items(), key=lambda kv: -kv[1]))}", flush=True)
    return 0


# --- map ---------------------------------------------------------------------------------------------
def product_codes(level: str) -> List[str]:
    con = duckdb.connect(str(DB), read_only=True)
    if level == "tpuu":
        return [r[0] for r in con.execute("SELECT DISTINCT tpuu_id FROM transcode ORDER BY 1").fetchall()]
    return [r[0] for r in con.execute("SELECT id FROM product WHERE level=? ORDER BY 1", [level.upper()]).fetchall()]


def maps_to(concept_id: int, key: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        d = get(f"/concepts/{concept_id}/mappings", key, page=page, page_size=50)
        if not d:
            break
        for m in ((d.get("data") or {}).get("mappings") or []):
            if m.get("relationship_id") == "Maps to":
                out.append({"target_concept_id": m["target_concept_id"], "target_name": m.get("target_concept_name"),
                            "target_vocabulary": m.get("target_vocabulary_id"), "target_code": m.get("target_concept_code"),
                            "target_standard": m.get("target_standard_concept"), "target_domain": m.get("target_domain_id")})
        pg = (d.get("meta") or {}).get("pagination") or {}
        if not pg.get("has_next"):
            break
        page += 1
    return out


def cmd_map(args) -> int:
    key = api_key()
    vocab = load(VOCAB_CACHE).get("concepts", {})
    if not vocab:
        sys.exit("run `vocab` first")
    maps = load(MAP_CACHE)
    codes = product_codes(args.level)
    todo = [c for c in codes if c not in maps]
    in_omop = [c for c in todo if c in vocab]
    print(f"{args.level.upper()}: {len(codes):,} codes; {len(codes) - len(todo):,} cached; {len(in_omop):,} of the remaining {len(todo):,} exist in OMOP's AMT", flush=True)
    for c in todo:
        if c not in vocab:
            maps[c] = {"in_omop": False, "level": args.level, "targets": []}
    t0 = time.time()
    for i, c in enumerate(in_omop, 1):
        v = vocab[c]
        targets = [] if v.get("standard_concept") == "S" else maps_to(int(v["concept_id"]), key)
        maps[c] = {"in_omop": True, "level": args.level, "concept_id": v["concept_id"], "concept_class": v["concept_class_id"],
                   "self_standard": v.get("standard_concept") == "S", "targets": targets}
        if i % 200 == 0:
            save(MAP_CACHE, maps)
            rate = i / (time.time() - t0) * 60
            print(f"  {i:,}/{len(in_omop):,} mapped  ({rate:.0f}/min, ~{(len(in_omop) - i) / max(rate, 1):.0f} min left)", flush=True)
    save(MAP_CACHE, maps)
    done = [m for c, m in maps.items() if m.get("level") == args.level]
    with_std = sum(1 for m in done if m.get("self_standard") or any(t.get("target_standard") == "S" for t in m["targets"]))
    print(f"{args.level.upper()}: {sum(1 for m in done if m['in_omop']):,} in OMOP, {with_std:,} with a standard drug concept, of {len(done):,}", flush=True)
    return 0


# --- substances ----------------------------------------------------------------------------------------
def cmd_substances(args) -> int:
    key = api_key()
    vocab = load(VOCAB_CACHE).get("concepts", {})
    rx = load(CACHE / "rxnorm_substances.json")
    subs = load(SUBS_CACHE)
    todo = [s for s in sorted(rx) if s not in subs]
    print(f"substances: {len(rx):,}; cached {len(subs):,}; to do {len(todo):,}", flush=True)
    t0 = time.time()
    for i, sid in enumerate(todo, 1):
        rec: Dict[str, Any] = {"omop": None, "targets": []}
        c = vocab.get(sid)  # AU substances live in OMOP's AMT vocabulary ("AU Substance")
        if c is None and len(sid) <= 9:
            d = get(f"/concepts/by-code/SNOMED/{sid}", key)
            data = (d or {}).get("data")
            if isinstance(data, list):
                data = data[0] if data else None
            c = slim(data) if data else None
        if c:
            rec["omop"] = c
            rec["targets"] = [] if c.get("standard_concept") == "S" else maps_to(int(c["concept_id"]), key)
        subs[sid] = rec
        if i % 200 == 0:
            save(SUBS_CACHE, subs)
            rate = i / (time.time() - t0) * 60
            print(f"  {i:,}/{len(todo):,}  ({rate:.0f}/min, ~{(len(todo) - i) / max(rate, 1):.0f} min left)", flush=True)
    save(SUBS_CACHE, subs)
    return cmd_report(args)


# --- report --------------------------------------------------------------------------------------------
def cmd_report(args) -> int:
    rx = load(CACHE / "rxnorm_substances.json")
    subs = load(SUBS_CACHE)
    maps = load(MAP_CACHE)
    vocab = load(VOCAB_CACHE).get("concepts", {})
    lines = ["# AMT -> OMOP bridge (OMOPHub, Athena 2026.2, AMT vocabulary v20210630)", ""]
    if vocab:
        lines.append(f"AMT concepts in OMOP: {len(vocab):,}.")
    for level in ("tpuu", "mpuu", "mp"):
        done = {c: m for c, m in maps.items() if m.get("level") == level}
        if not done:
            continue
        in_omop = sum(1 for m in done.values() if m["in_omop"])
        std = sum(1 for m in done.values() if m.get("self_standard") or any(t.get("target_standard") == "S" for t in m["targets"]))
        vocabs: Dict[str, int] = {}
        for m in done.values():
            for t in m["targets"][:1]:
                vocabs[t["target_vocabulary"]] = vocabs.get(t["target_vocabulary"], 0) + 1
        lines += ["", f"## {level.upper()}", "", f"| compendium {level.upper()}s | in OMOP's AMT | with a standard drug concept | target vocabularies |", "|---|---|---|---|",
                  f"| {len(done):,} | {in_omop:,} | {std:,} | {vocabs} |"]
    if subs:
        agree = disagree = omop_only = rx_only = neither = 0
        examples: List[str] = []
        for sid, rec in subs.items():
            rxcui = (rx.get(sid) or {}).get("rxcui")
            omop_rx = [t for t in rec["targets"] if t.get("target_vocabulary") in ("RxNorm", "RxNorm Extension")]
            omop_rxcuis = {str(t["target_code"]) for t in omop_rx if t.get("target_vocabulary") == "RxNorm"}
            if rxcui and omop_rxcuis:
                if rxcui in omop_rxcuis:
                    agree += 1
                else:
                    disagree += 1
                    if len(examples) < 25:
                        examples.append(f"| {sid} | {(rx[sid].get('pt') or '')[:40]} | {rxcui} {(rx[sid].get('name') or '')[:35]} ({rx[sid].get('method')}) | "
                                        f"{', '.join(t['target_code'] + ' ' + (t.get('target_name') or '')[:35] for t in omop_rx[:2])} |")
            elif omop_rxcuis:
                omop_only += 1
            elif rxcui:
                rx_only += 1
            else:
                neither += 1
        lines += ["", "## Substances: RxNav route vs OMOP route", "",
                  "| both routes, same RxCUI | both routes, different RxCUI | OMOP only | RxNav only | neither |", "|---|---|---|---|---|",
                  f"| {agree:,} | {disagree:,} | {omop_only:,} | {rx_only:,} | {neither:,} |", "",
                  "Disagreements (first 25):", "", "| sctid | AU term | RxNav link (method) | OMOP `Maps to` RxNorm |", "|---|---|---|---|", *examples]
    lines += ["", f"RxNav = cache/rxnorm_substances.json (rxnorm_resolve.py); OMOP = cache/omophub_substances.json. OMOPHub calls this run: {_calls[0]:,}."]
    OUT.mkdir(exist_ok=True)
    (OUT / "omop_bridge_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("vocab").set_defaults(fn=cmd_vocab)
    m = sub.add_parser("map"); m.add_argument("level", choices=["tpuu", "mpuu", "mp"]); m.set_defaults(fn=cmd_map)
    sub.add_parser("substances").set_defaults(fn=cmd_substances)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
