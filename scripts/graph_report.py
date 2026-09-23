#!/usr/bin/env python3
"""Score the graph's linkage routes, set their tiers, and report the graph's health and coverage.

A cross-vocabulary edge is a claim that two concepts are the same thing. Its strength is not declared: each linkage
route is scored against an INDEPENDENT second path to the same target, and its tier is earned from the Wilson lower
bound, exactly as scripts/route_scorer.py earns tiers for substance routes (reference/graph_tiers.json).

    mondo:exact_match -> SCT    vs  MONDO -> ICD-10-CM -> OMOP 'Maps to' -> SCT
    drugcentral:rxnorm          vs  DrugCentral -> SNOMEDCT_US -> OMOP 'Maps to' -> RxNorm ingredient

Agreement is reported two ways: EXACT (the two paths reach the same concept) and CONSISTENT (the same concept, or one
is an is-a ancestor of the other in SNOMED CT-AU). ICD-10-CM categories are broader than SNOMED concepts by design, so
a route can be right and still land one level up; the tier is earned on CONSISTENT, and EXACT is shown beside it so
the difference is visible. Where the two paths reach unrelated concepts, that is a contradiction.

Then: edges by category, source and state; nodes by vocabulary; the parallel-edge disagreement for product -> ATC
(PBS vs OMOP); and coverage -- how far MONDO reaches the corpus's bound conditions, and how far DrugCentral reaches the
compendium's RxNorm ingredients.

    scripts/graph_report.py [--vocab-dir ~/code/spine/out/omop-vocab]   # after build_edges.py; writes out/graph_report.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import duckdb

GRAPH = Path("out/graph.duckdb")
TIER1, TIER2, MIN_FIRED = 0.99, 0.80, 30


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def tier(lo: float, n: int) -> str:
    return "ungraded" if n < MIN_FIRED else "1" if lo >= TIER1 else "2" if lo >= TIER2 else "inadmissible"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    a = ap.parse_args()
    opts = "delim='\t', header=true, quote='', escape='', all_varchar=true"
    con = duckdb.connect(str(GRAPH))
    con.execute(f"CREATE TEMP VIEW C  AS SELECT * FROM read_csv('{a.vocab_dir}/CONCEPT.csv', {opts})")
    con.execute(f"CREATE TEMP VIEW CR AS SELECT * FROM read_csv('{a.vocab_dir}/CONCEPT_RELATIONSHIP.csv', {opts})")
    live = "state <> 'rejected'"
    report = {}

    def consistency(pairs_table: str) -> dict:
        """pairs_table(route_id, a, b): a = the route's SNOMED answer, b = the independent path's. Exact, or on one
        is-a line in SNOMED CT-AU (ancestor either way), or unrelated."""
        con.execute(f"""CREATE OR REPLACE TEMP TABLE anc AS
            WITH RECURSIVE up(start, node, depth) AS (
                SELECT DISTINCT x, x, 0 FROM (SELECT a AS x FROM {pairs_table} UNION SELECT b FROM {pairs_table})
                UNION
                SELECT u.start, e.o_code, u.depth + 1 FROM up u
                JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = u.node
                WHERE u.depth < 25)                      -- depth cap: the traversal rule, even on an acyclic hierarchy
            SELECT DISTINCT start, node FROM up""")
        row = con.execute(f"""
            WITH per AS (
                SELECT route_id,
                       bool_or(a = b) AS exact,
                       bool_or(a = b OR EXISTS (SELECT 1 FROM anc WHERE start = a AND node = b)
                                     OR EXISTS (SELECT 1 FROM anc WHERE start = b AND node = a)) AS consistent
                FROM {pairs_table} GROUP BY 1)
            SELECT count(*), count(*) FILTER (WHERE exact), count(*) FILTER (WHERE consistent) FROM per""").fetchone()
        n, ex, co = row
        lo_ex, _ = wilson(ex, n)
        lo_co, _ = wilson(co, n)
        return {"both_paths_fire": n, "exact": ex, "exact_rate": round(ex / n, 4) if n else None,
                "exact_wilson_lo": round(lo_ex, 4), "consistent": co, "consistent_rate": round(co / n, 4) if n else None,
                "consistent_wilson_lo": round(lo_co, 4), "contradicted": n - co, "earned_tier": tier(lo_co, n)}

    # --- route 1: MONDO -> SNOMED ------------------------------------------------------------------------------------
    con.execute(f"""CREATE OR REPLACE TEMP TABLE mondo_pairs AS
        SELECT d.s_code AS route_id, d.o_code AS a, i2s.o_code AS b
        FROM edge d
        JOIN edge m2i ON m2i.s_code = d.s_code AND m2i.predicate = 'mondo:exact_match' AND m2i.o_vocab = 'ICD10CM'
        JOIN edge i2s ON i2s.s_code = m2i.o_code AND i2s.predicate = 'icd10cm:maps_to'
        WHERE d.predicate = 'mondo:exact_match' AND d.o_vocab = 'SCT' AND d.{live}""")
    report["route:mondo->snomed"] = consistency("mondo_pairs")
    t = report["route:mondo->snomed"]["earned_tier"]
    con.execute("UPDATE edge SET tier = ? WHERE predicate = 'mondo:exact_match' AND o_vocab = 'SCT'", [t])

    # --- route 2: DrugCentral -> RxNorm (only if DrugCentral was loaded) --------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'drugcentral:rxnorm'").fetchone()[0]:
        con.execute("""CREATE OR REPLACE TEMP TABLE dc_sct AS SELECT DISTINCT o_code FROM edge WHERE predicate = 'drugcentral:snomed'""")
        con.execute("""CREATE OR REPLACE TEMP TABLE sct2rxn AS
            SELECT s.concept_code AS sct, t.concept_code AS rxn FROM dc_sct d
            JOIN C s ON s.vocabulary_id = 'SNOMED' AND s.concept_code = d.o_code
            JOIN CR r ON r.concept_id_1 = s.concept_id AND r.relationship_id = 'Maps to' AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
            JOIN C t ON t.concept_id = r.concept_id_2 AND t.vocabulary_id = 'RxNorm' AND t.concept_class_id = 'Ingredient'""")
        n, ex = con.execute("""
            WITH per AS (
                SELECT r.s_code AS dc, bool_or(r.o_code = x.rxn) AS agree
                FROM edge r JOIN edge s ON s.s_code = r.s_code AND s.predicate = 'drugcentral:snomed'
                JOIN sct2rxn x ON x.sct = s.o_code
                WHERE r.predicate = 'drugcentral:rxnorm' GROUP BY 1)
            SELECT count(*), count(*) FILTER (WHERE agree) FROM per""").fetchone()
        lo, _ = wilson(ex, n)
        report["route:drugcentral->rxnorm"] = {"both_paths_fire": n, "agree": ex, "rate": round(ex / n, 4) if n else None,
                                              "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
        con.execute("UPDATE edge SET tier = ? WHERE predicate = 'drugcentral:rxnorm'", [tier(lo, n)])

    # --- route 3: LOINC -> SNOMED measurement, checked by component --------------------------------------------------
    # Independent check: the LOINC term's COMPONENT part (LOINC's own axis) against the SNOMED target's Component
    # (246093002, from the SNOMED CT-AU release). Names only -- there is no code link between LOINC parts and SNOMED
    # substances -- so this is a consistency test, stated as such: consistent = the analyte names share a significant
    # word. Exact = the names are equal once normalised.
    rows = con.execute("""
        SELECT b.s_code, lower(pn.name), lower(sn.name)
        FROM edge b
        JOIN edge lc ON lc.s_code = b.s_code AND lc.predicate = 'loinc:has_component'
        JOIN node pn ON pn.vocab = 'LOINC' AND pn.code = lc.o_code
        JOIN edge sc ON sc.s_code = b.o_code AND sc.predicate = 'sct:246093002'
        JOIN node sn ON sn.vocab = 'SCT' AND sn.code = sc.o_code
        WHERE b.predicate = 'loinc:is_a_snomed'""").fetchall()
    import re
    STOP = {"measurement", "level", "total", "free", "serum", "plasma", "blood", "urine", "substance", "antibody", "antigen",
            "species", "with", "and", "the", "type", "ratio", "mass", "volume", "concentration"}
    tok = lambda s: {w for w in re.findall(r"[a-z0-9]{3,}", s or "") if w not in STOP}
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s or "")
    per = {}
    for lid, part, comp in rows:
        e, c = per.get(lid, (False, False))
        per[lid] = (e or norm(part) == norm(comp), c or norm(part) == norm(comp) or bool(tok(part) & tok(comp)))
    n = len(per); ex = sum(1 for e, _ in per.values() if e); co = sum(1 for _, c in per.values() if c)
    lo, _ = wilson(co, n)
    report["route:loinc->snomed (component check)"] = {"loinc_terms_checked": n, "exact": ex, "exact_rate": round(ex / n, 4) if n else None,
        "consistent": co, "consistent_rate": round(co / n, 4) if n else None, "consistent_wilson_lo": round(lo, 4),
        "earned_tier": tier(lo, n), "note": "a names-based consistency test, not a precision measurement"}
    con.execute("UPDATE edge SET tier = ? WHERE predicate = 'loinc:is_a_snomed'", [tier(lo, n)])
    report["coverage:LOINC terms bridged to SNOMED"] = dict(zip(("loinc_terms", "bridged"), con.execute("""
        SELECT (SELECT count(DISTINCT s_code) FROM edge WHERE predicate LIKE 'loinc:has_%'),
               (SELECT count(DISTINCT s_code) FROM edge WHERE predicate IN ('loinc:is_a_snomed', 'loinc:maps_to_snomed'))""").fetchone()))
    report["coverage:foreign SNOMED ids lifted to SNOMED CT-AU"] = dict(zip(("foreign_ids", "lifted"), con.execute("""
        SELECT (SELECT edges FROM build_log WHERE family LIKE 'foreign SNOMED ids%'),
               (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'sct:au_nearest_ancestor')""").fetchone()))

    # --- route 4: HPO -> SNOMED via a shared UMLS CUI, checked by hierarchy preservation ----------------------------
    # Where HPO says child is-a parent and both cross to SNOMED, the child's SNOMED concept should be the parent's or
    # below it in SNOMED CT-AU. A crossing that keeps HPO's structure is evidence the two concepts mean the same thing;
    # one that inverts or scatters it is evidence they do not.
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'hp:umls_snomed'").fetchone()[0]:
        con.execute("""CREATE OR REPLACE TEMP TABLE hp_pairs AS
            SELECT h.s_code AS child, h.o_code AS parent, mc.o_code AS c_sct, mp.o_code AS p_sct
            FROM edge h JOIN edge mc ON mc.s_code = h.s_code AND mc.predicate = 'hp:umls_snomed'
            JOIN edge mp ON mp.s_code = h.o_code AND mp.predicate = 'hp:umls_snomed'
            WHERE h.predicate = 'hp:is_a'""")
        con.execute("""CREATE OR REPLACE TEMP TABLE hp_up AS
            WITH RECURSIVE up(start, node, depth) AS (
                SELECT DISTINCT c_sct, c_sct, 0 FROM hp_pairs
                UNION SELECT u.start, e.o_code, u.depth + 1 FROM up u
                JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = u.node WHERE u.depth < 25)
            SELECT DISTINCT start, node FROM up""")
        n, ok = con.execute("""
            WITH per AS (SELECT child, parent, bool_or(c_sct = p_sct OR EXISTS (SELECT 1 FROM hp_up WHERE start = c_sct AND node = p_sct)) AS kept
                         FROM hp_pairs GROUP BY 1, 2)
            SELECT count(*), count(*) FILTER (WHERE kept) FROM per""").fetchone()
        lo, _ = wilson(ok, n)
        report["route:hpo->snomed (UMLS, hierarchy preserved)"] = {"hpo_is_a_pairs_both_mapped": n, "hierarchy_kept": ok,
            "rate": round(ok / n, 4) if n else None, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
        con.execute("UPDATE edge SET tier = ? WHERE predicate = 'hp:umls_snomed'", [tier(lo, n)])
        report["coverage:HPO phenotypes bridged to SNOMED"] = dict(zip(("hpo_phenotypes", "bridged", "bridged_in_au_release"), con.execute("""
            SELECT (SELECT count(*) FROM node WHERE vocab = 'HP'),
                   (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'hp:umls_snomed'),
                   (SELECT count(DISTINCT e.s_code) FROM edge e JOIN node n ON n.vocab = 'SCT' AND n.code = e.o_code
                     WHERE e.predicate = 'hp:umls_snomed' AND e.o_code NOT IN
                           (SELECT s_code FROM edge WHERE predicate = 'sct:au_nearest_ancestor'))""").fetchone()))

    # --- health ------------------------------------------------------------------------------------------------------
    report["edges"] = con.execute("SELECT count(*) FROM edge").fetchone()[0]
    report["nodes"] = con.execute("SELECT count(*) FROM node").fetchone()[0]
    report["edges_by_category"] = dict(con.execute("""SELECT p.category, count(*) FROM edge e JOIN predicate p ON p.id = e.predicate
                                                     GROUP BY 1 ORDER BY 2 DESC""").fetchall())
    report["edges_by_state"] = dict(con.execute("SELECT state, count(*) FROM edge GROUP BY 1 ORDER BY 2 DESC").fetchall())
    report["edges_by_tier"] = dict(con.execute("SELECT tier, count(*) FROM edge GROUP BY 1 ORDER BY 2 DESC").fetchall())
    report["nodes_by_vocabulary"] = dict(con.execute("SELECT vocab, count(*) FROM node GROUP BY 1 ORDER BY 2 DESC").fetchall())
    report["edges_by_source"] = dict(con.execute("SELECT source, count(*) FROM edge GROUP BY 1 ORDER BY 2 DESC").fetchall())
    report["sct_multi_parent"] = dict(zip(("concepts_with_parents", "with_more_than_one_parent"), con.execute("""
        SELECT count(*), count(*) FILTER (WHERE n > 1) FROM (SELECT s_code, count(*) n FROM edge
        WHERE predicate = 'sct:116680003' GROUP BY 1)""").fetchone()))

    # --- parallel edges: product -> ATC 5th level, PBS vs OMOP -------------------------------------------------------
    report["parallel:product->atc5 (PBS vs OMOP)"] = dict(zip(("products_with_both", "same_class", "no_class_in_common"), con.execute("""
        WITH p AS (SELECT s_code, list(DISTINCT o_code) cls FROM edge WHERE predicate = 'in_atc_class' AND source = 'PBS item-atc'
                     AND length(o_code) = 7 GROUP BY 1),
             o AS (SELECT s_code, list(DISTINCT o_code) cls FROM edge WHERE predicate = 'in_atc_class' AND source = 'OMOP CONCEPT_ANCESTOR'
                     AND length(o_code) = 7 GROUP BY 1)
        SELECT count(*), count(*) FILTER (WHERE len(list_intersect(p.cls, o.cls)) > 0),
               count(*) FILTER (WHERE len(list_intersect(p.cls, o.cls)) = 0)
        FROM p JOIN o USING (s_code)""").fetchone()))

    # --- coverage -----------------------------------------------------------------------------------------------------
    report["coverage:corpus conditions reached by MONDO"] = dict(zip(("bound_conditions", "direct", "via_snomed_ancestor"), con.execute("""
        WITH b AS (SELECT s_code AS cond, o_code AS sct FROM edge WHERE predicate = 'corpus:binds_to'),
             m AS (SELECT DISTINCT o_code AS sct FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab = 'SCT'),
             up AS (SELECT b.cond, e.o_code AS anc FROM b JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = b.sct)
        SELECT count(DISTINCT b.cond),
               count(DISTINCT b.cond) FILTER (WHERE b.sct IN (SELECT sct FROM m)),
               (SELECT count(DISTINCT cond) FROM up WHERE anc IN (SELECT sct FROM m))
        FROM b""").fetchone()))
    report["coverage:HPO diseases reachable from MONDO"] = dict(zip(("hpo_diseases", "with_a_mondo_match"), con.execute("""
        WITH d AS (SELECT DISTINCT s_vocab, s_code FROM edge WHERE predicate IN ('hpo:has_phenotype', 'hpo:lacks_phenotype')),
             m AS (SELECT DISTINCT o_vocab, o_code FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab IN ('OMIM', 'ORPHA'))
        SELECT count(*), count(*) FILTER (WHERE (s_vocab, s_code) IN (SELECT o_vocab, o_code FROM m)) FROM d""").fetchone()))
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'drugcentral:rxnorm'").fetchone()[0]:
        report["coverage:compendium RxNorm ingredients in DrugCentral"] = dict(zip(("compendium_rxnorm_ingredients", "in_drugcentral",
            "with_a_drugcentral_indication"), con.execute("""
            WITH ours AS (SELECT DISTINCT o_code FROM edge WHERE predicate = 'std_ingredient' AND o_vocab = 'RXN' AND state <> 'rejected'),
                 dc AS (SELECT s_code AS dc, o_code AS rxn FROM edge WHERE predicate = 'drugcentral:rxnorm'),
                 ind AS (SELECT DISTINCT s_code AS dc FROM edge WHERE predicate = 'drugcentral:indication')
            SELECT count(*), count(*) FILTER (WHERE o_code IN (SELECT rxn FROM dc)),
                   count(*) FILTER (WHERE o_code IN (SELECT rxn FROM dc WHERE dc IN (SELECT dc FROM ind)))
            FROM ours""").fetchone()))
    con.execute("CREATE OR REPLACE TABLE graph_report AS SELECT ? AS report", [json.dumps(report)])
    con.close()
    Path("out/graph_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
