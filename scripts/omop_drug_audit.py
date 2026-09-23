#!/usr/bin/env python3
"""Check every AMT product -> OMOP standard drug mapping against an INDEPENDENT witness of its ingredients.

`omop_drug` (and item 15's `omop_drug_indirect`) map each AMT product to one standard drug concept through OMOP's own
`Maps to`. That is the same mechanism that, at substance level, was right 40 of 40 when it kept the substance's name
and wrong 6 of 18 when it changed it -- tetanus antitoxin to tetanus toxoid vaccine among them. This asks whether the
product-level mappings carry the same failure.

**The witness must not be OMOP.** Checking OMOP's product mapping against OMOP's own substance mapping agrees with
itself: the 36 citrus-bioflavonoid products "matched" OMOP's strengths against *flavone* because OMOP made the same
choice twice. So the AMT side here is witnessed by RxNav (`rxnorm`, from scripts/rxnorm_resolve.py), which never
consulted OMOP. A precise ingredient (a salt) is lifted to its ingredient through RxNorm's `Form of`.

For each mapped product, compare W = the RxNav-witnessed standard ingredients of its AMT active substances with
S = the standard drug's ingredients (CONCEPT_ANCESTOR, ancestor class Ingredient). Packs take the union of the units
they contain.

    agrees (fully witnessed)                     every AMT ingredient witnessed, and W = S
    standard drug has extra ingredients          every AMT ingredient witnessed, W is a strict subset of S
    agrees on witnessed ingredients              some AMT ingredients have no RxNav witness; those that do are in S
    DISAGREES on a witnessed ingredient          some RxNav-witnessed ingredient is NOT in S   <- the failure sought
    no independent witness                       no AMT ingredient of this product was resolved by RxNav
    standard concept has no ingredient           OMOP's target carries no Ingredient ancestor

Writes `omop_drug_check`; prints the disagreements grouped by (AMT substance, OMOP ingredient) pair, because a
substance-level mis-mapping reappears in every product that uses it, and a person reviews the pair, not each row.

    scripts/omop_drug_audit.py [--vocab-dir ~/code/spine/out/omop-vocab] [--json out/omop_drug_audit.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    ap.add_argument("--json", default="out/omop_drug_audit.json")
    a = ap.parse_args()
    v = a.vocab_dir
    opts = "delim='\t', header=true, quote='', escape='', all_varchar=true"
    con = duckdb.connect(str(DB))
    con.execute(f"CREATE OR REPLACE TEMP VIEW C  AS SELECT * FROM read_csv('{v}/CONCEPT.csv', {opts})")
    con.execute(f"CREATE OR REPLACE TEMP VIEW CR AS SELECT * FROM read_csv('{v}/CONCEPT_RELATIONSHIP.csv', {opts})")
    con.execute(f"CREATE OR REPLACE TEMP VIEW CA AS SELECT * FROM read_csv('{v}/CONCEPT_ANCESTOR.csv', delim='\t', header=true, all_varchar=true)")

    # --- the mappings under audit: both OMOP routes, one row per (product, target) ----------------------------------
    con.execute("""CREATE OR REPLACE TEMP TABLE mapped AS
        SELECT product_id, level, 'omop_drug' AS source, CAST(standard_concept_id AS VARCHAR) AS std_id, standard_name
        FROM omop_drug WHERE standard_concept_id IS NOT NULL
        UNION ALL
        SELECT product_id, level, 'indirect:' || route, CAST(standard_concept_id AS VARCHAR), standard_name
        FROM omop_drug_indirect WHERE standard_concept_id IS NOT NULL""")

    # --- S: the standard drug's ingredients --------------------------------------------------------------------------
    con.execute("CREATE OR REPLACE TEMP TABLE targets AS SELECT DISTINCT std_id FROM mapped")
    con.execute("""CREATE OR REPLACE TEMP TABLE std_ing AS
        SELECT DISTINCT t.std_id, ca.ancestor_concept_id AS ing_id
        FROM targets t JOIN CA ca ON ca.descendant_concept_id = t.std_id
        JOIN C ing ON ing.concept_id = ca.ancestor_concept_id
        WHERE ing.concept_class_id = 'Ingredient' AND ing.standard_concept = 'S'""")

    # --- W: RxNav's witness per substance, lifted from precise ingredient to ingredient -------------------------------
    con.execute("""CREATE OR REPLACE TEMP TABLE witness AS
        WITH rx AS (
            SELECT r.substance_id, c.concept_id, c.concept_class_id
            FROM rxnorm r JOIN C c ON c.concept_code = r.rxcui_ingredient AND c.vocabulary_id = 'RxNorm'
            WHERE r.rxcui_ingredient IS NOT NULL AND r.rxnorm_tty IN ('IN', 'PIN'))
        SELECT substance_id, concept_id AS ing_id FROM rx WHERE concept_class_id = 'Ingredient'
        UNION
        SELECT rx.substance_id, cr.concept_id_2 FROM rx
        JOIN CR cr ON cr.concept_id_1 = rx.concept_id AND cr.relationship_id = 'Form of'
                  AND (cr.invalid_reason IS NULL OR cr.invalid_reason = '')
        WHERE rx.concept_class_id = 'Precise Ingredient'""")

    # --- the AMT side: active substances per unit; packs take the union of their units --------------------------------
    con.execute("""CREATE OR REPLACE TEMP TABLE amt_sub AS
        SELECT DISTINCT product_id, coalesce(active_substance_id, precise_substance_id) AS substance_id
        FROM ingredient WHERE coalesce(active_substance_id, precise_substance_id) IS NOT NULL
        UNION
        SELECT DISTINCT c.package_id, coalesce(i.active_substance_id, i.precise_substance_id)
        FROM contains c JOIN ingredient i ON i.product_id = c.unit_id
        WHERE coalesce(i.active_substance_id, i.precise_substance_id) IS NOT NULL""")

    # --- per product: what is witnessed, and is it in S? --------------------------------------------------------------
    con.execute("""CREATE OR REPLACE TEMP TABLE per_sub AS
        SELECT m.product_id, m.level, m.source, m.std_id, a.substance_id,
               bool_or(w.ing_id IS NOT NULL) AS witnessed,
               bool_or(s.ing_id IS NOT NULL) AS in_std
        FROM mapped m JOIN amt_sub a ON a.product_id = m.product_id
        LEFT JOIN witness w ON w.substance_id = a.substance_id
        LEFT JOIN std_ing s ON s.std_id = m.std_id AND s.ing_id = w.ing_id
        GROUP BY 1, 2, 3, 4, 5""")
    con.execute("""CREATE OR REPLACE TABLE omop_drug_check AS
        WITH agg AS (
            SELECT product_id, level, source, std_id,
                   count(*) AS amt_ingredients,
                   count(*) FILTER (WHERE witnessed) AS witnessed,
                   count(*) FILTER (WHERE witnessed AND NOT in_std) AS witnessed_not_in_std
            FROM per_sub GROUP BY 1, 2, 3, 4),
        ns AS (SELECT std_id, count(*) AS std_ingredients FROM std_ing GROUP BY 1)
        SELECT m.product_id, m.level, m.source, m.std_id AS standard_concept_id, m.standard_name,
               coalesce(g.amt_ingredients, 0) AS amt_ingredients, coalesce(g.witnessed, 0) AS witnessed,
               coalesce(g.witnessed_not_in_std, 0) AS witnessed_not_in_std,     -- = witnessed: nothing shared at all
               coalesce(ns.std_ingredients, 0) AS std_ingredients,
               CASE WHEN ns.std_ingredients IS NULL                          THEN 'standard concept has no ingredient'
                    WHEN coalesce(g.witnessed, 0) = 0                        THEN 'no independent witness'
                    WHEN g.witnessed_not_in_std > 0                          THEN 'DISAGREES on a witnessed ingredient'
                    WHEN g.witnessed = g.amt_ingredients AND g.amt_ingredients = ns.std_ingredients
                                                                             THEN 'agrees (fully witnessed)'
                    WHEN g.witnessed = g.amt_ingredients                     THEN 'standard drug has extra ingredients'
                    ELSE 'agrees on witnessed ingredients' END AS verdict
        FROM mapped m LEFT JOIN agg g USING (product_id, level, source, std_id)
        LEFT JOIN ns ON ns.std_id = m.std_id""")

    summary = {v: n for v, n in con.execute("SELECT verdict, count(*) FROM omop_drug_check GROUP BY 1 ORDER BY 2 DESC").fetchall()}
    by_source = {}
    for src, verdict, n in con.execute("SELECT source, verdict, count(*) FROM omop_drug_check GROUP BY 1, 2 ORDER BY 1, 3 DESC").fetchall():
        by_source.setdefault(src, {})[verdict] = n
    # the disagreements, as (AMT substance -> what OMOP's drug has instead) pairs
    pairs = con.execute("""
        WITH bad AS (SELECT p.* FROM per_sub p JOIN omop_drug_check c
                       ON c.product_id = p.product_id AND c.source = p.source AND c.standard_concept_id = p.std_id
                     WHERE c.verdict = 'DISAGREES on a witnessed ingredient' AND p.witnessed AND NOT p.in_std),
             omop_side AS (SELECT DISTINCT b.product_id, b.std_id, b.substance_id, ci.concept_name AS omop_ing
                           FROM bad b JOIN std_ing s ON s.std_id = b.std_id JOIN C ci ON ci.concept_id = s.ing_id
                           WHERE s.ing_id NOT IN (SELECT w.ing_id FROM witness w JOIN amt_sub a2 ON a2.substance_id = w.substance_id
                                                  WHERE a2.product_id = b.product_id))
        SELECT sub.substance, any_value(cw.concept_name) AS rxnav_says, string_agg(DISTINCT o.omop_ing, ' + ') AS omop_drug_has,
               count(DISTINCT b.product_id) AS products,
               count(DISTINCT b.product_id) FILTER (WHERE b.level IN ('TPUU','MPUU','TPP','CTPP','MPP')) AS real_products
        FROM bad b JOIN substance sub ON sub.substance_id = b.substance_id
        JOIN witness w ON w.substance_id = b.substance_id JOIN C cw ON cw.concept_id = w.ing_id
        LEFT JOIN omop_side o ON o.product_id = b.product_id AND o.std_id = b.std_id AND o.substance_id = b.substance_id
        GROUP BY 1 ORDER BY products DESC""").fetchall()
    con.close()
    out = {"verdicts": summary, "by_source": by_source,
           "disagreeing_substance_pairs": len(pairs),
           "pairs": [{"amt_substance": p[0], "rxnav_says": p[1], "omop_drug_has": p[2], "products": p[3],
                      "real_products": p[4]} for p in pairs]}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("verdicts", "by_source", "disagreeing_substance_pairs")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
