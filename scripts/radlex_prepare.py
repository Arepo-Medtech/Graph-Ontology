#!/usr/bin/env python3
"""Read RadLex (RSNA) into cache/radlex/, and list the anatomy codes the radiology bridge needs from UMLS.

LOINC's 7,000 radiology terms are coded by LOINC to RadLex (AccessoryFiles/LoincRsnaRadiologyPlaybook), and RadLex to
nothing in SNOMED CT. RadLex does carry cross-references: an FMA id on 33,404 classes and a UMLS CUI on 1,376 (its
ExternalRefID annotation). Those are the codes the bridge walks: RadLex -> FMA -> Uberon -> SNOMED CT (Uberon's own
maps), RadLex -> FMA -> SNOMED CT (UMLS shared CUI) and RadLex -> CUI -> SNOMED CT (UMLS atoms).

RadLex.owl spreads a class over three blocks -- owl:Class (axioms), owl:NamedIndividual (the pun) and rdf:Description
(the annotations, where the FMA id and the name live) -- so every block for an RID is merged. RadLex is RSNA's, used
under its licence: it is read in place and the derived JSON stays in cache/ (git-ignored).

    scripts/radlex_prepare.py            # ~20 s; then the two UMLS runs it prints
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ONT_ROOT = os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES"))   # the licensed releases, read in place
RADLEX_OWL = Path(os.environ.get("RADLEX_OWL", os.path.join(ONT_ROOT, "PunRadLex_Owl4.3/RadLex.owl")))
LOINC_RSNA = Path(os.path.join(ONT_ROOT, "Loinc_2.83/AccessoryFiles/LoincRsnaRadiologyPlaybook/LoincRsnaRadiologyPlaybook.csv"))
RSNA_PLAYBOOK = Path(os.environ.get("RSNA_PLAYBOOK", os.path.join(ONT_ROOT, "complete-playbook-dev.csv")))
OUT = Path("cache/radlex")

NS = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "owl": "http://www.w3.org/2002/07/owl#"}
RID = "http://www.radlex.org/RID/"
ABOUT, RES = f"{{{NS['rdf']}}}about", f"{{{NS['rdf']}}}resource"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"
PART_OF = ("Part_Of", "Regional_Part_Of", "Constitutional_Part_Of")
BLOCKS = {f"{{{NS['owl']}}}Class", f"{{{NS['owl']}}}NamedIndividual", f"{{{NS['rdf']}}}Description"}
# the RSNA playbook's anatomy columns; its RIDS field lists one RID (or 0) per column from MODALITY onward
PLAYBOOK_ANATOMY = ("BODY_REGION", "BODY_REGION_2", "BODY_REGION_3", "BODY_REGION_4", "BODY_REGION_5",
                    "ANATOMIC_FOCUS", "ANATOMIC_FOCUS_2")


def tail(uri: str) -> str:
    return uri.rsplit("/", 1)[1]


def parse_radlex() -> dict:
    out = collections.defaultdict(lambda: {"ext": [], "is_a": [], "part_of": [], "syn": []})
    for _, el in ET.iterparse(RADLEX_OWL):
        if el.tag in BLOCKS and el.get(ABOUT, "").startswith(RID + "RID"):
            d = out[tail(el.get(ABOUT))]
            for c in el:
                t, res = c.tag.split("}")[1], c.get(RES)
                if t in ("label", "Preferred_name") and c.get(LANG, "en") == "en":
                    d["name"] = c.text
                elif t == "ExternalRefID" and c.text:
                    d["ext"].append(c.text.strip())
                elif t == "Synonym" and c.get(LANG, "en") == "en" and c.text:
                    d["syn"].append(c.text)
                elif t in PART_OF and res:
                    d["part_of"].append(tail(res))
                elif t == "Replaced_by" and res:
                    d["replaced_by"] = tail(res)
                elif t == "subClassOf":
                    if res:
                        d["is_a"].append(tail(res))
                    elif (rs := c.find("owl:Restriction", NS)) is not None:
                        p, v = rs.find("owl:onProperty", NS), rs.find("owl:someValuesFrom", NS)
                        if p is not None and v is not None and v.get(RES) and tail(p.get(RES)) in PART_OF:
                            d["part_of"].append(tail(v.get(RES)))
            el.clear()
    for d in out.values():
        for k in ("ext", "is_a", "part_of", "syn"):
            d[k] = sorted({x for x in d[k] if x})
    return dict(out)


def playbook_anatomy_rids() -> set[str]:
    rids = {r["RID"] for r in csv.DictReader(open(LOINC_RSNA, encoding="utf-8"))
            if r["RID"] and r["PartTypeName"].startswith("Rad.Anatomic Location") and "Laterality" not in r["PartTypeName"]}
    if RSNA_PLAYBOOK.exists():
        rows = list(csv.DictReader(open(RSNA_PLAYBOOK, encoding="utf-8")))
        cols = list(rows[0].keys())
        i0 = cols.index("MODALITY")
        for r in rows:
            v = r["RIDS"].split("|")
            rids |= {v[cols.index(c) - i0] for c in PLAYBOOK_ANATOMY} - {"0", ""}
    return rids


def main() -> int:
    if not RADLEX_OWL.exists():
        sys.exit(f"RadLex not found at {RADLEX_OWL} (set RADLEX_OWL)")
    OUT.mkdir(parents=True, exist_ok=True)
    rl = parse_radlex()
    json.dump(rl, open(OUT / "radlex_classes.json", "w"))
    rids = playbook_anatomy_rids()
    missing = sorted(r for r in rids if r not in rl)
    fma = sorted({e[4:] for r in rids if r in rl for e in rl[r]["ext"] if e.startswith("FMA:")})
    cui = sorted({e[5:] for r in rids if r in rl for e in rl[r]["ext"] if e.startswith("UMLS:")})
    (OUT / "anatomy_fma.txt").write_text("\n".join(fma) + "\n")
    (OUT / "anatomy_cui.txt").write_text("\n".join(cui) + "\n")
    print(json.dumps({"radlex_classes": len(rl), "with_fma": sum(any(e.startswith("FMA:") for e in d["ext"]) for d in rl.values()),
                      "with_cui": sum(any(e.startswith("UMLS:") for e in d["ext"]) for d in rl.values()),
                      "playbook_anatomy_rids": len(rids), "not_in_radlex": missing, "fma_to_fetch": len(fma), "cui_to_fetch": len(cui)}, indent=1))
    print("then:\n  scripts/umls_crosswalk.py --source FMA --target SNOMEDCT_US --ids cache/radlex/anatomy_fma.txt --out fma_sct"
          "\n  scripts/umls_crosswalk.py --source CUI --target SNOMEDCT_US --ids cache/radlex/anatomy_cui.txt --out radlex_cui_sct")
    return 0


if __name__ == "__main__":
    sys.exit(main())
