#!/usr/bin/env python3
"""Reconcile pathology units: US conventional (mass, mg/dL) against Australian SI (molar, mmol/L) -- by code, not by name.

Australian laboratories report most small-molecule analytes in molar units (glucose, creatinine, cholesterol, urate in
mmol/L or umol/L) where US laboratories use mass (mg/dL); some analytes stay mass in both but at another scale
(haemoglobin 14 g/dL in the US, 140 g/L here). LOINC keeps the two as different codes, told apart by PROPERTY -- MCnc
(mass concentration) and SCnc (substance concentration) -- with every other axis equal. This script:

  1. pairs each active MCnc lab term with its SCnc counterpart on COMPONENT, SYSTEM, TIME, SCALE and METHOD;
  2. resolves the analyte by code: the mass term's primary COMPONENT part, through LOINC's own part mapping
     (PartRelatedCodeMapping, equivalence 'equivalent' only) to a PubChem CID or a ChEBI id;
  3. takes the molecular weight from PubChem (PUG REST, by CID or by the ChEBI registry id) -- cached in cache/pubchem/;
  4. writes the factor mg/dL -> mmol/L = 10 / MW (g/mol).

No name matching anywhere: an analyte with no equivalent PubChem / ChEBI code (proteins, lipoprotein fractions, cells)
gets no factor and is listed as unresolved. The Australian PREFERRED unit is not decided here -- that is the RCPA SPIA
Preferred Units Table's job (distributed through the NCTS); until it is loaded every pair carries au_preferred = null.

    scripts/unit_reconcile.py        # writes reference/loinc_unit_counterparts.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

L = Path(os.environ.get("LOINC_DIR", os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83")))
CACHE, OUT = Path("cache/pubchem/mw.json"), Path("reference/loinc_unit_counterparts.json")
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
# Reporting CONVENTIONS: the quantity a laboratory reports is not always the molecule LOINC's part maps to. Phosphate is
# reported as phosphorus; urea nitrogen as its nitrogen (N2, 28.01 g/mol per mol of urea); triglyceride as triolein;
# lipoprotein cholesterol as cholesterol. The convention is from Young DS, Implementation of SI units for clinical
# laboratory data, Ann Intern Med 1987 (PMID 3789557); the molecular weight is still PubChem's, by CID. The CHOICE of
# reference substance is authored, so every factor it gives is marked convention = true and awaits a person's sign-off.
CONVENTIONS = {
    "LP14912-7": (5462309, "phosphate reported as phosphorus"),
    "LP14492-0": (947, "urea nitrogen reported as nitrogen: 1 mol urea carries 2 N = 28.01 g (N2)"),
    "LP15275-8": (5497163, "triglyceride reported as triolein"),
    "LP15489-5": (5997, "cholesterol in HDL reported as cholesterol"),
    "LP15491-1": (5997, "cholesterol in LDL reported as cholesterol"),
    "LP15492-9": (5997, "cholesterol in VLDL reported as cholesterol"),
    "LP36472-6": (5997, "non-HDL cholesterol reported as cholesterol"),
}
# part numbers are checked against LOINC's own Part.csv at run time: a convention keyed to the wrong part is refused
CONVENTION_PART_NAMES = {"LP14912-7": "Phosphate", "LP14492-0": "Urea nitrogen", "LP15275-8": "Triglyceride",
                         "LP15489-5": "Cholesterol.in HDL", "LP15491-1": "Cholesterol.in LDL", "LP15492-9": "Cholesterol.in VLDL",
                         "LP36472-6": "Cholesterol.non HDL"}
CONVENTION_SOURCE = "Young DS. Ann Intern Med 1987 (PMID 3789557)"


def pubchem(kind: str, ident: str) -> dict | None:
    url = f"{PUG}/{kind}/{urllib.parse.quote(ident)}/property/MolecularWeight,Title/JSON"
    for i in range(3):
        try:
            time.sleep(0.25)                                   # PubChem asks for at most 5 requests a second
            p = json.load(urllib.request.urlopen(url, timeout=60))["PropertyTable"]["Properties"][0]
            return {"cid": p["CID"], "mw": float(p["MolecularWeight"]), "title": p.get("Title")}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 2 * i)
        except Exception:
            time.sleep(2 + 2 * i)
    return None


def main() -> int:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW lt AS SELECT * FROM read_csv('{L}/LoincTable/Loinc.csv', header=true, all_varchar=true)")
    con.execute(f"CREATE VIEW pl AS SELECT * FROM read_csv('{L}/AccessoryFiles/PartFile/LoincPartLink_Primary.csv', header=true, all_varchar=true)")
    con.execute(f"CREATE VIEW pm AS SELECT * FROM read_csv('{L}/AccessoryFiles/PartFile/PartRelatedCodeMapping.csv', header=true, all_varchar=true)")
    pairs = con.execute("""
        SELECT m.LOINC_NUM mass, s.LOINC_NUM molar, m.COMPONENT component, m.EXAMPLE_UCUM_UNITS mass_unit, s.EXAMPLE_UCUM_UNITS molar_unit,
               (SELECT any_value(PartNumber) FROM pl WHERE pl.LoincNumber = m.LOINC_NUM AND pl.PartTypeName = 'COMPONENT') part
        FROM lt m JOIN lt s ON s.COMPONENT = m.COMPONENT AND s.SYSTEM = m.SYSTEM AND s.TIME_ASPCT = m.TIME_ASPCT
             AND s.SCALE_TYP = m.SCALE_TYP AND coalesce(s.METHOD_TYP, '') = coalesce(m.METHOD_TYP, '') AND s.PROPERTY = 'SCnc'
        WHERE m.PROPERTY = 'MCnc' AND m.CLASSTYPE = '1' AND s.CLASSTYPE = '1' AND m.STATUS = 'ACTIVE' AND s.STATUS = 'ACTIVE'
        ORDER BY 1, 2""").fetchall()
    names = dict(con.execute(f"SELECT PartNumber, PartName FROM read_csv('{L}/AccessoryFiles/PartFile/Part.csv', header=true, all_varchar=true)").fetchall())
    bad = {p: (names.get(p), CONVENTION_PART_NAMES.get(p)) for p in CONVENTIONS if names.get(p) != CONVENTION_PART_NAMES.get(p)}
    if bad:
        raise SystemExit(f"convention keyed to the wrong LOINC part (found, expected): {bad}")
    ext = {}
    for part, code, system in con.execute("""SELECT PartNumber, ExtCodeId, ExtCodeSystem FROM pm WHERE Equivalence = 'equivalent'
            AND ExtCodeSystem IN ('http://pubchem.ncbi.nlm.nih.gov', 'https://www.ebi.ac.uk/chebi')""").fetchall():
        ext.setdefault(part, {})["pubchem" if "pubchem" in system else "chebi"] = code
    cache = json.load(open(CACHE)) if CACHE.exists() else {}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out, unresolved = [], 0
    for i, (mass, molar, comp, mu, su, part) in enumerate(pairs, 1):
        x = ext.get(part or "", {})
        conv = CONVENTIONS.get(part or "")
        mapped = f"cid:{x['pubchem']}" if "pubchem" in x else (f"chebi:{x['chebi']}" if "chebi" in x else None)
        key = f"cid:{conv[0]}" if conv else mapped
        if key and (key not in cache or cache[key] is None):      # a cached failure is retried
            ident = key.split(":", 1)[1]
            cache[key] = pubchem("cid", ident) if key.startswith("cid:") else pubchem("xref/RegistryID", ident if ident.startswith("CHEBI:") else "CHEBI:" + ident)
            if i % 50 == 0:
                json.dump(cache, open(CACHE, "w"))
        m = cache.get(key) if key else None
        if not m:
            unresolved += 1
        out.append({"mass_loinc": mass, "molar_loinc": molar, "component": comp, "component_part": part, "mass_unit_example": mu,
                    "molar_unit_example": su, "analyte_code": key, "pubchem_cid": m["cid"] if m else None,
                    "molecular_weight": m["mw"] if m else None,
                    "factor_mg_per_dL_to_mmol_per_L": round(10 / m["mw"], 6) if m else None, "au_preferred": None,
                    "convention": ({"reference_substance_cid": conv[0], "why": conv[1], "source": CONVENTION_SOURCE,
                                    "overrides_loinc_mapping": mapped, "state": "corrected_pending_attestation"} if conv else None)})
    json.dump(cache, open(CACHE, "w"))
    OUT.write_text(json.dumps({
        "_note": ("LOINC mass (MCnc) <-> molar (SCnc) counterparts and the conversion factor between them, resolved by code: the "
                  "component part's LOINC-asserted equivalent PubChem / ChEBI id, and PubChem's molecular weight. mmol/L = mg/dL x factor; "
                  "mg/dL = mmol/L / factor. au_preferred is null until the RCPA SPIA Preferred Units Table (NCTS) is loaded -- "
                  "Australian practice is not always molar (haemoglobin and albumin are reported in g/L)."),
        "_licence": ("This material contains content from LOINC (http://loinc.org). LOINC is copyright Regenstrief Institute, Inc. and the "
                     "LOINC Committee and is available at no cost under the license at http://loinc.org/license. Molecular weights from PubChem (NCBI)."),
        "pairs": len(out), "with_factor": len(out) - unresolved, "unresolved": unresolved, "counterparts": out}, indent=1) + "\n")
    print(f"pairs {len(out):,}; with a factor {len(out) - unresolved:,}; unresolved (no equivalent PubChem / ChEBI code) {unresolved:,}; "
          f"by reporting convention {sum(1 for c in out if c['convention'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
