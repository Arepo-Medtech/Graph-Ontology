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
import collections
import json
import math
import os
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))     # scripts/ (consistency.compute)


ONT_ROOT = os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES"))   # the licensed releases, read in place
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
    vocab = next((d for d in (Path(os.path.expanduser("~/code/spine/out/omop-vocab")), Path("out/omop-vocab")) if (d / "CONCEPT.csv").exists()),
                 Path(os.path.expanduser("~/code/spine/out/omop-vocab")))   # out/ on a machine restored by scripts/graph_inputs.py
    ap.add_argument("--vocab-dir", default=str(vocab))
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
    report["coverage:foreign SNOMED ids lifted to SNOMED CT-AU"] = dict(zip(("foreign_ids", "nearest_ancestor_via_athena",
            "successor_via_au_historical_association", "successor_by_association", "either"), con.execute("""
        SELECT (SELECT edges FROM build_log WHERE family LIKE 'foreign SNOMED ids%'),
               (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'sct:au_nearest_ancestor'),
               (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'sct:historical_association'),
               (SELECT json_group_object(m, n) FROM (SELECT method m, count(DISTINCT s_code) n FROM edge
                  WHERE predicate = 'sct:historical_association' GROUP BY 1 ORDER BY 2 DESC)),
               (SELECT count(DISTINCT s_code) FROM edge WHERE predicate IN ('sct:au_nearest_ancestor', 'sct:historical_association'))""").fetchone()))
    fs = report["coverage:foreign SNOMED ids lifted to SNOMED CT-AU"]
    fs["successor_by_association"] = json.loads(fs["successor_by_association"] or "{}")

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
            "rate": round(ok / n, 4) if n else None, "wilson_lo": round(lo, 4),
            "use": "diagnostic -- two ontologies' structures agreeing, not mapping precision; tier set by hand check"}
        # Diagnostic only. Read by hand, the pairs that fail are mostly CORRECT mappings where SNOMED organises the same
        # concepts differently from HPO (Spastic paraparesis is not under Paraparesis in SNOMED) -- it measures agreement
        # between two ontologies' structures, not mapping precision. The tier comes from the hand check (build_edges.py).
        report["coverage:HPO phenotypes bridged to SNOMED"] = dict(zip(("hpo_phenotypes", "bridged", "bridged_in_au_release"), con.execute("""
            SELECT (SELECT count(*) FROM node WHERE vocab = 'HP'),
                   (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'hp:umls_snomed'),
                   (SELECT count(DISTINCT e.s_code) FROM edge e JOIN node n ON n.vocab = 'SCT' AND n.code = e.o_code
                     WHERE e.predicate = 'hp:umls_snomed' AND e.o_code NOT IN
                           (SELECT s_code FROM edge WHERE predicate = 'sct:au_nearest_ancestor'))""").fetchone()))

    # --- Interprets: does a lab term reach a finding that interprets it? Both LOINC routes, measured the same way ----
    # A finding interprets an observable (Interprets), usually with an interpretation beside it in the same role group
    # (Has interpretation: above / below reference range, abnormal ...). A LOINC term reaches that finding if its SNOMED
    # concept, or any is-a ancestor of it, is what the finding interprets. Athena lands LOINC on measurement procedures;
    # the LOINC Ontology lands it on observables -- which is where Interprets points.
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'loinc:sct_concept'").fetchone()[0]:
        con.execute("""CREATE OR REPLACE TEMP TABLE interp AS
            SELECT DISTINCT i.o_code AS target, i.s_code AS finding,
                   EXISTS (SELECT 1 FROM edge h WHERE h.s_code = i.s_code AND h.predicate = 'sct:363713009'
                             AND json_extract(h.attrs, '$.group') = json_extract(i.attrs, '$.group')) AS with_interpretation
            FROM edge i WHERE i.predicate = 'sct:363714003'""")
        def reach(route_preds: str) -> dict:
            con.execute(f"""CREATE OR REPLACE TEMP TABLE start AS SELECT DISTINCT s_code AS loinc, o_code AS sct FROM edge
                            WHERE predicate IN ({route_preds}) AND state <> 'rejected'""")
            con.execute("""CREATE OR REPLACE TEMP TABLE up AS
                WITH RECURSIVE u(loinc, node, depth) AS (
                    SELECT loinc, sct, 0 FROM start
                    UNION SELECT u.loinc, e.o_code, u.depth + 1 FROM u
                    JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = u.node WHERE u.depth < 25)
                SELECT DISTINCT loinc, node FROM u""")
            row = con.execute("""SELECT count(DISTINCT s.loinc),
                   count(DISTINCT u.loinc) FILTER (WHERE i.target IS NOT NULL),
                   count(DISTINCT u.loinc) FILTER (WHERE i.with_interpretation),
                   count(DISTINCT i.finding) FILTER (WHERE i.with_interpretation)
                FROM start s LEFT JOIN up u ON u.loinc = s.loinc LEFT JOIN interp i ON i.target = u.node""").fetchone()
            # direct = the term's own SNOMED concept is what the finding interprets; through ancestors the count is
            # inflated by generic targets ('Evaluation procedure', 'Measurement' reach ~20k terms and a few dozen findings)
            direct = con.execute("""SELECT count(DISTINCT s.loinc), count(DISTINCT i.finding) FROM start s
                JOIN interp i ON i.target = s.sct AND i.with_interpretation""").fetchone()
            return dict(zip(("loinc_terms", "reach_an_interpreting_finding", "reach_one_with_an_interpretation",
                             "distinct_findings_with_interpretation", "direct_loinc_terms", "direct_findings"), row + direct))
        report["interprets:via Athena (LOINC -> measurement procedure)"] = reach("'loinc:is_a_snomed', 'loinc:maps_to_snomed'")
        report["interprets:via LOINC Ontology (LOINC -> observable)"] = reach("'loinc:sct_concept'")

        # --- the Athena bridge, re-checked by CODE against the LOINC Ontology: same analyte (Component)? ---------------
        con.execute("""CREATE OR REPLACE TEMP TABLE cmp_pairs AS
            SELECT a.s_code AS loinc, ca.o_code AS athena_comp, co.o_code AS ontology_comp
            FROM edge a JOIN edge o ON o.s_code = a.s_code AND o.predicate = 'loinc:sct_concept'
            JOIN edge ca ON ca.s_code = a.o_code AND ca.predicate = 'sct:246093002'
            JOIN edge co ON co.s_code = o.o_code AND co.predicate = 'sct:246093002'
            WHERE a.predicate = 'loinc:is_a_snomed'""")
        con.execute("""CREATE OR REPLACE TEMP TABLE comp_up AS
            WITH RECURSIVE u(start, node, depth) AS (
                SELECT DISTINCT x, x, 0 FROM (SELECT athena_comp AS x FROM cmp_pairs UNION SELECT ontology_comp FROM cmp_pairs)
                UNION SELECT u.start, e.o_code, u.depth + 1 FROM u JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = u.node
                WHERE u.depth < 25)
            SELECT DISTINCT start, node FROM u""")
        n, ex, co = con.execute("""WITH per AS (SELECT loinc, bool_or(athena_comp = ontology_comp) AS exact,
                bool_or(athena_comp = ontology_comp
                        OR EXISTS (SELECT 1 FROM comp_up WHERE start = ontology_comp AND node = athena_comp)
                        OR EXISTS (SELECT 1 FROM comp_up WHERE start = athena_comp AND node = ontology_comp)) AS consistent
              FROM cmp_pairs GROUP BY 1)
            SELECT count(*), count(*) FILTER (WHERE exact), count(*) FILTER (WHERE consistent) FROM per""").fetchone()
        lo, _ = wilson(co, n)
        report["route:loinc->snomed (Athena, checked by component CODE against the LOINC Ontology)"] = {
            "loinc_terms_both_routes": n, "same_component": ex, "exact_rate": round(ex / n, 4) if n else None,
            "consistent": co, "consistent_rate": round(co / n, 4) if n else None, "consistent_wilson_lo": round(lo, 4),
            "earned_tier": tier(lo, n), "contradicted": n - co}
        con.execute("UPDATE edge SET tier = ? WHERE predicate = 'loinc:is_a_snomed'", [tier(lo, n)])

        # --- lab result -> finding: a tier per route (the edge's method), earned from the hand check ----------------
        hc = Path("reference/interprets_handcheck.json")
        if hc.exists() and con.execute("SELECT count(*) FROM edge WHERE predicate = 'loinc:interpreted_in_finding'").fetchone()[0]:
            scored = json.load(open(hc))["scored"]
            for method, e, terms, finds in con.execute("""SELECT method, count(*), count(DISTINCT s_code), count(DISTINCT o_code)
                    FROM edge WHERE predicate = 'loinc:interpreted_in_finding' GROUP BY 1 ORDER BY 2 DESC""").fetchall():
                rows = [r for r in scored if r.get("method") == method]
                k, n = sum(r["verdict"] == "correct" for r in rows), len(rows)
                lo, _ = wilson(k, n)
                con.execute("UPDATE edge SET tier = ? WHERE predicate = 'loinc:interpreted_in_finding' AND method = ?", [tier(lo, n), method])
                report[f"route:loinc result -> finding ({method})"] = {"edges": e, "loinc_terms": terms, "findings": finds,
                    "hand_checked": n, "correct": k, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
            # two witnesses: where both the analyte join and Athena's placement make an edge, do they make the same one?
            report["parallel:loinc result -> finding (analyte vs Athena)"] = dict(zip(
                ("distinct_edges", "by_both", "analyte_only", "athena_only", "loinc_terms_by_both", "same_findings"), con.execute("""
                WITH e AS (SELECT s_code, o_code, json_extract_string(attrs, '$.interpretation') i,
                                  bool_or(method = 'same component, specimen at or below') a, bool_or(method LIKE 'Athena%') t
                           FROM edge WHERE predicate = 'loinc:interpreted_in_finding' GROUP BY 1, 2, 3),
                     f AS (SELECT s_code, list(DISTINCT o_code ORDER BY o_code) FILTER (WHERE a) fa,
                                  list(DISTINCT o_code ORDER BY o_code) FILTER (WHERE t) ft FROM e GROUP BY 1)
                SELECT (SELECT count(*) FROM e), (SELECT count(*) FROM e WHERE a AND t), (SELECT count(*) FROM e WHERE a AND NOT t),
                       (SELECT count(*) FROM e WHERE t AND NOT a),
                       (SELECT count(*) FROM f WHERE fa IS NOT NULL AND ft IS NOT NULL),
                       (SELECT count(*) FROM f WHERE fa IS NOT NULL AND ft IS NOT NULL AND fa = ft)""").fetchone()))
            report["coverage:lab results reaching a finding they define"] = dict(zip(("loinc_terms", "findings"), con.execute("""
                SELECT count(DISTINCT s_code), count(DISTINCT o_code) FROM edge WHERE predicate = 'loinc:interpreted_in_finding'""").fetchone()))

    # --- ICD-10-CM -> SNOMED, every code: tier from the hand check; MONDO (route 1) is the second witness ---------------
    hc = Path("reference/icd10cm_handcheck.json")
    if hc.exists():
        scored = json.load(open(hc))["scored"]
        k, n = sum(r["verdict"] == "correct" for r in scored), len(scored)
        lo, _ = wilson(k, n)
        con.execute("UPDATE edge SET tier = ? WHERE predicate = 'icd10cm:maps_to'", [tier(lo, n)])
        e, codes, sct, only = con.execute("""
            WITH x AS (SELECT DISTINCT s_code c FROM edge WHERE s_vocab = 'SCT' AND o_vocab <> 'SCT' AND predicate <> 'icd10cm:maps_to'
                       UNION SELECT DISTINCT o_code FROM edge WHERE o_vocab = 'SCT' AND s_vocab <> 'SCT' AND predicate <> 'icd10cm:maps_to')
            SELECT count(*), count(DISTINCT s_code), count(DISTINCT o_code),
                   count(DISTINCT o_code) FILTER (WHERE o_code NOT IN (SELECT c FROM x))
            FROM edge WHERE predicate = 'icd10cm:maps_to'""").fetchone()
        report["route:icd10cm->snomed (all codes; hand check)"] = {"edges": e, "icd_codes": codes, "snomed_concepts": sct,
            "snomed_concepts_with_no_other_cross_vocabulary_edge": only, "hand_checked": n, "correct": k,
            "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}

    # --- finding -> diagnosis likelihood ratios: tier from transcription verification; every edge awaits a person -----
    ver = Path("reference/diagnostic_accuracy_verification.json")
    LRP = "'finding_lr_if_present', 'finding_lr_if_absent', 'test_result_lr', 'score_result_lr', 'finding_lr_for_outcome'"
    if ver.exists() and con.execute(f"SELECT count(*) FROM edge WHERE predicate IN ({LRP})").fetchone()[0]:
        v = json.load(open(ver))
        k, n = v["verified"], v["records"]
        lo, _ = wilson(k, n)
        # the edge is only as good as its weakest verified step: transcription (mechanical) and binding (read by hand)
        br = v.get("binding_review") or {}
        fams = {f: (x["distinct_bindings_read"], x["distinct_bindings_read"] - x["read_as_wrong"]) for f, x in br.items() if isinstance(x, dict)}
        order = ["1", "2", "inadmissible", "ungraded"]
        binding = {f: (bn, bk, wilson(bk, bn)[0], tier(wilson(bk, bn)[0], bn)) for f, (bn, bk) in fams.items()}
        # the edge's tier: the weaker of transcription and its family's binding
        for f, preds in (("finding", "'finding_lr_if_present', 'finding_lr_if_absent'"),
                         ("test_score_prognosis", "'test_result_lr', 'score_result_lr', 'finding_lr_for_outcome'")):
            if f in binding:
                con.execute(f"UPDATE edge SET tier = ? WHERE predicate IN ({preds})", [max(tier(lo, n), binding[f][3], key=order.index)])
        t_edge = max([tier(lo, n)] + [b[3] for f, b in binding.items() if f == "finding"], key=order.index)
        bn = sum(b[0] for b in binding.values()); bk = sum(b[1] for b in binding.values()); blo = wilson(bk, bn)[0]
        held = con.execute("SELECT coalesce(max(edges), 0) FROM build_log WHERE family LIKE 'likelihood-ratio records bound but held%'").fetchone()[0]
        # the held tests are already matched to the graph's terminology: how many of their SNOMED procedures reach LOINC codes?
        held_loinc = {}
        bpath, apath = Path("reference/diagnostic_accuracy_bindings.json"), Path("reference/diagnostic_accuracy.json")
        if bpath.exists() and apath.exists():
            kinds = {r["id"]: r.get("kind", "finding") for r in json.load(open(apath))["records"]}
            tests = sorted({x["finding"]["concept_id"] for x in json.load(open(bpath))["results"]
                            if kinds.get(x["id"]) == "test" and x.get("finding") and x.get("diagnosis")})
            if tests:
                con.execute("CREATE OR REPLACE TEMP TABLE held_test AS SELECT unnest(?) AS c", [tests])
                row = con.execute("""SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM edge l WHERE l.o_code = h.c AND l.s_vocab = 'LOINC')),
                        (SELECT count(DISTINCT l.s_code) FROM edge l JOIN held_test h2 ON h2.c = l.o_code WHERE l.s_vocab = 'LOINC')
                    FROM held_test h""").fetchone()
                held_loinc = {"distinct_test_concepts": row[0], "with_loinc_codes_in_graph": row[1], "loinc_codes_reached": row[2]}
        e, dx, fi, dv = con.execute(f"""SELECT count(*), count(DISTINCT o_code), count(DISTINCT s_code),
                count(*) FILTER (WHERE json_extract(attrs, '$.derived')::BOOLEAN) FROM edge WHERE predicate IN ({LRP})""").fetchone()
        report["evidence:finding -> diagnosis likelihood ratios"] = {"records_transcribed": n, "numbers_verified_against_abstract": k,
            "transcription_wilson_lo": round(lo, 4), "transcription_tier": tier(lo, n),
            "binding_by_family": {f: {"read": b[0], "right_first_time": b[1], "wilson_lo": round(b[2], 4), "tier": b[3]} for f, b in binding.items()},
            "held_as_candidates": con.execute("SELECT edges FROM build_log WHERE family LIKE 'likelihood-ratio records bound but held%'").fetchone()[0],
            "earned_tier": t_edge, "edges": e, "diagnoses": dx, "findings": fi, "derived_from_sens_spec": dv,
            "candidates": {"total": n - e, "bound_but_family_not_admitted": held, "not_bound_exactly": n - e - held},
            "held_tests_reaching_loinc": held_loinc,
            "state": "corrected_pending_attestation (a person signs off each)",
            # independent sources on the same finding, diagnosis and side: do they agree which way it moves the odds?
            "by_predicate_and_method": {f"{p} / {m}": c for p, m, c in con.execute(f"""SELECT predicate, method, count(*) FROM edge
                WHERE predicate IN ({LRP}) GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()},
            "parallel_sources": dict(zip(("pairs_with_2_or_more_sources", "same_direction", "direction_differs"), con.execute(f"""
                WITH g AS (SELECT s_code, o_code, predicate, count(DISTINCT json_extract_string(attrs, '$.pmid')) n,
                                  bool_and(json_extract(attrs, '$.lr')::DOUBLE > 1) up, bool_and(json_extract(attrs, '$.lr')::DOUBLE < 1) down
                           FROM edge WHERE predicate IN ({LRP}) AND json_extract(attrs, '$.lr') IS NOT NULL
                             AND json_extract_string(attrs, '$.lr') <> 'null' GROUP BY 1, 2, 3)
                SELECT count(*) FILTER (WHERE n > 1), count(*) FILTER (WHERE n > 1 AND (up OR down)),
                       count(*) FILTER (WHERE n > 1 AND NOT (up OR down)) FROM g""").fetchone())),
            "edges_listed": [f"{fn} [{json.loads(a).get('result') or json.loads(a).get('when')}] -> {dn}: LR {json.loads(a)['lr'] if json.loads(a)['lr'] is not None else 'range ' + str(json.loads(a)['lr_range'])}"
                             for p, fn, dn, a in con.execute(f"""SELECT e.predicate, nf.name, nd.name, e.attrs FROM edge e
                                 LEFT JOIN node nf ON nf.vocab = 'SCT' AND nf.code = e.s_code LEFT JOIN node nd ON nd.vocab = 'SCT' AND nd.code = e.o_code
                                 WHERE e.predicate IN ({LRP}) ORDER BY nd.name, json_extract(e.attrs, '$.lr')::DOUBLE DESC""").fetchall()]}

    # --- anatomy and organisms -------------------------------------------------------------------------------------
    hc = Path("reference/uberon_handcheck.json")
    if hc.exists() and con.execute("SELECT count(*) FROM edge WHERE predicate = 'uberon:sct_narrow_match'").fetchone()[0]:
        sc = json.load(open(hc))["scored"]
        k, n = sum(r["verdict"] == "correct" for r in sc), len(sc)
        lo, _ = wilson(k, n)
        con.execute("UPDATE edge SET tier = ? WHERE predicate = 'uberon:sct_narrow_match'", [tier(lo, n)])
        e, u, sct = con.execute("SELECT count(*), count(DISTINCT s_code), count(DISTINCT o_code) FROM edge WHERE predicate = 'uberon:sct_narrow_match'").fetchone()
        report["route:uberon->snomed (narrowMatch; hand check)"] = {"edges": e, "uberon_classes": u, "snomed_structures": sct,
            "hand_checked": n, "correct": k, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'radlex:anatomy_sct'").fetchone()[0]:
        # three code routes from RadLex to SNOMED CT, each tiered by its own hand check; the LOINC edges built on a route
        # (loinc:part_maps_to_sct, method 'RadLex anatomy: <route>') take that route's tier -- LOINC's own step is native
        sc = []
        for f in (Path("reference/radlex_handcheck.json"), Path("cache/umls/radlex_handcheck.json")):   # the UMLS half is git-ignored
            if f.exists():
                sc += json.load(open(f))["scored"]
        entry = {"edges_by_method": {m: {"edges": e, "radlex_terms": r, "snomed_structures": o} for m, e, r, o in con.execute(
                     "SELECT method, count(*), count(DISTINCT s_code), count(DISTINCT o_code) FROM edge WHERE predicate = 'radlex:anatomy_sct' GROUP BY 1 ORDER BY 1").fetchall()},
                 "hand_check": {}}
        for m in sorted({r["method"] for r in sc}):
            rs = [r for r in sc if r["method"] == m]
            k, n = sum(r["verdict"] == "correct" for r in rs), len(rs)
            lo, _ = wilson(k, n)
            con.execute("UPDATE edge SET tier = ? WHERE predicate = 'radlex:anatomy_sct' AND method = ?", [tier(lo, n), m])
            con.execute("UPDATE edge SET tier = ? WHERE predicate = 'loinc:part_maps_to_sct' AND method = ?", [tier(lo, n), "RadLex anatomy: " + m])
            entry["hand_check"][m] = {"checked": n, "correct": k, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
        # witness: where two routes answer for one RadLex term, is it the same SNOMED concept, or one is-a the other
        # ("Entire kidney" is-a "Structure of kidney")?
        con.execute("""CREATE TEMP TABLE rx AS SELECT DISTINCT s_code rid, o_code sct, method FROM edge WHERE predicate = 'radlex:anatomy_sct'""")
        con.execute("""CREATE TEMP TABLE rx_isa AS WITH RECURSIVE up(d, a) AS (
                SELECT DISTINCT sct, sct FROM rx
                UNION SELECT up.d, e.o_code FROM up JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = up.a)
            SELECT * FROM up""")
        entry["witness"] = [dict(zip(("route_a", "route_b", "radlex_terms_in_both", "same_concept", "is_a_related", "unrelated"), r))
                            for r in con.execute("""WITH p AS (SELECT DISTINCT a.method ma, b.method mb, a.rid FROM rx a JOIN rx b ON a.rid = b.rid AND a.method < b.method),
                  f AS (SELECT p.ma, p.mb, p.rid,
                          bool_or(a.sct = b.sct) same,
                          bool_or(EXISTS (SELECT 1 FROM rx_isa i WHERE (i.d = a.sct AND i.a = b.sct) OR (i.d = b.sct AND i.a = a.sct))) rel
                        FROM p JOIN rx a ON a.rid = p.rid AND a.method = p.ma JOIN rx b ON b.rid = p.rid AND b.method = p.mb GROUP BY 1, 2, 3)
                SELECT ma, mb, count(*), count(*) FILTER (WHERE same), count(*) FILTER (WHERE rel AND NOT same), count(*) FILTER (WHERE NOT rel)
                FROM f GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()]
        anat = """json_extract_string(attrs, '$.part_type') LIKE 'Rad.Anatomic Location.%' AND json_extract_string(attrs, '$.part_type') NOT LIKE '%Laterality%'"""
        entry["coverage"] = dict(zip(("loinc_radiology_terms", "with_an_anatomy_part", "reach_snomed_through_an_anatomy_part",
                                      "every_anatomy_part_reaches_snomed", "rsna_procedures", "rsna_procedures_reaching_snomed"), con.execute(f"""
            WITH lp AS (SELECT s_code, o_code FROM edge WHERE predicate = 'loinc:radlex_part' AND {anat}),
                 ok AS (SELECT DISTINCT s_code rid FROM edge WHERE predicate = 'radlex:anatomy_sct'),
                 rp AS (SELECT s_code, o_code FROM edge WHERE predicate = 'rsna:radlex_part'
                        AND (json_extract_string(attrs, '$.field') LIKE 'BODY_REGION%' OR json_extract_string(attrs, '$.field') LIKE 'ANATOMIC_FOCUS%'))
            SELECT (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'loinc:radlex_part'),
                   (SELECT count(DISTINCT s_code) FROM lp),
                   (SELECT count(DISTINCT s_code) FROM lp WHERE o_code IN (SELECT rid FROM ok)),
                   (SELECT count(*) FROM (SELECT s_code FROM lp GROUP BY 1 HAVING bool_and(o_code IN (SELECT rid FROM ok)))),
                   (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'rsna:radlex_part'),
                   (SELECT count(DISTINCT s_code) FROM rp WHERE o_code IN (SELECT rid FROM ok))""").fetchone()))
        entry["not_loaded"] = dict(con.execute("SELECT family, edges FROM build_log WHERE family LIKE 'RadLex -> SNOMED CT not loaded%' OR family LIKE 'RadLex anatomy%'").fetchall())
        report["route:radiology LOINC / RSNA -> RadLex -> SNOMED CT body structure"] = entry
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent'").fetchone()[0]:
        by = dict(con.execute("SELECT method, count(*) FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent' GROUP BY 1").fetchall())
        # the LOINC route is the witness: where both give an answer for a SNOMED organism, is it the same taxon?
        both, agree = con.execute("""WITH l AS (SELECT s_code, o_code FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent' AND method = 'LOINC part asserts both'),
                u AS (SELECT s_code, o_code FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent' AND method LIKE 'UMLS%')
            SELECT count(DISTINCT l.s_code), count(DISTINCT l.s_code) FILTER (WHERE EXISTS (SELECT 1 FROM u u2 WHERE u2.s_code = l.s_code AND u2.o_code = l.o_code))
            FROM l JOIN u ON u.s_code = l.s_code""").fetchone()
        ohc = Path("cache/umls/organism_handcheck.json")   # UMLS-derived pairs: git-ignored, not redistributed
        # NCBI keeps a genus (Salmonella, 590) and a placeholder for its unidentified isolates ("Salmonella sp.", 599): LOINC's part
        # "Salmonella sp" points at the placeholder, UMLS at the genus. That is a rank convention, not a disagreement about the organism.
        placeholder = con.execute("""WITH l AS (SELECT e.s_code, e.o_code, n.name FROM edge e LEFT JOIN node n ON n.vocab = 'NCBITAXON' AND n.code = e.o_code
                                     WHERE e.predicate = 'sct:ncbitaxon_equivalent' AND e.method = 'LOINC part asserts both'),
                u AS (SELECT s_code, o_code, json_extract_string(attrs, '$.ncbi_name') nm FROM edge
                      WHERE predicate = 'sct:ncbitaxon_equivalent' AND method LIKE 'UMLS%')
            SELECT count(DISTINCT l.s_code) FROM l JOIN u ON u.s_code = l.s_code
            WHERE NOT EXISTS (SELECT 1 FROM u u2 WHERE u2.s_code = l.s_code AND u2.o_code = l.o_code)
              AND lower(l.name) = lower(u.nm) || ' sp.'""").fetchone()[0]
        entry = {"edges_by_method": by, "loinc_witness": {"snomed_organisms_in_both": both, "same_taxon": agree,
                 "genus_vs_unidentified_species_placeholder": placeholder, "other_differences": both - agree - placeholder}}
        if ohc.exists():
            sc = json.load(open(ohc))["scored"]
            entry["umls_hand_check"] = {}
            for m in sorted({r["method"] for r in sc}):
                rs = [r for r in sc if r["method"] == m]
                k, n = sum(r["verdict"] == "correct" for r in rs), len(rs)
                lo, _ = wilson(k, n)
                con.execute("UPDATE edge SET tier = ? WHERE predicate = 'sct:ncbitaxon_equivalent' AND method = ?", [tier(lo, n), m])
                entry["umls_hand_check"][m] = {"checked": n, "correct": k, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
            entry["candidates_not_loaded"] = con.execute("""SELECT edges FROM build_log WHERE family LIKE 'SNOMED organism <-> NCBI Taxonomy candidates%'""").fetchone()
        report["route:snomed organism <-> NCBI Taxonomy"] = entry
        report["coverage:organisms and anatomy"] = dict(zip(("snomed_organisms_bridged", "ncbitaxa_reached", "mondo_diseases_with_agent",
                "mondo_diseases_with_location", "uberon_classes"), con.execute("""SELECT
            (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent'),
            (SELECT count(DISTINCT o_code) FROM edge WHERE predicate = 'sct:ncbitaxon_equivalent'),
            (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'mondo:disease_has_infectious_agent'),
            (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'mondo:disease_has_location'),
            (SELECT count(*) FROM node WHERE vocab = 'UBERON')""").fetchone()))

    # --- LOINC reach by class, and MBS ------------------------------------------------------------------------------
    lt_path = Path(os.path.join(ONT_ROOT, "Loinc_2.83/LoincTable/Loinc.csv"))
    if lt_path.exists():
        rows = con.execute(f"""WITH b AS (SELECT DISTINCT s_code c FROM edge WHERE s_vocab = 'LOINC' AND o_vocab NOT IN ('LOINC', 'UCUM', 'RADLEX', 'RPID')
                                    UNION SELECT DISTINCT o_code FROM edge WHERE o_vocab = 'LOINC' AND s_vocab <> 'LOINC'),
                 bp AS (SELECT DISTINCT s_code c FROM edge WHERE s_vocab = 'LOINC' AND o_vocab NOT IN ('LOINC', 'UCUM', 'RADLEX', 'RPID')
                          AND predicate <> 'loinc:part_maps_to_sct'
                        UNION SELECT DISTINCT o_code FROM edge WHERE o_vocab = 'LOINC' AND s_vocab <> 'LOINC')
            SELECT CLASSTYPE, count(*), count(*) FILTER (WHERE LOINC_NUM IN (SELECT c FROM bp)), count(*) FILTER (WHERE LOINC_NUM IN (SELECT c FROM b))
            FROM read_csv('{lt_path}', header=true, all_varchar=true) WHERE STATUS = 'ACTIVE' GROUP BY 1 ORDER BY 1""").fetchall()
        names = {"1": "laboratory", "2": "clinical", "3": "claims attachment", "4": "survey"}
        report["coverage:LOINC active terms bridged, by class"] = {names.get(c, c): {"terms": n, "before_part_route": b0, "with_part_route": b1}
                                                                  for c, n, b0, b1 in rows}
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'loinc:part_xref'").fetchone()[0] and lt_path.exists():
        # a medicine meets the test that measures it: LOINC's own RxNorm code for the analyte, and -- the witness -- LOINC's
        # ChEBI / UNII / PubChem code for it carried to RxNorm by DrugCentral's identifiers
        con.execute(f"""CREATE TEMP TABLE drug_test AS
            WITH au AS (SELECT DISTINCT o_code rxn FROM edge WHERE predicate = 'std_ingredient' AND o_vocab = 'RXN' AND state <> 'rejected'),
                 d AS (SELECT DISTINCT s_code loinc, o_code rxn, 'LOINC RxNorm code' AS route FROM edge WHERE predicate = 'loinc:part_xref' AND o_vocab = 'RXN'),
                 v AS (SELECT DISTINCT lx.s_code loinc, r.o_code rxn, 'LOINC ChEBI/UNII/PubChem -> DrugCentral' AS route
                       FROM edge lx JOIN edge x ON x.predicate = 'drugcentral:xref' AND x.o_vocab = lx.o_vocab AND x.o_code = lx.o_code
                       JOIN edge r ON r.predicate = 'drugcentral:rxnorm' AND r.s_code = x.s_code
                       WHERE lx.predicate = 'loinc:part_xref' AND lx.o_vocab IN ('CHEBI', 'UNII', 'PUBCHEM'))
            SELECT t.*, l.CLASS AS loinc_class, t.rxn IN (SELECT rxn FROM au) AS au_medicine
            FROM (SELECT * FROM d UNION SELECT * FROM v) t
            JOIN read_csv('{lt_path}', header=true, all_varchar=true) l ON l.LOINC_NUM = t.loinc""")
        both, agree = con.execute("""SELECT count(DISTINCT d.loinc), count(DISTINCT d.loinc) FILTER (WHERE EXISTS (SELECT 1 FROM drug_test v
                WHERE v.route <> 'LOINC RxNorm code' AND v.loinc = d.loinc AND v.rxn = d.rxn))
            FROM drug_test d WHERE d.route = 'LOINC RxNorm code' AND d.loinc IN (SELECT loinc FROM drug_test WHERE route <> 'LOINC RxNorm code')""").fetchone()
        report["coverage:medicines and the tests that measure them"] = {
            "au_rxnorm_ingredients_with_a_test": con.execute("SELECT count(DISTINCT rxn) FROM drug_test WHERE au_medicine").fetchone()[0],
            "loinc_tests": con.execute("SELECT count(DISTINCT loinc) FROM drug_test WHERE au_medicine").fetchone()[0],
            "by_loinc_class": dict(con.execute("""SELECT loinc_class, count(DISTINCT loinc) FROM drug_test WHERE au_medicine
                                                 GROUP BY 1 ORDER BY 2 DESC LIMIT 10""").fetchall()),
            "drug_level_tests_only (class DRUG/TOX)": dict(zip(("au_ingredients", "loinc_tests"), con.execute("""SELECT count(DISTINCT rxn),
                count(DISTINCT loinc) FROM drug_test WHERE au_medicine AND loinc_class = 'DRUG/TOX'""").fetchone())),
            "witness: tests both routes answer": both, "same drug": agree,
            "note": "the component is the drug for drug-level tests (DRUG/TOX) and also for susceptibility tests (ABXBACT: the organism against the drug); filter by class for levels"}
        report["coverage:analyte codes LOINC gives its terms"] = dict(con.execute("""SELECT o_vocab, count(DISTINCT s_code) FROM edge
            WHERE predicate = 'loinc:part_xref' GROUP BY 1 ORDER BY 2 DESC""").fetchall())
    sv = Path("reference/survey_instrument_candidates.json")
    if sv.exists():
        report["survey instruments: LOINC <-> SNOMED candidate frames (no edges)"] = json.load(open(sv))["summary"]
    mc = Path("reference/mbs_procedure_candidates.json")
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'mbs:in_group'").fetchone()[0]:
        m = {"items": con.execute("SELECT count(*) FROM edge WHERE predicate = 'mbs:in_group'").fetchone()[0], "snomed_edges": 0}
        if mc.exists():
            m["candidate_frames"] = json.load(open(mc)).get("summary")
        report["mbs:items and SNOMED candidates"] = m

    # --- US <-> Australian pathology units --------------------------------------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate IN ('loinc:au_preferred_unit', 'loinc:unit_counterpart')").fetchone()[0]:
        a = con.execute("""SELECT count(*), count(DISTINCT s_code),
                count(*) FILTER (WHERE json_extract(attrs, '$.differs_from_us_example')::BOOLEAN),
                count(*) FILTER (WHERE json_extract(attrs, '$.factor_us_example_to_au') IS NOT NULL
                                 AND json_extract_string(attrs, '$.factor_us_example_to_au') <> 'null'
                                 AND json_extract(attrs, '$.differs_from_us_example')::BOOLEAN)
            FROM edge WHERE predicate = 'loinc:au_preferred_unit'""").fetchone()
        side = dict(con.execute("""SELECT coalesce(json_extract_string(attrs, '$.au_preferred'), 'not in RCPA sets'), count(*)
            FROM edge WHERE predicate = 'loinc:unit_counterpart' GROUP BY 1 ORDER BY 2 DESC""").fetchall())
        f = con.execute("""SELECT count(*), count(*) FILTER (WHERE json_extract_string(attrs, '$.factor_mg_per_dL_to_mmol_per_L') <> 'null'
                AND json_extract(attrs, '$.factor_mg_per_dL_to_mmol_per_L') IS NOT NULL) FROM edge WHERE predicate = 'loinc:unit_counterpart'""").fetchone()
        diffs = dict(con.execute("""SELECT json_extract_string(attrs, '$.difference'), count(*) FROM edge
            WHERE predicate = 'loinc:au_preferred_unit' GROUP BY 1 ORDER BY 2 DESC""").fetchall())
        mal = con.execute("""SELECT count(*), count(DISTINCT o_code) FROM edge WHERE predicate = 'loinc:au_preferred_unit'
            AND json_extract_string(attrs, '$.rcpa_ucum_malformed') IS NOT NULL AND json_extract_string(attrs, '$.rcpa_ucum_malformed') <> 'null'""").fetchone()
        kinds = [f"{c} {n} (LOINC {us} / RCPA {au})" for c, n, us, au in con.execute("""SELECT e.s_code, n.name, json_extract_string(e.attrs, '$.us_example_ucum'), e.o_code
            FROM edge e LEFT JOIN node n ON n.vocab = 'LOINC' AND n.code = e.s_code WHERE e.predicate = 'loinc:au_preferred_unit'
              AND json_extract_string(e.attrs, '$.difference') = 'kind' ORDER BY 1""").fetchall()]
        report["units:US vs Australian (RCPA SPIA)"] = {"difference_from_loinc_us_example": diffs,
            "rcpa_ucum_malformed": {"edges": mal[0], "distinct_units": mal[1]}, "kind_differences_to_review": kinds,
            "loinc_au_preferred_unit_edges": a[0], "loinc_codes_with_au_unit": a[1],
            "au_unit_differs_from_loinc_us_example": a[2], "of_which_scale_only_with_factor": a[3],
            "mass_molar_pairs": f[0], "pairs_with_conversion_factor": f[1], "pairs_by_side_australia_reports": side}
        tu = Path("reference/threshold_units.json")
        if tu.exists():
            t = json.load(open(tu))
            report["units:likelihood-ratio thresholds"] = {"thresholds_with_units": len(t["thresholds"]), "conversion": t["summary"], "primacy": t.get("primacy")}

    # --- how a drug works: drug -> target -> protein -> gene -> disease ------------------------------------------
    # Native assertions (DrugCentral, HPO), so no earned tier; two independent witnesses are measured instead.
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'drugcentral:mechanism_target'").fetchone()[0]:
        report["witness:drug mechanism vs ChEMBL (independently sourced rows only)"] = dict(con.execute("""
            SELECT coalesce(json_extract_string(attrs, '$.chembl_witness'), 'not checked'), count(*) FROM edge
            WHERE predicate = 'drugcentral:mechanism_target' GROUP BY 1 ORDER BY 2 DESC""").fetchall())
        n, same = con.execute("""
            WITH d AS (SELECT DISTINCT o_code g, upper(json_extract_string(attrs, '$.gene_symbol')) s FROM edge WHERE predicate = 'uniprot:encoded_by'),
                 h AS (SELECT DISTINCT s_code g, upper(json_extract_string(attrs, '$.gene_symbol')) s FROM edge WHERE predicate = 'hpo:gene_disease')
            SELECT count(DISTINCT d.g), count(DISTINCT d.g) FILTER (WHERE d.s = h.s) FROM d JOIN h USING (g)""").fetchone()
        report["witness:gene id -> symbol, DrugCentral vs HPO"] = {"shared_gene_ids": n, "same_symbol": same,
            "note": "most differences are HGNC renames since DrugCentral 2023-11 (GBA -> GBA1)"}
        report["coverage:drug -> mechanism -> gene -> disease"] = dict(zip(
            ("drugs_with_mechanism", "reach_a_gene", "reach_a_genetic_disease", "reach_snomed_via_mondo"), con.execute("""
            WITH m AS (SELECT DISTINCT s_code drug, o_code tgt FROM edge WHERE predicate = 'drugcentral:mechanism_target'),
                 tg AS (SELECT DISTINCT c.s_code tgt, g.o_code gene FROM edge c JOIN edge g ON g.s_code = c.o_code
                        AND g.predicate = 'uniprot:encoded_by' WHERE c.predicate = 'drugcentral:target_component'),
                 gd AS (SELECT DISTINCT s_code gene, o_vocab dv, o_code dis FROM edge WHERE predicate = 'hpo:gene_disease'),
                 ms AS (SELECT DISTINCT x.o_vocab dv, x.o_code dis FROM edge x JOIN edge s ON s.s_code = x.s_code
                        AND s.predicate = 'mondo:exact_match' AND s.o_vocab = 'SCT' WHERE x.predicate = 'mondo:exact_match')
            SELECT (SELECT count(DISTINCT drug) FROM m), (SELECT count(DISTINCT drug) FROM m JOIN tg USING (tgt)),
                   (SELECT count(DISTINCT drug) FROM m JOIN tg USING (tgt) JOIN gd USING (gene)),
                   (SELECT count(DISTINCT drug) FROM m JOIN tg USING (tgt) JOIN gd USING (gene) JOIN ms USING (dv, dis))""").fetchone()))

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

    # --- genes, rare diseases, pathways: HGNC, Orphanet, Reactome ----------------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate IN ('hgnc:xref', 'orpha:xref', 'reactome:participates_in')").fetchone()[0]:
        e = {}
        # HGNC witnesses the gene <-> protein step DrugCentral's target components gave (uniprot:encoded_by)
        e["hgnc_witness_on_uniprot_encoded_by"] = dict(zip(("protein_gene_pairs", "hgnc_agrees", "hgnc_names_another_gene", "hgnc_silent"), con.execute("""
            WITH u AS (SELECT DISTINCT s_code up, o_code gene FROM edge WHERE predicate = 'uniprot:encoded_by'),
                 h AS (SELECT DISTINCT a.o_code up, b.o_code gene FROM edge a JOIN edge b ON b.predicate = 'hgnc:xref' AND b.s_code = a.s_code
                       AND b.o_vocab = 'NCBIGENE' WHERE a.predicate = 'hgnc:xref' AND a.o_vocab = 'UNIPROT')
            SELECT count(*), count(*) FILTER (WHERE (up, gene) IN (SELECT up, gene FROM h)),
                   count(*) FILTER (WHERE (up, gene) NOT IN (SELECT up, gene FROM h) AND up IN (SELECT up FROM h)),
                   count(*) FILTER (WHERE up NOT IN (SELECT up FROM h)) FROM u""").fetchone()))
        # Orphanet's alignment against MONDO's, both directions of one claim
        e["orphanet_vs_mondo"] = dict(zip(("orpha_mondo_pairs_by_orphanet", "also_asserted_by_mondo", "orpha_codes_mondo_maps", "orphanet_agrees_exactly"), con.execute("""
            WITH o AS (SELECT DISTINCT s_code orpha, o_code mondo, method FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'MONDO'),
                 m AS (SELECT DISTINCT s_code mondo, o_code orpha FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab = 'ORPHA')
            SELECT count(*), count(*) FILTER (WHERE (orpha, mondo) IN (SELECT orpha, mondo FROM m)),
                   (SELECT count(DISTINCT orpha) FROM m),
                   (SELECT count(DISTINCT m.orpha) FROM m JOIN o USING (orpha, mondo) WHERE o.method = 'E') FROM o""").fetchone()))
        e["orphanet_alignments_by_target_and_relation"] = [dict(zip(("target", "relation", "edges"), r)) for r in con.execute("""
            SELECT o_vocab, method, count(*) FROM edge WHERE predicate = 'orpha:xref' GROUP BY 1, 2 ORDER BY 1, 3 DESC""").fetchall()]
        # pathways: which medicines and diseases now reach one
        e["pathway_reach"] = dict(zip(("human_proteins_with_a_pathway", "pathways", "drugcentral_drugs_reaching_a_pathway",
                                       "au_rxnorm_ingredients_reaching_a_pathway", "diseases_reaching_a_pathway_through_a_gene"), con.execute("""
            WITH pp AS (SELECT DISTINCT s_code up FROM edge WHERE predicate = 'reactome:participates_in'),
                 dt AS (SELECT DISTINCT m.s_code dc FROM edge m JOIN edge c ON c.predicate = 'drugcentral:target_component' AND c.s_code = m.o_code
                        WHERE m.predicate IN ('drugcentral:mechanism_target', 'drugcentral:bioactivity') AND c.o_code IN (SELECT up FROM pp)),
                 au AS (SELECT DISTINCT o_code rxn FROM edge WHERE predicate = 'std_ingredient' AND o_vocab = 'RXN' AND state <> 'rejected'),
                 gp AS (SELECT DISTINCT g.o_code gene FROM edge h JOIN edge g ON g.predicate = 'hgnc:xref' AND g.s_code = h.s_code AND g.o_vocab = 'NCBIGENE'
                        WHERE h.predicate = 'hgnc:xref' AND h.o_vocab = 'UNIPROT' AND h.o_code IN (SELECT up FROM pp))
            SELECT (SELECT count(*) FROM pp), (SELECT count(DISTINCT o_code) FROM edge WHERE predicate = 'reactome:participates_in'),
                   (SELECT count(*) FROM dt),
                   (SELECT count(DISTINCT r.o_code) FROM edge r WHERE r.predicate = 'drugcentral:rxnorm' AND r.s_code IN (SELECT dc FROM dt)
                      AND r.o_code IN (SELECT rxn FROM au)),
                   (SELECT count(DISTINCT o_vocab || o_code) FROM edge WHERE predicate = 'hpo:gene_disease' AND s_code IN (SELECT gene FROM gp))""").fetchone()))
        report["genes, rare diseases, pathways (HGNC, Orphanet, Reactome)"] = e

    # --- WHO ICD-10 <-> ICD-11 ----------------------------------------------------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate LIKE 'who:%'").fetchone()[0]:
        w = {"edges": dict(con.execute("SELECT predicate || ' / ' || method, count(*) FROM edge WHERE predicate LIKE 'who:%' GROUP BY 1 ORDER BY 1").fetchall())}
        # witness 1: a rare disease Orphanet codes in both ICD-10 and ICD-11 -- does WHO's table carry its ICD-11 code to
        # the same ICD-10 code (or to the 3-character category above it)?
        # witness 1: a rare disease Orphanet codes in both ICD-10 and ICD-11 -- does WHO's table carry its ICD-11 code to the
        # same ICD-10 code (or the 3-character category above it)? Split by Orphanet's relations: only E/E should agree.
        w["orphanet_icd10_vs_who_map_by_relation (icd11 / icd10)"] = {f"{m11}/{m10}": dict(zip(("orpha_codes", "who_same_code",
                "who_same_3_character_category"), (n, k, c))) for m11, m10, n, k, c in con.execute("""
            WITH o10 AS (SELECT s_code o, o_code c10, method m10 FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'ICD10WHO'),
                 o11 AS (SELECT s_code o, o_code c11, method m11 FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'ICD11MMS'),
                 w AS (SELECT s_code c11, o_code c10 FROM edge WHERE predicate = 'who:icd11_to_icd10' AND s_vocab = 'ICD11MMS'),
                 j AS (SELECT o11.o, m11, m10, bool_or(w.c10 = o10.c10) same, bool_or(left(w.c10, 3) = left(o10.c10, 3)) cat
                       FROM o11 JOIN o10 USING (o) JOIN w USING (c11) GROUP BY 1, 2, 3)
            SELECT m11, m10, count(*), count(*) FILTER (WHERE same), count(*) FILTER (WHERE cat) FROM j GROUP BY 1, 2 ORDER BY 3 DESC""").fetchall()}
        # witness 2: MONDO's ICD-11 foundation id and Orphanet's MMS code for the same disease, by Orphanet's relation --
        # an NTBT code linearises a broader entity by definition, so only E should agree
        w["mondo_foundation_vs_orphanet_mms_by_relation"] = {m: {"diseases": n, "mms_code_linearises_mondos_entity": k} for m, n, k in con.execute("""
            WITH p AS (SELECT s_code mondo, o_code orpha FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab = 'ORPHA'),
                 mf AS (SELECT s_code mondo, o_code f FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab = 'ICD11'),
                 om AS (SELECT s_code orpha, o_code m, method FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'ICD11MMS'),
                 lin AS (SELECT s_code m, o_code f FROM edge WHERE predicate = 'who:icd11_mms_foundation')
            SELECT om.method, count(DISTINCT p.mondo), count(DISTINCT p.mondo) FILTER (WHERE (om.m, mf.f) IN (SELECT m, f FROM lin))
            FROM p JOIN mf USING (mondo) JOIN om USING (orpha) GROUP BY 1 ORDER BY 2 DESC""").fetchall()}
        w["reach"] = dict(zip(("icd10_codes_in_graph", "reaching_icd11", "mondo_diseases_reaching_icd10_through_icd11"), con.execute("""
            SELECT (SELECT count(*) FROM node WHERE vocab = 'ICD10WHO'),
                   (SELECT count(DISTINCT s_code) FROM edge WHERE predicate = 'who:icd10_to_icd11'),
                   (SELECT count(DISTINCT m.s_code) FROM edge m JOIN edge w ON w.predicate = 'who:icd11_to_icd10' AND w.s_vocab = 'ICD11'
                      AND w.s_code = m.o_code WHERE m.predicate = 'mondo:exact_match' AND m.o_vocab = 'ICD11')""").fetchone()))
        report["who:ICD-10 <-> ICD-11 (WHO mapping tables 2026-01)"] = w

    # --- UMLS Metathesaurus shared-CUI pairs: a tier per vocabulary pair ---------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'umls:shared_cui'").fetchone()[0]:
        uh = Path("cache/umls/umls_shared_cui_handcheck.json")       # UMLS-derived: git-ignored
        sc = json.load(open(uh))["scored"] if uh.exists() else []
        fam = {}
        for m in sorted({r["method"] for r in sc if not r.get("pool")}):
            rs = [r for r in sc if r["method"] == m and not r.get("pool")]
            k, n = sum(r["verdict"] == "correct" for r in rs), len(rs)
            fam[m] = (k, n, "hand check")
        for pool in sorted({r["pool"] for r in sc if r.get("pool")}):   # small families checked as one stratified sample
            rs = [r for r in sc if r.get("pool") == pool]
            k, n = sum(r["verdict"] == "correct" for r in rs), len(rs)
            for m in {r["method"] for r in rs}:
                fam[m] = (k, n, f"pooled hand check ({pool})")
        # HGNC -> OMIM: HGNC's own cross-references are the witness
        k, n = con.execute("""WITH u AS (SELECT s_code h, o_code o FROM edge WHERE predicate = 'umls:shared_cui' AND method = 'HGNC-OMIM same name'),
                                   x AS (SELECT s_code h, o_code o FROM edge WHERE predicate = 'hgnc:xref' AND o_vocab = 'OMIM')
                              SELECT count(*) FILTER (WHERE (h, o) IN (SELECT h, o FROM x)), count(*) FILTER (WHERE h IN (SELECT h FROM x)) FROM u""").fetchone()
        if n:
            fam["HGNC-OMIM same name"] = (k, n, "agreement with HGNC's own OMIM cross-reference")
        by = {}
        for m, e in con.execute("SELECT method, count(*) FROM edge WHERE predicate = 'umls:shared_cui' GROUP BY 1 ORDER BY 2 DESC").fetchall():
            if m in fam:
                k, n, how = fam[m]
                lo, _ = wilson(k, n)
                con.execute("UPDATE edge SET tier = ? WHERE predicate = 'umls:shared_cui' AND method = ?", [tier(lo, n), m])
                by[m] = {"edges": e, "checked": n, "correct": k, "how": how, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
            else:
                by[m] = {"edges": e, "earned_tier": "ungraded (no hand check yet)"}
        con.execute("CREATE TEMP TABLE uhc (m VARCHAR, s VARCHAR, o VARCHAR)")
        con.executemany("INSERT INTO uhc VALUES (?, ?, ?)", [(r["method"], r["s"], r["o"]) for r in sc if r["verdict"] != "correct"])
        con.execute("""UPDATE edge SET state = 'rejected' WHERE predicate = 'umls:shared_cui' AND (method, s_code, o_code) IN (SELECT m, s, o FROM uhc)""")
        report["route:UMLS shared CUI (MRCONSO 2026AA), by vocabulary pair"] = {
            "families": by,
            "candidates_names_differ": con.execute("SELECT edges FROM build_log WHERE family LIKE 'UMLS shared CUI, names differ%'").fetchone(),
            "edges_graded": sum(v["edges"] for v in by.values() if "checked" in v), "edges_ungraded": sum(v["edges"] for v in by.values() if "checked" not in v),
            "rejected_by_hand_check": con.execute("SELECT count(*) FROM edge WHERE predicate = 'umls:shared_cui' AND state = 'rejected'").fetchone()[0]}

    # --- UMLS concept -> its SNOMED CT disorders and findings: one family, one hand check ---------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'umls:concept_member'").fetchone()[0]:
        ch = Path("cache/umls/umls_concept_member_handcheck.json")    # UMLS-derived: git-ignored
        hc = json.load(open(ch)) if ch.exists() else {"scored": [], "rejected_by_name": []}
        k, n = sum(r["verdict"] == "correct" for r in hc["scored"]), len(hc["scored"])
        cm = {"edges": con.execute("SELECT count(*) FROM edge WHERE predicate = 'umls:concept_member'").fetchone()[0], "checked": n, "correct": k}
        if n:
            lo, _ = wilson(k, n)
            con.execute("UPDATE edge SET tier = ? WHERE predicate = 'umls:concept_member'", [tier(lo, n)])
            cm.update(wilson_lo=round(lo, 4), earned_tier=tier(lo, n))
        bad = [(r["cui"], r["sct"]) for r in hc["scored"] if r["verdict"] != "correct"] + [(r["cui"], r["sct"]) for r in hc.get("rejected_by_name", [])]
        for c_, s_ in bad:
            con.execute("UPDATE edge SET state = 'rejected' WHERE predicate = 'umls:concept_member' AND s_code = ? AND o_code = ?", [c_, s_])
        cm["rejected_by_name"] = len(bad)
        cm["orphanet_disorders_reaching_snomed_only_this_way"] = con.execute("""WITH via AS (SELECT DISTINCT x.s_code o FROM edge x
                JOIN edge m ON m.predicate = 'umls:concept_member' AND m.s_code = x.o_code AND m.state <> 'rejected'
                WHERE x.predicate = 'orpha:xref' AND x.o_vocab = 'UMLS')
            SELECT count(*) FROM via WHERE o NOT IN (SELECT s_code FROM edge WHERE s_vocab = 'ORPHA' AND o_vocab = 'SCT'
                                                     UNION SELECT o_code FROM edge WHERE o_vocab = 'ORPHA' AND s_vocab = 'SCT')""").fetchone()[0]
        report["route:UMLS concept -> SNOMED CT (MRCONSO 2026AA)"] = cm

    # --- Orphanet -> ICD-10 through SNOMED CT's map: a chain family, tiered by census, witnessed by Orphanet itself ------
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'orpha:icd10_via_snomed'").fetchone()[0]:
        cf = Path("cache/orphanet/orpha_icd10_chain_census.json")      # SNOMED / UMLS-derived names: git-ignored
        cs = json.load(open(cf))["census"] if cf.exists() else []
        con.execute("CREATE TEMP TABLE och (o VARCHAR, i VARCHAR, ok BOOLEAN)")
        con.executemany("INSERT INTO och VALUES (?, ?, ?)", sorted({(r["orpha"], r["icd10"], r["verdict"] == "correct") for r in cs}))
        pairs = con.execute("SELECT DISTINCT s_code, o_code FROM edge WHERE predicate = 'orpha:icd10_via_snomed'").fetchall()
        k, n = con.execute("""SELECT count(*) FILTER (WHERE h.ok), count(*) FROM (SELECT DISTINCT s_code, o_code FROM edge
                              WHERE predicate = 'orpha:icd10_via_snomed') e JOIN och h ON h.o = e.s_code AND h.i = e.o_code""").fetchone()
        ch = {"edges": con.execute("SELECT count(*) FROM edge WHERE predicate = 'orpha:icd10_via_snomed'").fetchone()[0],
              "orphanet_disorders": len({p_ for p_, _ in pairs}), "pairs": len(pairs), "census_pairs_checked": n, "correct": k}
        if n:
            lo, _ = wilson(k, n)
            t_ = tier(lo, n) if n >= len(pairs) or n >= 30 else "ungraded"
            con.execute("UPDATE edge SET tier = ? WHERE predicate = 'orpha:icd10_via_snomed'", [t_])
            con.execute("""UPDATE edge SET state = 'rejected' WHERE predicate = 'orpha:icd10_via_snomed'
                           AND (s_code, o_code) IN (SELECT o, i FROM och WHERE NOT ok)""")
            ch.update(wilson_lo=round(lo, 4), earned_tier=t_, unchecked_pairs=len(pairs) - n)
        # witness: where Orphanet has its own exact ICD-10 code, what the same chain (without the gap filter) gives
        ch["witness_orphanet_exact_codes"] = dict(zip(("disorders", "same_code", "same_3_character_category"), con.execute("""
            WITH o2s AS (SELECT DISTINCT x.s_code orpha, m.o_code sct FROM edge x JOIN edge m ON m.predicate = 'umls:concept_member'
                             AND m.s_code = x.o_code AND m.state <> 'rejected' WHERE x.predicate = 'orpha:xref' AND x.o_vocab = 'UMLS' AND x.method = 'E'
                         UNION SELECT DISTINCT x.s_code, e.o_code FROM edge x JOIN edge e ON e.predicate = 'mondo:exact_match' AND e.s_code = x.o_code
                             AND e.o_vocab = 'SCT' WHERE x.predicate = 'orpha:xref' AND x.o_vocab = 'MONDO' AND x.method = 'E'),
                 single AS (SELECT s_code FROM edge WHERE predicate = 'sct:icd10_map' GROUP BY 1
                            HAVING max(CAST(attrs->>'group' AS INT)) = 1 AND bool_and(method = 'unconditional')),
                 via AS (SELECT DISTINCT o.orpha, i.o_code icd FROM o2s o JOIN edge i ON i.predicate = 'sct:icd10_map' AND i.s_code = o.sct
                         WHERE i.s_code IN (SELECT s_code FROM single)),
                 own AS (SELECT DISTINCT s_code orpha, o_code icd FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'ICD10WHO' AND method = 'E')
            SELECT count(DISTINCT own.orpha), count(DISTINCT own.orpha) FILTER (WHERE (own.orpha, own.icd) IN (SELECT orpha, icd FROM via)),
                   count(DISTINCT own.orpha) FILTER (WHERE EXISTS (SELECT 1 FROM via v WHERE v.orpha = own.orpha AND left(v.icd, 3) = left(own.icd, 3)))
            FROM own WHERE own.orpha IN (SELECT orpha FROM via)""").fetchone()))
        report["chain:Orphanet -> ICD-10 via SNOMED CT's map"] = ch

    # --- Orphanet's own gene and phenotype files beside HPO's relay of them --------------------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate IN ('orpha:gene_disease', 'orpha:has_phenotype')").fetchone()[0]:
        og = {}
        og["genes_by_involvement"] = dict(con.execute("""SELECT method, count(*) FROM edge WHERE predicate = 'orpha:gene_disease'
                                                         GROUP BY 1 ORDER BY 2 DESC""").fetchall())
        og["phenotypes_by_frequency"] = dict(con.execute("""SELECT method, count(*) FROM edge WHERE predicate IN ('orpha:has_phenotype', 'orpha:lacks_phenotype')
                                                           GROUP BY 1 ORDER BY 2 DESC""").fetchall())
        og["diagnostic_criteria"] = dict(con.execute("""SELECT attrs->>'diagnostic_criteria', count(*) FROM edge WHERE predicate = 'orpha:has_phenotype'
                                                       AND (attrs->>'diagnostic_criteria') IS NOT NULL GROUP BY 1""").fetchall())
        og["witness_hpo_relay_phenotypes"] = dict(zip(("orphanet_pairs", "also_in_hpo_annotations", "hpo_orpha_pairs", "also_in_orphanet"), con.execute("""
            WITH o AS (SELECT DISTINCT s_code d, o_code h FROM edge WHERE predicate = 'orpha:has_phenotype'),
                 h AS (SELECT DISTINCT s_code d, o_code h FROM edge WHERE predicate = 'hpo:has_phenotype' AND s_vocab = 'ORPHA')
            SELECT (SELECT count(*) FROM o), (SELECT count(*) FROM o WHERE (d, h) IN (SELECT d, h FROM h)),
                   (SELECT count(*) FROM h), (SELECT count(*) FROM h WHERE (d, h) IN (SELECT d, h FROM o))""").fetchone()))
        og["witness_hpo_relay_genes"] = dict(zip(("orphanet_pairs", "also_in_hpo_genes_to_disease"), con.execute("""
            WITH o AS (SELECT DISTINCT x.o_code gene, e.o_code d FROM edge e JOIN edge x ON x.predicate = 'hgnc:xref' AND x.s_code = e.s_code AND x.o_vocab = 'NCBIGENE'
                       WHERE e.predicate = 'orpha:gene_disease'),
                 h AS (SELECT DISTINCT s_code gene, o_code d FROM edge WHERE predicate = 'hpo:gene_disease' AND o_vocab = 'ORPHA')
            SELECT (SELECT count(*) FROM (SELECT DISTINCT s_code, o_code FROM edge WHERE predicate = 'orpha:gene_disease')),
                   (SELECT count(*) FROM o WHERE (gene, d) IN (SELECT gene, d FROM h))""").fetchone()))
        og["stated_absences"] = con.execute("SELECT count(*) FROM edge WHERE predicate = 'orpha:lacks_phenotype'").fetchone()[0]
        report["orphanet:genes and phenotypes (products 6 and 4)"] = og

    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'ccsr:category'").fetchone()[0]:
        report["classification:ICD-10-CM -> AHRQ CCSR categories"] = dict(zip(("edges", "icd10cm_codes_classified", "of_icd10cm_codes_in_graph",
                "categories", "body_systems", "codes_in_more_than_one_category"), con.execute("""
            WITH c AS (SELECT * FROM edge WHERE predicate = 'ccsr:category')
            SELECT count(*), count(DISTINCT s_code), (SELECT count(*) FROM node WHERE vocab = 'ICD10CM'), count(DISTINCT o_code),
                   count(DISTINCT left(o_code, 3)),
                   (SELECT count(*) FROM (SELECT s_code FROM c WHERE method = 'classified_as' GROUP BY 1 HAVING count(DISTINCT o_code) > 1))
            FROM c""").fetchone()))

    # --- UMLS relationships: sources' own hierarchies (native) and MED-RT (hand check + DrugCentral witness) ---------
    if con.execute("SELECT count(*) FROM edge WHERE predicate LIKE 'medrt:%' OR predicate = 'umls:source_parent'").fetchone()[0]:
        mh = Path("cache/umls/umls_medrt_handcheck.json")        # UMLS-derived: git-ignored
        sc = json.load(open(mh))["scored"] if mh.exists() else []
        con.execute("CREATE TEMP TABLE mhc (predicate VARCHAR, s VARCHAR, ov VARCHAR, o VARCHAR, correct BOOLEAN)")
        con.executemany("INSERT INTO mhc VALUES (?, ?, ?, ?, ?)", [(r["predicate"], r["rxn"], r["o_vocab"], r["o_code"], r["verdict"] == "correct") for r in sc])
        checked = {(p_, m_): (k, n) for p_, m_, k, n in con.execute("""SELECT e.predicate, e.method, count(*) FILTER (WHERE h.correct), count(*)
            FROM mhc h JOIN edge e ON e.predicate = h.predicate AND e.s_code = h.s AND e.o_vocab = h.ov AND e.o_code = h.o GROUP BY 1, 2""").fetchall()}
        med = {}
        for pred, m_, e in con.execute("SELECT predicate, method, count(*) FROM edge WHERE predicate LIKE 'medrt:%' GROUP BY 1, 2 ORDER BY 1, 3 DESC").fetchall():
            key = pred + (" [" + m_.split('; ', 1)[1] + "]" if '; ' in m_ else "")
            if (pred, m_) in checked:
                k, n = checked[(pred, m_)]
                lo, _ = wilson(k, n)
                con.execute("UPDATE edge SET tier = ? WHERE predicate = ? AND method = ?", [tier(lo, n), pred, m_])
                med[key] = {"edges": e, "checked": n, "correct": k, "wilson_lo": round(lo, 4), "earned_tier": tier(lo, n)}
            else:
                med[key] = {"edges": e, "earned_tier": "ungraded (no hand check yet)"}
        # every edge a hand check found wrong is rejected by name: kept, never followed
        con.execute("""UPDATE edge SET state = 'rejected' WHERE predicate LIKE 'medrt:%'
                       AND (predicate, s_code, o_vocab, o_code) IN (SELECT predicate, s, ov, o FROM mhc WHERE NOT correct)""")
        med["rejected_by_hand_check"] = con.execute("SELECT count(*) FROM edge WHERE predicate LIKE 'medrt:%' AND state = 'rejected'").fetchone()[0]
        fda = con.execute("SELECT method, count(*), count(DISTINCT s_code), count(DISTINCT o_code) FROM edge WHERE predicate = 'fda:pharmacologic_class' GROUP BY 1").fetchall()
        med["fda_route (native)"] = {m_: {"edges": e, "drugs": d, "classes": c} for m_, e, d, c in fda}
        wit = {}
        for m_, d_ in (("medrt:may_treat", "drugcentral:indication"), ("medrt:contraindicated_with", "drugcentral:contraindication")):
            wit[m_ + " vs " + d_] = dict(zip(("drugs_in_both", "medrt_edges_for_them", "same_snomed_concept", "is_a_related"), con.execute(f"""
                WITH m AS (SELECT DISTINCT s_code rxn, o_code sct FROM edge WHERE predicate = '{m_}' AND o_vocab = 'SCT'),
                     d AS (SELECT DISTINCT r.o_code rxn, i.o_code sct FROM edge i JOIN edge r ON r.predicate = 'drugcentral:rxnorm' AND r.s_code = i.s_code
                           WHERE i.predicate = '{d_}'),
                     mm AS (SELECT * FROM m WHERE rxn IN (SELECT rxn FROM d)),
                     isa AS (SELECT s_code c, o_code p FROM edge WHERE predicate = 'sct:116680003')
                SELECT (SELECT count(DISTINCT rxn) FROM mm), count(*), count(*) FILTER (WHERE (rxn, sct) IN (SELECT rxn, sct FROM d)),
                       count(*) FILTER (WHERE (rxn, sct) NOT IN (SELECT rxn, sct FROM d) AND EXISTS (SELECT 1 FROM d JOIN isa
                           ON (isa.c = d.sct AND isa.p = mm.sct) OR (isa.p = d.sct AND isa.c = mm.sct) WHERE d.rxn = mm.rxn))
                FROM mm""").fetchone()))
        report["route:UMLS relationships (MRREL 2026AA Level 0)"] = {
            "source_hierarchies (native)": dict(con.execute("""SELECT method, count(*) FROM edge WHERE predicate = 'umls:source_parent'
                                                                GROUP BY 1 ORDER BY 2 DESC""").fetchall()),
            "medrt": med, "medrt_witness_drugcentral": wit,
            "note": "DrugCentral is label-based and narrower than MED-RT; its silence is not disagreement (unknown, not 'no')"}

    # --- SNOMED CT-AU reference sets: how much of each set reaches beyond SNOMED ----------------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate = 'sct:in_refset'").fetchone()[0]:
        con.execute("""CREATE TEMP TABLE sct_out AS SELECT DISTINCT s_code c FROM edge WHERE s_vocab = 'SCT' AND o_vocab <> 'SCT'
                       UNION SELECT DISTINCT o_code FROM edge WHERE o_vocab = 'SCT' AND s_vocab <> 'SCT'""")
        rs = con.execute("""SELECT method, count(*), count(*) FILTER (WHERE s_code IN (SELECT c FROM sct_out))
                            FROM edge WHERE predicate = 'sct:in_refset' GROUP BY 1 ORDER BY 2 DESC""").fetchall()
        # medicines regulation, on the products the compendium carries and the PBS lists
        reg = con.execute("""WITH m AS (SELECT s_code, method FROM edge WHERE predicate = 'sct:in_refset'
                                 AND (method LIKE '%Schedule 8%' OR method LIKE '%Black Triangle%' OR method LIKE '%Brand Consideration%'
                                      OR method LIKE '%Excluded Medicinal Items%' OR method LIKE '%Schedule 4%')),
                  pbs AS (SELECT DISTINCT s_code c FROM edge WHERE predicate = 'pbs:lists')
            SELECT method, count(DISTINCT s_code), count(DISTINCT s_code) FILTER (WHERE s_code IN (SELECT c FROM pbs))
            FROM m GROUP BY 1 ORDER BY 1""").fetchall()
        report["refsets:SNOMED CT-AU reference set membership"] = {
            "reference_sets": len(rs), "memberships": sum(r[1] for r in rs),
            "not_loaded_inactive_members": con.execute("SELECT edges FROM build_log WHERE family LIKE 'SNOMED CT-AU reference set members not loaded%'").fetchone(),
            "members_reaching_another_vocabulary": {m: {"members": n, "reach_outside_snomed": k, "share": round(k / n, 3)} for m, n, k in rs},
            "medicines_regulation_on_pbs": {m: {"concepts": n, "pbs_listed": k} for m, n, k in reg}}

    # --- SNOMED CT -> ICD-10 / ICD-10-CM maps (US Edition): what they add, and two witnesses -------------------------
    if con.execute("SELECT count(*) FROM edge WHERE predicate IN ('sct:icd10_map', 'sct:icd10cm_map')").fetchone()[0]:
        by = con.execute("""SELECT predicate, method, count(*), count(DISTINCT s_code), count(DISTINCT o_code) FROM edge
                            WHERE predicate IN ('sct:icd10_map', 'sct:icd10cm_map') GROUP BY 1, 2 ORDER BY 1, 3 DESC""").fetchall()
        # diagnosis reference sets: members reaching WHO ICD-10 by this map, by any other route, and on to ICD-11
        sets = ("Problem/Diagnosis reference set", "Australian emergency department principal diagnosis reference set for ED funding",
                "Emergency department diagnosis reference set")
        reach = {}
        for s_ in sets:
            n, via_map, other, icd11 = con.execute(f"""WITH m AS (SELECT DISTINCT s_code c FROM edge WHERE predicate = 'sct:in_refset' AND method = ?),
                    mp AS (SELECT DISTINCT s_code c, o_code icd FROM edge WHERE predicate = 'sct:icd10_map'),
                    oth AS (SELECT DISTINCT s_code c FROM edge WHERE s_vocab = 'SCT' AND o_vocab = 'ICD10WHO' AND predicate <> 'sct:icd10_map'
                            UNION SELECT DISTINCT o_code FROM edge WHERE o_vocab = 'SCT' AND s_vocab = 'ICD10WHO'),
                    w AS (SELECT DISTINCT s_code icd FROM edge WHERE predicate = 'who:icd10_to_icd11'
                          UNION SELECT DISTINCT d.s_code FROM edge d JOIN edge x ON x.predicate = 'who:icd10_to_icd11' AND x.s_code = d.o_code
                          WHERE d.predicate = 'icd10:subdivision_of')
                SELECT count(*), count(*) FILTER (WHERE c IN (SELECT c FROM mp)), count(*) FILTER (WHERE c IN (SELECT c FROM oth)),
                       count(*) FILTER (WHERE c IN (SELECT mp.c FROM mp JOIN w ON w.icd = mp.icd)) FROM m""", [s_]).fetchone()
            reach[s_] = {"members": n, "reach_icd10_by_map": n and round(via_map / n, 3), "reach_icd10_by_other_routes": n and round(other / n, 3),
                         "reach_icd11_via_map_then_who": n and round(icd11 / n, 3)}
        # witness 1: NLM's ICD-10-CM map against OMOP's ICD-10-CM -> SNOMED (reverse direction, separate source)
        w1 = con.execute("""WITH nlm AS (SELECT DISTINCT s_code sct, o_code icd FROM edge WHERE predicate = 'sct:icd10cm_map' AND method = 'unconditional'),
                omop AS (SELECT DISTINCT o_code sct, s_code icd FROM edge WHERE predicate = 'icd10cm:maps_to')
            SELECT count(*), count(*) FILTER (WHERE icd IN (SELECT icd FROM omop)),
                   count(*) FILTER (WHERE (sct, icd) IN (SELECT (sct, icd) FROM omop)) FROM nlm""").fetchone()
        # witness 2: ICD-10-CM extends WHO ICD-10, so a concept's two maps should share the three-character category
        w2 = con.execute("""WITH a AS (SELECT DISTINCT s_code c, left(o_code, 3) k FROM edge WHERE predicate = 'sct:icd10_map' AND method = 'unconditional'),
                b AS (SELECT DISTINCT s_code c, left(o_code, 3) k FROM edge WHERE predicate = 'sct:icd10cm_map' AND method = 'unconditional'),
                both_ AS (SELECT DISTINCT c FROM a WHERE c IN (SELECT c FROM b))
            SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM a JOIN b ON b.c = a.c AND b.k = a.k WHERE a.c = both_.c)) FROM both_""").fetchone()
        report["maps:SNOMED CT -> ICD-10 / ICD-10-CM (US Edition 20260901)"] = {
            "edges": {f"{p} | {m}": {"edges": e, "snomed_concepts": s, "icd_codes": o} for p, m, e, s, o in by},
            "not_loaded": {k: v for k, v in con.execute("""SELECT family, edges FROM build_log WHERE family LIKE 'SNOMED CT -> ICD-10%not loaded%'
                                                            OR family LIKE 'ICD-10 mapped codes absent%'""").fetchall()},
            "icd10_fifth_character_parents": con.execute("SELECT count(*) FROM edge WHERE predicate = 'icd10:subdivision_of'").fetchone()[0],
            "diagnosis_refsets": reach,
            "witness_omop_icd10cm": {"nlm_unconditional_pairs": w1[0], "icd_code_mapped_by_omop": w1[1], "same_pair_in_omop": w1[2],
                                     "note": "OMOP maps ICD-10-CM up to one concept; NLM maps each concept to its code -- a pair OMOP lacks is unknown, not wrong"},
            "witness_icd10_vs_icd10cm_category": {"concepts_with_both": w2[0], "share_a_3_character_category": w2[1],
                                                  "share": w2[0] and round(w2[1] / w2[0], 3)},
            "tier": "native: each map is its publisher's own assertion (SNOMED International; NLM)"}

    # --- equivalence edges that bridge a one-to-one conflict, hand-checked (scripts/consistency.py) -------------------
    bh = Path("cache/consistency/bridge_handcheck.json")          # licensed codes and names: git-ignored
    if bh.exists():
        bs = json.load(open(bh))["scored"]
        bad = [(r["s"], r["o"], r["predicate"]) for r in bs if r["verdict"] != "correct"]
        for s_, o_, p_ in bad:
            con.execute("""UPDATE edge SET state = 'rejected' WHERE predicate = ? AND ((s_vocab || ':' || s_code = ? AND o_vocab || ':' || o_code = ?)
                           OR (s_vocab || ':' || s_code = ? AND o_vocab || ':' || o_code = ?))""", [p_, s_, o_, o_, s_])
        rnd = [r for r in bs if r["sample"].startswith("30 random")]
        report["consistency:bridge hand check"] = {
            "checked": len(bs), "wrong_rejected_by_name": len(bad),
            "random_umls_bridges": {"checked": len(rnd), "correct": sum(r["verdict"] == "correct" for r in rnd),
                                    "on_one_conflict_path": [sum(r["verdict"] == "correct" for r in rnd if r["paths"] == 1), sum(r["paths"] == 1 for r in rnd)],
                                    "on_two_or_more": [sum(r["verdict"] == "correct" for r in rnd if r["paths"] > 1), sum(r["paths"] > 1 for r in rnd)]}}

    # --- hold back the UMLS pairs that bridge a one-to-one conflict on two or more paths --------------------------------
    # One pass over the finished tiers and rejections (the population the hand check was drawn from): a UMLS-derived
    # equivalence on two or more shortest paths between two codes of a one-to-one vocabulary was right 15 of 30 (a
    # subtype paired with its parent, a numbered locus with the disease); on one path, 13 of 13. The first family is
    # inadmissible -- kept, marked in attrs.held, not followed.
    if bh.exists():
        import consistency
        _, _, br, _, _ = consistency.compute(con)
        held = [(a_, b_, p_) for (a_, b_, p_, m_), n_ in br.items() if n_ >= 2 and p_ in ("umls:shared_cui", "umls:concept_member")]
        con.execute("CREATE TEMP TABLE umls_bridge (a VARCHAR, b VARCHAR, p VARCHAR)")
        con.executemany("INSERT INTO umls_bridge VALUES (?, ?, ?)", held)
        con.execute("""UPDATE edge SET tier = 'inadmissible',
                           attrs = json_merge_patch(coalesce(attrs, '{}'), '{"held": "bridges a one-to-one conflict on 2+ paths (15/30)"}')
                       WHERE state <> 'rejected' AND (predicate, s_vocab || ':' || s_code, o_vocab || ':' || o_code) IN (
                             SELECT p, a, b FROM umls_bridge UNION SELECT p, b, a FROM umls_bridge)""")
        fam = [r for r in json.load(open(bh))["scored"] if r["predicate"].startswith("umls") and r.get("paths", 0) >= 2 and r["sample"] != "top 30 bridges"]
        k_, n_ = sum(r["verdict"] == "correct" for r in fam), len(fam)
        report["consistency:bridge hand check"]["umls_bridges_on_two_or_more_paths"] = {
            "held_back_edges": con.execute("SELECT count(*) FROM edge WHERE (attrs->>'held') IS NOT NULL").fetchone()[0],
            "checked": n_, "correct": k_, "wilson_lo": round(wilson(k_, n_)[0], 4), "earned_tier": tier(wilson(k_, n_)[0], n_)}

    # --- islands: weakly connected components, and each vocabulary's reach outside itself --------------------------
    # An island is a piece of the graph no path joins to the rest. Rejected and inadmissible edges are not followed.
    keys = [k for (k,) in con.execute("SELECT key FROM node").fetchall()]
    idx = {k: i for i, k in enumerate(keys)}
    par = list(range(len(keys)))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for s_, o_ in con.execute("""SELECT s_vocab || ':' || s_code, o_vocab || ':' || o_code FROM edge
                                 WHERE state <> 'rejected' AND tier <> 'inadmissible'""").fetchall():
        x, y = find(idx[s_]), find(idx[o_])
        if x != y:
            par[x] = y
    root = [find(i) for i in range(len(keys))]
    size = collections.Counter(root)
    giant = size.most_common(1)[0][0]
    con.execute("CREATE TEMP TABLE comp (key VARCHAR, c BIGINT, sz BIGINT)")
    con.executemany("INSERT INTO comp VALUES (?, ?, ?)", [(k, root[i], size[root[i]]) for i, k in enumerate(keys) if root[i] != giant])
    report["islands"] = {
        "components": len(size), "main_component_nodes": size[giant], "nodes_outside_it": len(keys) - size[giant],
        "outside_by_vocabulary": dict(con.execute("""SELECT n.vocab, count(*) FROM comp JOIN node n USING (key)
                                                     GROUP BY 1 ORDER BY 2 DESC""").fetchall()),
        "largest_outside": [{"nodes": sz, "vocabularies": v} for sz, v in con.execute("""
            SELECT any_value(sz), list(DISTINCT n.vocab ORDER BY n.vocab) FROM comp JOIN node n USING (key)
            GROUP BY c ORDER BY 1 DESC LIMIT 8""").fetchall()],
        "reach_outside_own_vocabulary": {v: {"nodes": n, "with_a_link_to_another_vocabulary": b, "share": round(b / n, 3)}
            for v, n, b in con.execute("""WITH x AS (SELECT s_vocab v, s_code k FROM edge WHERE s_vocab <> o_vocab
                                                     UNION SELECT o_vocab, o_code FROM edge WHERE s_vocab <> o_vocab)
                SELECT n.vocab, count(*), count(x.k) FROM node n LEFT JOIN x ON x.v = n.vocab AND x.k = n.code
                GROUP BY 1 ORDER BY count(x.k) * 1.0 / count(*), 1""").fetchall()}}

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
