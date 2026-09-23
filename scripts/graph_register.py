#!/usr/bin/env python3
"""(Re)generate the SNOMED CT-AU attribute section of reference/graph_predicates.json from the release itself.

The register is the multigraph's contract: scripts/build_edges.py refuses any edge whose predicate is not in it. The
authored predicates are written by hand; the SNOMED attribute types are too many and too release-specific for that,
so this derives them from the compendium's `rel` table (the RF2 relationship snapshot) -- one predicate `sct:<typeId>`
per attribute type, with its label, its count, the semantic tag its objects most often carry, and a category.

The category is DERIVED, not asserted: from the attribute's name for time and quantity, and otherwise from what the
attribute actually points at in this release -- an attribute whose objects are qualifier values carries an adjective.

Run it deliberately when the SNOMED CT-AU pin moves; a new attribute in a new edition fails the build until then.

    scripts/graph_register.py            # rewrites snomed_attributes, preserving everything else
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
REGISTER = Path("reference/graph_predicates.json")
IS_A, METHOD = "116680003", "260686004"
PART_OF = {"774160008"}                      # Contains clinical drug: a pack is made of units
TIME = re.compile(r"occurrence|course|episodicity|temporal|during|after|before|onset|duration|timing", re.I)
QUANTITY = re.compile(r"unit|quantity|size|count|value|strength|number", re.I)


def category(type_id: str, label: str, top_tag: str | None) -> str:
    if type_id == IS_A or type_id in PART_OF:
        return "structure"
    if type_id == METHOD:
        return "action"
    if TIME.search(label):
        return "temporality"
    if QUANTITY.search(label):
        return "rationality"
    if top_tag == "qualifier value":
        return "adjective"
    return "relation"


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    rows = con.execute("""
        WITH t AS (SELECT r.typ, c.tag, count(*) AS n FROM rel r LEFT JOIN concept c ON c.id = r.dst GROUP BY 1, 2),
             tot AS (SELECT typ, sum(n) AS total FROM t GROUP BY 1),
             top AS (SELECT typ, arg_max(tag, n) AS top_tag, max(n) AS top_n FROM t GROUP BY 1)
        SELECT tot.typ, coalesce(lbl.pt, '?'), tot.total, top.top_tag, top.top_n
        FROM tot JOIN top USING (typ) LEFT JOIN concept lbl ON lbl.id = tot.typ
        ORDER BY tot.total DESC""").fetchall()
    con.close()
    attrs = [{"id": f"sct:{typ}", "type_id": typ, "label": label,
              "subject": ["SCT"], "object": ["SCT"],
              "category": category(typ, label, top_tag),
              "derivation": "lookup", "strength_kind": "exact",
              "source": "SNOMED CT-AU RF2 snapshot, REL 20260731 (compendium `rel`)", "status": "built",
              "count": int(total), "object_tag": top_tag, "object_tag_share": round(top_n / total, 3)}
             for typ, label, total, top_tag, top_n in rows]
    reg = json.load(open(REGISTER))
    reg["snomed_attributes"] = attrs
    REGISTER.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    by = {}
    for a in attrs:
        by.setdefault(a["category"], [0, 0])
        by[a["category"]][0] += 1
        by[a["category"]][1] += a["count"]
    print(json.dumps({"attribute_types": len(attrs), "by_category": {k: {"types": v[0], "edges": v[1]}
                      for k, v in sorted(by.items(), key=lambda x: -x[1][1])}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
