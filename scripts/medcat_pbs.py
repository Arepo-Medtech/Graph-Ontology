#!/usr/bin/env python3
"""PBS indication texts -> SNOMED CT-AU candidates through MedCAT (UMLS self-trained pack, 2023) and UMLS 2026AA.

    cache/medcat/venv/bin/python scripts/medcat_subset.py --texts cache/medcat/pbs_texts.txt --out cache/medcat/subset_pbs
    cache/medcat/venv/bin/python scripts/medcat_pbs.py

Per text: MedCAT recognises and links concepts (UMLS CUIs as of its 2023 training); each CUI is carried to 2026AA
(unchanged if still current, else MRCUI's SY -- merged into -- only; a concept split, narrowed or deleted since is not
followed), then to SNOMED CT through MRCONSO's SNOMEDCT_US atoms (not suppressed), then kept only if the code is an
active concept of SNOMED CT-AU 20260831. The proposal for a text is the linked concept whose span covers most of it.

Checked on the 312 texts already bound by exact name: how often MedCAT's proposal is the bound concept. That is the
evidence for what its proposals on the 341 unbound texts are worth -- they are candidates for a person, never edges.
UMLS-derived: output stays in cache/medcat/ (git-ignored).
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import duckdb

SUBSET = Path("cache/medcat/subset_pbs")
BIND = Path("reference/pbs_indication_bindings.json")
U = Path("cache/umls/2026AA")
AU = Path(os.environ.get("AU_RF2_SNAPSHOT", os.path.expanduser("~/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/Snapshot")))
OUT = Path("cache/medcat/pbs_medcat_candidates.json")


def load_cat():
    from medcat.utils.legacy.conversion_all import Converter
    return Converter(str(SUBSET), None).convert()


def main() -> int:
    logging.disable(logging.WARNING)
    t0 = time.time()
    cat = load_cat()
    rows = json.load(open(BIND))["results"]
    found = []
    for i, r in enumerate(rows):
        text = r["text"]
        ents = cat.get_entities(text)["entities"].values()
        for e in ents:
            found.append((i, e["cui"], e["pretty_name"], e["source_value"], e["start"], e["end"],
                          float(e.get("context_similarity") or 0), len(text)))
    con = duckdb.connect()
    con.execute("CREATE TABLE f (i INT, cui VARCHAR, pretty VARCHAR, span VARCHAR, s INT, e INT, sim DOUBLE, tlen INT)")
    con.executemany("INSERT INTO f VALUES (?,?,?,?,?,?,?,?)", found)
    # 2023 CUI -> 2026AA CUI: current as is; else merged (MRCUI SY) only
    con.execute(f"""CREATE TABLE live AS SELECT DISTINCT CUI FROM '{U / "mrconso.parquet"}' WHERE CUI IN (SELECT cui FROM f)""")
    con.execute(f"""CREATE TABLE rekey AS SELECT DISTINCT f.cui c_old, coalesce(l.CUI, m.CUI2) c_new,
                        CASE WHEN l.CUI IS NOT NULL THEN 'current' WHEN m.CUI2 IS NOT NULL THEN 'merged' ELSE 'retired' END how
        FROM (SELECT DISTINCT cui FROM f) f LEFT JOIN live l ON l.CUI = f.cui
        LEFT JOIN (SELECT CUI1, CUI2 FROM '{U / "mrcui.parquet"}' WHERE REL = 'SY' AND CUI2 IS NOT NULL AND CUI2 <> '') m
               ON l.CUI IS NULL AND m.CUI1 = f.cui""")
    con.execute(f"""CREATE TABLE au AS SELECT id FROM read_csv('{AU / "Terminology/sct2_Concept_Snapshot_AU1000036_20260831.txt"}',
                    delim='\t', header=true, quote='', all_varchar=true) WHERE active = '1'""")
    con.execute(f"""CREATE TABLE fsn AS SELECT conceptId id, any_value(term) nm FROM read_csv('{AU / "Terminology/sct2_Description_Snapshot-en-au_AU1000036_20260831.txt"}',
                    delim='\t', header=true, quote='', all_varchar=true) WHERE active = '1' AND typeId = '900000000000003001' GROUP BY 1""")
    con.execute(f"""CREATE TABLE sct AS SELECT DISTINCT r.c_old, r.c_new, r.how, m.CODE sct FROM rekey r
        JOIN '{U / "mrconso.parquet"}' m ON m.CUI = r.c_new AND m.SAB = 'SNOMEDCT_US' AND m.SUPPRESS = 'N'
        JOIN au ON au.id = m.CODE""")
    ents = con.execute("""SELECT f.i, f.cui, r.c_new, r.how, f.pretty, f.span, f.s, f.e, round(f.sim, 3) sim_r,
                                 (f.e - f.s) / f.tlen::DOUBLE cover, list(DISTINCT s.sct ORDER BY s.sct) FILTER (WHERE s.sct IS NOT NULL)
                          FROM f JOIN rekey r ON r.c_old = f.cui LEFT JOIN sct s ON s.c_old = f.cui
                          GROUP BY ALL ORDER BY f.i, cover DESC, sim_r DESC""").fetchall()
    names = dict(con.execute("SELECT id, nm FROM fsn WHERE id IN (SELECT sct FROM sct)").fetchall())
    by = {}
    for i, cui, new, how, pretty, span, s, e, sim, cover, scts in ents:
        by.setdefault(i, []).append({"cui_2023": cui, "cui_2026AA": new, "rekey": how, "medcat_name": pretty, "span": span,
                                     "cover": round(cover, 2), "similarity": sim,
                                     "snomed": [{"id": c, "fsn": names.get(c)} for c in (scts or [])]})
    out, stats = [], {"texts": len(rows), "texts_with_entity": 0, "texts_with_snomed": 0,
                      "bound": {"n": 0, "proposal_is_bound": 0, "bound_among_any_entity": 0, "no_proposal": 0},
                      "unbound": {"n": 0, "with_proposal": 0, "proposal_among_ontoserver_candidates": 0, "covers_whole_text": 0},
                      "rekey": dict(con.execute("SELECT how, count(*) FROM rekey GROUP BY 1").fetchall())}
    for i, r in enumerate(rows):
        es = by.get(i, [])
        stats["texts_with_entity"] += bool(es)
        prop = next((x for x in es if x["snomed"]), None)            # widest span that reaches SNOMED CT-AU
        stats["texts_with_snomed"] += prop is not None
        ids = {s["id"] for s in prop["snomed"]} if prop else set()
        if r["bound"]:
            b = stats["bound"]
            b["n"] += 1
            b["proposal_is_bound"] += r["bound"]["concept_id"] in ids
            b["bound_among_any_entity"] += any(r["bound"]["concept_id"] in {s["id"] for s in x["snomed"]} for x in es)
            b["no_proposal"] += prop is None
        else:
            u = stats["unbound"]
            u["n"] += 1
            u["with_proposal"] += prop is not None
            u["proposal_among_ontoserver_candidates"] += bool(ids & {c["concept_id"] for c in r.get("candidates", [])})
            u["covers_whole_text"] += bool(prop and prop["cover"] >= 0.9)
        out.append({"text": r["text"], "indication_prescribing_txt_id": r["indication_prescribing_txt_id"],
                    "bound": r["bound"]["concept_id"] if r["bound"] else None,
                    "ontoserver_candidates": [c["concept_id"] for c in r.get("candidates", [])],
                    "proposal": prop, "entities": es})
    stats["seconds"] = round(time.time() - t0)
    json.dump({"_note": "MedCAT (UMLS self-trained pack, 2023) candidates; UMLS-derived, not redistributed; frames for a "
                        "person, never edges", "summary": stats, "results": out}, open(OUT, "w"), indent=1)
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
