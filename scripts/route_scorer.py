#!/usr/bin/env python3
"""Score every edge-producing route on one common scale, so their strengths can be compared.

Routes produce edges by different mechanisms — an OMOP code mapping, a normalised name match, a salt-to-base
inference — and their internal measures are not commensurable: a belief interval, a likelihood ratio and an
ordinal grade do not average. What *is* commensurable is how each route performs on the same held-out truth set,
answering the same question: when this route fires, how often is it right, and how surprising is that agreement?

For each route this reports:

    fired / coverage      how often the route produces an answer at all
    precision (PPV)       of those, how often it matches the gold value        -- depends on prevalence
    Wilson 95% interval   because 24/32 and 3074/3074 are not the same evidence
    m, u, log(m/u)        Fellegi & Sunter weight (scripts/evidence_scorer.py) -- prevalence-INDEPENDENT
    silence rate          on the hard population: does the route go quiet, or does it guess?

**Store log(m/u), not precision.** Precision is a PPV and does not transport to a population with a different
base rate; the log-odds weight does. The distinction is the same one that separates a diagnostic test's
predictive value from its likelihood ratio, and it is why a route scored on easy cases can still be trusted on
hard ones -- provided its failure mode is silence rather than a guess, which `silence rate` measures.

    scripts/route_scorer.py [--vocab-dir ~/code/spine/out/omop-vocab] [--json out/route_scores.json]

Offline. Adding a route means adding one entry to ROUTES: a name, a `source_class` (lookup | authored), and
SQL yielding (subject_id, predicted_code). The route's TIER is not declared -- `earned_tier()` assigns it from the
Wilson lower bound, so a route cannot be promoted by its author, only by its score. See
reference/graph_tiers.json and docs/weighted-graph-design.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
DECISIONS = Path("reference/rxnorm_substance_decisions.json")

# Routes yielding (subject_id, pred). Each must be unambiguous per subject or it does not fire:
# a route that returns two answers has not answered.
ROUTES = {
    "code:snomed-maps-to-ingredient": {
        "source_class": "lookup",
        "why": "OMOP's own code-level mapping. No name matching; chance agreement is essentially impossible.",
        "sql": """
            SELECT t.subject_id, any_value(tgt.concept_code) AS pred
            FROM subjects t
            JOIN C src ON src.concept_code = t.subject_id AND src.vocabulary_id = 'SNOMED'
            JOIN CR r  ON r.concept_id_1 = src.concept_id AND r.relationship_id = 'Maps to'
                      AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
            JOIN C tgt ON tgt.concept_id = r.concept_id_2
                      AND tgt.concept_class_id = 'Ingredient' AND tgt.standard_concept = 'S'
            GROUP BY 1 HAVING count(DISTINCT tgt.concept_code) = 1""",
    },
    "name:exact-normalised": {
        "source_class": "lookup",
        "why": "Normalised exact name equality. Common names (Glucose, Sodium) agree by chance, so u is high.",
        "sql": """
            SELECT t.subject_id, any_value(i.concept_code) AS pred
            FROM subjects t JOIN ingr i ON i.k = nm(t.subject_name)
            WHERE i.standard_concept = 'S' AND i.invalid_reason IS NULL
            GROUP BY 1 HAVING count(DISTINCT i.concept_code) = 1""",
    },
    "deprecation:name-then-replaced-by": {
        "source_class": "lookup",
        "why": "Name matches a retired ingredient; follow RxNorm's own replacement. The vocabulary decides, not us.",
        "sql": """
            SELECT t.subject_id, any_value(tgt.concept_code) AS pred
            FROM subjects t
            JOIN ingr dead ON dead.k = nm(t.subject_name) AND dead.invalid_reason IS NOT NULL
            JOIN CR r ON r.concept_id_1 = dead.concept_id
                     AND r.relationship_id IN ('Concept replaced by', 'Maps to')
                     AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
            JOIN C tgt ON tgt.concept_id = r.concept_id_2
                      AND tgt.concept_class_id = 'Ingredient' AND tgt.standard_concept = 'S'
            GROUP BY 1 HAVING count(DISTINCT tgt.concept_code) = 1""",
    },
}


# A tier is EARNED from the measurement, never declared by the route's author. The thresholds are on the Wilson
# lower bound, not on the point estimate, so a route cannot reach Tier 1 on a lucky small sample.
TIER1_FLOOR = 0.99   # lookup, clean result
TIER2_FLOOR = 0.80   # lookup, ambiguous but significant signal
MIN_FIRED = 30       # below this the interval is too wide to grade at all


def earned_tier(source_class: str, wilson_lo: float, fired: int) -> str:
    """Tier 3 is reserved for authored-from-memory content and is ordinal-only by construction; a lookup route
    can never fall into it. A lookup that scores below Tier 2 is INADMISSIBLE: its output is routed to the
    review queue as candidates, not written as edges."""
    if source_class == "authored":
        return "3"
    if fired < MIN_FIRED:
        return "ungraded"
    if wilson_lo >= TIER1_FLOOR:
        return "1"
    if wilson_lo >= TIER2_FLOOR:
        return "2"
    return "inadmissible"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    halfwidth = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


def connect(vocab_dir: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    opts = "delim='\t', header=true, quote='', escape='', all_varchar=true"
    con.execute(f"CREATE VIEW C AS SELECT * FROM read_csv('{os.path.join(vocab_dir,'CONCEPT.csv')}', {opts})")
    con.execute(f"CREATE VIEW CR AS SELECT * FROM read_csv('{os.path.join(vocab_dir,'CONCEPT_RELATIONSHIP.csv')}', {opts})")
    con.execute(f"ATTACH '{DB}' AS cmp (READ_ONLY)")
    con.execute("""CREATE MACRO nm(s) AS lower(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
        regexp_replace(trim(s), '\\s*\\(substance\\)$', ''), 'sulph','sulf','g'), 'oe','e','g'),
        '[^a-z0-9 ]',' ','g'), '\\s+',' ','g'))""")
    con.execute("""CREATE TEMP TABLE ingr AS
        SELECT concept_id, concept_code, concept_name, nm(concept_name) AS k, standard_concept, invalid_reason
        FROM C WHERE vocabulary_id IN ('RxNorm','RxNorm Extension') AND concept_class_id = 'Ingredient'""")
    return con


def score(con, name: str, spec: dict, n_truth: int, n_hard: int) -> dict:
    """Precision on the truth set; silence on the hard set. A route that fires on hard rows it cannot know
    is guessing, and the gap between the two populations is exactly where a stored PPV would mislead."""
    con.execute("CREATE OR REPLACE TEMP TABLE subjects AS SELECT subject_id, subject_name FROM truth")
    rows = con.execute(spec["sql"]).fetchall()
    gold = {r[0]: r[1] for r in con.execute("SELECT subject_id, gold FROM truth").fetchall()}
    fired = len(rows)
    correct = sum(1 for sid, pred in rows if gold.get(sid) == pred)
    lo, hi = wilson(correct, fired)

    # m = P(route fires AND agrees | true correspondence). u is estimated by permutation: how often the route's
    # answer would match a DIFFERENT subject's gold value, i.e. agreement attributable to chance alone.
    golds = list(gold.values())
    by_pred = {}
    for sid, pred in rows:
        by_pred[pred] = by_pred.get(pred, 0) + 1
    chance = sum(cnt * golds.count(pred) for pred, cnt in by_pred.items()) / max(1, fired * len(golds))
    m = correct / n_truth if n_truth else 0.0
    u = max(chance, 1.0 / max(1, len(set(golds))))          # floor: never claim impossibility from a finite sample
    weight = math.log(m / u) if m > 0 and u > 0 else float("-inf")

    con.execute("CREATE OR REPLACE TEMP TABLE subjects AS SELECT subject_id, subject_name FROM hard")
    hard_fired = len(con.execute(spec["sql"]).fetchall())
    return {
        "route": name, "source_class": spec["source_class"],
        "earned_tier": earned_tier(spec["source_class"], lo, fired), "why": spec["why"],
        "fired": fired, "coverage": round(fired / n_truth, 4) if n_truth else 0,
        "correct": correct, "precision": round(correct / fired, 4) if fired else None,
        "wilson95": [round(lo, 4), round(hi, 4)],
        "m": round(m, 6), "u_estimated": round(u, 8), "log_odds_weight": round(weight, 3),
        "hard_population_fired": hard_fired,
        "hard_population_silence": round(1 - hard_fired / n_hard, 4) if n_hard else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    ap.add_argument("--json", default="out/route_scores.json")
    a = ap.parse_args()
    con = connect(a.vocab_dir)

    # Truth: RxNav resolved it AND OMOP independently agreed. Two sources, so it is not one method marking itself.
    con.execute("""CREATE TEMP TABLE truth AS
        SELECT s.substance_id AS subject_id, sub.substance AS subject_name, s.rxnav_rxcui AS gold
        FROM cmp.omop_substance s JOIN cmp.substance sub ON sub.substance_id = s.substance_id
        WHERE s.agreement = 'agree' AND s.rxnav_rxcui IS NOT NULL""")
    # Hard: rows a person still has to read. No gold value exists — only whether a route dares to answer.
    con.execute("""CREATE TEMP TABLE hard AS
        SELECT r.sctid AS subject_id, coalesce(sub.substance, r.pt) AS subject_name
        FROM read_csv_auto('out/rxnorm_review.tsv', delim='\t', all_varchar=true) r
        LEFT JOIN cmp.substance sub ON sub.substance_id = r.sctid
        WHERE r.status IN ('unresolved', 'rxnav-by-name-unverified')""")
    n_truth = con.execute("SELECT count(*) FROM truth").fetchone()[0]
    n_hard = con.execute("SELECT count(*) FROM hard").fetchone()[0]

    out = {"truth_set": n_truth, "hard_set": n_hard,
           "routes": [score(con, n, s, n_truth, n_hard) for n, s in ROUTES.items()]}
    out["routes"].sort(key=lambda r: -(r["log_odds_weight"] if r["log_odds_weight"] != float("-inf") else -99))
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
