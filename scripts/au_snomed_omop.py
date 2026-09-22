#!/usr/bin/env python3
"""SNOMED CT-AU where OMOP cannot see it: the nearest standard concept above each Australian one.

OMOP's SNOMED vocabulary is the international release with the US and UK editions. It has no Australian edition, and
the numbers are absolute rather than approximate:

* of the **6,849** Australian-authored clinical concepts in this compendium — procedures, findings, substances,
  qualifiers, assessment scales — **6** exist in OMOP by code;
* of the **165,628** Australian-authored medicine concepts, **none** do (they live in OMOP's separate `AMT`
  vocabulary, which items 13 to 15 already bridge).

So an Australian procedure in a patient record reaches no standard concept and disappears from every OMOP query.
This script walks up the `is a` hierarchy from each Australian concept until it meets an ancestor that OMOP holds
as a standard concept, and records it with the number of hops it took. The claim is the weaker one the data
supports: *this Australian concept is subsumed by that standard one* — not that they are the same thing.

Quality is measured two ways, because there is no set of known answers to check against: how far the walk had to
go, and whether the standard concept's OMOP domain matches the Australian concept's own semantic tag. A procedure
that lands on a Condition is a mapping to distrust, and those are counted rather than hidden.

    scripts/au_snomed_omop.py [--vocab-dir ~/code/spine/out/omop-vocab] [--max-hops 12]

Offline; writes `au_omop_ancestor` and `au_omop_unreached` into out/compendium.duckdb.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
# an Australian concept's semantic tag, and the OMOP domains that are a sane home for it
TAG_DOMAIN = {
    "procedure": ("Procedure", "Measurement", "Device", "Observation"),
    "finding": ("Condition", "Observation", "Measurement"),
    "disorder": ("Condition", "Observation"),
    "substance": ("Drug", "Observation", "Spec Anatomic Site", "Measurement"),
    "qualifier value": ("Meas Value", "Observation", "Qualifier Value", "Unit", "Route", "Condition Status"),
    "assessment scale": ("Measurement", "Observation"),
    "observable entity": ("Measurement", "Observation"),
    "physical object": ("Device", "Observation"),
    "situation": ("Condition", "Observation"),
    "regime/therapy": ("Procedure", "Observation"),
    "body structure": ("Spec Anatomic Site", "Observation"),
    "organism": ("Observation", "Condition"),
    "environment": ("Observation",),
    "record artifact": ("Observation", "Note"),
}
AMT_TAGS = ("containerized branded clinical drug package", "branded clinical drug package", "branded clinical drug",
            "clinical drug package", "product name", "clinical drug", "medicinal product", "medicinal product form",
            "containerized branded product package", "branded product package", "containerized branded physical object",
            "branded physical object package", "branded physical object", "physical object package", "product package",
            "branded product", "trade product pack", "containered trade product pack")


def build(vocab_dir: str, max_hops: int, log=print) -> dict:
    concept_csv = os.path.join(vocab_dir, "CONCEPT.csv")
    if not os.path.exists(concept_csv) or os.path.getsize(concept_csv) < 1_000_000:
        raise SystemExit(f"{concept_csv} missing or a stub — install an Athena bundle first")
    opts = "delim='\\t', header=true, quote='', escape='', nullstr='', all_varchar=true"
    con = duckdb.connect(str(DB))
    con.execute(f"""CREATE OR REPLACE TEMP TABLE omop_sct AS
        SELECT CAST(concept_id AS BIGINT) concept_id, concept_code, concept_name, domain_id, concept_class_id,
               standard_concept, invalid_reason
        FROM read_csv('{concept_csv}', {opts}) WHERE vocabulary_id='SNOMED'""")
    amt_list = ",".join(f"'{t}'" for t in AMT_TAGS)
    con.execute(f"""CREATE OR REPLACE TEMP TABLE au AS
        SELECT k.id, k.pt, k.tag FROM concept k
        WHERE k.au_authored AND k.tag NOT IN ({amt_list})
          AND NOT EXISTS (SELECT 1 FROM omop_sct o WHERE o.concept_code=k.id AND o.standard_concept='S')""")
    log(f"Australian clinical concepts with no standard OMOP concept of their own: "
        f"{con.execute('SELECT count(*) FROM au').fetchone()[0]:,}")

    # walk up `is a` until the first ancestor OMOP holds as standard; keep every such ancestor at that depth, since
    # a concept can have more than one parent and neither is more right than the other
    con.execute(f"""CREATE OR REPLACE TABLE au_omop_ancestor AS
        WITH RECURSIVE up(id, ancestor, hops) AS (
            SELECT a.id, p.parent_id, 1 FROM au a JOIN parent_of p ON p.child_id=a.id
            UNION ALL
            SELECT u.id, p.parent_id, u.hops+1 FROM up u JOIN parent_of p ON p.child_id=u.ancestor
            WHERE u.hops < {max_hops}
              AND NOT EXISTS (SELECT 1 FROM omop_sct o WHERE o.concept_code=u.ancestor AND o.standard_concept='S')),
        hit AS (
            SELECT u.id, u.ancestor, u.hops FROM up u
            JOIN omop_sct o ON o.concept_code=u.ancestor AND o.standard_concept='S'),
        nearest AS (SELECT id, min(hops) AS hops FROM hit GROUP BY 1)
        SELECT h.id AS au_id, any_value(a.pt) AS au_name, any_value(a.tag) AS au_tag, h.hops,
               h.ancestor AS ancestor_code, o.concept_id AS omop_concept_id, o.concept_name AS omop_name,
               o.domain_id AS omop_domain, o.concept_class_id AS omop_class
        FROM hit h JOIN nearest n ON n.id=h.id AND n.hops=h.hops
        JOIN au a ON a.id=h.id JOIN omop_sct o ON o.concept_code=h.ancestor AND o.standard_concept='S'
        GROUP BY h.id, h.hops, h.ancestor, o.concept_id, o.concept_name, o.domain_id, o.concept_class_id""")
    con.execute("""CREATE OR REPLACE TABLE au_omop_unreached AS
        SELECT a.id, a.pt, a.tag FROM au a
        WHERE NOT EXISTS (SELECT 1 FROM au_omop_ancestor x WHERE x.au_id=a.id)""")

    # the only quality signals available: how far the walk went, and whether the domain suits the tag
    case = " ".join(f"WHEN '{tag}' THEN {'(' + ','.join(chr(39)+d+chr(39) for d in domains) + ')'}" for tag, domains in TAG_DOMAIN.items())
    con.execute(f"""ALTER TABLE au_omop_ancestor ADD COLUMN IF NOT EXISTS domain_suits_tag VARCHAR""")
    con.execute(f"""UPDATE au_omop_ancestor SET domain_suits_tag =
        CASE {' '.join(f"WHEN au_tag='{tag}' THEN CASE WHEN omop_domain IN ({','.join(chr(39)+d+chr(39) for d in domains)}) THEN 'yes' ELSE 'no' END" for tag, domains in TAG_DOMAIN.items())}
             ELSE 'no rule for this tag' END""")
    reached = con.execute("SELECT count(DISTINCT au_id) FROM au_omop_ancestor").fetchone()[0]
    total = con.execute("SELECT count(*) FROM au").fetchone()[0]
    report = {
        "australian_clinical_concepts": total,
        "reached_a_standard_ancestor": reached,
        "unreached": con.execute("SELECT count(*) FROM au_omop_unreached").fetchone()[0],
        "by_tag": {r[0]: {"concepts": r[1], "reached": r[2]} for r in con.execute(f"""
            SELECT a.tag, count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM au_omop_ancestor x WHERE x.au_id=a.id))
            FROM au a GROUP BY 1 ORDER BY 2 DESC LIMIT 12""").fetchall()},
        "hops": dict(con.execute("SELECT hops, count(DISTINCT au_id) FROM au_omop_ancestor GROUP BY 1 ORDER BY 1").fetchall()),
        "more_than_one_nearest_ancestor": con.execute(
            "SELECT count(*) FROM (SELECT au_id FROM au_omop_ancestor GROUP BY 1 HAVING count(*)>1)").fetchone()[0],
        "domain_suits_the_semantic_tag": dict(con.execute(
            "SELECT domain_suits_tag, count(*) FROM au_omop_ancestor GROUP BY 1 ORDER BY 2 DESC").fetchall()),
        "top_targets": dict(con.execute("""SELECT omop_name, count(DISTINCT au_id) FROM au_omop_ancestor
                                           GROUP BY 1 ORDER BY 2 DESC LIMIT 8""").fetchall()),
    }
    con.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    ap.add_argument("--max-hops", type=int, default=12)
    a = ap.parse_args()
    print(json.dumps(build(a.vocab_dir, a.max_hops), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
