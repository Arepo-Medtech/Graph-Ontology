#!/usr/bin/env python3
"""Wave 2 of the linkage plan: five families of cross-vocabulary links that come from sources we hold but rest on UMLS
synonymy or a derived step. PREPARATION ONLY -- candidates, a score against an independent second path, and a sampled
hand-check sheet. Nothing here writes an edge: the build may load a family only after a person has read its sheet and
the family has earned a tier (reference/graph_tiers.json). Read-only on the graph.

    1 umls_disease_member  a UMLS CUI node named by MONDO or Orphanet -> its OMIM / NCIt / MeSH / HPO atoms (MRCONSO 2026AA)
                           second path: the same MONDO / Orphanet node's own exact cross-reference in that vocabulary
    2 unii_rxnorm          FDA SPL substance (MTHSPL SU, code = UNII) <-> RxNorm IN / PIN / MIN under one CUI
                           second path: DrugCentral's identifier table (one struct_id carrying both ids)
    3 drug_pharma_role     DrugCentral pharma_class: MeSH pharmacological action (PA), ChEBI 'has role'
                           second path: the drug's FDA / MED-RT classes and the other source's roles, by class name
                           (a confirmation only -- a drug holds many true classes, so a miss is not a contradiction);
                           for ChEBI rows also ChEBI's own roles (chebi:has_role) through DrugCentral's ChEBI xref
    4 hpo_snomed_lifted    HPO -> SNOMED crosswalk rows whose SNOMED code is retired in SNOMED CT-AU, lifted through the
                           association refset (SAME AS 900000000000527005, REPLACED BY 900000000000526001); same-name rule
                           second path: the HPO term's current SNOMED atoms in MRCONSO 2026AA (exact, or one is-a line)
    5 chembl_moa_target    ChEMBL mechanism (drug -> target) -> UniProt accession, beyond DrugCentral's own mechanisms
                           second path: DrugCentral act_table_full for the same drug (same accession, or same gene)

For each family: candidates (total, already reached, new, nodes that would get their first link to another vocabulary),
the second-path score (both fire, exact, one is-a line, Wilson lower bound, the tier it would earn), and a sample of 30
new pairs per stratum drawn by md5(seed || key) plus every new pair the second path contradicts. A re-run keeps any
verdicts already written on a sheet (matched by key), so a first reading or a reviewer's verdict is not lost.

    cp -c out/graph.duckdb $TMPDIR/graph.duckdb          # score a copy: the build may rewrite out/graph.duckdb meanwhile
    .venv/bin/python scripts/wave2_candidates.py --graph $TMPDIR/graph.duckdb [--compendium out/compendium.duckdb]
        [--assoc <SNOMED CT-AU der2_cRefset_AssociationSnapshot_*.txt>] [--seed wave2-27sep] [--families 1,2,3,4,5]

Writes cache/wave2/<family>_candidates.parquet, cache/wave2/<family>_handcheck.json and cache/wave2/summary.json.
UMLS, SNOMED CT and DrugCentral names are licensed or carry their own terms: everything written here stays in cache/
(git-ignored); the committed record (docs/review-queues.md) carries counts and method only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

import duckdb

UMLS = Path("cache/umls")
CONSO = UMLS / "2026AA/mrconso.parquet"
MRREL = UMLS / "2026AA/mrrel_l0.parquet"
AUI = UMLS / "2026AA/aui_l0.parquet"
REL_EDGES = UMLS / "umls_rel_edges.parquet"
PAIRS = UMLS / "umls_shared_cui.parquet"
HPO_SCT = UMLS / "hpo_snomed.tsv"
DC = Path("cache/drugcentral")
CHEMBL_RAW = Path("cache/chembl/moa_chembl_raw.json")
OUT = Path("cache/wave2")
ASSOC = Path(os.path.expanduser("~/Documents/Graph-Ontology-Kit/sources/SnomedCT_Release_AU1000036_20260831/Snapshot/Refset/"
                                "Content/der2_cRefset_AssociationSnapshot_AU1000036_20260831.txt"))
SAME_AS, REPLACED_BY = "900000000000527005", "900000000000526001"
TIER1, TIER2, MIN_FIRED = 0.99, 0.80, 30          # as graph_report.py
N_SAMPLE = 30
READING = "first reading (Claude), awaiting reviewer"


def wilson(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return max(0.0, ((p + z * z / (2 * n)) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n))


def tier(lo: float, n: int) -> str:
    return "ungraded" if n < MIN_FIRED else "1" if lo >= TIER1 else "2" if lo >= TIER2 else "inadmissible"


def score(n: int, exact: int, consistent: int | None = None) -> dict:
    co = exact if consistent is None else consistent
    return {"both_fire": n, "exact": exact, "exact_wilson_lo": round(wilson(exact, n), 4),
            "consistent": co, "consistent_wilson_lo": round(wilson(co, n), 4), "contradicted": n - co,
            "tier_it_would_earn": tier(wilson(co, n), n)}


def norm(s: str) -> str:                       # scripts/umls_mrconso.py: the shared-name rule
    s = re.sub(r"\s*\((disorder|finding|procedure|body structure|substance|organism|observable entity|qualifier value|"
               r"product|medicinal product|clinical drug|morphologic abnormality|cell|situation|regime/therapy|"
               r"physical object|specimen|assessment scale|record artifact|event)\)\s*$", "", (s or "").lower())
    return " ".join(sorted(re.findall(r"[a-z0-9]+", s)))


STOP = {"receptor", "receptors", "agents", "agent", "drugs", "drug", "of", "the", "and"}


def class_key(v: str) -> str:                  # build_edges.py's class_key, with hyphens joined ("Non-Steroidal" = "Nonsteroidal")
    v = re.sub(r"\s*\[(moa|pe|epc|cs)\]\s*$", "", (v or "").lower()).replace("-", "")
    v = re.sub(r"([a-z])(\d)", r"\1 \2", v)
    return " ".join(sorted({w[:-1] if w.endswith("s") and len(w) > 3 else w for w in re.findall(r"[a-z0-9]+", v)} - STOP))


def tsv(name: str) -> str:
    return f"read_csv('{DC / (name + '.tsv')}', delim='\t', header=true, all_varchar=true, quote='')"


def q1(con, sql: str):
    return con.execute(sql).fetchone()


def first_links(con, table: str, v: str, c: str) -> dict:
    """Targets of the NEW gated pairs in `table` that hold no link to another vocabulary yet (or are not nodes at all)."""
    return dict(zip(("distinct_targets", "not_yet_a_node", "node_with_no_cross_vocab_link", "would_get_first_link"), q1(con, f"""
        WITH t AS (SELECT DISTINCT {v} v, {c} c FROM {table} WHERE gate AND NOT present)
        SELECT count(*), count(*) FILTER (WHERE (v, c) NOT IN (SELECT vocab, code FROM node)),
               count(*) FILTER (WHERE (v, c) IN (SELECT vocab, code FROM node) AND (v, c) NOT IN (SELECT v, c FROM linked)),
               count(*) FILTER (WHERE (v, c) NOT IN (SELECT v, c FROM linked)) FROM t""")))


def sample(con, table: str, key: str, strata: str | None, seed: str, extra_where: str = "TRUE") -> list[dict]:
    part = f"PARTITION BY {strata}" if strata else ""
    df = con.execute(f"""SELECT * EXCLUDE (rk) FROM (SELECT *, row_number() OVER ({part} ORDER BY md5('{seed}' || {key})) rk
                         FROM {table} WHERE gate AND NOT present AND {extra_where}) WHERE rk <= {N_SAMPLE}
                         ORDER BY {strata + ', ' if strata else ''}md5('{seed}' || {key})""").df()
    return json.loads(df.to_json(orient="records"))


def write_sheet(family: str, note: str, rows: list[dict], key_fields: tuple[str, ...]) -> dict:
    """The hand-check file, in the house format ({"_note", "scored": [...]}); verdicts already on it are kept by key."""
    path = OUT / f"{family}_handcheck.json"
    old = {}
    if path.exists():
        for r in json.load(open(path)).get("scored", []):
            old[tuple(str(r.get(k)) for k in key_fields) + (r.get("sample"),)] = r
    out = []
    for i, r in enumerate(rows, 1):
        r = {"sample": r.pop("smp"), "n": i, **r}
        prev = old.get(tuple(str(r.get(k)) for k in key_fields) + (r["sample"],), {})
        for k in ("verdict", "why", "reading"):
            r[k] = prev.get(k)
        if r["verdict"] is None:
            r["reading"] = READING
        out.append(r)
    json.dump({"_note": note, "scored": out}, open(path, "w"), indent=1, ensure_ascii=False)
    tally = {}
    for r in out:
        tally.setdefault(r["sample"], {}).setdefault(r["verdict"] or "unread", 0)
        tally[r["sample"]][r["verdict"] or "unread"] += 1
    return tally


def save(con, table: str, family: str) -> None:
    con.execute(f"COPY (SELECT * FROM {table}) TO '{OUT / (family + '_candidates.parquet')}' (FORMAT parquet)")


def counts(con, table: str, by: str | None = None) -> dict:
    sel = f"{by}, " if by else ""
    rows = con.execute(f"""SELECT {sel}count(*), count(*) FILTER (WHERE gate), count(*) FILTER (WHERE gate AND present),
                                  count(*) FILTER (WHERE gate AND NOT present) FROM {table} {'GROUP BY 1 ORDER BY 1' if by else ''}""").fetchall()
    f = lambda r: dict(zip(("candidates", "pass_gate", "already_reached", "new"), r))
    return {r[0]: f(r[1:]) for r in rows} if by else f(rows[0])


# --- family 1: UMLS disease concept -> OMIM / NCIt / MeSH / HPO member codes ------------------------------------------
def family1(con, seed: str) -> dict:
    fam = "umls_disease_member"
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_src AS
        SELECT DISTINCT e.o_code cui, e.s_vocab sv, e.s_code sc, n.name sname FROM edge e
        LEFT JOIN node n ON n.vocab = e.s_vocab AND n.code = e.s_code
        WHERE e.o_vocab = 'UMLS' AND e.state <> 'rejected'
          AND ((e.predicate = 'mondo:exact_match' AND e.s_vocab = 'MONDO') OR (e.predicate = 'orpha:xref' AND e.s_vocab = 'ORPHA'))""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f1_atom AS
        SELECT m.CUI cui, CASE m.SAB WHEN 'OMIM' THEN 'OMIM' WHEN 'NCI' THEN 'NCIT' WHEN 'MSH' THEN 'MESH' ELSE 'HP' END v,
               m.CODE code, m.TTY tty, m.TS ts, m.ISPREF ispref, m.STR str, norm(m.STR) n
        FROM '{CONSO}' m WHERE m.SUPPRESS = 'N' AND m.SAB IN ('OMIM', 'NCI', 'MSH', 'HPO') AND m.SRL IN (0, 9)
          AND m.CODE NOT LIKE 'MTH%' AND m.CODE <> 'NOCODE' AND m.CUI IN (SELECT cui FROM f1_src)""")
    # the second path: what the CUI's own MONDO / Orphanet node states for that vocabulary (exact), and Orphanet's
    # narrower / broader links (on one line, not the same)
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_sp AS
        SELECT DISTINCT s.cui, e.o_vocab v, e.o_code code, CASE WHEN e.predicate = 'orpha:xref' AND e.method <> 'E' THEN 'line' ELSE 'exact' END how
        FROM f1_src s JOIN edge e ON e.s_vocab = s.sv AND e.s_code = s.sc AND e.state <> 'rejected'
        WHERE e.o_vocab IN ('OMIM', 'NCIT', 'MESH', 'HP')
          AND (e.predicate = 'mondo:exact_match' OR (e.predicate = 'orpha:xref' AND e.method IN ('E', 'NTBT', 'BTNT')))""")
    # MeSH tree and NCIt is-a (the sources' own PAR rows, MRREL Level 0, in full) and HPO is-a, for "one is-a line"
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f1_par AS
        SELECT DISTINCT s_vocab v, s_code c, o_code p FROM '{REL_EDGES}' WHERE predicate = 'umls:source_parent' AND s_vocab IN ('MESH', 'NCIT')
        UNION SELECT 'HP', s_code, o_code FROM edge WHERE predicate = 'hp:is_a'""")
    con.execute("CREATE OR REPLACE TEMP TABLE f1_srcn AS SELECT *, norm(sname) sn FROM f1_src")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_same AS SELECT a.cui, a.v, a.code, string_agg(DISTINCT a.tty, ' ') match_ttys,
                   bool_and(a.tty IN ('PHENO', 'PHENO_ET')) pheno_only FROM f1_atom a
                   JOIN f1_srcn s ON s.cui = a.cui AND s.sn = a.n WHERE a.v <> 'MESH' OR a.tty IN ('MH', 'NM') GROUP BY 1, 2, 3""")
    # each target code's own preferred term, whatever CUI it sits in (an OMIM gene or locus entry is named for the locus)
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f1_pt AS SELECT CASE SAB WHEN 'OMIM' THEN 'OMIM' WHEN 'NCI' THEN 'NCIT' WHEN 'MSH' THEN 'MESH' ELSE 'HP' END v,
                    CODE code, any_value(STR) t_pt FROM '{CONSO}' WHERE SAB IN ('OMIM', 'NCI', 'MSH', 'HPO') AND TTY IN ('PT', 'MH', 'NM') AND SUPPRESS = 'N'
                    GROUP BY 1, 2""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_sagg AS SELECT cui, string_agg(DISTINCT sv || ':' || sc, ' ') src,
                   any_value(sname ORDER BY sv, sc) src_name, bool_or(sname ILIKE '%susceptib%') s_sus FROM f1_src GROUP BY 1""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_direct AS SELECT DISTINCT CASE WHEN s_vocab = 'UMLS' THEN s_code ELSE o_code END cui,
                   CASE WHEN s_vocab = 'UMLS' THEN o_vocab ELSE s_vocab END v, CASE WHEN s_vocab = 'UMLS' THEN o_code ELSE s_code END code
                   FROM edge WHERE (s_vocab = 'UMLS' AND o_vocab IN ('OMIM', 'NCIT', 'MESH', 'HP')) OR (o_vocab = 'UMLS' AND s_vocab IN ('OMIM', 'NCIT', 'MESH', 'HP'))""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_spagg AS SELECT cui, v, string_agg(DISTINCT code, ' ') sp_codes FROM f1_sp GROUP BY 1, 2""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1 AS
        WITH p AS (
            SELECT cui, v, code, bool_or(tty IN ('MH', 'NM')) heading,
                   arg_min(str, (CASE WHEN tty IN ('PT', 'MH', 'NM', 'PHENO') THEN 0 ELSE 1 END) * 4 + (CASE WHEN ts = 'P' THEN 0 ELSE 2 END)
                                + (CASE WHEN ispref = 'Y' THEN 0 ELSE 1 END)) t_name,
                   string_agg(DISTINCT tty, ' ') ttys
            FROM f1_atom WHERE v <> 'MESH' OR tty IN ('MH', 'NM') GROUP BY 1, 2, 3)
        SELECT p.*, pt.t_pt, sm.match_ttys, g.src, g.src_name, sm.cui IS NOT NULL same_name,
               p.v = 'OMIM' AND coalesce(sm.pheno_only, FALSE) omim_pheno_only,
               p.v = 'OMIM' AND p.code IN (SELECT o_code FROM edge WHERE predicate = 'hgnc:xref' AND o_vocab = 'OMIM') omim_gene,
               p.v = 'OMIM' AND p.t_name ILIKE '%susceptib%' AND NOT g.s_sus omim_suscept,
               d.cui IS NOT NULL direct_edge, sa.cui IS NOT NULL sp_fires, ex.cui IS NOT NULL sp_exact, sa.sp_codes
        FROM p JOIN f1_sagg g ON g.cui = p.cui
        LEFT JOIN f1_same sm ON sm.cui = p.cui AND sm.v = p.v AND sm.code = p.code
        LEFT JOIN f1_pt pt ON pt.v = p.v AND pt.code = p.code
        LEFT JOIN f1_direct d ON d.cui = p.cui AND d.v = p.v AND d.code = p.code
        LEFT JOIN f1_spagg sa ON sa.cui = p.cui AND sa.v = p.v
        LEFT JOIN (SELECT DISTINCT cui, v, code FROM f1_sp WHERE how = 'exact') ex ON ex.cui = p.cui AND ex.v = p.v AND ex.code = p.code""")
    # one is-a line: an Orphanet narrower / broader link, or a code that is an ancestor of the other in its own hierarchy
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_anc AS
        WITH RECURSIVE up(v, start, node, d) AS (
            SELECT DISTINCT v, code, code, 0 FROM (SELECT v, code FROM f1 WHERE sp_fires AND NOT sp_exact
                                                   UNION SELECT v, code FROM f1_sp WHERE v <> 'OMIM')
            UNION SELECT u.v, u.start, p.p, u.d + 1 FROM up u JOIN f1_par p ON p.v = u.v AND p.c = u.node WHERE u.d < 25)
        SELECT DISTINCT v, start, node FROM up""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1_line AS
        SELECT DISTINCT f.cui, f.v, f.code FROM f1 f JOIN f1_sp x ON x.cui = f.cui AND x.v = f.v
        WHERE f.sp_fires AND NOT f.sp_exact AND (x.code = f.code
           OR (f.v, f.code, x.code) IN (SELECT v, start, node FROM f1_anc) OR (f.v, x.code, f.code) IN (SELECT v, start, node FROM f1_anc))""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f1 AS SELECT f.*, f.sp_exact OR l.cui IS NOT NULL sp_line,
                   f.same_name AND NOT f.omim_gene AND NOT f.omim_suscept gate, f.direct_edge OR f.sp_exact present
                   FROM f1 f LEFT JOIN f1_line l ON l.cui = f.cui AND l.v = f.v AND l.code = f.code""")
    res = {"candidates_by_vocab": counts(con, "f1", "v"), "candidates": counts(con, "f1"),
           "cui_nodes_named_by_mondo_or_orphanet": q1(con, "SELECT count(DISTINCT cui) FROM f1_src")[0],
           "atoms_before_mesh_heading_rule_by_vocab": dict(con.execute(
               "SELECT v, count(DISTINCT cui || '|' || code) FROM f1_atom GROUP BY 1 ORDER BY 1").fetchall()),
           "gate_losses": dict(zip(("names_differ", "omim_gene_entry", "omim_susceptibility"), q1(con,
               "SELECT count(*) FILTER (WHERE NOT same_name), count(*) FILTER (WHERE same_name AND omim_gene), "
               "count(*) FILTER (WHERE same_name AND NOT omim_gene AND omim_suscept) FROM f1"))),
           "score_gated_by_vocab": {}, "score_all_by_vocab": {},
           "omim_named_only_by_a_phenotype_atom": dict(zip(("gated", "new"), q1(con,
               "SELECT count(*) FILTER (WHERE gate AND omim_pheno_only), count(*) FILTER (WHERE gate AND NOT present AND omim_pheno_only) FROM f1"))),
           "omim_pheno_only_note": "an OMIM gene or locus entry (its PT names the gene, region or enhancer) "
                                   "carries its disorder as a PHENO atom; hgnc:xref catches only HGNC genes. A proposed rule, not applied here: "
                                   "an OMIM target must share a name through its PT / ET atoms, not a PHENO atom alone"}
    for v, n, ex, co in con.execute("SELECT v, count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_line) "
                                    "FROM f1 WHERE gate AND sp_fires GROUP BY 1 ORDER BY 1").fetchall():
        res["score_gated_by_vocab"][v] = score(n, ex, co)
    for v, n, ex, co in con.execute("SELECT v, count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_line) "
                                    "FROM f1 WHERE sp_fires GROUP BY 1 ORDER BY 1").fetchall():
        res["score_all_by_vocab"][v] = score(n, ex, co)
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_line) FROM f1 WHERE gate AND sp_fires")
    res["score_gated"] = score(n, ex, co)
    res["first_links"] = first_links(con, "f1", "v", "code")
    res["first_links_by_vocab"] = {v: first_links(con, f"(SELECT * FROM f1 WHERE v = '{v}')", "v", "code")
                                   for v in ("HP", "MESH", "NCIT", "OMIM")}
    save(con, "f1", fam)
    cols = "'random 30 per vocabulary' AS smp, v, cui, src, src_name, code AS target, t_name AS target_name, t_pt AS target_pt, match_ttys, sp_codes AS second_path"
    rows = sample(con, f"(SELECT {cols}, gate, present, sp_fires, sp_line, cui || v || code k FROM f1)", "k", "v", seed)
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f1_contra AS SELECT 'second path contradicts' AS smp, v, cui, src, src_name,
                    code AS target, t_name AS target_name, t_pt AS target_pt, match_ttys, sp_codes AS second_path, gate, present, sp_fires, sp_line, cui || v || code k
                    FROM f1 WHERE gate AND NOT present AND sp_fires AND NOT sp_line ORDER BY v, cui, code""")
    rows += json.loads(con.execute("SELECT * FROM f1_contra").df().to_json(orient="records"))
    for r in rows:
        for k in ("gate", "present", "k"):
            r.pop(k, None)
    res["contradictions_new"] = len(rows) - sum(1 for r in rows if r["smp"].startswith("random"))
    res["hand_check"] = write_sheet(fam, (
        "Wave 2 family 1 (27 Sep 2026): umls:concept_member extended from SNOMED CT to OMIM, NCIt, MeSH (MH/NM headings) and "
        "HPO. Subject: a UMLS CUI node named by MONDO (exact_match) or Orphanet (xref E); target: a non-suppressed MRCONSO "
        "2026AA atom's code in that CUI. Gate: the target shares a name with the MONDO / Orphanet label that named the CUI "
        "(umls_mrconso.norm), OMIM gene entries and non-matching susceptibility entries out. Sample: 30 new pairs per target "
        "vocabulary, md5(seed || key); then every new pair whose second path (the same MONDO / Orphanet node's own xref in "
        "that vocabulary) names other codes, none on one is-a line. CORRECT when the target denotes the disease the CUI "
        "names. UMLS-derived: git-ignored."), rows, ("v", "cui", "target"))
    return res


# --- family 2: UNII <-> RxNorm ingredient --------------------------------------------------------------------------------
def family2(con, seed: str) -> dict:
    fam = "unii_rxnorm"
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f2_dc AS          -- DrugCentral: struct -> UNII, struct -> RxCUI
        SELECT DISTINCT struct_id s, 'UNII' k, identifier id FROM {tsv('identifier')} WHERE id_type = 'UNII'
        UNION SELECT DISTINCT struct_id, 'RXN', identifier FROM {tsv('identifier')} WHERE id_type = 'RXNORM'
        UNION SELECT DISTINCT s_code, 'RXN', o_code FROM edge WHERE predicate = 'drugcentral:rxnorm' AND state <> 'rejected'""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f2_form AS      -- RxNorm's own form_of / has_form (a salt and its base)
        SELECT DISTINCT a.CODE a, b.CODE b FROM '{MRREL}' r JOIN '{AUI}' a ON a.AUI = r.AUI1 AND a.SAB = 'RXNORM'
        JOIN '{AUI}' b ON b.AUI = r.AUI2 AND b.SAB = 'RXNORM' WHERE r.SAB = 'RXNORM' AND r.RELA IN ('form_of', 'has_form')""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f2 AS
        WITH su AS (SELECT CUI cui, CODE unii, any_value(STR) su_name FROM '{CONSO}' WHERE SAB = 'MTHSPL' AND TTY = 'SU' AND SUPPRESS = 'N' GROUP BY 1, 2),
             rx AS (SELECT CUI cui, CODE rxcui, any_value(TTY) tty, any_value(STR) rx_name FROM '{CONSO}'
                    WHERE SAB = 'RXNORM' AND TTY IN ('IN', 'PIN', 'MIN') AND SUPPRESS = 'N' GROUP BY 1, 2)
        SELECT su.cui, su.unii, su.su_name, rx.rxcui, rx.tty, rx.rx_name, norm(su.su_name) = norm(rx.rx_name) same_name
        FROM su JOIN rx ON rx.cui = su.cui""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f2_ur AS SELECT DISTINCT a.id unii, b.id rxcui FROM f2_dc a JOIN f2_dc b ON b.s = a.s AND b.k = 'RXN'
                   WHERE a.k = 'UNII'""")                        # DrugCentral's own UNII x RxCUI, same struct_id
    con.execute("""CREATE OR REPLACE TEMP TABLE f2 AS SELECT f2.*,
            d.unii IS NOT NULL direct_edge, s.unii IS NOT NULL dc_same_struct,
            (u.unii IS NOT NULL OR s.unii IS NOT NULL) sp_fires, (r.rxcui IS NOT NULL AND s.unii IS NULL) rx_side_differs,
            fl.unii IS NOT NULL dc_form_line, u.ids dc_rxcuis_for_unii, r.ids dc_uniis_for_rxcui,
            f2.unii IN (SELECT id FROM f2_dc WHERE k = 'UNII') unii_in_dc, f2.rxcui IN (SELECT id FROM f2_dc WHERE k = 'RXN') rxcui_in_dc,
            (f2.unii IN (SELECT code FROM node WHERE vocab = 'UNII') OR f2.rxcui IN (SELECT code FROM node WHERE vocab = 'RXN')) gate,
            (d.unii IS NOT NULL OR s.unii IS NOT NULL) present
        FROM f2
        LEFT JOIN (SELECT DISTINCT CASE WHEN s_vocab = 'UNII' THEN s_code ELSE o_code END unii, CASE WHEN s_vocab = 'UNII' THEN o_code ELSE s_code END rxcui
                   FROM edge WHERE (s_vocab = 'UNII' AND o_vocab = 'RXN') OR (s_vocab = 'RXN' AND o_vocab = 'UNII')) d ON d.unii = f2.unii AND d.rxcui = f2.rxcui
        LEFT JOIN f2_ur s ON s.unii = f2.unii AND s.rxcui = f2.rxcui
        LEFT JOIN (SELECT unii, string_agg(rxcui, ' ') ids FROM f2_ur GROUP BY 1) u ON u.unii = f2.unii
        LEFT JOIN (SELECT rxcui, string_agg(unii, ' ') ids FROM f2_ur GROUP BY 1) r ON r.rxcui = f2.rxcui
        LEFT JOIN (SELECT DISTINCT x.unii, f.b rxcui FROM f2_ur x JOIN (SELECT a, b FROM f2_form UNION SELECT b, a FROM f2_form) f ON f.a = x.rxcui) fl
               ON fl.unii = f2.unii AND fl.rxcui = f2.rxcui""")
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE dc_same_struct), count(*) FILTER (WHERE dc_same_struct OR dc_form_line) FROM f2 WHERE gate AND sp_fires")
    res = {"gate": "one end already a graph node (the umls:shared_cui rule: nothing arrives detached)",
           "rxcui_side_differs_new": q1(con, "SELECT count(*) FROM f2 WHERE gate AND NOT present AND rx_side_differs")[0],
           "rxcui_side_note": "DrugCentral holds this RxCUI on a struct with another UNII (mostly a salt PIN on the parent's struct): "
                              "DrugCentral's one-UNII-per-struct modelling, not counted as a contradiction","candidates": counts(con, "f2"), "by_rxnorm_tty": counts(con, "f2", "tty"),
           "same_name": q1(con, "SELECT count(*) FILTER (WHERE same_name) FROM f2")[0],
           "new_with_neither_id_in_drugcentral": q1(con, "SELECT count(*) FROM f2 WHERE gate AND NOT present AND NOT unii_in_dc AND NOT rxcui_in_dc")[0],
           "score": score(n, ex, co),
           "first_links_unii": first_links(con, "(SELECT 'UNII' v, unii c, gate, present FROM f2)", "v", "c"),
           "first_links_rxnorm": first_links(con, "(SELECT 'RXN' v, rxcui c, gate, present FROM f2)", "v", "c")}
    save(con, "f2", fam)
    cols = "unii, su_name, rxcui, tty, rx_name, same_name, dc_rxcuis_for_unii, dc_uniis_for_rxcui, gate, present, sp_fires, dc_form_line"
    rows = sample(con, f"(SELECT 'random 30' AS smp, {cols}, unii || rxcui k FROM f2)", "k", None, seed)
    rows += json.loads(con.execute(f"""SELECT 'second path contradicts' AS smp, {cols}, unii || rxcui k FROM f2
                                       WHERE gate AND NOT present AND sp_fires AND NOT dc_form_line ORDER BY unii, rxcui""").df().to_json(orient="records"))
    for r in rows:
        for k in ("gate", "present", "k"):
            r.pop(k, None)
    res["contradictions_new"] = sum(1 for r in rows if r["smp"].startswith("second"))
    res["hand_check"] = write_sheet(fam, (
        "Wave 2 family 2 (27 Sep 2026): FDA SPL substance (MRCONSO 2026AA MTHSPL SU, code = UNII) <-> RxNorm IN / PIN / MIN "
        "atom under the same CUI. New = DrugCentral does not already carry both ids on one struct_id. Sample: 30 new pairs, "
        "md5(seed || key); then every new pair where DrugCentral pairs the UNII with other RxCUIs, none a salt / base form "
        "of it in RxNorm. Gate: one end already a graph node. CORRECT when the UNII and the RxCUI denote the same substance (a salt for its base is "
        "WRONG). UMLS-derived: git-ignored."), rows, ("unii", "rxcui"))
    return res


# --- family 3: drug -> MeSH pharmacological action / ChEBI role -----------------------------------------------------------
def family3(con, seed: str) -> dict:
    fam = "drug_pharma_role"
    con.create_function("class_key", class_key, ["VARCHAR"], "VARCHAR")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f3_pc AS SELECT DISTINCT struct_id s, source, type, name, class_code,
                    class_key(name) ck FROM {tsv('pharma_class')}""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3_other AS         -- the drug's classes from sources other than the row's own
        SELECT s, 'FDA ' || type src, name, ck FROM f3_pc WHERE source = 'FDA' AND type IN ('EPC', 'MoA', 'PE')
        UNION SELECT r.s_code, 'MED-RT', n.name, class_key(n.name) FROM edge r
            JOIN edge m ON m.s_vocab = 'RXN' AND m.s_code = r.o_code AND m.predicate IN ('medrt:has_mechanism_of_action', 'medrt:has_physiologic_effect')
            JOIN node n ON n.vocab = 'MEDRT' AND n.code = m.o_code
            WHERE r.predicate = 'drugcentral:rxnorm' AND m.state <> 'rejected'
        UNION SELECT s, 'MeSH PA', name, ck FROM f3_pc WHERE source = 'MeSH' AND type = 'PA'
        UNION SELECT s, 'ChEBI role', name, ck FROM f3_pc WHERE source = 'CHEBI'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3_p AS SELECT s drug, CASE source WHEN 'MeSH' THEN 'MESH' ELSE 'CHEBI' END v,
                   replace(class_code, 'CHEBI:', '') code, name class_name, ck, CASE source WHEN 'MeSH' THEN 'MeSH PA' ELSE 'ChEBI role' END stratum
                   FROM f3_pc WHERE (source = 'MeSH' AND type = 'PA') OR source = 'CHEBI'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3 AS
        SELECT p.drug, n.name drug_name, p.v, p.code, p.class_name, p.stratum, e.s_code IS NOT NULL present,
               (SELECT count(*) > 0 FROM f3_other o WHERE o.s = p.drug AND o.src <> p.stratum) sp_fires,
               (SELECT string_agg(DISTINCT o.src || ': ' || o.name, '; ') FROM f3_other o WHERE o.s = p.drug AND o.ck = p.ck AND o.src <> p.stratum) sp_agreeing,
               (SELECT string_agg(DISTINCT o.src || ': ' || o.name, '; ') FROM f3_other o WHERE o.s = p.drug AND o.src LIKE 'FDA%') fda_classes,
               TRUE gate
        FROM f3_p p LEFT JOIN node n ON n.vocab = 'DRUGCENTRAL' AND n.code = p.drug
        LEFT JOIN (SELECT DISTINCT s_code, o_vocab, o_code FROM edge WHERE s_vocab = 'DRUGCENTRAL' AND o_vocab IN ('MESH', 'CHEBI')) e
               ON e.s_code = p.drug AND e.o_vocab = p.v AND e.o_code = p.code""")
    con.execute("CREATE OR REPLACE TEMP TABLE f3 AS SELECT *, sp_agreeing IS NOT NULL sp_agree FROM f3")
    # ChEBI's own roles, where the graph holds them (chebi:has_role, loaded from chebi.obo since Wave 3), reached from the
    # drug through DrugCentral's ChEBI cross-reference: a ChEBI row the graph reaches in two steps is already there; a
    # role on one chebi:is_a line with one ChEBI states is consistent; ChEBI stating roles for the drug, none on a line
    # with this one, is a disagreement (DrugCentral's copy is of an older ChEBI release)
    con.execute("""CREATE OR REPLACE TEMP TABLE f3_cr AS SELECT DISTINCT x.s_code drug, r.o_code chrole FROM edge x
                   JOIN edge r ON r.predicate = 'chebi:has_role' AND r.s_vocab = 'CHEBI' AND r.s_code = x.o_code AND r.state <> 'rejected'
                   WHERE x.predicate = 'drugcentral:xref' AND x.o_vocab = 'CHEBI'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3_anc AS
        WITH RECURSIVE up(start, node, d) AS (
            SELECT DISTINCT c, c, 0 FROM (SELECT code c FROM f3 WHERE v = 'CHEBI' UNION SELECT chrole FROM f3_cr)
            UNION SELECT u.start, e.o_code, u.d + 1 FROM up u JOIN edge e ON e.predicate = 'chebi:is_a' AND e.s_code = u.node WHERE u.d < 25)
        SELECT DISTINCT start, node FROM up""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3_cl AS SELECT DISTINCT f.drug, f.code FROM f3 f JOIN f3_cr r ON r.drug = f.drug
                   WHERE f.v = 'CHEBI' AND (r.chrole = f.code OR (f.code, r.chrole) IN (SELECT start, node FROM f3_anc)
                                            OR (r.chrole, f.code) IN (SELECT start, node FROM f3_anc))""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f3 AS SELECT f.*,
                   f.v = 'CHEBI' AND f.drug IN (SELECT drug FROM f3_cr) chebi_fires,
                   f.v = 'CHEBI' AND (f.drug, f.code) IN (SELECT drug, chrole FROM f3_cr) chebi_exact,
                   f.v = 'CHEBI' AND (f.drug, f.code) IN (SELECT drug, code FROM f3_cl) chebi_line,
                   (SELECT string_agg(DISTINCT r.chrole, ' ') FROM f3_cr r WHERE r.drug = f.drug) chebi_roles
                   FROM f3 f""")
    con.execute("UPDATE f3 SET present = present OR chebi_exact")
    res = {"candidates_by_source": counts(con, "f3", "stratum"), "score_by_source": {}, "note":
           "the second path confirms by class name; a drug holds many true classes, so a miss is not a contradiction and the "
           "rate is a floor on corroboration, not a precision -- the tier must come from the hand check"}
    for st, n, ag in con.execute("SELECT stratum, count(*), count(*) FILTER (WHERE sp_agree) FROM f3 WHERE sp_fires GROUP BY 1").fetchall():
        res["score_by_source"][st] = {"both_fire": n, "name_agrees": ag, "rate": round(ag / n, 4), "wilson_lo": round(wilson(ag, n), 4)}
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE chebi_exact), count(*) FILTER (WHERE chebi_line) FROM f3 WHERE chebi_fires")
    res["chebi_role_vs_chebi_255"] = score(n, ex, co)
    res["chebi_role_vs_chebi_255"]["note"] = ("ChEBI's own release, reached through DrugCentral's ChEBI xref: the same source, a newer "
                                              "release, so a check of DrugCentral's copy and of the drug xref, not an independent path")
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE chebi_exact), count(*) FILTER (WHERE chebi_line) FROM f3 WHERE chebi_fires AND NOT present")
    res["chebi_role_vs_chebi_255_new"] = score(n, ex, co)
    res["first_links_by_source"] = {st: first_links(con, f"(SELECT * FROM f3 WHERE stratum = '{st}')", "v", "code")
                                    for st in ("MeSH PA", "ChEBI role")}
    res["distinct_classes_by_source"] = dict(con.execute("SELECT stratum, count(DISTINCT code) FROM f3 GROUP BY 1").fetchall())
    save(con, "f3", fam)
    cols = "stratum, drug, drug_name, v, code, class_name, sp_agreeing, fda_classes, chebi_roles, gate, present, sp_fires, sp_agree, chebi_line"
    rows = sample(con, f"(SELECT 'random 30 per source' AS smp, {cols}, drug || code k FROM f3)", "k", "stratum", seed)
    rows += json.loads(con.execute(f"""SELECT 'second path contradicts' AS smp, {cols}, drug || code k FROM f3
                                       WHERE NOT present AND chebi_fires AND NOT chebi_line ORDER BY drug, code""").df().to_json(orient="records"))
    for r in rows:
        for k in ("gate", "present", "k"):
            r.pop(k, None)
    res["contradictions_new"] = {"MeSH PA": "none definable (confirmation-only second path)",
                                 "ChEBI role": sum(1 for r in rows if r["smp"].startswith("second"))}
    res["hand_check"] = write_sheet(fam, (
        "Wave 2 family 3 (27 Sep 2026): DrugCentral pharma_class -- MeSH pharmacological action (PA) and ChEBI 'has role' -- "
        "as drug -> class edges. Sample: 30 per source, md5(seed || key). The second path (the drug's FDA EPC / MoA / PE and "
        "MED-RT classes, and the other source's roles, compared by class name) can only confirm; for the ChEBI rows, ChEBI 255's own roles (chebi:has_role, "
        "through DrugCentral's ChEBI xref) also can disagree, and every new ChEBI row where ChEBI states roles for the drug, "
        "none on one chebi:is_a line with this one, follows the random sample. CORRECT when the drug truly has that action or role (a well-established use or mechanism); a broad parent class the "
        "drug does belong to is CORRECT; a role belonging to a different salt, isomer or metabolite is WRONG."), rows, ("stratum", "drug", "code"))
    return res


# --- family 4: HPO -> SNOMED through retired SNOMED codes -----------------------------------------------------------------
def family4(con, seed: str, assoc: Path) -> dict:
    fam = "hpo_snomed_lifted"
    con.execute("""CREATE OR REPLACE TEMP MACRO nrm(x) AS
                   regexp_replace(replace(replace(lower(coalesce(x, '')), 'ae', 'e'), 'oe', 'e'), '[^a-z0-9]', '', 'g')""")   # build_edges.py
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f4_u AS SELECT * FROM read_csv('{HPO_SCT}', delim='\t', header=true, all_varchar=true, quote='')
                    WHERE snomed_code IS NOT NULL AND snomed_code <> ''""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f4_as AS SELECT referencedComponentId o_id, targetComponentId n_id, refsetId r
                    FROM read_csv('{assoc}', delim='\t', header=true, all_varchar=true, quote='')
                    WHERE active = '1' AND refsetId IN ('{SAME_AS}', '{REPLACED_BY}')""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4_lift AS          -- follow SAME AS / REPLACED BY until an active concept (3 steps)
        WITH RECURSIVE ch(o_id, cur, how, d) AS (
            SELECT DISTINCT a.o_id, a.n_id, CASE a.r WHEN '900000000000527005' THEN 'SAME AS' ELSE 'REPLACED BY' END, 1 FROM f4_as a
            WHERE a.o_id IN (SELECT snomed_code FROM f4_u WHERE snomed_code NOT IN (SELECT id FROM cmp.concept))
            UNION ALL SELECT ch.o_id, a.n_id, ch.how || ' > ' || CASE a.r WHEN '900000000000527005' THEN 'SAME AS' ELSE 'REPLACED BY' END, ch.d + 1
            FROM ch JOIN f4_as a ON a.o_id = ch.cur WHERE ch.d < 3 AND ch.cur NOT IN (SELECT id FROM cmp.concept))
        SELECT DISTINCT o_id, cur n_id, how FROM ch WHERE cur IN (SELECT id FROM cmp.concept)""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4 AS
        SELECT u.hpo_id, hp.name hp_name, u.snomed_code old_code, u.snomed_name old_name, l.n_id sct, c.pt sct_pt, c.fsn sct_fsn, l.how,
               (SELECT count(*) FROM f4_lift x WHERE x.o_id = u.snomed_code) n_targets,
               nrm(hp.name) = nrm(c.pt) same_name_new, nrm(hp.name) = nrm(u.snomed_name) same_name_old
        FROM f4_u u JOIN f4_lift l ON l.o_id = u.snomed_code JOIN cmp.concept c ON c.id = l.n_id
        JOIN node hp ON hp.vocab = 'HP' AND hp.code = u.hpo_id""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f4_cur AS SELECT DISTINCT sc hp, oc sct FROM '{PAIRS}'
                    WHERE sv = 'HP' AND ov = 'SCT' AND oc IN (SELECT id FROM cmp.concept)""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4_hpsct AS SELECT DISTINCT CASE WHEN s_vocab = 'HP' THEN s_code ELSE o_code END hp,
                   CASE WHEN s_vocab = 'HP' THEN o_code ELSE s_code END sct FROM edge
                   WHERE ((s_vocab = 'HP' AND o_vocab = 'SCT') OR (s_vocab = 'SCT' AND o_vocab = 'HP')) AND state <> 'rejected'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4 AS SELECT f4.*, same_name_new OR same_name_old gate, h.hp IS NOT NULL present,
            ca.hp IS NOT NULL sp_fires, cx.hp IS NOT NULL sp_exact, ca.codes sp_codes
        FROM f4 LEFT JOIN f4_hpsct h ON h.hp = f4.hpo_id AND h.sct = f4.sct
        LEFT JOIN (SELECT hp, string_agg(sct, ' ') codes FROM f4_cur GROUP BY 1) ca ON ca.hp = f4.hpo_id
        LEFT JOIN f4_cur cx ON cx.hp = f4.hpo_id AND cx.sct = f4.sct""")
    # one row per (HPO term, active concept): two retired codes of one term can lift to the same concept
    con.execute("""CREATE OR REPLACE TEMP TABLE f4 AS SELECT DISTINCT ON (hpo_id, sct) * FROM f4
                   ORDER BY hpo_id, sct, gate DESC, same_name_new DESC, old_code""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4_anc AS
        WITH RECURSIVE up(start, node, d) AS (
            SELECT DISTINCT x, x, 0 FROM (SELECT sct x FROM f4 WHERE sp_fires UNION SELECT sct FROM f4_cur WHERE hp IN (SELECT hpo_id FROM f4))
            UNION SELECT u.start, e.o_code, u.d + 1 FROM up u JOIN edge e ON e.predicate = 'sct:116680003' AND e.s_code = u.node WHERE u.d < 25)
        SELECT DISTINCT start, node FROM up""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4_line AS SELECT DISTINCT f.hpo_id, f.sct FROM f4 f JOIN f4_cur x ON x.hp = f.hpo_id
                   WHERE (f.sct, x.sct) IN (SELECT start, node FROM f4_anc) OR (x.sct, f.sct) IN (SELECT start, node FROM f4_anc)""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f4 AS SELECT f4.*, sp_exact OR l.hpo_id IS NOT NULL sp_line FROM f4
                   LEFT JOIN f4_line l ON l.hpo_id = f4.hpo_id AND l.sct = f4.sct""")
    res = {"crosswalk_rows": q1(con, "SELECT count(*) FROM f4_u")[0],
           "rows_with_retired_code": q1(con, "SELECT count(*) FROM f4_u WHERE snomed_code NOT IN (SELECT id FROM cmp.concept)")[0],
           "retired_rows_liftable": q1(con, "SELECT count(*) FROM f4_u WHERE snomed_code IN (SELECT o_id FROM f4_lift)")[0],
           "lifted_by": dict(con.execute("SELECT how, count(*) FROM f4 GROUP BY 1 ORDER BY 2 DESC").fetchall()),
           "candidates": counts(con, "f4"),
           "hpo_terms_new": q1(con, "SELECT count(DISTINCT hpo_id) FROM f4 WHERE gate AND NOT present")[0],
           "distinct_pairs_new": q1(con, "SELECT count(DISTINCT hpo_id || sct) FROM f4 WHERE gate AND NOT present")[0],
           "gate_by": dict(zip(("same_name_new_concept", "same_name_old_code_only"), q1(con,
               "SELECT count(*) FILTER (WHERE same_name_new), count(*) FILTER (WHERE same_name_old AND NOT same_name_new) FROM f4 WHERE gate AND NOT present"))),
           "hpo_terms_with_no_snomed_link_yet": q1(con, """SELECT count(DISTINCT hpo_id) FROM f4 WHERE gate AND NOT present
               AND hpo_id NOT IN (SELECT s_code FROM edge WHERE s_vocab = 'HP' AND o_vocab = 'SCT' AND state <> 'rejected')""")[0]}
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_line) FROM f4 WHERE gate AND NOT present AND sp_fires")
    res["score_new"] = score(n, ex, co)
    n, ex, co = q1(con, "SELECT count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_line) FROM f4 WHERE gate AND sp_fires")
    res["score_gated"] = score(n, ex, co)
    res["first_links"] = first_links(con, "(SELECT 'SCT' v, sct c, gate, present FROM f4)", "v", "c")
    res["first_links_hp"] = first_links(con, "(SELECT 'HP' v, hpo_id c, gate, present FROM f4)", "v", "c")
    save(con, "f4", fam)
    cols = "hpo_id, hp_name, old_code, old_name, sct, sct_fsn, how, n_targets, sp_codes, gate, present, sp_fires, sp_line"
    rows = sample(con, f"(SELECT 'random 30' AS smp, {cols}, hpo_id || sct k FROM f4)", "k", None, seed)
    rows += json.loads(con.execute(f"""SELECT 'second path contradicts' AS smp, {cols}, hpo_id || sct k FROM f4
                                       WHERE gate AND NOT present AND sp_fires AND NOT sp_line ORDER BY hpo_id, sct""").df().to_json(orient="records"))
    for r in rows:
        for k in ("gate", "present", "k"):
            r.pop(k, None)
        r["sp_names"] = None
    for r in rows:          # the second path's SNOMED names, for the reader
        if r.get("sp_codes"):
            r["sp_names"] = "; ".join(x[0] for x in con.execute(
                "SELECT fsn FROM cmp.concept WHERE id IN (SELECT unnest(string_split(?, ' ')))", [r["sp_codes"]]).fetchall())
    res["contradictions_new"] = sum(1 for r in rows if r["smp"].startswith("second"))
    res["hand_check"] = write_sheet(fam, (
        "Wave 2 family 4 (27 Sep 2026): HPO -> SNOMED CT rows of the UTS crosswalk (cache/umls/hpo_snomed.tsv) whose SNOMED "
        "code is retired in SNOMED CT-AU, lifted through the AU association refset (SAME AS, REPLACED BY; up to 3 steps) to "
        "an active concept. Gate: build_edges.py's same-name rule (the HPO label equals the active concept's preferred term, "
        "or the retired code's UMLS name). Sample: 30 new pairs, md5(seed || key); then every new pair where MRCONSO 2026AA "
        "puts the HPO term with other active SNOMED concepts, none on one is-a line. CORRECT when the SNOMED concept denotes "
        "the HPO phenotype. UMLS- and SNOMED-derived: git-ignored."), rows, ("hpo_id", "sct"))
    return res


# --- family 5: ChEMBL mechanism drug -> UniProt target --------------------------------------------------------------------
def family5(con, seed: str) -> dict:
    fam = "chembl_moa_target"
    raw = json.load(open(CHEMBL_RAW))
    mech = [(k, m.get("molecule_chembl_id"), m.get("target_chembl_id"), acc, m.get("action_type"), m.get("mechanism_of_action"),
             m.get("direct_interaction"), m.get("molecular_mechanism"))
            for k, ms in raw["mechanisms"].items() for m in ms for acc in raw["targets"].get(m.get("target_chembl_id"), [])]
    con.execute("""CREATE OR REPLACE TEMP TABLE f5_m (queried VARCHAR, molecule VARCHAR, target_chembl VARCHAR, acc VARCHAR,
                   action_type VARCHAR, moa VARCHAR, direct_interaction INT, molecular_mechanism INT)""")
    con.executemany("INSERT INTO f5_m VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mech)
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f5_x AS SELECT DISTINCT struct_id s, identifier chembl FROM {tsv('identifier')} WHERE id_type = 'ChEMBL_ID'""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f5_act AS SELECT DISTINCT struct_id s, unnest(string_split(accession, '|')) acc, moa
                    FROM {tsv('act_table_full')} WHERE accession IS NOT NULL AND accession <> ''""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE f5_gene AS SELECT DISTINCT accession acc, upper(gene) gene, organism FROM {tsv('target_component')}
                    WHERE gene IS NOT NULL AND gene <> ''
                    UNION SELECT DISTINCT e.o_code, upper(n.name), 'Homo sapiens' FROM edge e JOIN node n ON n.vocab = 'HGNC' AND n.code = e.s_code
                    WHERE e.predicate = 'hgnc:xref' AND e.o_vocab = 'UNIPROT'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f5_dcm AS SELECT DISTINCT m.s_code drug, t.o_code acc FROM edge m
                   JOIN edge t ON t.s_vocab = 'DC_TARGET' AND t.s_code = m.o_code AND t.predicate = 'drugcentral:target_component'
                   WHERE m.predicate = 'drugcentral:mechanism_target' AND m.state <> 'rejected'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f5 AS
        WITH sz AS (SELECT target_chembl, count(DISTINCT acc) n FROM f5_m GROUP BY 1),
             p AS (SELECT x.s drug, m.acc, string_agg(DISTINCT m.queried, ' ') chembl, string_agg(DISTINCT m.molecule, ' ') molecule,
                          string_agg(DISTINCT m.target_chembl, ' ') target_chembl, max(sz.n) target_size,
                          string_agg(DISTINCT m.action_type, ' ') action_type, string_agg(DISTINCT m.moa, '; ') moa
                   FROM f5_m m JOIN f5_x x ON x.chembl = m.queried JOIN sz ON sz.target_chembl = m.target_chembl GROUP BY 1, 2)
        SELECT p.*, (SELECT any_value(name) FROM node WHERE vocab = 'DRUGCENTRAL' AND code = p.drug) drug_name,
               (SELECT string_agg(DISTINCT gene || ' (' || organism || ')', ', ') FROM f5_gene g WHERE g.acc = p.acc) acc_gene,
               (p.drug, p.acc) IN (SELECT drug, acc FROM f5_dcm) present,
               EXISTS (SELECT 1 FROM f5_act a WHERE a.s = p.drug) sp_fires,
               EXISTS (SELECT 1 FROM f5_act a WHERE a.s = p.drug AND a.acc = p.acc) sp_exact,
               EXISTS (SELECT 1 FROM f5_act a JOIN f5_gene g1 ON g1.acc = a.acc JOIN f5_gene g2 ON g2.acc = p.acc AND g2.gene = g1.gene
                       WHERE a.s = p.drug) sp_gene,
               (SELECT string_agg(DISTINCT g.gene, ' ') FROM f5_act a JOIN f5_gene g ON g.acc = a.acc WHERE a.s = p.drug AND a.moa = '1') dc_moa_genes,
               TRUE gate
        FROM p""")
    # a subunit of the same ChEMBL target (a complex or protein family) that DrugCentral does record for the drug
    con.execute("""CREATE OR REPLACE TEMP TABLE f5_cx AS SELECT DISTINCT x.s drug, m.acc FROM f5_m m JOIN f5_x x ON x.chembl = m.queried
                   JOIN f5_m m2 ON m2.queried = m.queried AND m2.target_chembl = m.target_chembl
                   JOIN f5_act a ON a.s = x.s AND a.acc = m2.acc""")
    con.execute("""CREATE OR REPLACE TEMP TABLE f5 AS SELECT f5.*, (f5.drug, f5.acc) IN (SELECT drug, acc FROM f5_cx) sp_complex FROM f5""")
    con.execute("UPDATE f5 SET sp_gene = sp_gene OR sp_exact OR sp_complex")
    res = {"chembl_molecules_in_raw": len(raw["mechanisms"]), "mechanism_rows_with_accession": len(mech),
           "raw_scope": "moa_chembl_raw.json holds ChEMBL's answers only for the molecules chembl_moa_witness.py asked about -- "
                        "drugs whose DrugCentral mechanism came from a source other than ChEMBL -- not the whole ChEMBL mechanism table",
           "candidates": counts(con, "f5"),
           "new_drugs": q1(con, "SELECT count(DISTINCT drug) FROM f5 WHERE NOT present")[0]}
    for label, where in (("score_all", "sp_fires"), ("score_new", "sp_fires AND NOT present")):
        n, ex, co = q1(con, f"SELECT count(*), count(*) FILTER (WHERE sp_exact), count(*) FILTER (WHERE sp_gene) FROM f5 WHERE {where}")
        res[label] = score(n, ex, co)
        res[label]["consistent_means"] = ("same accession, the same gene symbol (another species' ortholog), or another component of the "
                                          "same ChEMBL target, in DrugCentral's activities for the drug")
    res["first_links"] = first_links(con, "(SELECT 'UNIPROT' v, acc c, gate, present FROM f5)", "v", "c")
    save(con, "f5", fam)
    cols = "drug, drug_name, chembl, molecule, target_chembl, acc, acc_gene, target_size, action_type, moa, dc_moa_genes, gate, present, sp_fires, sp_exact, sp_gene"
    rows = sample(con, f"(SELECT 'random 30' AS smp, {cols}, drug || acc k FROM f5)", "k", None, seed)
    rows += json.loads(con.execute(f"""SELECT 'second path contradicts' AS smp, {cols}, drug || acc k FROM f5
                                       WHERE NOT present AND sp_fires AND NOT sp_gene ORDER BY drug, acc""").df().to_json(orient="records"))
    for r in rows:
        for k in ("gate", "present", "k"):
            r.pop(k, None)
    res["contradictions_new"] = sum(1 for r in rows if r["smp"].startswith("second"))
    res["hand_check"] = write_sheet(fam, (
        "Wave 2 family 5 (27 Sep 2026): ChEMBL drug mechanisms (cache/chembl/moa_chembl_raw.json) -> the UniProt accessions "
        "of the mechanism's target, for DrugCentral drugs (by ChEMBL id), where DrugCentral's own mechanism rows do not "
        "already reach that accession. Sample: 30 new pairs, md5(seed || key); then every new pair where DrugCentral records "
        "activities for the drug but none on that accession or gene. CORRECT when the protein is a component of the target "
        "through which the drug acts (a subunit of a complex target counts; a protein the drug merely binds does not)."),
        rows, ("drug", "acc"))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graph", default="out/graph.duckdb", help="a COPY of the graph (opened read-only)")
    ap.add_argument("--compendium", default="out/compendium.duckdb")
    ap.add_argument("--assoc", default=str(ASSOC))
    ap.add_argument("--seed", default="wave2-27sep")
    ap.add_argument("--families", default="1,2,3,4,5")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(a.graph, read_only=True)
    con.execute("SET threads=8")
    con.execute(f"ATTACH '{a.compendium}' AS cmp (READ_ONLY)")
    con.create_function("norm", norm, ["VARCHAR"], "VARCHAR")
    con.execute("""CREATE TEMP TABLE linked AS SELECT DISTINCT s_vocab v, s_code c FROM edge WHERE s_vocab <> o_vocab AND state <> 'rejected'
                   UNION SELECT DISTINCT o_vocab, o_code FROM edge WHERE s_vocab <> o_vocab AND state <> 'rejected'""")
    summ_path = OUT / "summary.json"
    summ = json.load(open(summ_path)) if summ_path.exists() else {}
    fams = {"1": ("umls_disease_member", lambda: family1(con, a.seed)), "2": ("unii_rxnorm", lambda: family2(con, a.seed)),
            "3": ("drug_pharma_role", lambda: family3(con, a.seed)), "4": ("hpo_snomed_lifted", lambda: family4(con, a.seed, Path(a.assoc))),
            "5": ("chembl_moa_target", lambda: family5(con, a.seed))}
    for f in a.families.split(","):
        name, fn = fams[f.strip()]
        print(f"family {f}: {name}", flush=True)
        summ[name] = fn()
        print(json.dumps(summ[name], indent=1), flush=True)
    summ["_meta"] = {"seed": a.seed, "graph": a.graph, "sample_per_stratum": N_SAMPLE}
    json.dump(summ, open(summ_path, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
