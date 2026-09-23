#!/usr/bin/env python3
"""AMT ingredient strengths, and what OMOP's DRUG_STRENGTH says about the same products.

AMT records a product's strength as *concrete values* inside its OWL axiom — `DataHasValue(:1142135004
"12"^^xsd:decimal)` — not as relationships, so the RF2 relationship file (and therefore the compendium's `rel`
table) does not carry them at all. This script reads them out of the OWL expression refset into a `strength` table,
then checks them against OMOP's DRUG_STRENGTH through the AMT -> RxNorm bridge the compendium already holds
(`omop_drug`), which is the only route: the Athena bundle carries 2,966,568 strength rows and **none** of them are
AMT (RxNorm Extension 2,756,719 and RxNorm 209,849).

    scripts/drug_strength.py extract [--rf2 <snapshot dir>]
    scripts/drug_strength.py validate [--vocab-dir ~/code/spine/out/omop-vocab]

Both phases are offline and write only into out/compendium.duckdb.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT",
                     "/Users/ken-lee-arepo/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/Snapshot")
DB = Path("out/compendium.duckdb")
ROLE_GROUP = "609096000"
BOSS, PRECISE = "732943007", "762949000"
# (numerator value, numerator unit, denominator value, denominator unit) per strength style
STYLES = {
    "presentation": ("1142135004", "732945000", "1142136003", "732947008"),
    "concentration": ("1142138002", "733725009", "1142137007", "733722007"),
    # the AU extension's own pair, used by the older AMT concepts: a value and its unit, no denominator
    "concentration_au": ("999000021000168100", "999000031000168102", None, None),
    "total_quantity": ("999000041000168106", "999000051000168108", None, None),
}
DATA = re.compile(r'DataHasValue\(:(\d+) "([^"]+)"\^\^xsd:\w+\)')
OBJ = re.compile(r"ObjectSomeValuesFrom\(:(\d+) :(\d+)\)")


def _groups(expression: str):
    """Every role group in an axiom, as its inner text (parenthesis-balanced, so nested groups survive)."""
    marker = f"ObjectSomeValuesFrom(:{ROLE_GROUP} ObjectIntersectionOf("
    i = expression.find(marker)
    while i >= 0:
        depth, j = 1, i + len(marker)
        while j < len(expression) and depth:
            depth += (expression[j] == "(") - (expression[j] == ")")
            j += 1
        yield expression[i + len(marker):j - 1]
        i = expression.find(marker, j)


def extract(rf2: str, log=print) -> dict:
    owl = glob.glob(os.path.join(rf2, "Terminology", "sct2_sRefset_OWLExpression*.txt"))
    if not owl:
        raise SystemExit(f"no OWL expression refset under {rf2}/Terminology")
    rows, seen_products = [], set()
    with open(owl[0], encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7 or f[2] != "1":
                continue
            product, expression = f[5], f[6]
            for n, inner in enumerate(_groups(expression), 1):
                objects = dict(OBJ.findall(inner))
                values = dict(DATA.findall(inner))
                boss = objects.get(BOSS)
                if not boss:
                    continue
                for style, (nv, nu, dv, du) in STYLES.items():
                    if nv in values:
                        rows.append((product, n, style, boss, objects.get(PRECISE),
                                     float(values[nv]), objects.get(nu),
                                     float(values[dv]) if dv and dv in values else None,
                                     objects.get(du) if du else None))
                        seen_products.add(product)
    con = duckdb.connect(str(DB))
    con.execute("""CREATE OR REPLACE TABLE strength (
        product_id VARCHAR, grp INTEGER, style VARCHAR, boss_substance_id VARCHAR, precise_substance_id VARCHAR,
        numerator_value DOUBLE, numerator_unit_id VARCHAR, denominator_value DOUBLE, denominator_unit_id VARCHAR)""")
    con.executemany("INSERT INTO strength VALUES (?,?,?,?,?,?,?,?,?)", rows)
    by_style = dict(con.execute("SELECT style, count(*) FROM strength GROUP BY 1 ORDER BY 2 DESC").fetchall())
    known = con.execute("SELECT count(DISTINCT s.product_id) FROM strength s JOIN product p ON p.id=s.product_id").fetchone()[0]
    log(f"strength: {len(rows):,} rows for {len(seen_products):,} concepts ({known:,} of them products in this compendium); by style {by_style}")
    con.close()
    return {"rows": len(rows), "concepts": len(seen_products), "products": known, "by_style": by_style}


def validate(vocab_dir: str, log=print) -> dict:
    concept_csv = os.path.join(vocab_dir, "CONCEPT.csv")
    rel_csv = os.path.join(vocab_dir, "CONCEPT_RELATIONSHIP.csv")
    ds_csv = os.path.join(vocab_dir, "DRUG_STRENGTH.csv")
    for f in (concept_csv, rel_csv, ds_csv):
        if not os.path.exists(f) or os.path.getsize(f) < 1_000_000:
            raise SystemExit(f"{f} missing or a stub — install an Athena bundle first (spine omop vocab --athena <zip>)")
    opts = "delim='\\t', header=true, quote='', escape='', nullstr='', all_varchar=true"
    con = duckdb.connect(str(DB))
    con.execute(f"""CREATE OR REPLACE TEMP TABLE omop_concept AS SELECT CAST(concept_id AS BIGINT) concept_id, concept_name,
                    vocabulary_id, concept_class_id, standard_concept, concept_code FROM read_csv('{concept_csv}', {opts})""")
    # the strengths of every OMOP drug the compendium's products map to
    con.execute(f"""CREATE OR REPLACE TABLE omop_strength AS
        SELECT CAST(d.drug_concept_id AS BIGINT) drug_concept_id, CAST(d.ingredient_concept_id AS BIGINT) ingredient_concept_id,
               TRY_CAST(d.amount_value AS DOUBLE) amount_value, CAST(NULLIF(d.amount_unit_concept_id,'0') AS BIGINT) amount_unit_concept_id,
               TRY_CAST(d.numerator_value AS DOUBLE) numerator_value, CAST(NULLIF(d.numerator_unit_concept_id,'0') AS BIGINT) numerator_unit_concept_id,
               TRY_CAST(d.denominator_value AS DOUBLE) denominator_value, CAST(NULLIF(d.denominator_unit_concept_id,'0') AS BIGINT) denominator_unit_concept_id
        FROM read_csv('{ds_csv}', {opts}) d
        WHERE d.invalid_reason IS NULL
          AND CAST(d.drug_concept_id AS BIGINT) IN (SELECT standard_concept_id FROM omop_drug WHERE standard_concept_id IS NOT NULL)""")
    # AMT's unit concepts are SNOMED; OMOP's are UCUM. The bridge is the SNOMED unit concept's own `Maps to`.
    con.execute(f"""CREATE OR REPLACE TABLE unit_bridge AS
        WITH amt_units AS (SELECT DISTINCT numerator_unit_id AS unit FROM strength WHERE numerator_unit_id IS NOT NULL
                           UNION SELECT DISTINCT denominator_unit_id FROM strength WHERE denominator_unit_id IS NOT NULL),
             sct AS (SELECT u.unit, c.concept_id, c.concept_name FROM amt_units u
                     JOIN omop_concept c ON c.vocabulary_id='SNOMED' AND c.concept_code=u.unit),
             maps AS (SELECT CAST(concept_id_1 AS BIGINT) s, CAST(concept_id_2 AS BIGINT) t
                      FROM read_csv('{rel_csv}', {opts}) WHERE relationship_id='Maps to' AND invalid_reason IS NULL
                        AND CAST(concept_id_1 AS BIGINT) IN (SELECT concept_id FROM sct))
        SELECT sct.unit AS amt_unit_id, sct.concept_name AS amt_unit_name, t.concept_id AS omop_unit_concept_id,
               t.concept_name AS omop_unit_name, t.vocabulary_id AS omop_unit_vocabulary
        FROM sct LEFT JOIN maps ON maps.s=sct.concept_id LEFT JOIN omop_concept t ON t.concept_id=maps.t""")
    # Both sides state the same fact in different normalisations: AMT gives a pack total ("1 mg vial") or a
    # concentration ("6 mg/mL"), OMOP gives amount_value, or numerator over denominator ("30 mg / 5 mL"). Comparing
    # the raw numbers calls 30 different from 6. So both sides are reduced to base units (mass in mg, volume in mL,
    # activity in units) and compared as a total AND as a ratio; anything whose unit is outside the table is
    # reported as not comparable rather than as a disagreement.
    con.execute("""CREATE OR REPLACE TABLE unit_factor (unit VARCHAR, base VARCHAR, factor DOUBLE)""")
    con.executemany("INSERT INTO unit_factor VALUES (?,?,?)", [
        ("ng", "mass", 1e-6), ("mcg", "mass", 1e-3), ("ug", "mass", 1e-3), ("microgram", "mass", 1e-3),
        ("mg", "mass", 1.0), ("milligram", "mass", 1.0), ("g", "mass", 1000.0), ("gram", "mass", 1000.0),
        ("uL", "volume", 1e-3), ("microliter", "volume", 1e-3), ("mL", "volume", 1.0), ("milliliter", "volume", 1.0),
        ("L", "volume", 1000.0), ("liter", "volume", 1000.0),
        ("Unit", "activity", 1.0), ("unit", "activity", 1.0), ("IU", "activity", 1.0), ("international unit", "activity", 1.0),
        ("Million unit", "activity", 1e6), ("Million international units", "activity", 1e6), ("mmol", "amount", 1.0), ("millimole", "amount", 1.0)])
    # the AMT side: unit names as AMT spells them, split on "/" for the compound ones
    con.execute("""CREATE OR REPLACE TABLE amt_quantity AS
        WITH named AS (
            SELECT s.product_id, s.style, s.boss_substance_id, s.numerator_value AS value,
                   (SELECT pt FROM concept WHERE id=s.numerator_unit_id) AS unit_name,
                   s.denominator_value, (SELECT pt FROM concept WHERE id=s.denominator_unit_id) AS den_unit_name
            FROM strength s),
        split AS (
            SELECT *, CASE WHEN unit_name LIKE '%/%' THEN split_part(unit_name,'/',1) ELSE unit_name END AS num_unit,
                      CASE WHEN unit_name LIKE '%/%' THEN split_part(unit_name,'/',2) ELSE den_unit_name END AS den_unit
            FROM named)
        SELECT sp.product_id, sp.style, sp.boss_substance_id,
               sp.value * nf.factor AS amount_base, nf.base AS amount_base_unit,
               CASE WHEN df.factor IS NOT NULL AND coalesce(sp.denominator_value,1)<>0
                    THEN sp.value*nf.factor/(coalesce(sp.denominator_value,1)*df.factor) END AS ratio_base,
               df.base AS per_base_unit, sp.unit_name
        FROM split sp LEFT JOIN unit_factor nf ON nf.unit=sp.num_unit LEFT JOIN unit_factor df ON df.unit=sp.den_unit""")
    # the OMOP side: unit concepts resolved to their UCUM-ish names, then the same reduction
    con.execute("""CREATE OR REPLACE TABLE omop_quantity AS
        WITH named AS (
            SELECT o.drug_concept_id, o.ingredient_concept_id,
                   coalesce(o.amount_value, o.numerator_value) AS value,
                   (SELECT concept_name FROM omop_concept c WHERE c.concept_id=coalesce(o.amount_unit_concept_id,o.numerator_unit_concept_id)) AS unit_name,
                   o.denominator_value,
                   (SELECT concept_name FROM omop_concept c WHERE c.concept_id=o.denominator_unit_concept_id) AS den_unit_name
            FROM omop_strength o)
        SELECT n.drug_concept_id, n.ingredient_concept_id, n.value*nf.factor AS amount_base, nf.base AS amount_base_unit,
               CASE WHEN df.factor IS NOT NULL AND coalesce(n.denominator_value,1)<>0
                    THEN n.value*nf.factor/(coalesce(n.denominator_value,1)*df.factor) END AS ratio_base,
               df.base AS per_base_unit, n.unit_name
        FROM named n LEFT JOIN unit_factor nf ON nf.unit=n.unit_name LEFT JOIN unit_factor df ON df.unit=n.den_unit_name""")
    con.execute("""CREATE OR REPLACE TABLE strength_check AS
        WITH ours AS (
            SELECT a.product_id, od.standard_concept_id AS drug_concept_id, a.style, a.boss_substance_id,
                   a.amount_base, a.amount_base_unit, a.ratio_base, a.unit_name AS amt_unit,
                   ing.concept_id AS our_ingredient_concept, os2.omop_rxnorm_name AS our_ingredient_name
            FROM amt_quantity a
            JOIN omop_drug od ON od.product_id=a.product_id AND od.standard_concept_id IS NOT NULL
            LEFT JOIN omop_substance os2 ON os2.substance_id=a.boss_substance_id AND os2.review_status IS NULL
            LEFT JOIN omop_concept ing ON ing.vocabulary_id='RxNorm' AND ing.concept_class_id='Ingredient'
                                      AND ing.concept_code=os2.omop_rxcui)
        SELECT o.*, t.amount_base AS omop_amount_base, t.ratio_base AS omop_ratio_base, t.unit_name AS omop_unit,
               CASE WHEN o.our_ingredient_concept IS NULL THEN 'ingredient not bridged to RxNorm'
                    WHEN t.ingredient_concept_id IS NULL THEN 'ingredient absent from OMOP strength'
                    WHEN o.amount_base IS NULL AND o.ratio_base IS NULL THEN 'AMT unit outside the factor table'
                    WHEN t.amount_base IS NULL AND t.ratio_base IS NULL THEN 'OMOP unit outside the factor table'
                    WHEN abs(coalesce(o.amount_base,-1) - coalesce(t.amount_base,-2)) <= 0.005*greatest(abs(coalesce(o.amount_base,1)), abs(coalesce(t.amount_base,1))) THEN 'same total'
                    WHEN o.ratio_base IS NOT NULL AND t.ratio_base IS NOT NULL
                         AND abs(o.ratio_base - t.ratio_base) <= 0.005*greatest(abs(o.ratio_base), abs(t.ratio_base)) THEN 'same concentration'
                    WHEN o.amount_base IS NOT NULL AND t.ratio_base IS NOT NULL
                         AND abs(o.amount_base - t.ratio_base) <= 0.005*greatest(abs(o.amount_base), abs(t.ratio_base)) THEN 'same concentration'
                    WHEN o.ratio_base IS NOT NULL AND t.amount_base IS NOT NULL
                         AND abs(o.ratio_base - t.amount_base) <= 0.005*greatest(abs(o.ratio_base), abs(t.amount_base)) THEN 'same concentration'
                    -- a clean power of ten between the two is a normalisation difference (per litre against per
                    -- millilitre, gram against milligram), not a disagreement about the medicine
                    WHEN abs(coalesce(o.amount_base,o.ratio_base)/nullif(coalesce(t.amount_base,t.ratio_base),0)) > 0
                         AND abs(log(10, abs(coalesce(o.amount_base,o.ratio_base)/nullif(coalesce(t.amount_base,t.ratio_base),0)))
                                 - round(log(10, abs(coalesce(o.amount_base,o.ratio_base)/nullif(coalesce(t.amount_base,t.ratio_base),0))))) < 0.001
                         AND round(log(10, abs(coalesce(o.amount_base,o.ratio_base)/nullif(coalesce(t.amount_base,t.ratio_base),0)))) <> 0
                        THEN 'differs by a power of ten'
                    WHEN abs(coalesce(o.amount_base,o.ratio_base) - coalesce(t.amount_base,t.ratio_base))
                         <= 0.05*greatest(abs(coalesce(o.amount_base,o.ratio_base)), abs(coalesce(t.amount_base,t.ratio_base)))
                        THEN 'within five per cent'
                    ELSE 'different' END AS verdict
        FROM ours o LEFT JOIN omop_quantity t ON t.drug_concept_id=o.drug_concept_id AND t.ingredient_concept_id=o.our_ingredient_concept""")
    report = {
        "omop_strength_rows_for_our_drugs": con.execute("SELECT count(*) FROM omop_strength").fetchone()[0],
        "units_bridged": con.execute("SELECT count(*) FILTER (WHERE omop_unit_concept_id IS NOT NULL), count(*) FROM unit_bridge").fetchone(),
        "pairs_checked": con.execute("SELECT count(*) FROM strength_check").fetchone()[0],
        "products_checked": con.execute("SELECT count(DISTINCT product_id) FROM strength_check").fetchone()[0],
        "verdict": dict(con.execute("SELECT verdict, count(*) FROM strength_check GROUP BY 1 ORDER BY 2 DESC").fetchall()),
        "verdict_by_style": {f"{r[0]} / {r[1]}": r[2] for r in con.execute(
            "SELECT style, verdict, count(*) FROM strength_check GROUP BY 1,2 ORDER BY 1,3 DESC").fetchall()},
    }
    con.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("--rf2", default=RF2)
    v = sub.add_parser("validate"); v.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    a = ap.parse_args()
    import json
    print(json.dumps(extract(a.rf2) if a.cmd == "extract" else validate(a.vocab_dir), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
