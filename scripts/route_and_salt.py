#!/usr/bin/env python3
"""Two things the compendium could not answer: which route a product takes, and which salt is which base.

**Route.** Nothing in the compendium said whether a product is swallowed, injected or applied. The information is
in SNOMED's own dose-form model — every pharmaceutical dose form carries `Has dose form intended site` — and in the
PBS schedule's `manner_of_administration` for a listed item. Both are written, tagged with their source, and
compared where they overlap.

**Salt and base.** AMT records a product's *precise* ingredient (the salt, "amlodipine besylate") and its *basis of
strength* (the base, "amlodipine") separately, which is how a strength is stated against the active moiety. SNOMED's
is-a hierarchy does **not** relate the two: amlodipine besylate is not a descendant of amlodipine, so a query
written as `<<amlodipine` misses every product that names the salt. That is not a modelling error — a salt is not a
kind of its base — but it is a trap, and it is the same defect class that cost a Data Golf submission. The 497
salt-to-base pairs AMT implies are written out as a table, with what SNOMED and OMOP each say about the same pair.

    scripts/route_and_salt.py [--vocab-dir ~/code/spine/out/omop-vocab]

Offline; writes `product_route`, `product_route_check` and `substance_salt_base` into out/compendium.duckdb.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
INTENDED_SITE = "736474004"
# the PBS's own vocabulary for the same idea, mapped to the SNOMED site it means. Only the unambiguous ones: a PBS
# "Application" says nothing about where, and is left unmapped rather than guessed at.
PBS_MANNER_SITE = {
    "ORAL": "738956005", "INJECTION": "738984000", "INHALATION_BY_MOUTH": "738985004", "INHALATION": "738985004",
    "APPLICATION_TO_THE_EYE": "738952007", "TRANSDERMAL": "738987007", "RECTAL": "738986003", "NASAL": "738948007",
    "SUBLINGUAL": "761829007", "VAGINAL": "738989005", "APPLICATION_TO_THE_EAR": "738983006",
    "FOR_EXTERNAL_USE": "738904002", "DENTAL": "738906000", "BUCCAL": "763825005",
}


def build(vocab_dir: str, log=print) -> dict:
    con = duckdb.connect(str(DB))
    # --- route -------------------------------------------------------------------------------------------------
    con.execute(f"""CREATE OR REPLACE TABLE product_route AS
        SELECT DISTINCT df.product_id, r.dst AS route_id, k.pt AS route, 'dose form' AS source
        FROM dose_form df JOIN rel r ON r.src=df.dose_form_id AND r.typ='{INTENDED_SITE}'
        JOIN concept k ON k.id=r.dst""")
    manner_case = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in PBS_MANNER_SITE.items())
    con.execute(f"""INSERT INTO product_route
        SELECT DISTINCT p.amt_code, CASE i.manner_of_administration {manner_case} END AS route_id,
               i.moa_preferred_term, 'pbs'
        FROM pbs p JOIN pbs_item i ON i.pbs_code=p.pbs_code
        WHERE p.amt_code IS NOT NULL AND i.manner_of_administration IS NOT NULL
          AND CASE i.manner_of_administration {manner_case} END IS NOT NULL
          AND EXISTS (SELECT 1 FROM product pr WHERE pr.id=p.amt_code)""")
    # a pack's route is its units' route
    con.execute("""INSERT INTO product_route
        SELECT DISTINCT co.unit_id, pr.route_id, pr.route, 'pbs'
        FROM product_route pr JOIN contains co ON co.package_id=pr.product_id
        WHERE pr.source='pbs'
          AND NOT EXISTS (SELECT 1 FROM product_route x WHERE x.product_id=co.unit_id AND x.route_id=pr.route_id AND x.source='pbs')""")
    con.execute("""CREATE OR REPLACE TABLE product_route_check AS
        WITH d AS (SELECT DISTINCT product_id, route_id FROM product_route WHERE source='dose form'),
             p AS (SELECT DISTINCT product_id, route_id FROM product_route WHERE source='pbs')
        SELECT d.product_id, list_sort(list(DISTINCT d.route_id)) AS dose_form_routes,
               list_sort(list(DISTINCT p.route_id)) AS pbs_routes, bool_or(d.route_id=p.route_id) AS agree
        FROM d JOIN p ON p.product_id=d.product_id GROUP BY 1""")

    # --- salt and base -----------------------------------------------------------------------------------------
    con.execute("""CREATE OR REPLACE TABLE substance_salt_base AS
        SELECT i.precise_substance_id AS salt_id, any_value(sp.substance) AS salt,
               i.boss_substance_id AS base_id, any_value(sb.substance) AS base,
               count(DISTINCT i.product_id) AS products,
               EXISTS (SELECT 1 FROM parent_of po WHERE po.child_id=i.precise_substance_id AND po.parent_id=i.boss_substance_id) AS snomed_child_of_base
        FROM ingredient i
        JOIN substance sp ON sp.substance_id=i.precise_substance_id
        JOIN substance sb ON sb.substance_id=i.boss_substance_id
        WHERE i.precise_substance_id <> i.boss_substance_id
        GROUP BY i.precise_substance_id, i.boss_substance_id""")
    # what does OMOP do with the same pair? OHDSI's convention collapses a salt onto its base with `Maps to`.
    concept_csv = os.path.join(vocab_dir, "CONCEPT.csv")
    rel_csv = os.path.join(vocab_dir, "CONCEPT_RELATIONSHIP.csv")
    if os.path.exists(concept_csv) and os.path.getsize(concept_csv) > 1_000_000:
        opts = "delim='\\t', header=true, quote='', escape='', nullstr='', all_varchar=true"
        con.execute(f"""CREATE OR REPLACE TEMP TABLE oc AS SELECT CAST(concept_id AS BIGINT) concept_id, concept_code,
                        concept_name, vocabulary_id FROM read_csv('{concept_csv}', {opts}) WHERE vocabulary_id='SNOMED'""")
        con.execute(f"""CREATE OR REPLACE TEMP TABLE maps AS SELECT CAST(concept_id_1 AS BIGINT) src, CAST(concept_id_2 AS BIGINT) tgt
                        FROM read_csv('{rel_csv}', {opts}) WHERE relationship_id='Maps to' AND invalid_reason IS NULL""")
        con.execute("""ALTER TABLE substance_salt_base ADD COLUMN omop_verdict VARCHAR""")
        # a SNOMED substance's `Maps to` target is an RxNorm ingredient, not another SNOMED concept, so the
        # question is whether the salt and the base CONVERGE on the same standard ingredient — which is how OHDSI
        # expresses "this salt is that active moiety".
        con.execute("""CREATE OR REPLACE TEMP TABLE salt_targets AS
            SELECT b.salt_id, m.tgt FROM substance_salt_base b
            JOIN oc ON oc.concept_code=b.salt_id JOIN maps m ON m.src=oc.concept_id""")
        con.execute("""CREATE OR REPLACE TEMP TABLE base_targets AS
            SELECT b.base_id, m.tgt FROM substance_salt_base b
            JOIN oc ON oc.concept_code=b.base_id JOIN maps m ON m.src=oc.concept_id""")
        con.execute("""UPDATE substance_salt_base b SET omop_verdict =
            CASE WHEN NOT EXISTS (SELECT 1 FROM oc WHERE oc.concept_code=b.salt_id) THEN 'the salt is not in OMOP'
                 WHEN NOT EXISTS (SELECT 1 FROM salt_targets s WHERE s.salt_id=b.salt_id) THEN 'OMOP does not map the salt'
                 WHEN NOT EXISTS (SELECT 1 FROM base_targets t WHERE t.base_id=b.base_id) THEN 'OMOP does not map the base'
                 WHEN EXISTS (SELECT 1 FROM salt_targets s JOIN base_targets t ON t.tgt=s.tgt
                              WHERE s.salt_id=b.salt_id AND t.base_id=b.base_id)
                     THEN 'both reach the same standard ingredient'
                 ELSE 'they reach different standard ingredients' END""")
    report = {
        "route": {
            "products_with_a_route": con.execute("SELECT count(DISTINCT product_id) FROM product_route").fetchone()[0],
            "by_source": dict(con.execute("SELECT source, count(DISTINCT product_id) FROM product_route GROUP BY 1").fetchall()),
            "top_routes": dict(con.execute("""SELECT route, count(DISTINCT product_id) FROM product_route
                                              WHERE source='dose form' GROUP BY 1 ORDER BY 2 DESC LIMIT 8""").fetchall()),
            "products_with_more_than_one_route": con.execute(
                "SELECT count(*) FROM (SELECT product_id FROM product_route WHERE source='dose form' GROUP BY 1 HAVING count(DISTINCT route_id)>1)").fetchone()[0],
            "both_sources": con.execute("SELECT count(*) FROM product_route_check").fetchone()[0],
            "they_agree": con.execute("SELECT count(*) FROM product_route_check WHERE agree").fetchone()[0],
        },
        "salt_base": {
            "pairs": con.execute("SELECT count(*) FROM substance_salt_base").fetchone()[0],
            "products_affected": con.execute("SELECT sum(products) FROM substance_salt_base").fetchone()[0],
            "salt_is_a_snomed_child_of_its_base": con.execute("SELECT count(*) FROM substance_salt_base WHERE snomed_child_of_base").fetchone()[0],
            "omop": dict(con.execute("SELECT omop_verdict, count(*) FROM substance_salt_base GROUP BY 1 ORDER BY 2 DESC").fetchall())
            if con.execute("SELECT count(*) FROM duckdb_columns() WHERE table_name='substance_salt_base' AND column_name='omop_verdict'").fetchone()[0] else {},
        },
    }
    con.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    a = ap.parse_args()
    print(json.dumps(build(a.vocab_dir), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
