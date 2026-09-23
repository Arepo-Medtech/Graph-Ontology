#!/usr/bin/env python3
"""Load the Australian preferred reporting units from the RCPA SPIA reference sets (NCTS release), read in place.

The RCPA's SPIA Reporting Terminology Reference Sets give, for each RCPA preferred term, the LOINC code Australian
laboratories should report it under and its preferred unit (display and UCUM). That is the authority for "the local
unit": which of LOINC's mass (US) or molar (SI) codes Australia uses, and at which scale (haemoglobin g/L, not g/dL).

RCPA content is copyright (NEHTA-RCPA Terms of Use): it is read in place from ~/Documents/ONTOLOGIES/RCPA_<version>
and what is derived from it stays in cache/rcpa/ (git-ignored) -- never committed.

    scripts/rcpa_units.py      # writes cache/rcpa/reporting_units.json
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

import openpyxl

SRC = Path(os.environ.get("RCPA_DIR", sorted(d for d in glob.glob(os.path.expanduser("~/Documents/ONTOLOGIES/RCPA_v*")) if os.path.isdir(d))[-1]))
OUT = Path("cache/rcpa/reporting_units.json")
SETS = ("Reporting Terminology Reference Set", "Blood Gases Terminology Reference Set")


def main() -> int:
    rows, per_set = [], {}
    for f in sorted(SRC.glob("*.xlsx")):
        if not any(s in f.name for s in SETS):
            continue
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        n = 0
        # the reporting sets have one reporting sheet; blood gases have one sheet per specimen (arterial, venous, cord ...),
        # each with a banner above its header row. Working sheets (feedback, QAP codes, drafts) are not reporting content.
        sheets = [w for w in wb.worksheets if w.title != "Rev History"]
        if "Blood Gases" not in f.name:
            sheets = sheets[:1]
        for ws in sheets:
            rows_ = list(ws.iter_rows(values_only=True))
            hi = next((i for i, r in enumerate(rows_[:12]) if r and "UCUM" in [str(c).strip() if c is not None else "" for c in r]), None)
            if hi is None:
                continue
            head = [str(h).strip() if h is not None else "" for h in rows_[hi]]
            term = next((h for h in ("RCPA Preferred term", "RCPA SPIA Reporting Term", "SPIA Preferred Term") if h in head), None)
            loinc_i = max(i for i, h in enumerate(head) if h == "LOINC") if "LOINC" in head else None
            if term is None or loinc_i is None:
                print(f"  skipped (columns not recognised): {f.name} / {ws.title}", file=sys.stderr)
                continue
            col = {h: i for i, h in enumerate(head) if h}
            g = lambda r, k: (str(r[col[k]]).strip() if k in col and col[k] < len(r) and r[col[k]] is not None else None)
            for r in rows_[hi + 1:]:
                loinc = str(r[loinc_i] or "").strip() if loinc_i < len(r) else ""
                if not loinc or "-" not in loinc:
                    continue
                rows.append({"set": f.stem, "sheet": ws.title, "rcpa_term": g(r, term), "specimen": g(r, "Specimen"), "unit": g(r, "Unit"),
                             "ucum": g(r, "UCUM"), "loinc": loinc, "property": (g(r, "Property") or "").strip(), "system": g(r, "System")})
                n += 1
        per_set[f.stem] = n
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"_note": f"Derived from the RCPA SPIA reporting reference sets in {SRC.name} (RCPA copyright; not for redistribution).",
                               "source_dir": SRC.name, "sets": per_set, "rows": rows}, indent=1, ensure_ascii=False))
    loincs = {x["loinc"] for x in rows}
    props = {}
    for x in rows:
        props[x["property"]] = props.get(x["property"], 0) + 1
    print(json.dumps({"source": SRC.name, "sets": per_set, "rows": len(rows), "distinct_loinc": len(loincs),
                      "by_property": dict(sorted(props.items(), key=lambda kv: -kv[1])[:10])}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
