#!/usr/bin/env python3
"""A second witness for DrugCentral's mechanism-of-action rows: does ChEMBL independently record the same target?

DrugCentral takes most mechanisms from ChEMBL (moa_source = CHEMBL) -- those cannot be checked against ChEMBL. The rest
come from the drug label, the literature, IUPHAR or KEGG, and for those ChEMBL is an independent curation. For each such
row this asks ChEMBL's public REST API for the drug's mechanisms (by molecule or parent molecule) and the protein
accessions of their targets, and records one verdict per DrugCentral act_id:

    agrees     ChEMBL records a mechanism on a target sharing a UniProt accession with DrugCentral's
    differs    ChEMBL records mechanisms for the drug, none on a shared protein (a secondary target called mechanism,
               or the same target recorded for another strain / as a coarser group -- a person tells which)
    silent     ChEMBL records no mechanism for the drug
    same_source  DrugCentral's mechanism came from ChEMBL (not checked: not independent)

Writes cache/chembl/moa_witness.tsv and the raw answers (ChEMBL is CC BY-SA 3.0). Resumable per batch.

    scripts/chembl_moa_witness.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DC, OUT = Path("cache/drugcentral"), Path("cache/chembl")
API = "https://www.ebi.ac.uk/chembl/api/data"


def get(path: str, q: dict) -> dict:
    url = f"{API}/{path}.json?" + urllib.parse.urlencode(q)
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=120))
        except Exception:
            time.sleep(2 + 3 * i)
    raise SystemExit(f"ChEMBL did not answer: {path}")


def tsv(name: str) -> list[dict]:
    return list(csv.DictReader(open(DC / f"{name}.tsv", encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "moa_chembl_raw.json"
    raw = json.load(open(raw_path)) if raw_path.exists() else {"mechanisms": {}, "targets": {}}
    chembl = {}
    for r in tsv("identifier"):
        if r["id_type"] == "ChEMBL_ID":
            chembl.setdefault(r["struct_id"], []).append(r["identifier"])
    moa = [r for r in tsv("act_table_full") if r["moa"] == "1"]
    todo = sorted({c for r in moa if r["moa_source"] != "CHEMBL" for c in chembl.get(r["struct_id"], [])} - set(raw["mechanisms"]))
    print(f"mechanism rows {len(moa):,}; ChEMBL molecules to ask: {len(todo):,}", flush=True)
    for i in range(0, len(todo), 40):
        batch = todo[i:i + 40]
        found = {c: [] for c in batch}
        for field in ("molecule_chembl_id__in", "parent_molecule_chembl_id__in"):
            for m in get("mechanism", {field: ",".join(batch), "limit": 1000})["mechanisms"]:
                for c in {m.get("molecule_chembl_id"), m.get("parent_molecule_chembl_id")} & set(batch):
                    if m not in found[c]:
                        found[c].append(m)
        raw["mechanisms"].update(found)
        json.dump(raw, open(raw_path, "w"))
        time.sleep(0.5)
    tids = sorted({m["target_chembl_id"] for ms in raw["mechanisms"].values() for m in ms if m.get("target_chembl_id")} - set(raw["targets"]))
    for i in range(0, len(tids), 40):
        for t in get("target", {"target_chembl_id__in": ",".join(tids[i:i + 40]), "limit": 1000})["targets"]:
            raw["targets"][t["target_chembl_id"]] = sorted({c["accession"] for c in t.get("target_components", []) if c.get("accession")})
        json.dump(raw, open(raw_path, "w"))
        time.sleep(0.5)
    counts = {}
    with open(OUT / "moa_witness.tsv", "w", encoding="utf-8") as fh:
        fh.write("act_id\tverdict\tchembl_mechanisms\n")
        for r in moa:
            if r["moa_source"] == "CHEMBL":
                v, ms = "same_source", []
            else:
                ms = [m for c in chembl.get(r["struct_id"], []) for m in raw["mechanisms"].get(c, [])]
                acc = set((r["accession"] or "").split("|")) - {""}
                v = ("silent" if not ms else
                     "agrees" if any(acc & set(raw["targets"].get(m.get("target_chembl_id"), [])) for m in ms) else "differs")
            counts[v] = counts.get(v, 0) + 1
            fh.write(f"{r['act_id']}\t{v}\t{'; '.join(sorted({(m.get('mechanism_of_action') or '').replace(chr(9), ' ') for m in ms}))}\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
