#!/usr/bin/env python3
"""Reaching OMOP for the AMT concepts its 2021 snapshot never had.

OMOP's `AMT` vocabulary is a 2021 snapshot. Australian medicines have moved on: 5,426 of the compendium's 24,634
branded units (TPUU) and 9,673 of its 16,137 generic units (MPUU) have no OMOP concept of their own, so they reach
no standard drug and fall out of every OMOP-facing query. Two indirect routes put them back, both stated as the
weaker claim they are:

* **generic** — a branded unit with no concept of its own is placed at its own generic unit's standard concept. The
  claim is "this branded product is that clinical drug", which is what the AMT `is a` edge already says; the brand
  is simply not represented.
* **strength match** — a generic unit is matched to an RxNorm clinical drug whose DRUG_STRENGTH ingredient set,
  strengths (in base units) and dose form all agree exactly. A partial match is recorded as a candidate, never as a
  mapping.

Before either is trusted, both are run against the products that **already** have a direct mapping, and the
agreement with that mapping is reported. A method that cannot reproduce the known answers has no business filling
the unknown ones.

    scripts/amt_indirect.py [--vocab-dir ~/code/spine/out/omop-vocab]

Needs `strength` (scripts/drug_strength.py extract). Offline; writes `omop_drug_indirect` and
`omop_drug_indirect_check` into out/compendium.duckdb.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")


def build(vocab_dir: str, log=print) -> dict:
    concept_csv = os.path.join(vocab_dir, "CONCEPT.csv")
    if not os.path.exists(concept_csv) or os.path.getsize(concept_csv) < 1_000_000:
        raise SystemExit(f"{concept_csv} missing or a stub — install an Athena bundle first")
    opts = "delim='\\t', header=true, quote='', escape='', nullstr='', all_varchar=true"
    con = duckdb.connect(str(DB))
    if not con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name='strength'").fetchone()[0]:
        raise SystemExit("no `strength` table — run scripts/drug_strength.py extract first")
    rel_csv = os.path.join(vocab_dir, "CONCEPT_RELATIONSHIP.csv")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE omop_concept AS
        SELECT CAST(concept_id AS BIGINT) concept_id, concept_name, vocabulary_id, concept_class_id,
               standard_concept, concept_code, domain_id
        FROM read_csv('{concept_csv}', {opts})""")

    # --- route 1: a product with no concept of its own inherits its generic's -----------------------------------
    con.execute("""CREATE OR REPLACE TABLE omop_drug_indirect AS
        SELECT ug.tpuu_id AS product_id, 'TPUU' AS level, od.standard_concept_id, od.standard_name,
               od.standard_vocabulary, 'generic' AS route, ug.mpuu_id AS via_product_id
        FROM unit_generic ug
        JOIN omop_drug od ON od.product_id=ug.mpuu_id AND od.standard_concept_id IS NOT NULL
        WHERE NOT EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=ug.tpuu_id AND d.standard_concept_id IS NOT NULL)""")
    con.execute("""INSERT INTO omop_drug_indirect
        SELECT pg.tpp_id, 'TPP', od.standard_concept_id, od.standard_name, od.standard_vocabulary, 'generic', pg.mpp_id
        FROM pack_generic pg JOIN omop_drug od ON od.product_id=pg.mpp_id AND od.standard_concept_id IS NOT NULL
        WHERE NOT EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=pg.tpp_id AND d.standard_concept_id IS NOT NULL)""")

    # "is the proposed generic the same medicine as the branded concept the direct mapping found?" is an ancestry
    # question, not a relationship one: RxNorm says `Tradename of`, RxNorm Extension's supplier-specific concepts say
    # `Marketed form of`, and only CONCEPT_ANCESTOR covers both.
    ancestor_csv = os.path.join(vocab_dir, "CONCEPT_ANCESTOR.csv")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE anc AS
        SELECT CAST(ancestor_concept_id AS BIGINT) a, CAST(descendant_concept_id AS BIGINT) d
        FROM read_csv('{ancestor_csv}', {opts})
        WHERE CAST(ancestor_concept_id AS BIGINT) IN (SELECT standard_concept_id FROM omop_drug WHERE standard_concept_id IS NOT NULL)
           OR CAST(descendant_concept_id AS BIGINT) IN (SELECT standard_concept_id FROM omop_drug WHERE standard_concept_id IS NOT NULL)""")

    # --- route 2: match a generic unit on its ingredients, strengths and dose form -------------------------------
    # our side: the set of (RxNorm ingredient, strength in base units) per product, plus its dose form's OMOP concept
    con.execute("""CREATE OR REPLACE TEMP TABLE our_fingerprint AS
        WITH ing AS (
            SELECT s.product_id, ing.concept_id AS ingredient_concept_id,
                   coalesce(q.amount_base, q.ratio_base) AS value
            FROM strength s
            JOIN amt_quantity q ON q.product_id=s.product_id AND q.boss_substance_id=s.boss_substance_id AND q.style=s.style
            JOIN omop_substance os ON os.substance_id=s.boss_substance_id
            JOIN omop_concept ing ON ing.vocabulary_id='RxNorm' AND ing.concept_class_id='Ingredient'
                                 AND ing.concept_code=os.omop_rxcui
            WHERE coalesce(q.amount_base, q.ratio_base) IS NOT NULL)
        SELECT i.product_id,
               list_sort(list(DISTINCT i.ingredient_concept_id || ':' || round(i.value, 4))) AS fingerprint,
               count(DISTINCT i.ingredient_concept_id) AS ingredients
        FROM ing i GROUP BY 1""")
    # their side: the same fingerprint for every RxNorm / RxNorm Extension standard drug
    con.execute("""CREATE OR REPLACE TEMP TABLE their_fingerprint AS
        SELECT q.drug_concept_id,
               list_sort(list(DISTINCT q.ingredient_concept_id || ':' || round(coalesce(q.amount_base, q.ratio_base), 4))) AS fingerprint,
               count(DISTINCT q.ingredient_concept_id) AS ingredients
        FROM omop_quantity q JOIN omop_concept c ON c.concept_id=q.drug_concept_id AND c.standard_concept='S'
                              AND c.concept_class_id IN ('Clinical Drug','Quant Clinical Drug')
        WHERE coalesce(q.amount_base, q.ratio_base) IS NOT NULL GROUP BY 1""")
    # AMT names its dose form with a SNOMED concept and OMOP's drugs with an RxNorm one, and no relationship joins
    # the two, so the dose form cannot narrow the match. Instead the fingerprint must identify exactly ONE generic
    # drug in the whole vocabulary: where it does not, the strength alone is not evidence and nothing is written.
    con.execute("""CREATE OR REPLACE TEMP TABLE unique_fingerprint AS
        SELECT fingerprint, min(drug_concept_id) AS drug_concept_id
        FROM their_fingerprint GROUP BY 1 HAVING count(DISTINCT drug_concept_id)=1""")
    con.execute("""INSERT INTO omop_drug_indirect
        SELECT DISTINCT o.product_id, p.level, t.drug_concept_id, c.concept_name, c.vocabulary_id, 'strength match', NULL
        FROM our_fingerprint o
        JOIN unique_fingerprint t ON t.fingerprint=o.fingerprint
        JOIN product p ON p.id=o.product_id
        JOIN omop_concept c ON c.concept_id=t.drug_concept_id
        WHERE NOT EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=o.product_id AND d.standard_concept_id IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM omop_drug_indirect i WHERE i.product_id=o.product_id)""")

    # --- does either route reproduce the mappings we already have? ----------------------------------------------
    con.execute("""CREATE OR REPLACE TABLE omop_drug_indirect_check AS
        WITH generic_route AS (
            SELECT ug.tpuu_id AS product_id, 'generic' AS route, od.standard_concept_id AS proposed
            FROM unit_generic ug JOIN omop_drug od ON od.product_id=ug.mpuu_id AND od.standard_concept_id IS NOT NULL),
        strength_route AS (
            SELECT o.product_id, 'strength match' AS route, t.drug_concept_id AS proposed
            FROM our_fingerprint o JOIN unique_fingerprint t ON t.fingerprint=o.fingerprint)
        SELECT r.product_id, r.route, r.proposed, d.standard_concept_id AS actual,
               CASE WHEN r.proposed = d.standard_concept_id THEN 'same concept'
                    WHEN EXISTS (SELECT 1 FROM anc x WHERE x.a=r.proposed AND x.d=d.standard_concept_id)
                        THEN 'the generic of the direct concept'
                    WHEN EXISTS (SELECT 1 FROM anc x WHERE x.a=d.standard_concept_id AND x.d=r.proposed)
                        THEN 'more specific than the direct concept'
                    WHEN c1.concept_name = c2.concept_name THEN 'same name, different concept'
                    ELSE 'different' END AS verdict
        FROM (SELECT * FROM generic_route UNION ALL SELECT * FROM strength_route) r
        JOIN omop_drug d ON d.product_id=r.product_id AND d.standard_concept_id IS NOT NULL
        LEFT JOIN omop_concept c1 ON c1.concept_id=r.proposed
        LEFT JOIN omop_concept c2 ON c2.concept_id=d.standard_concept_id""")

    direct = con.execute("SELECT count(DISTINCT product_id) FROM omop_drug WHERE standard_concept_id IS NOT NULL").fetchone()[0]
    report = {
        "products_with_a_direct_mapping": direct,
        "added_by_route": dict(con.execute("SELECT route, count(DISTINCT product_id) FROM omop_drug_indirect GROUP BY 1").fetchall()),
        "added_by_level": dict(con.execute("SELECT level, count(DISTINCT product_id) FROM omop_drug_indirect GROUP BY 1 ORDER BY 2 DESC").fetchall()),
        "tpuu": {
            "total": con.execute("SELECT count(*) FROM product WHERE level='TPUU'").fetchone()[0],
            "direct": con.execute("SELECT count(*) FROM omop_drug WHERE level='TPUU' AND standard_concept_id IS NOT NULL").fetchone()[0],
            "with_the_indirect_routes": con.execute("""SELECT count(*) FROM product p WHERE p.level='TPUU'
                AND (EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=p.id AND d.standard_concept_id IS NOT NULL)
                  OR EXISTS (SELECT 1 FROM omop_drug_indirect i WHERE i.product_id=p.id))""").fetchone()[0],
        },
        "mpuu": {
            "total": con.execute("SELECT count(*) FROM product WHERE level='MPUU'").fetchone()[0],
            "direct": con.execute("SELECT count(*) FROM omop_drug WHERE level='MPUU' AND standard_concept_id IS NOT NULL").fetchone()[0],
            "with_the_indirect_routes": con.execute("""SELECT count(*) FROM product p WHERE p.level='MPUU'
                AND (EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=p.id AND d.standard_concept_id IS NOT NULL)
                  OR EXISTS (SELECT 1 FROM omop_drug_indirect i WHERE i.product_id=p.id))""").fetchone()[0],
        },
        "method_check_against_known_mappings": {
            r[0]: {v: n for v, n in con.execute(
                "SELECT verdict, count(*) FROM omop_drug_indirect_check WHERE route=? GROUP BY 1 ORDER BY 2 DESC", [r[0]]).fetchall()}
            for r in con.execute("SELECT DISTINCT route FROM omop_drug_indirect_check").fetchall()},
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
