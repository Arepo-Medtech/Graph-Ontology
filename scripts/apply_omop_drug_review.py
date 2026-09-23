#!/usr/bin/env python3
"""Set rejected AMT -> OMOP product mappings aside after a build, and re-export what changed.

`reference/omop_drug_review.json` lists product mappings that three independent witnesses show to be wrong: OMOP's
own `Maps to` sending *Azamun 50 mg tablet* (azathioprine) to *Bonjela* gel, *Buscopan* (butylscopolamine) to
scopolamine, and so on. A build rewrites `omop_drug` and `transcode` from OMOP wholesale, so without this step every
rejection would return with the next build -- the failure `apply_corrections.py` prevents for SNOMED bindings. Run it
straight after `build_compendium.py`, before anything that reads `omop_drug`.

**How a rejection is applied.** The refused answer moves to `refused_standard_concept_id` / `refused_standard_name`
and the live `standard_concept_id` becomes NULL, with `review_status` saying why. Every reader of `omop_drug`
already filters on `standard_concept_id IS NOT NULL` -- `transcode`, `atc_bridge.py`, `drug_strength.py`,
`amt_indirect.py`, the review queue -- so all of them stop using it without a code change. A rejected mapping is
ignorance, not an answer; and `amt_indirect.py` may then legitimately reach the product through its generic.

`transcode` rows for rejected TPUUs lose their `omop_drug_*` values and gain `omop_drug_review`. The changed tables
are re-exported to `out/*.parquet` / `out/*.csv`, so the shipped files agree with the database.

Idempotent: a mapping already set aside is left alone.

    scripts/apply_omop_drug_review.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
REVIEW = Path("reference/omop_drug_review.json")
OUT = Path("out")


def main() -> int:
    review = [r for r in json.load(open(REVIEW))["review"] if r["status"] == "rejected"]
    con = duckdb.connect(str(DB))
    for col, typ in (("review_status", "VARCHAR"), ("refused_standard_concept_id", "BIGINT"),
                     ("refused_standard_name", "VARCHAR")):
        con.execute(f"ALTER TABLE omop_drug ADD COLUMN IF NOT EXISTS {col} {typ}")
    con.execute("ALTER TABLE transcode ADD COLUMN IF NOT EXISTS omop_drug_review VARCHAR")

    applied = already = missing = 0
    for r in review:
        row = con.execute("SELECT standard_concept_id, refused_standard_concept_id FROM omop_drug WHERE product_id = ?",
                          [r["product_id"]]).fetchone()
        if row is None:
            missing += 1
            continue
        live, refused = row
        if live is None and refused == r["refused_standard_concept_id"]:
            already += 1
            continue
        if live != r["refused_standard_concept_id"]:
            # OMOP now says something else for this product: the rejection no longer describes the data. Say so,
            # and do not touch it -- a person should look at the new answer.
            print(f"STALE {r['product_id']} {r['pt'][:50]}: review refused {r['refused_standard_concept_id']}, "
                  f"OMOP now gives {live}", file=sys.stderr)
            missing += 1
            continue
        reason = f"rejected ({r['class']}): {r['why']}"
        con.execute("""UPDATE omop_drug SET refused_standard_concept_id = standard_concept_id,
                           refused_standard_name = standard_name, review_status = ?,
                           standard_concept_id = NULL, standard_name = NULL, standard_vocabulary = NULL,
                           standard_code = NULL
                       WHERE product_id = ?""", [reason, r["product_id"]])
        applied += 1
    rejected_tpuu = [(f"rejected ({r['class']}): {r['why']}", r["product_id"]) for r in review if r["level"] == "TPUU"]
    con.executemany("""UPDATE transcode SET omop_drug_concept_id = NULL, omop_drug_name = NULL,
                           omop_drug_vocabulary = NULL, omop_drug_review = ? WHERE tpuu_id = ?""", rejected_tpuu)

    exported = []
    for table, fmts in (("omop_drug", ("parquet",)), ("transcode", ("parquet", "csv"))):
        for fmt in fmts:
            path = OUT / f"{table}.{fmt}"
            if path.exists():
                con.execute(f"COPY {table} TO '{path}' " + ("(FORMAT PARQUET)" if fmt == "parquet" else "(HEADER)"))
                exported.append(str(path))
    by = dict(collections.Counter(r["class"] for r in review))
    set_aside = con.execute("SELECT count(*) FROM omop_drug WHERE refused_standard_concept_id IS NOT NULL").fetchone()[0]
    tc = con.execute("SELECT count(*) FROM transcode WHERE omop_drug_review IS NOT NULL").fetchone()[0]
    con.close()
    print(json.dumps({"rejections_in_review": len(review), "by_class": by, "applied_now": applied,
                      "already_set_aside": already, "not_applied": missing,
                      "omop_drug_rows_set_aside": set_aside, "transcode_rows_marked": tc, "re_exported": exported},
                     indent=1))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
