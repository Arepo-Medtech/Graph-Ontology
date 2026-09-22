#!/usr/bin/env python3
"""ATC classes for every AMT product — from the PBS listing where there is one, and from OMOP for the rest.

The compendium already knows the ATC class of a **PBS-listed item** (6,844 item-to-ATC rows from the PBS schedule).
That leaves every product the PBS does not list — private, over-the-counter, hospital-only — with no class at all,
which is most of the compendium. OMOP's vocabulary carries the whole ATC classification rolled up over RxNorm and
RxNorm Extension in CONCEPT_ANCESTOR (10.2 M rows), so a product that reaches a standard drug concept through
`omop_drug` can be classified that way instead.

Both routes are written, tagged with their source, and compared where they overlap: the PBS assigns one ATC to a
listed item by its own rules, and OMOP classifies the substance, so they can legitimately differ (a combination
product, a different indication). The comparison says how often, and where.

    scripts/atc_bridge.py [--vocab-dir ~/code/spine/out/omop-vocab]

Offline; writes `atc`, `product_atc` and `product_atc_check` into out/compendium.duckdb.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
LEVEL_OF = {"ATC 1st": 1, "ATC 2nd": 2, "ATC 3rd": 3, "ATC 4th": 4, "ATC 5th": 5}


def build(vocab_dir: str, log=print) -> dict:
    concept_csv = os.path.join(vocab_dir, "CONCEPT.csv")
    ancestor_csv = os.path.join(vocab_dir, "CONCEPT_ANCESTOR.csv")
    for f in (concept_csv, ancestor_csv):
        if not os.path.exists(f) or os.path.getsize(f) < 1_000_000:
            raise SystemExit(f"{f} missing or a stub — install an Athena bundle first, with CONCEPT_ANCESTOR "
                             f"(spine omop vocab --athena <zip> --full)")
    opts = "delim='\\t', header=true, quote='', escape='', nullstr='', all_varchar=true"
    con = duckdb.connect(str(DB))
    con.execute(f"""CREATE OR REPLACE TABLE atc AS
        SELECT CAST(concept_id AS BIGINT) AS concept_id, concept_code AS atc_code, concept_name AS atc_name,
               concept_class_id AS atc_class,
               CASE concept_class_id {' '.join(f"WHEN '{k}' THEN {v}" for k, v in LEVEL_OF.items())} END AS atc_level,
               invalid_reason
        FROM read_csv('{concept_csv}', {opts}) WHERE vocabulary_id='ATC'""")
    log(f"atc: {con.execute('SELECT count(*) FROM atc').fetchone()[0]:,} concepts "
        f"{dict(con.execute('SELECT atc_class, count(*) FROM atc GROUP BY 1 ORDER BY 2 DESC').fetchall())}")

    # the OMOP route: product -> standard drug concept -> its ATC ancestors. The ancestor table is 1.6 GB, so the
    # scan is filtered to the drug concepts this compendium actually maps to.
    con.execute(f"""CREATE OR REPLACE TEMP TABLE drug_atc AS
        SELECT CAST(ca.descendant_concept_id AS BIGINT) AS drug_concept_id, a.atc_code, a.atc_name, a.atc_level
        FROM read_csv('{ancestor_csv}', {opts}) ca
        JOIN atc a ON a.concept_id=CAST(ca.ancestor_concept_id AS BIGINT)
        WHERE CAST(ca.descendant_concept_id AS BIGINT) IN (SELECT standard_concept_id FROM omop_drug WHERE standard_concept_id IS NOT NULL)""")
    con.execute("""CREATE OR REPLACE TABLE product_atc AS
        SELECT DISTINCT od.product_id, d.atc_code, d.atc_name, d.atc_level, 'omop' AS source
        FROM omop_drug od JOIN drug_atc d ON d.drug_concept_id=od.standard_concept_id
        WHERE od.standard_concept_id IS NOT NULL""")
    # the PBS route: the schedule's own ATC for a listed item, attached to whatever AMT concept the item names
    con.execute("""INSERT INTO product_atc
        SELECT DISTINCT p.amt_code, ia.atc_code, coalesce(a.atc_name, ac.atc_description), coalesce(a.atc_level, ac.atc_level), 'pbs'
        FROM pbs p JOIN pbs_item_atc ia ON ia.pbs_code=p.pbs_code
        LEFT JOIN atc a ON a.atc_code=ia.atc_code
        LEFT JOIN pbs_atc_code ac ON ac.atc_code=ia.atc_code
        WHERE p.amt_code IS NOT NULL AND EXISTS (SELECT 1 FROM product pr WHERE pr.id=p.amt_code)""")
    # a listed item usually names a pack (MPP/TPP 14,805 each, MPUU 15,167, TPUU only 753); the ATC of a pack
    # belongs to the units inside it, so it is carried down one hop through `contains`
    con.execute("""INSERT INTO product_atc
        SELECT DISTINCT co.unit_id, pa.atc_code, pa.atc_name, pa.atc_level, 'pbs'
        FROM product_atc pa JOIN contains co ON co.package_id=pa.product_id
        WHERE pa.source='pbs'
          AND NOT EXISTS (SELECT 1 FROM product_atc x WHERE x.product_id=co.unit_id AND x.atc_code=pa.atc_code AND x.source='pbs')""")
    # and from a containerised pack to the pack it contains
    con.execute("""INSERT INTO product_atc
        SELECT DISTINCT ct.tpp_id, pa.atc_code, pa.atc_name, pa.atc_level, 'pbs'
        FROM product_atc pa JOIN ctpp_tpp ct ON ct.ctpp_id=pa.product_id
        WHERE pa.source='pbs'
          AND NOT EXISTS (SELECT 1 FROM product_atc x WHERE x.product_id=ct.tpp_id AND x.atc_code=pa.atc_code AND x.source='pbs')""")
    counts = dict(con.execute("SELECT source, count(*) FROM product_atc GROUP BY 1").fetchall())
    log(f"product_atc: {counts}")

    # where both routes speak, do they agree? compared at the 5th level and, failing that, at the 4th
    con.execute("""CREATE OR REPLACE TABLE product_atc_check AS
        WITH pbs5 AS (SELECT product_id, atc_code FROM product_atc WHERE source='pbs' AND atc_level=5),
             omop5 AS (SELECT product_id, atc_code FROM product_atc WHERE source='omop' AND atc_level=5)
        SELECT p.product_id,
               list_sort(list_distinct(list(DISTINCT p.atc_code))) AS pbs_atc,
               list_sort(list_distinct(list(DISTINCT o.atc_code))) AS omop_atc,
               bool_or(p.atc_code = o.atc_code) AS same_fifth,
               bool_or(substr(p.atc_code,1,5) = substr(o.atc_code,1,5)) AS same_fourth,
               bool_or(substr(p.atc_code,1,4) = substr(o.atc_code,1,4)) AS same_third
        FROM pbs5 p JOIN omop5 o ON o.product_id=p.product_id GROUP BY 1""")
    both = con.execute("SELECT count(*) FROM product_atc_check").fetchone()[0]
    report = {
        "atc_concepts": con.execute("SELECT count(*) FROM atc").fetchone()[0],
        "products_with_an_atc": con.execute("SELECT count(DISTINCT product_id) FROM product_atc").fetchone()[0],
        "by_source": {s: con.execute(f"SELECT count(DISTINCT product_id) FROM product_atc WHERE source='{s}'").fetchone()[0]
                      for s in ("pbs", "omop")},
        "products_only_omop_can_classify": con.execute(
            "SELECT count(DISTINCT product_id) FROM product_atc o WHERE source='omop' "
            "AND NOT EXISTS (SELECT 1 FROM product_atc p WHERE p.product_id=o.product_id AND p.source='pbs')").fetchone()[0],
        "tpuu_coverage": con.execute("SELECT count(DISTINCT pa.product_id) FROM product_atc pa JOIN product p ON p.id=pa.product_id WHERE p.level='TPUU'").fetchone()[0],
        "tpuu_total": con.execute("SELECT count(*) FROM product WHERE level='TPUU'").fetchone()[0],
        "both_routes": both,
        "agreement": {
            "same ATC 5th": con.execute("SELECT count(*) FROM product_atc_check WHERE same_fifth").fetchone()[0],
            "same 4th level only": con.execute("SELECT count(*) FROM product_atc_check WHERE NOT same_fifth AND same_fourth").fetchone()[0],
            "same 3rd level only": con.execute("SELECT count(*) FROM product_atc_check WHERE NOT same_fourth AND same_third").fetchone()[0],
            "different": con.execute("SELECT count(*) FROM product_atc_check WHERE NOT same_third").fetchone()[0],
        } if both else {},
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
