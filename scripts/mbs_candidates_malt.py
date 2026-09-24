#!/usr/bin/env python3
"""A second search for MBS items, inside the SNOMED CT-AU reference set that fits each category: the RACS MALT surgical
procedure reference set (Ken's pointer, 24 Sep 2026) for diagnostic and therapeutic procedures, the Imaging procedure
reference set for diagnostic imaging, the RCPA requesting pathology reference set for pathology.

The first search (scripts/mbs_candidates.py) looked for the descriptor's head phrase among all SNOMED CT-AU procedures, so
a surgical item often came back with a neighbour ("Muscle graft" for a ruptured-muscle repair, EEG electrode placement for
an EEG). The Royal Australasian College of Surgeons Morbidity Audit and Logbook Tool reference set (1061861000168107,
16,553 active members in SNOMED CT-AU 20260831) is the list of procedures surgeons log -- the granularity an MBS surgical
item names. It carries no MBS numbers (it is a simple reference set, and the release has no MBS map), so this is still a
frame for a person: up to 5 MALT members an item, not already offered, for the diagnostic (2) and therapeutic (3)
procedure categories; the imaging (32570361000036108, 8,921) and RCPA requesting (1072351000168102, 1,974) sets do the
same for categories 5 and 6. Queries an item: the head phrase, the descriptor's first clause, and -- since the server
needs every word of a query to match -- each part of an "A or B" clause cut to its content words ("cervical or upper
thoracic sympathectomy by any surgical approach" -> "cervical sympathectomy", "upper thoracic sympathectomy"). A query
the server throttles is retried, never taken as empty.

    .venv/bin/python scripts/mbs_candidates_malt.py [--categories 2 3 5 6]   # -> reference/mbs_procedure_candidates_malt.json
    #   (~10 min for 2 and 3, live Ontoserver; a run merges into the file, so categories can be run apart)
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bind_indications as bi
from mbs_candidates import XML, head, out_of_scope

MALT = "1061861000168107"
REFSET = {"2": MALT, "3": MALT, "5": "32570361000036108", "6": "1072351000168102"}
FIRST = Path("reference/mbs_procedure_candidates.json")
OUT = Path("reference/mbs_procedure_candidates_malt.json")
SCOPE = Path("reference/mbs_out_of_scope.json")
FILLER = set("""of the a an for by any surgical approach method with without or and to in on at from per each
    including other than service item items patient procedure procedures one more not being where if""".split())
CUT = re.compile(r",? (?:other than|not being|not associated with|being a service|including|where|if|for a patient)\b|\(|;|:", re.I)


def clause(desc: str) -> str:
    """The descriptor before its billing conditions, lower-cased: 'LARYNGOPHARYNGECTOMY or PRIMARY RESTORATION ...' ->
    'laryngopharyngectomy or primary restoration ...'."""
    d = CUT.split(re.sub(r"\s+", " ", desc.replace("‑", "-")).strip(), maxsplit=1)[0].strip(" ,.-")
    return " ".join(d.lower().split()[:10])


def keywords(desc: str) -> list[str]:
    """Short content-word queries from each part of the first clause, the procedure word carried to every part."""
    parts = [p.strip() for p in re.split(r" or | and/or |, ", clause(desc)) if p.strip()]
    words = [[w for w in re.findall(r"[a-z][a-z-]+", p) if w not in FILLER] for p in parts]
    last = words[-1][-1:] if words and words[-1] else []
    out = []
    for w in words:
        if not w:
            continue
        w = w if len(w) > 1 or not last or w == last else w + last     # "cervical or upper thoracic sympathectomy"
        out += [" ".join(w[:4]), " ".join(w[-2:])]
    generic = {"removal", "repair", "excision", "insertion", "treatment", "management", "complete", "partial", "simple",
               "complex", "initiation", "attendance", "note", "examination"}
    return [q for q in dict.fromkeys(out) if len(q) > 3 and not (" " not in q and q in generic)]


def expand(q: str) -> list[dict]:
    """bi.expand, but a throttled or failed request is retried, not read as no hits."""
    import time, urllib.error, urllib.parse, urllib.request
    url = f"{bi.BASE}/ValueSet/$expand?" + urllib.parse.urlencode({
        "url": "http://snomed.info/sct/32506021000036107?fhir_vs=ecl/" + bi.ECL, "filter": q, "count": 8,
        "includeDesignations": "true", "system-version": f"http://snomed.info/sct|{bi.EDITION}"})
    for i in range(6):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/fhir+json"}), timeout=60))
            return d.get("expansion", {}).get("contains", [])
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                return []
        except Exception:
            pass
        time.sleep(2 + 4 * i)
    print(f"  gave up on {q!r}", file=sys.stderr)
    return []


def write_scope(items: list[dict]) -> set[str]:
    """MBS items with no procedure to link (anaesthesia time and initiation, mbs_candidates.out_of_scope): kept out of the
    search and of the review sheet, and listed with the reason so none is silently dropped."""
    scope = {i["ItemNum"]: why for i in items if (why := out_of_scope(i))}
    SCOPE.write_text(json.dumps({"_note": "MBS items out of scope for a procedure link: they fund anaesthesia time, its initiation or "
                                          "a modifier, not a procedure (Ken, 24 Sep 2026). scripts/mbs_candidates.py out_of_scope().",
                                 "mbs_release": XML.name, "items": len(scope), "by_reason": dict(sorted(
                                     {w: sum(v == w for v in scope.values()) for w in set(scope.values())}.items())),
                                 "out_of_scope": dict(sorted(scope.items(), key=lambda kv: int(kv[0])))}, indent=1) + "\n")
    return set(scope)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", nargs="+", default=["2", "3"], choices=sorted(REFSET))
    cats = ap.parse_args().categories
    items = [{c.tag: (c.text or "").strip() for c in d} for d in ET.parse(XML).getroot().iter("Data")]
    items = [i for i in items if i["Category"] in cats and not i.get("ItemEndDate")]
    skip = write_scope(items)
    items = [i for i in items if i["ItemNum"] not in skip]
    had = {r["item"]: {c["concept_id"] for c in r.get("candidates") or []} for r in json.load(open(FIRST))["results"]}
    qs = {i["ItemNum"]: list(dict.fromkeys(q for q in (head(i["Description"], i["Category"]), clause(i["Description"]),
                                                        *keywords(i["Description"])) if q)) for i in items}
    hits = {}
    for rs in sorted({REFSET[c] for c in cats}):          # expand() reads the module's ECL, so one refset at a time
        bi.ECL = f"^ {rs}"
        uniq = sorted({q for i in items if REFSET[i["Category"]] == rs for q in qs[i["ItemNum"]]})
        with cf.ThreadPoolExecutor(4) as ex:
            hits.update({(rs, q): h for q, h in zip(uniq, ex.map(expand, uniq))})
    res = {x["item"]: x for x in json.load(open(OUT))["results"]} if OUT.exists() else {}
    for i in items:
        seen, cands = set(had.get(i["ItemNum"], ())), []
        for q in qs[i["ItemNum"]]:
            for h in hits[(REFSET[i["Category"]], q)]:
                if h["code"] not in seen and len(cands) < 5:
                    seen.add(h["code"])
                    exact = any(bi.norm(t) == bi.norm(q) for t in [h.get("display", "")] + [d.get("value", "") for d in h.get("designation", [])])
                    cands.append({"concept_id": h["code"], "display": h.get("display"), "query": q, "exact_name": exact})
        res[i["ItemNum"]] = {"item": i["ItemNum"], "category": i["Category"], "group": i["Group"], "refset": REFSET[i["Category"]],
                             "candidates": cands}
    res = sorted(res.values(), key=lambda x: int(re.sub(r"\D", "", x["item"]) or 0))
    summary = {"items": len(res), "with_candidates": sum(bool(x["candidates"]) for x in res),
               "with_an_exact_name": sum(any(c["exact_name"] for c in x["candidates"]) for x in res),
               "by_category": {c: sum(x["category"] == c for x in res) for c in sorted({x["category"] for x in res})},
               "refsets": REFSET, "edition": bi.EDITION, "server": bi.BASE, "mbs_release": XML.name}
    OUT.write_text(json.dumps({"_note": __doc__.strip().split("\n\n")[0] + " Candidates are frames for a person, never edges.",
                               "summary": summary, "results": res}, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
