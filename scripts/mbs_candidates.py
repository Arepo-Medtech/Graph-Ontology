#!/usr/bin/env python3
"""Candidate SNOMED CT-AU procedures for Medicare Benefits Schedule items -- a frame for a person, never an edge.

No map from MBS items to SNOMED CT exists (the RCPA requesting set codes pathology requests to SNOMED but carries no MBS
numbers). An MBS item is a billing rule -- a service plus eligibility conditions ("other than a service to which item X
applies") -- so even an exact name match is not an equivalence. For the procedural categories (2 diagnostic procedures,
3 therapeutic procedures, 5 diagnostic imaging, 6 pathology) this proposes, from the live Ontoserver (SNOMED CT-AU
20260831, procedures only), the nearest concepts to the descriptor's head phrase, and notes where the head phrase equals a
preferred term or synonym exactly. Resumable.

    scripts/mbs_candidates.py      # writes reference/mbs_procedure_candidates.json
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

spec = importlib.util.spec_from_file_location("bind_indications", Path(__file__).with_name("bind_indications.py"))
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)
bi.ECL = "<< 71388002"                                      # procedures only
XML, OUT = Path("cache/mbs/MBS-XML-20260801.XML"), Path("reference/mbs_procedure_candidates.json")
CATEGORIES = {"2", "3", "5", "6"}
SITE_FIRST = re.compile(r"^([^,(:;]{2,50}),\s*(?:[a-z]+\s*\([^)]*\),\s*)?(?!examination)([a-z][^,(:;]{2,50}?)\s+of\b")
IMAGING = re.compile(r"^(.+?),\s*(ultrasound|CT|computed tomography|MRI|magnetic resonance imaging|radiography|x-ray)\s+(scan\s+)?of\b", re.I)


# Anaesthesia items that fund anaesthesia time or its initiation, not a procedure: out of scope for a procedure link
# (Ken, 24 Sep 2026). The procedures group T10 also holds (intubation, central lines, nerve blocks, TOE) stay in.
ANAESTHESIA = [
    ("anaesthesia time band", re.compile(r"^\(?\s*\d+(?::\d+)?\s+(?:HOURS?|MINUTES)\s+TO\s|service time is not more than", re.I)),
    ("initiation of anaesthesia", re.compile(r"^INITIATION OF (?:THE )?MANAGEMENT (?:BY A MEDICAL PRACTITIONER )?OF ANAESTHESIA", re.I)),
    ("anaesthesia modifier", re.compile(r"^(?:Anaesthesia,|Assistance in the management of|Perfusion,) ", re.I)),
]


# a bulk-billing incentive pays a loading on another item's service; it funds no procedure of its own (Ken, 24 Sep 2026)
BULK = re.compile(r"^An? (?:medical|diagnostic imaging|pathology) service to which .*bulk.?bill", re.I)
# a receiving laboratory's item funds a test another item describes ("A test described in item 65150, if rendered by a
# receiving APP"): it takes that item's candidates and reading, marked as inherited (Ken, 24 Sep 2026)
REFERS = re.compile(r"^A test described in items? (\d+(?:\s*(?:,|or|and)\s*\d+)*)", re.I)


def out_of_scope(item: dict) -> str | None:
    """Why an MBS item has no procedure to link, or None."""
    d = re.sub(r"\s+", " ", item.get("Description", "")).strip()
    if item.get("Group") == "T10":
        for why, rx in ANAESTHESIA:
            if rx.search(d):
                return why
    if BULK.search(d):
        return "bulk-billing incentive"
    return None


def refers_to(item: dict) -> list[str]:
    """The items whose test this item funds when a receiving laboratory renders it, or []."""
    m = REFERS.match(re.sub(r"\s+", " ", item.get("Description", "")).strip())
    return re.findall(r"\d+", m.group(1)) if m else []


def head(desc: str, cat: str) -> str:
    d = re.sub(r"\s+", " ", desc.replace("‑", "-")).strip()
    m = IMAGING.match(d) if cat == "5" else None
    if m:
        return f"{m.group(2)} of {m.group(1)}"
    m = SITE_FIRST.match(d)                                   # "PERICARDIUM, paracentesis of" -> "paracentesis of pericardium"
    if m:
        return f"{m.group(2).strip()} of {m.group(1).strip().lower()}"
    h = re.split(r",|:|;| - |\(|—", d, maxsplit=1)[0].strip()
    return " ".join(h.split()[:8])


def main() -> int:
    items = [{c.tag: (c.text or "").strip() for c in d} for d in ET.parse(XML).getroot().iter("Data")]
    items = [i for i in items if i["Category"] in CATEGORIES and not i.get("ItemEndDate")]
    done = {x["item"]: x for x in json.load(open(OUT))["results"]} if OUT.exists() else {}
    cache, t0 = {}, time.time()
    for n, i in enumerate(items, 1):
        if i["ItemNum"] in done:
            continue
        q = head(i["Description"], i["Category"])
        if q not in cache:
            hits = bi.expand(q, 5)
            time.sleep(0.2)
            exact = next(({"concept_id": h["code"], "display": h.get("display")} for h in hits
                          for t in [h.get("display", "")] + [d.get("value", "") for d in h.get("designation", [])] if bi.norm(t) == bi.norm(q)), None)
            cache[q] = {"candidates": [{"concept_id": h["code"], "display": h.get("display")} for h in hits], "exact_head_match": exact}
        done[i["ItemNum"]] = {"item": i["ItemNum"], "category": i["Category"], "group": i["Group"], "query": q, **cache[q]}
        if n % 250 == 0:
            OUT.write_text(json.dumps({"results": list(done.values())}, ensure_ascii=False))
            print(f"  {n:,}/{len(items):,}  {time.time() - t0:.0f}s", flush=True)
    res = sorted(done.values(), key=lambda x: int(re.sub(r"\D", "", x["item"]) or 0))
    summary = {"items": len(res), "with_candidates": sum(1 for x in res if x["candidates"]),
               "exact_head_match": sum(1 for x in res if x["exact_head_match"]), "edition": bi.EDITION, "server": bi.BASE,
               "mbs_release": XML.name}
    OUT.write_text(json.dumps({"_note": __doc__.strip().split("\n\n")[0] + " Every row is a candidate frame (state: needs a person).",
                               "summary": summary, "results": res}, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
