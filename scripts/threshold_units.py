#!/usr/bin/env python3
"""Give every unit-bearing likelihood-ratio threshold an Australian value beside the published (mostly US) one.

For each record in reference/diagnostic_accuracy.json whose result or finding carries a unit, this writes to
reference/threshold_units.json:

    as_published   the value and unit exactly as the source wrote them (the source trace; never altered)
    au             the value in the Australian reporting unit
    conversion     'molar' (mg/dL -> mmol/L = x 10 / MW, MW from PubChem by CID -- cache/pubchem/mw.json),
                   'relabel' (the same number under the Australian unit name: pg/mL = ng/L, ng/mL = ug/L, mEq/L = mmol/L
                   for a monovalent ion), or 'same' (already the Australian unit: mg/L, U/L, x10^9/L, mmHg, C, %)
    au_unit_confirmed   true only when the RCPA SPIA Preferred Units Table (NCTS) confirms the Australian unit for
                   that analyte -- false until it is loaded
    primacy        'au' once the conversion is by code or by relabel AND the Australian unit is confirmed; until then
                   'as_published'. The local unit takes primacy only once corrected.

    scripts/threshold_units.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC, MW, OUT = Path("reference/diagnostic_accuracy.json"), Path("cache/pubchem/mw.json"), Path("reference/threshold_units.json")
RCPA = Path("cache/rcpa/reporting_units.json")            # scripts/rcpa_units.py (RCPA copyright; git-ignored)
RCPA_MAP = Path("reference/threshold_rcpa_map.json")       # which RCPA row confirms which threshold analyte
# analytes whose threshold needs a molar conversion: record finding text -> PubChem CID (read from the record, not guessed
# from a name at run time) and the Australian unit
MOLAR = {"pleural fluid cholesterol": (5997, "mmol/L"), "serum uric acid": (1175, "mmol/L")}
RELABEL = {"pg/mL": "ng/L", "ng/mL": "ug/L", "mEq/L": "mmol/L"}
SAME = {"mg/L", "U/L", "ug/g", "x 10^9/L", "mm Hg", "C", "%", "cm"}
NUM_UNIT = re.compile(r"(-?\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*(mg/dL|pg/mL|ng/mL|mEq/L|mg/L|U/L|ug/g|x 10\^9/L|mm Hg|%|cm|C)\b")


def norm(u) -> str:
    return re.sub(r"\s+|^x", "", str(u or "")).replace("10*9", "10^9").replace("µ", "u")


def main() -> int:
    recs = json.load(open(SRC))["records"]
    mw = json.load(open(MW)) if MW.exists() else {}
    rcpa = {}
    if RCPA.exists():
        for x in json.load(open(RCPA))["rows"]:
            rcpa.setdefault(x["loinc"], set()).add(norm(x["unit"]))
    rmap = json.load(open(RCPA_MAP))["map"] if RCPA_MAP.exists() else {}
    PATHOLOGY_FREE = {"mm Hg", "C", "cm"}           # vital signs and anatomy: not pathology reporting units
    rows = []
    for r in recs:
        text = r.get("result") or ""
        if r.get("kind", "finding") == "finding" and not text.strip("present absent"):
            text = r["finding_text"]
        m = NUM_UNIT.search(text)
        if not m:
            continue
        v1, v2, unit = m.group(1), m.group(2), m.group(3)
        pub = {"value": float(v1), "value_to": float(v2) if v2 else None, "unit": unit, "text": text}
        if r["finding_text"] in MOLAR and unit == "mg/dL":
            cid, au_unit = MOLAR[r["finding_text"]]
            w = (mw.get(f"cid:{cid}") or {}).get("mw")
            if not w:
                print(f"no molecular weight cached for CID {cid}; run scripts/unit_reconcile.py", file=sys.stderr)
                return 1
            f = 10 / w
            au = {"value": round(float(v1) * f, 3), "value_to": round(float(v2) * f, 3) if v2 else None, "unit": au_unit}
            conv = {"kind": "molar", "factor": round(f, 6), "molecular_weight": w, "pubchem_cid": cid}
        elif unit in RELABEL:
            au = {"value": float(v1), "value_to": float(v2) if v2 else None, "unit": RELABEL[unit]}
            conv = {"kind": "relabel", "factor": 1.0}
        elif unit in SAME:
            au = {"value": float(v1), "value_to": float(v2) if v2 else None, "unit": unit}
            conv = {"kind": "same", "factor": 1.0}
        else:
            continue
        m_ = rmap.get(r["finding_text"], {})
        code = m_.get("rcpa_loinc")
        if au["unit"] in PATHOLOGY_FREE or (unit == "%" and not code):
            confirm = {"status": "not a pathology unit"}
            ok = None
        elif not RCPA.exists():
            confirm = {"status": "RCPA reference sets not loaded"}
            ok = False
        elif not code:
            confirm = {"status": "no RCPA row for this analyte and specimen", "why": m_.get("why", "not mapped")}
            ok = False
        else:
            ok = norm(au["unit"]) in rcpa.get(code, set())
            confirm = {"status": "confirmed" if ok else ("RCPA unit differs" if code in rcpa else "RCPA row not found"),
                       "rcpa_loinc": code, "rcpa_unit": sorted(rcpa.get(code, set())) or None}
            if m_.get("why"):
                confirm["why"] = m_["why"]
        row = {"id": r["id"], "pmid": r["pmid"], "analyte": r["finding_text"], "as_published": pub, "au": au, "conversion": conv,
               "au_unit_confirmation": confirm, "au_unit_confirmed": ok,
               "primacy": "au" if ok else ("same" if ok is None else "as_published")}
        if r["pmid"] == "41729549" and "natriuretic" in r["finding_text"]:
            row["flag"] = "the abstract gives BNP in ng/mL; the conventional unit is pg/mL (= ng/L) -- check the full text before converting"
        rows.append(row)
    for r in recs:                                      # a threshold whose unit the abstract leaves out entirely
        if r["pmid"] == "41729549" and "natriuretic" in r["finding_text"] and not any(x["id"] == r["id"] for x in rows):
            rows.append({"id": r["id"], "pmid": r["pmid"], "analyte": r["finding_text"], "as_published": {"text": r.get("result"), "unit": "ng/mL (abstract)"},
                         "au": None, "conversion": None, "au_unit_confirmed": False, "primacy": "as_published",
                         "flag": "the abstract gives BNP 100 ng/mL; the conventional threshold is 100 pg/mL (= 100 ng/L) -- not converted until checked"})
    by = {}
    for x in rows:
        k = (x["conversion"] or {}).get("kind", "flagged")
        by[k] = by.get(k, 0) + 1
    prim = {}
    for x in rows:
        prim[x["primacy"]] = prim.get(x["primacy"], 0) + 1
    OUT.write_text(json.dumps({"_note": __doc__.strip().split("\n\n")[0], "summary": by, "primacy": prim,
                               "rcpa_reference_sets_loaded": RCPA.exists(), "thresholds": rows}, indent=1, ensure_ascii=False) + "\n")
    print("primacy:", json.dumps(prim))
    print(json.dumps(by), "| RCPA reference sets loaded:", RCPA.exists())
    for x in rows:
        if (x["conversion"] or {}).get("kind") in ("molar", "relabel") or x.get("flag"):
            a = x["au"] or {}
            print(f"  {x['analyte'][:34]:<34} {x['as_published'].get('text','')[:36]:<36} -> {a.get('value')}{'-'+str(a['value_to']) if a.get('value_to') else ''} {a.get('unit','')}  [{(x['conversion'] or {}).get('kind','FLAG')}] {x['primacy']:<12} {(x.get('au_unit_confirmation') or {}).get('status','')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
