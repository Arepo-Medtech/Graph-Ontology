#!/usr/bin/env python3
"""Re-apply human decisions and route resolutions after a build: substance -> standard ingredient.

A build rewrites `out/compendium.duckdb` wholesale from the resolver's cache. Without this step every review
decision and every checked route resolution would be silently discarded by the next build -- the same failure
`scripts/apply_corrections.py` prevents for SNOMED bindings. Run it after every build.

Writes one table, `substance_standard_ingredient`, one row per (substance, standard ingredient):

    substance_id  code  vocabulary  name  source  tier  state  check

Precedence, highest first; every row says which won:

    decision   reference/rxnorm_substance_decisions.json   a person chose (corrected_pending_attestation / attested)
    route      reference/rxnorm_route_resolutions.json     a scored route, status 'accepted' only
    resolver   the build's `rxnorm` table                  RxNav, via scripts/rxnorm_resolve.py

**Why a new table rather than the `rxnorm` table.** `rxnorm.rxcui_ingredient` holds genuine RxCUIs only (0 of
4,530 rows are OMOP codes). 144 of the 153 route resolutions are RxNorm Extension concepts -- that is exactly why
RxNav could not find them -- and an `OMOP...` code in an RxCUI column would break its type for every consumer.
Here the vocabulary is a column, so both kinds sit side by side without either pretending to be the other.

**Refuses to write** a decision or route target that is not a standard, valid Ingredient in the Athena bundle.

    scripts/apply_standard_ingredients.py [--vocab-dir ~/code/spine/out/omop-vocab]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
DECISIONS = Path("reference/rxnorm_substance_decisions.json")
ROUTES = Path("reference/rxnorm_route_resolutions.json")
OMOP_REVIEW = Path("reference/omop_substance_review.json")


def standard_ingredients(vocab_dir: str, codes: set[tuple[str, str]]) -> dict:
    """(code, vocabulary) -> (concept_id, name) for those that are standard, valid Ingredients."""
    if not codes:
        return {}
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE want(code VARCHAR, vocab VARCHAR)")
    con.executemany("INSERT INTO want VALUES (?, ?)", sorted(codes))
    rows = con.execute(f"""
        SELECT c.concept_code, c.vocabulary_id, c.concept_id, c.concept_name
        FROM read_csv('{os.path.join(vocab_dir, 'CONCEPT.csv')}', delim='\t', header=true, quote='', escape='',
                      all_varchar=true) c
        JOIN want w ON w.code = c.concept_code AND w.vocab = c.vocabulary_id
        WHERE c.concept_class_id = 'Ingredient' AND c.standard_concept = 'S'
          AND (c.invalid_reason IS NULL OR c.invalid_reason = '')""").fetchall()
    return {(r[0], r[1]): (r[2], r[3]) for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    a = ap.parse_args()

    decisions = json.load(open(DECISIONS))["decisions"]
    routes = json.load(open(ROUTES))["resolutions"]
    chosen = [(d["substance_id"], d["rxcui"], d["vocabulary"], "decision", None, d["state"], "decided by review")
              for d in decisions if d.get("rxcui") and d["state"] != "rejected"]
    decided = {d["substance_id"] for d in decisions}           # a rejection is still a decision: no route row
    chosen += [(r["substance_id"], r["rxcui"], r["vocabulary"], f"route:{r['route']}", r["route_tier"], "asserted",
                r["check"]) for r in routes if r["status"] == "accepted" and r["substance_id"] not in decided]

    valid = standard_ingredients(a.vocab_dir, {(c[1], c[2]) for c in chosen})
    bad = [c for c in chosen if (c[1], c[2]) not in valid]
    if bad:
        for c in bad:
            print(f"REFUSED {c[0]} -> {c[1]} ({c[2]}): not a standard valid Ingredient", file=sys.stderr)
        return 1

    con = duckdb.connect(str(DB))
    con.execute("""CREATE OR REPLACE TABLE substance_standard_ingredient (
        substance_id VARCHAR, code VARCHAR, concept_id VARCHAR, vocabulary VARCHAR, name VARCHAR,
        source VARCHAR, tier VARCHAR, state VARCHAR, "check" VARCHAR)""")
    overlaid = {c[0] for c in chosen}
    con.executemany("INSERT INTO substance_standard_ingredient VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(s, code, valid[(code, v)][0], v, valid[(code, v)][1], src, tier, state, chk)
                     for s, code, v, src, tier, state, chk in chosen])
    # the resolver's links, for every substance nothing above has spoken for
    resolver = con.execute("SELECT substance_id, rxcui_ingredient, rxnorm_name, source, rxnorm_tty FROM rxnorm "
                           "WHERE substance_id IS NOT NULL AND rxcui_ingredient IS NOT NULL").fetchall()
    superseded = [r for r in resolver if r[0] in overlaid]
    con.executemany("INSERT INTO substance_standard_ingredient VALUES (?, ?, NULL, 'RxNorm', ?, ?, NULL, 'asserted', ?)",
                    [(s, rx, nm, f"resolver:{src}", f"RxNav ({tty})") for s, rx, nm, src, tty in resolver
                     if s not in overlaid])
    # mark OMOP's own substance answers where review has objected, so readers that build product edges skip them
    review = json.load(open(OMOP_REVIEW))["review"] if OMOP_REVIEW.exists() else []
    status = {x["substance_id"]: "flagged" for x in review if x["status"] == "flagged"}
    status.update({r["substance_id"]: "rejected" for r in routes if r["status"] == "route_answer_rejected"})
    omop_answer = dict(con.execute("SELECT substance_id, omop_rxcui FROM omop_substance").fetchall())
    for d in decisions:
        if d["state"] == "rejected":
            status[d["substance_id"]] = "rejected"
        elif d.get("rxcui") and omop_answer.get(d["substance_id"]) not in (None, d["rxcui"]):
            status[d["substance_id"]] = "superseded"
    con.execute("ALTER TABLE omop_substance ADD COLUMN IF NOT EXISTS review_status VARCHAR")
    con.execute("UPDATE omop_substance SET review_status = NULL")
    con.executemany("UPDATE omop_substance SET review_status = ? WHERE substance_id = ?",
                    [(v, k) for k, v in status.items()])
    marked = dict(con.execute("SELECT review_status, count(*) FROM omop_substance WHERE review_status IS NOT NULL "
                              "GROUP BY 1").fetchall())
    by = dict(con.execute("SELECT split_part(source, ':', 1), count(DISTINCT substance_id) FROM substance_standard_ingredient "
                          "GROUP BY 1").fetchall())
    vocab = dict(con.execute("SELECT vocabulary, count(DISTINCT substance_id) FROM substance_standard_ingredient GROUP BY 1").fetchall())
    total = con.execute("SELECT count(DISTINCT substance_id) FROM substance_standard_ingredient").fetchone()[0]
    # the shipped files must agree with the database: omop_substance changed, and the new table ships too
    for table in ("omop_substance", "substance_standard_ingredient"):
        con.execute(f"COPY {table} TO 'out/{table}.parquet' (FORMAT PARQUET)")
    con.close()
    print(json.dumps({"substances_with_a_standard_ingredient": total, "by_source": by, "by_vocabulary": vocab,
                      "resolver_rows_superseded": len(superseded),
                      "omop_substance_review_status": marked,
                      "route_rows_rejected_or_overridden": collections.Counter(
                          r["status"] for r in routes if r["status"] != "accepted")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
