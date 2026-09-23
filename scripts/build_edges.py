#!/usr/bin/env python3
"""Build the medical multigraph: one `node` table and one `edge` table, validated against the register.

Every edge is a row -- subject, predicate, object, and where it came from -- so parallel edges (the same fact from two
sources), cycles and loops are natural, and "where do two sources disagree?" is a GROUP BY. Design:
docs/weighted-graph-design.md. The register, reference/graph_predicates.json, is a contract:

    * an edge whose predicate is not registered is refused;
    * an edge whose subject or object vocabulary is not the registered one is refused;
    * an edge with no source is refused (rule zero);
    * a predicate registered as needs_source / needs_binding / needs_scoring cannot be loaded at all.

Any refusal aborts the build and prints what was refused. Nodes are keyed (vocabulary, code) and are never merged
across vocabularies: the same substance in SNOMED and RxNorm is two nodes joined by an identity edge.

Families loaded (those the register marks `built`):

    SNOMED CT-AU   every relationship in the RF2 snapshot (compendium `rel`): the poly-hierarchy, AMT structure,
                   finding site, morphology, method, laterality, occurrence, clinical course ...   115 attribute types
    OMOP           AMT product -> standard drug (direct, and item 15's indirect routes); rejected ones kept as
                   state=rejected so the refused answer survives but traversal skips it
    ingredients    substance -> standard ingredient (substance_standard_ingredient)
    ATC            product -> ATC class, from PBS and from OMOP, as PARALLEL edges
    PBS            AMT -> PBS item -> restriction -> indication (severity / episodicity as attrs)
    corpus         guideline condition -> SNOMED binding
    LOINC          term -> component / property / time / system / scale / method, question -> answer (spine.duckdb)
    MONDO          is-a, and exactMatch to SNOMED / ICD-10-CM / OMIM / Orphanet (+ OMOP ICD-10-CM -> SNOMED, to score it)
    HPO            is-a, and disease -> phenotype (present / absent) with frequency, onset, sex
    DrugCentral    drug -> RxNorm / SNOMED / ATC, and indication / contraindication / off-label use  (if extracted)

Writes out/graph.duckdb. Pins recorded on every edge.

    scripts/build_edges.py [--vocab-dir ~/code/spine/out/omop-vocab]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import duckdb

CMP = Path("out/compendium.duckdb")
SPINE = Path(os.path.expanduser("~/code/spine/out/spine.duckdb"))
GRAPH = Path("out/graph.duckdb")
REGISTER = Path("reference/graph_predicates.json")
BINDINGS = Path("reference/snomed_bindings.json")
PBS = Path("cache/pbs")
MONDO_OBO, MONDO_SSSOM = Path("cache/mondo/mondo.obo"), Path("cache/mondo/mondo.sssom.tsv")
HP_OBO, HPOA = Path("cache/hpo/hp.obo"), Path("cache/hpo/phenotype.hpoa")
DC = Path("cache/drugcentral")
UMLS_HPO = Path("cache/umls/hpo_snomed.tsv")
PBS_BIND = Path("reference/pbs_indication_bindings.json")   # scripts/bind_indications.py
LOINC_EXT = Path(os.environ.get("LOINC_EXTENSION", os.path.expanduser(
    "~/Documents/ONTOLOGIES/SnomedCT_LOINCExtension_PRODUCTION_LO1010000_20260321T120000Z/Snapshot")))   # licensed; read in place
LOINC_TABLE = Path(os.environ.get("LOINC_TABLE", os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/LoincTable/Loinc.csv")))     # written by scripts/umls_hpo_crosswalk.py (licensed; not redistributed)

PIN = {"sct": "SNOMED CT-AU 20260731", "athena": "Athena v5.0 29-AUG-26", "pbs": "PBS schedule 4333",
       "loinc": "LOINC 2.82 (Athena)", "mondo": "MONDO releases/2026-09-01", "hpo": "HPO 2026-09-02",
       "dc": "DrugCentral 2023-11-01", "corpus": "reference/snomed_bindings.json", "umls": "UMLS current (UTS crosswalk)", "loinc_ext": "LOINC Extension 20260321", "loinc_table": "LOINC 2.83"}
OMOP_VOCAB = {"RxNorm": "RXN", "RxNorm Extension": "RXE", "AMT": "SCT", "SNOMED": "SCT", "ATC": "ATC", "ICD10CM": "ICD10CM"}
LOINC_AXIS = {"COMPONENT": "loinc:has_component", "PROPERTY": "loinc:has_property", "TIME": "loinc:has_time_aspect",
              "SYSTEM": "loinc:has_system", "SCALE": "loinc:has_scale", "METHOD": "loinc:has_method"}
EDGE_COLS = "s_vocab, s_code, predicate, o_vocab, o_code, source, source_locator, method, tier, state, pin, attrs"


def obo_terms(path: Path) -> list[dict]:
    """Minimal OBO reader: id, name, is_a, obsolete. Enough for hierarchy and labels."""
    terms, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line == "[Term]":
            cur = {"is_a": []}
            terms.append(cur)
        elif line.startswith("[") and line.endswith("]"):
            cur = None
        elif cur is not None and ": " in line:
            k, v = line.split(": ", 1)
            if k == "id":
                cur["id"] = v
            elif k == "name":
                cur["name"] = v
            elif k == "is_a":
                cur["is_a"].append(v.split(" ")[0])
            elif k == "is_obsolete" and v.strip() == "true":
                cur["obsolete"] = True
    return [t for t in terms if "id" in t and not t.get("obsolete")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    a = ap.parse_args()
    opts = "delim='\t', header=true, quote='', escape='', all_varchar=true"
    if GRAPH.exists():
        GRAPH.unlink()
    con = duckdb.connect(str(GRAPH))
    con.execute(f"ATTACH '{CMP}' AS cmp (READ_ONLY)")
    con.execute(f"ATTACH '{SPINE}' AS sp (READ_ONLY)")
    con.execute(f"CREATE TEMP VIEW C  AS SELECT * FROM read_csv('{a.vocab_dir}/CONCEPT.csv', {opts})")
    con.execute(f"CREATE TEMP VIEW CR AS SELECT * FROM read_csv('{a.vocab_dir}/CONCEPT_RELATIONSHIP.csv', {opts})")
    con.execute("""CREATE TABLE edge (s_vocab VARCHAR, s_code VARCHAR, predicate VARCHAR, o_vocab VARCHAR, o_code VARCHAR,
                   source VARCHAR, source_locator VARCHAR, method VARCHAR, tier VARCHAR, state VARCHAR, pin VARCHAR, attrs JSON)""")
    con.execute("CREATE TEMP TABLE name_hint (vocab VARCHAR, code VARCHAR, name VARCHAR)")
    log = {}

    def ins(label: str, sql: str, params=None) -> None:
        before = con.execute("SELECT count(*) FROM edge").fetchone()[0]
        con.execute(f"INSERT INTO edge ({EDGE_COLS}) " + sql, params or [])
        log[label] = con.execute("SELECT count(*) FROM edge").fetchone()[0] - before
        print(f"  {label:<44} {log[label]:>10,}", flush=True)

    def ins_rows(label: str, rows: list[tuple]) -> None:
        before = con.execute("SELECT count(*) FROM edge").fetchone()[0]
        if rows:
            con.executemany(f"INSERT INTO edge ({EDGE_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        log[label] = con.execute("SELECT count(*) FROM edge").fetchone()[0] - before
        print(f"  {label:<44} {log[label]:>10,}", flush=True)

    vmap = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in OMOP_VOCAB.items())
    print("loading edges:")
    # --- SNOMED CT-AU: the whole relationship snapshot ------------------------------------------------------------
    ins("SNOMED CT-AU relationships", f"""SELECT 'SCT', src, 'sct:' || typ, 'SCT', dst, 'SNOMED CT-AU RF2', 'compendium rel',
            'native', 'native', 'asserted', '{PIN['sct']}', json_object('group', grp) FROM cmp.rel""")

    # --- OMOP product mappings (concept ids resolved to (vocabulary, code) once) -----------------------------------
    con.execute("""CREATE TEMP TABLE want AS SELECT DISTINCT CAST(id AS VARCHAR) AS id FROM (
        SELECT standard_concept_id AS id FROM cmp.omop_drug WHERE standard_concept_id IS NOT NULL
        UNION SELECT refused_standard_concept_id FROM cmp.omop_drug WHERE refused_standard_concept_id IS NOT NULL
        UNION SELECT standard_concept_id FROM cmp.omop_drug_indirect WHERE standard_concept_id IS NOT NULL)""")
    con.execute("""CREATE TEMP TABLE cmap AS SELECT c.concept_id, c.vocabulary_id, c.concept_code, c.concept_name
                   FROM C c JOIN want w ON w.id = c.concept_id""")
    ins("OMOP product -> standard drug", f"""SELECT 'SCT', o.product_id, 'omop:maps_to', CASE m.vocabulary_id {vmap} END,
            m.concept_code, 'OMOP Athena', 'omop_drug', 'Maps to', 'ungraded', 'asserted', '{PIN['athena']}',
            json_object('level', o.level, 'witness', chk.verdict)
        FROM cmp.omop_drug o JOIN cmap m ON m.concept_id = CAST(o.standard_concept_id AS VARCHAR)
        LEFT JOIN cmp.omop_drug_check chk ON chk.product_id = o.product_id AND chk.source = 'omop_drug'""")
    ins("OMOP product -> standard drug (rejected)", f"""SELECT 'SCT', o.product_id, 'omop:maps_to', CASE m.vocabulary_id {vmap} END,
            m.concept_code, 'OMOP Athena', 'omop_drug.refused_standard_concept_id', 'Maps to', 'ungraded', 'rejected',
            '{PIN['athena']}', json_object('level', o.level, 'review', o.review_status)
        FROM cmp.omop_drug o JOIN cmap m ON m.concept_id = CAST(o.refused_standard_concept_id AS VARCHAR)""")
    ins("OMOP product -> standard drug (indirect)", f"""SELECT 'SCT', x.product_id, 'omop:maps_to_indirect', CASE m.vocabulary_id {vmap} END,
            m.concept_code, 'scripts/amt_indirect.py', 'omop_drug_indirect', x.route, 'ungraded', 'asserted', '{PIN['athena']}',
            json_object('level', x.level, 'via', x.via_product_id)
        FROM cmp.omop_drug_indirect x JOIN cmap m ON m.concept_id = CAST(x.standard_concept_id AS VARCHAR)""")

    # --- substance -> standard ingredient ---------------------------------------------------------------------------
    ins("substance -> standard ingredient", """SELECT 'SCT', substance_id, 'std_ingredient',
            CASE vocabulary WHEN 'RxNorm' THEN 'RXN' ELSE 'RXE' END, code, source, 'substance_standard_ingredient',
            split_part(source, ':', 1), CASE WHEN source LIKE 'route:%' THEN tier WHEN source = 'decision' THEN 'decision'
                                              ELSE 'ungraded' END,
            CASE WHEN state = 'asserted' THEN 'asserted' ELSE state END, '', json_object('check', "check")
        FROM cmp.substance_standard_ingredient""")
    con.execute(f"UPDATE edge SET pin = '{PIN['athena']}' WHERE predicate = 'std_ingredient'")

    # --- ATC: PBS and OMOP as parallel edges -------------------------------------------------------------------------
    ins("product -> ATC (PBS and OMOP, parallel)", f"""SELECT 'SCT', product_id, 'in_atc_class', 'ATC', atc_code,
            CASE source WHEN 'pbs' THEN 'PBS item-atc' ELSE 'OMOP CONCEPT_ANCESTOR' END, 'product_atc',
            CASE source WHEN 'pbs' THEN 'native' ELSE 'omop ancestry' END, CASE source WHEN 'pbs' THEN 'native' ELSE 'ungraded' END,
            'asserted', CASE source WHEN 'pbs' THEN '{PIN['pbs']}' ELSE '{PIN['athena']}' END, json_object('atc_level', atc_level)
        FROM cmp.product_atc""")

    # --- PBS: AMT -> item -> restriction -> indication ---------------------------------------------------------------
    rows = lambda f: f"(SELECT unnest(rows, recursive := true) FROM read_json_auto('{PBS}/{f}.json', maximum_object_size=300000000))"
    ins("AMT -> PBS item", f"""SELECT DISTINCT 'SCT', CAST(amt_code AS VARCHAR), 'pbs:lists', 'PBS_ITEM', split_part(li_item_id, '_', 1),
            'PBS API v3 amt-items', 'cache/pbs/amt-items.json', 'native', 'native', 'asserted', '{PIN['pbs']}',
            json_object('amt_level', concept_type_code) FROM {rows('amt-items')} WHERE amt_code IS NOT NULL""")
    ins("PBS item -> restriction", f"""SELECT DISTINCT 'PBS_ITEM', pbs_code, 'pbs:has_restriction', 'PBS_RESTRICTION', res_code,
            'PBS API v3 item-restriction-relationships', 'cache/pbs/item-restriction-relationships.json', 'native', 'native',
            'asserted', '{PIN['pbs']}', json_object('benefit_type', benefit_type_code) FROM {rows('item-restriction-relationships')}""")
    con.execute(f"CREATE TEMP TABLE ind AS SELECT * FROM {rows('indications')}")
    ins("PBS restriction -> indication", f"""SELECT DISTINCT 'PBS_RESTRICTION', r.res_code, 'pbs:restricted_to', 'PBS_INDICATION',
            CAST(i.indication_prescribing_txt_id AS VARCHAR), 'PBS API v3 restriction-prescribing-text-relationships + indications',
            'cache/pbs/indications.json', 'native', 'native', 'asserted', '{PIN['pbs']}',
            json_object('severity', i.severity, 'episodicity', i.episodicity)
        FROM {rows('restriction-prescribing-text-relationships')} r
        JOIN ind i ON CAST(i.indication_prescribing_txt_id AS VARCHAR) = CAST(r.prescribing_text_id AS VARCHAR)""")
    con.execute("INSERT INTO name_hint SELECT 'PBS_INDICATION', CAST(indication_prescribing_txt_id AS VARCHAR), condition FROM ind")
    con.execute(f"""INSERT INTO name_hint SELECT 'PBS_ITEM', pbs_code, any_value(li_drug_name || coalesce(' (' || brand_name || ')', ''))
                    FROM {rows('items')} GROUP BY pbs_code""")

    # --- PBS indication text -> SNOMED: exact matches only (scripts/bind_indications.py); the rest stay candidates -----
    if PBS_BIND.exists():
        pb = json.load(open(PBS_BIND))["results"]
        ins_rows("PBS indication -> SNOMED (exact matches only)", [
            ("PBS_INDICATION", str(r["indication_prescribing_txt_id"]), "pbs:indication_is", "SCT", r["bound"]["concept_id"],
             "reference/pbs_indication_bindings.json", r["text"], r["bound"]["method"], "ungraded", "asserted",
             "SNOMED CT-AU 20260831 (live Ontoserver)",
             json.dumps({k: v for k, v in (("stripped_qualifier", r["bound"].get("stripped_qualifier")),
                                           ("pbs_severity", r.get("pbs_severity")), ("pbs_episodicity", r.get("pbs_episodicity"))) if v}))
            for r in pb if r.get("bound")])

    # --- corpus condition bindings ----------------------------------------------------------------------------------
    b = json.load(open(BINDINGS))["results"]
    ins_rows("corpus condition -> SNOMED", [("CORPUS", r["condition"], "corpus:binds_to", "SCT", r["snomed"]["concept_id"],
             "reference/snomed_bindings.json", r["condition"], r["snomed"].get("method"), "ungraded",
             "asserted", PIN["corpus"], json.dumps({"parent_verified": r["snomed"].get("parent_verified")}))
             for r in b if r.get("snomed")])
    con.executemany("INSERT INTO name_hint VALUES ('CORPUS', ?, ?)", [(r["condition"], r["condition"]) for r in b])

    # --- LOINC -------------------------------------------------------------------------------------------------------
    axis = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in LOINC_AXIS.items())
    ins("LOINC term -> axis part", f"""SELECT 'LOINC', code, CASE axis {axis} END, 'LOINC', part_code, 'LOINC via Athena',
            'spine.duckdb loinc_axis', 'native', 'native', 'asserted', '{PIN['loinc']}', NULL FROM sp.loinc_axis""")
    ins("LOINC question -> answer", f"""SELECT DISTINCT 'LOINC', question_code, 'loinc:has_answer', 'LOINC', answer_code, 'LOINC via Athena',
            'spine.duckdb loinc_answer', 'native', 'native', 'asserted', '{PIN['loinc']}', NULL FROM sp.loinc_answer""")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', code, concept_name FROM sp.loinc_omop")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', part_code, any_value(part_name) FROM sp.loinc_axis GROUP BY part_code")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', answer_code, any_value(answer_name) FROM sp.loinc_answer GROUP BY answer_code")

    # --- LOINC -> SNOMED: the bridge out of LOINC's island (Athena places lab tests under SNOMED measurements) -----
    ins("LOINC -> SNOMED (Is a / Maps to)", f"""SELECT DISTINCT 'LOINC', l.concept_code,
            CASE r.relationship_id WHEN 'Is a' THEN 'loinc:is_a_snomed' ELSE 'loinc:maps_to_snomed' END, 'SCT', s.concept_code,
            'OMOP Athena', 'CONCEPT_RELATIONSHIP', r.relationship_id, 'ungraded', 'asserted', '{PIN['athena']}', NULL
        FROM CR r JOIN C l ON l.concept_id = r.concept_id_1 AND l.vocabulary_id = 'LOINC'
        JOIN C s ON s.concept_id = r.concept_id_2 AND s.vocabulary_id = 'SNOMED'
        WHERE r.relationship_id IN ('Is a', 'Maps to', 'Maps to value') AND (r.invalid_reason IS NULL OR r.invalid_reason = '')""")

    # --- LOINC Ontology: LOINC lab terms as SNOMED CT observable entities (the extension, read in place) ------------
    # Its observables are where SNOMED's Interprets points, so lab result -> finding becomes a lookup chain. The
    # extension's relationships are ordinary SNOMED edges (same predicates); LOINC num <-> SCTID is the official
    # identifier table; order groupers get their own predicate so they can never pass for result codes.
    if LOINC_EXT.exists():
        T, R = LOINC_EXT / "Terminology", LOINC_EXT / "Refset"
        ext = lambda f: f"read_csv('{f}', delim='\\t', header=true, quote='', escape='', all_varchar=true)"
        ins("LOINC Extension relationships", f"""SELECT 'SCT', sourceId, 'sct:' || typeId, 'SCT', destinationId,
                'SNOMED CT LOINC Extension', 'sct2_Relationship_Snapshot', 'native', 'native', 'asserted', '{PIN['loinc_ext']}',
                json_object('group', relationshipGroup)
            FROM {ext(T / 'sct2_Relationship_Snapshot_LO1010000_20260321.txt')} WHERE active = '1'""")
        con.execute(f"""CREATE TEMP TABLE lx_role AS SELECT referencedComponentId AS sct,
                bool_or(refsetId = '635121010000106') AS observation, bool_or(refsetId = '635111010000100') AS orderable
            FROM {ext(R / 'Content' / 'der2_Refset_SimpleSnapshot_LO1010000_20260321.txt')} WHERE active = '1' GROUP BY 1""")
        con.execute(f"""CREATE TEMP TABLE lx_disc AS SELECT DISTINCT referencedComponentId AS sct FROM
            {ext(R / 'Metadata' / 'der2_scsRefset_ComponentAnnotationStringValueSnapshot_LO1010000_20260321.txt')}
            WHERE active = '1' AND value = 'Discouraged'""")
        lt = (f"(SELECT LOINC_NUM, CLASS, CLASSTYPE, STATUS, LONG_COMMON_NAME FROM read_csv('{LOINC_TABLE}', header=true, all_varchar=true))"
              if LOINC_TABLE.exists() else "(SELECT NULL AS LOINC_NUM, NULL AS CLASS, NULL AS CLASSTYPE, NULL AS STATUS, NULL AS LONG_COMMON_NAME)")
        con.execute(f"CREATE TEMP TABLE lx_loinc AS SELECT * FROM {lt}")
        ins("LOINC -> SNOMED observable (LOINC Ontology identifier)", f"""SELECT DISTINCT 'LOINC', i.alternateIdentifier,
                CASE WHEN l.CLASS = 'LABORDERS.ONTOLOGY' THEN 'loinc:order_grouper_concept' ELSE 'loinc:sct_concept' END,
                'SCT', i.referencedComponentId, 'SNOMED CT LOINC Extension', 'sct2_Identifier_Snapshot', 'official identifier',
                'native', 'asserted', '{PIN['loinc_ext']}',
                json_object('observation', r.observation, 'orderable', r.orderable, 'discouraged', d.sct IS NOT NULL,
                            'loinc_class', l.CLASS, 'classtype', l.CLASSTYPE, 'loinc_status', l.STATUS)
            FROM {ext(T / 'sct2_Identifier_Snapshot_LO1010000_20260321.txt')} i
            LEFT JOIN lx_role r ON r.sct = i.referencedComponentId LEFT JOIN lx_disc d ON d.sct = i.referencedComponentId
            LEFT JOIN lx_loinc l ON l.LOINC_NUM = i.alternateIdentifier
            WHERE i.active = '1' AND i.identifierSchemeId = '30051010000102'""")
        # names: the extension's preferred synonym (language refset 'preferred'), else its FSN; LOINC 2.83 names for LOINC codes
        con.execute(f"""INSERT INTO name_hint
            SELECT 'SCT', d.conceptId, any_value(d.term) FROM {ext(T / 'sct2_Description_Snapshot-en_LO1010000_20260321.txt')} d
            JOIN {ext(R / 'Language' / 'der2_cRefset_LanguageSnapshot-en_LO1010000_20260321.txt')} g
              ON g.referencedComponentId = d.id AND g.active = '1' AND g.acceptabilityId = '900000000000548007'
            WHERE d.active = '1' AND d.typeId = '900000000000013009' GROUP BY 2""")
        con.execute("INSERT INTO name_hint SELECT 'LOINC', LOINC_NUM, LONG_COMMON_NAME FROM lx_loinc WHERE LOINC_NUM IS NOT NULL")

        # --- lab result -> finding, through the analyte (reference/interprets_handcheck.json) -------------------------
        # SNOMED findings interpret measurement PROCEDURES; the LOINC Ontology puts LOINC terms under OBSERVABLES, so
        # is-a never joins them (14 findings). They meet on the analyte: the observable and the Interprets target share a
        # Component, and the LOINC specimen is the target's or below it. Each rule below answers a failure in the hand check.
        IS_A, COMP, SPEC, SITE = "sct:116680003", "sct:246093002", "sct:116686009", "sct:704327008"
        con.execute(f"""CREATE TEMP TABLE ix_tgt AS SELECT DISTINCT i.s_code AS finding, i.o_code AS tgt, c.o_code AS comp,
                sp.o_code AS spec, h.o_code AS interp
            FROM edge i JOIN edge c ON c.s_code = i.o_code AND c.predicate = '{COMP}'
            JOIN edge sp ON sp.s_code = i.o_code AND sp.predicate = '{SPEC}'
            JOIN edge h ON h.s_code = i.s_code AND h.predicate = 'sct:363713009'
                        AND json_extract(h.attrs, '$.group') = json_extract(i.attrs, '$.group')
            WHERE i.predicate = 'sct:363714003'""")
        # the most general procedure for its (component, specimen) only: Random / Fasting / electrophoresis refinements of
        # 'Blood glucose measurement' or 'Urine protein measurement' matched timed and plain LOINC terms they do not describe
        con.execute(f"""CREATE TEMP TABLE ix_refined AS
            WITH RECURSIVE u(s, n, d) AS (SELECT DISTINCT tgt, tgt, 0 FROM ix_tgt
                UNION SELECT u.s, e.o_code, u.d + 1 FROM u JOIN edge e ON e.predicate = '{IS_A}' AND e.s_code = u.n WHERE u.d < 20)
            SELECT DISTINCT t.tgt FROM ix_tgt t JOIN u ON u.s = t.tgt AND u.n <> t.tgt
            JOIN edge c ON c.s_code = u.n AND c.predicate = '{COMP}' AND c.o_code = t.comp
            JOIN edge sp ON sp.s_code = u.n AND sp.predicate = '{SPEC}' AND sp.o_code = t.spec""")
        lx_axes = (f"(SELECT LOINC_NUM, PROPERTY, COMPONENT FROM read_csv('{LOINC_TABLE}', header=true, all_varchar=true))"
                   if LOINC_TABLE.exists() else "(SELECT NULL AS LOINC_NUM, NULL AS PROPERTY, NULL AS COMPONENT)")
        # ratios and differences are not levels; these component heads lose their refinement in the extension's Component
        con.execute(f"""CREATE TEMP TABLE ix_lo AS SELECT l.s_code AS loinc, l.o_code AS obs, c.o_code AS comp, s.o_code AS site
            FROM edge l JOIN edge c ON c.s_code = l.o_code AND c.predicate = '{COMP}'
            JOIN edge s ON s.s_code = l.o_code AND s.predicate = '{SITE}' LEFT JOIN {lx_axes} x ON x.LOINC_NUM = l.s_code
            WHERE l.predicate = 'loinc:sct_concept'
              AND NOT EXISTS (SELECT 1 FROM edge r WHERE r.s_code = l.o_code AND r.predicate = 'sct:704325000')
              AND coalesce(x.PROPERTY, '') NOT ILIKE '%diff%' AND coalesce(x.PROPERTY, '') NOT ILIKE '%rto%'
              AND split_part(coalesce(x.COMPONENT, ''), '^', 1) NOT IN
                  ('Protein.abnormal band', 'Other cells', 'Unidentified cells', 'Cells counted.total')""")
        con.execute(f"""CREATE TEMP TABLE ix_site_up AS
            WITH RECURSIVE u(s, n, d) AS (SELECT DISTINCT site, site, 0 FROM ix_lo
                UNION SELECT u.s, e.o_code, u.d + 1 FROM u JOIN edge e ON e.predicate = '{IS_A}' AND e.s_code = u.n WHERE u.d < 25)
            SELECT DISTINCT s, n FROM u""")
        ins("LOINC result -> finding it defines (Interprets, by analyte)", f"""SELECT 'LOINC', lo.loinc,
                'loinc:interpreted_in_finding', 'SCT', t.finding, 'SNOMED CT-AU + SNOMED CT LOINC Extension',
                'Interprets ' || t.tgt || ' / Component ' || t.comp || ' / LOINC observable ' || lo.obs,
                'same component, specimen at or below', 'ungraded', 'asserted', '{PIN['sct']} + {PIN['loinc_ext']}',
                json_object('interpretation', t.interp, 'interprets', t.tgt, 'component', t.comp,
                            'finding_specimen', t.spec, 'loinc_specimen', lo.site, 'loinc_observable', lo.obs)
            FROM ix_lo lo JOIN ix_tgt t ON t.comp = lo.comp JOIN ix_site_up su ON su.s = lo.site AND su.n = t.spec
            WHERE t.tgt NOT IN (SELECT tgt FROM ix_refined)""")

        # --- the same, through Athena's placement: parallel edges, a second witness ------------------------------------
        # Athena files a LOINC term under a SNOMED measurement procedure; a finding that interprets that procedure is
        # reached directly (never through is-a ancestors: 'Evaluation procedure' reaches 20,000 terms). Unrestricted, the
        # new edges were right about half the time -- Athena's procedures are often specimen-less ('Sodium measurement'),
        # so sodium in breast milk reached hyponatraemia. Kept only where the LOINC Ontology's specimen agrees:
        # at or below the target's, or blood / serum / plasma where the target states none. Result codes only (Observation
        # refset, active, not Discouraged), the ratio rules above, and a reviewed list of FRACTION analytes whose level is
        # not the whole's (free testosterone is not testosterone) where the LOINC component differs from the target's.
        con.execute(f"""CREATE TEMP TABLE ax_lo AS SELECT l.s_code AS loinc, l.o_code AS obs, s.o_code AS site
            FROM edge l JOIN edge s ON s.s_code = l.o_code AND s.predicate = '{SITE}' LEFT JOIN {lx_axes} x ON x.LOINC_NUM = l.s_code
            JOIN lx_loinc st ON st.LOINC_NUM = l.s_code
            WHERE l.predicate = 'loinc:sct_concept' AND json_extract_string(l.attrs, '$.observation') = 'true'
              AND json_extract_string(l.attrs, '$.discouraged') = 'false' AND st.STATUS = 'ACTIVE'
              AND NOT EXISTS (SELECT 1 FROM edge r WHERE r.s_code = l.o_code AND r.predicate = 'sct:704325000')
              AND coalesce(x.PROPERTY, '') NOT ILIKE '%diff%' AND coalesce(x.PROPERTY, '') NOT ILIKE '%rto%'
              AND split_part(coalesce(x.COMPONENT, ''), '^', 1) NOT IN
                  ('Protein.abnormal band', 'Other cells', 'Unidentified cells', 'Cells counted.total')""")
        con.execute(f"""CREATE TEMP TABLE ax_site_up AS
            WITH RECURSIVE u(s, n, d) AS (SELECT DISTINCT site, site, 0 FROM ax_lo
                UNION SELECT u.s, e.o_code, u.d + 1 FROM u JOIN edge e ON e.predicate = '{IS_A}' AND e.s_code = u.n WHERE u.d < 25)
            SELECT DISTINCT s, n FROM u""")
        fractions = "'259355006', '710118001', '708043004', '73828001', '37852002', '540101010000101', '115333008', '1382094000'"
        ins("LOINC result -> finding it defines (Interprets, via Athena)", f"""
            WITH ap AS (SELECT DISTINCT a.s_code AS loinc, a.o_code AS proc, i.s_code AS finding, h.o_code AS interp
                  FROM edge a JOIN edge i ON i.o_code = a.o_code AND i.predicate = 'sct:363714003'
                  JOIN edge h ON h.s_code = i.s_code AND h.predicate = 'sct:363713009'
                              AND json_extract(h.attrs, '$.group') = json_extract(i.attrs, '$.group')
                  WHERE a.predicate IN ('loinc:is_a_snomed', 'loinc:maps_to_snomed') AND a.state <> 'rejected'),
            kept AS (SELECT ap.*, lo.obs, lo.site,
                    (SELECT any_value(sp.o_code) FROM edge sp WHERE sp.s_code = ap.proc AND sp.predicate = '{SPEC}') AS spec
                  FROM ap JOIN ax_lo lo USING (loinc)
                  WHERE NOT EXISTS (SELECT 1 FROM edge lc JOIN edge pc ON pc.s_code = ap.proc AND pc.predicate = '{COMP}'
                                    WHERE lc.s_code = lo.obs AND lc.predicate = '{COMP}' AND lc.o_code IN ({fractions})
                                      AND lc.o_code <> pc.o_code))
            SELECT DISTINCT 'LOINC', k.loinc, 'loinc:interpreted_in_finding', 'SCT', k.finding,
                'OMOP Athena + SNOMED CT-AU + SNOMED CT LOINC Extension',
                'Athena Is a / Maps to ' || k.proc || ' / Interprets ' || k.proc || ' / LOINC observable ' || k.obs,
                CASE WHEN k.spec IS NULL THEN 'Athena placement, specimen-less target, blood-family LOINC specimen'
                     ELSE 'Athena placement, specimen at or below' END,
                'ungraded', 'asserted', '{PIN['athena']} + {PIN['sct']} + {PIN['loinc_ext']}',
                json_object('interpretation', k.interp, 'interprets', k.proc, 'finding_specimen', k.spec,
                            'loinc_specimen', k.site, 'loinc_observable', k.obs)
            FROM kept k
            WHERE (k.spec IS NOT NULL AND EXISTS (SELECT 1 FROM edge sp JOIN ax_site_up su ON su.s = k.site AND su.n = sp.o_code
                                                   WHERE sp.s_code = k.proc AND sp.predicate = '{SPEC}'))
               OR (k.spec IS NULL AND EXISTS (SELECT 1 FROM ax_site_up su WHERE su.s = k.site AND su.n = '119297000'))""")

    # --- MONDO -------------------------------------------------------------------------------------------------------
    if MONDO_OBO.exists():
        mt = obo_terms(MONDO_OBO)
        ins_rows("MONDO is-a", [("MONDO", t["id"], "mondo:is_a", "MONDO", p, "MONDO", "mondo.obo", "native", "native",
                                 "asserted", PIN["mondo"], None) for t in mt if t["id"].startswith("MONDO:") for p in t["is_a"]
                                if p.startswith("MONDO:")])
        con.executemany("INSERT INTO name_hint VALUES ('MONDO', ?, ?)", [(t["id"], t.get("name")) for t in mt])
        prefix = {"SCTID": "SCT", "ICD10CM": "ICD10CM", "OMIM": "OMIM", "Orphanet": "ORPHA"}
        sssom = [r for r in csv.DictReader((l for l in open(MONDO_SSSOM) if not l.startswith("#")), delimiter="\t")
                 if r["predicate_id"] == "skos:exactMatch" and r["object_id"].split(":")[0] in prefix]
        con.executemany("INSERT INTO name_hint VALUES (?, ?, ?)",
                        [("MONDO", r["subject_id"], r.get("subject_label")) for r in sssom] +
                        [(prefix[r["object_id"].split(":")[0]], r["object_id"].split(":", 1)[1], r.get("object_label")) for r in sssom
                         if prefix[r["object_id"].split(":")[0]] != "SCT"])   # SNOMED names come from the SNOMED CT-AU release
        ins_rows("MONDO exactMatch -> SNOMED / ICD-10-CM / OMIM / Orphanet",
                 [("MONDO", r["subject_id"], "mondo:exact_match", prefix[r["object_id"].split(":")[0]], r["object_id"].split(":", 1)[1],
                   "MONDO SSSOM", "mondo.sssom.tsv", r.get("mapping_justification"), "ungraded", "asserted", PIN["mondo"], None)
                  for r in sssom])
        ins("ICD-10-CM -> SNOMED (for MONDO's codes)", f"""SELECT DISTINCT 'ICD10CM', s.concept_code, 'icd10cm:maps_to', 'SCT', t.concept_code,
                'OMOP Athena', 'CONCEPT_RELATIONSHIP', 'Maps to', 'ungraded', 'asserted', '{PIN['athena']}', NULL
            FROM (SELECT DISTINCT o_code FROM edge WHERE predicate = 'mondo:exact_match' AND o_vocab = 'ICD10CM') m
            JOIN C s ON s.vocabulary_id = 'ICD10CM' AND s.concept_code = m.o_code
            JOIN CR r ON r.concept_id_1 = s.concept_id AND r.relationship_id = 'Maps to' AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
            JOIN C t ON t.concept_id = r.concept_id_2 AND t.vocabulary_id = 'SNOMED'""")

    # --- HPO ---------------------------------------------------------------------------------------------------------
    if HP_OBO.exists():
        ht = obo_terms(HP_OBO)
        ins_rows("HPO is-a", [("HP", t["id"], "hp:is_a", "HP", p, "HPO", "hp.obo", "native", "native", "asserted", PIN["hpo"], None)
                              for t in ht if t["id"].startswith("HP:") for p in t["is_a"] if p.startswith("HP:")])
        con.executemany("INSERT INTO name_hint VALUES ('HP', ?, ?)", [(t["id"], t.get("name")) for t in ht])
    if HPOA.exists():
        dbv = {"OMIM": "OMIM", "ORPHA": "ORPHA", "DECIPHER": "DECIPHER"}
        rows_h, names = [], {}
        for r in csv.DictReader((l for l in open(HPOA, encoding="utf-8") if not l.startswith("#")), delimiter="\t"):
            if r["aspect"] != "P":
                continue
            v, code = r["database_id"].split(":", 1)
            if v not in dbv:
                continue
            names[(dbv[v], code)] = r["disease_name"]
            rows_h.append((dbv[v], code, "hpo:lacks_phenotype" if r["qualifier"] == "NOT" else "hpo:has_phenotype", "HP", r["hpo_id"],
                           "HPO annotations", r["reference"], r["evidence"], "native", "asserted", PIN["hpo"],
                           json.dumps({k: r[k] for k in ("frequency", "onset", "sex", "modifier") if r[k]})))
        ins_rows("HPO disease -> phenotype (present / absent)", rows_h)
        con.executemany("INSERT INTO name_hint VALUES (?, ?, ?)", [(k[0], k[1], n) for k, n in names.items()])

    # --- DrugCentral (extracted by scripts/drugcentral_extract.py) --------------------------------------------------
    if (DC / "identifier.tsv").exists():
        dc = lambda f: f"read_csv('{DC}/{f}.tsv', delim='\t', header=true, all_varchar=true, quote='')"
        # DrugCentral's RXNORM ids are not all ingredients: 815 are precise ingredients (salts -- amantadine hydrochloride)
        # and 368 brand names (Klonopin). Written as-is they would assert "is ingredient" falsely, and scored as-is they
        # look like disagreement between two correct answers (62% on the first run). Each is lifted to its standard
        # RxNorm ingredient through RxNorm's own relationship; the original id and term type ride as attrs.
        con.execute(f"""CREATE TEMP TABLE dc_rx AS
            WITH ids AS (SELECT DISTINCT struct_id, identifier FROM {dc('identifier')} WHERE id_type = 'RXNORM'),
                 a AS (SELECT i.struct_id, i.identifier, c.concept_id, c.concept_class_id, c.standard_concept
                       FROM ids i JOIN C c ON c.vocabulary_id = 'RxNorm' AND c.concept_code = i.identifier)
            SELECT struct_id, identifier, concept_class_id AS id_class, identifier AS ing, 'itself' AS via
              FROM a WHERE concept_class_id = 'Ingredient' AND standard_concept = 'S'
            UNION
            SELECT a.struct_id, a.identifier, a.concept_class_id, t.concept_code, r.relationship_id
              FROM a JOIN CR r ON r.concept_id_1 = a.concept_id AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
                     AND r.relationship_id = CASE a.concept_class_id WHEN 'Precise Ingredient' THEN 'Form of'
                                                  WHEN 'Brand Name' THEN 'Brand name of' WHEN 'Multiple Ingredients' THEN 'Maps to' END
              JOIN C t ON t.concept_id = r.concept_id_2 AND t.vocabulary_id = 'RxNorm' AND t.concept_class_id = 'Ingredient'
                     AND t.standard_concept = 'S'""")
        ins("DrugCentral -> RxNorm ingredient (lifted)", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:rxnorm', 'RXN', ing,
                'DrugCentral', 'identifier', 'RXNORM ' || via, 'ungraded', 'asserted', '{PIN['dc']}',
                json_object('id_rxcui', identifier, 'id_class', id_class, 'lifted_via', via) FROM dc_rx""")
        ins("DrugCentral -> SNOMED", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:snomed', 'SCT', identifier, 'DrugCentral',
                'identifier', 'SNOMEDCT_US', 'ungraded', 'asserted', '{PIN['dc']}', NULL FROM {dc('identifier')} WHERE id_type = 'SNOMEDCT_US'""")
        if (DC / "struct2atc.tsv").exists():
            ins("DrugCentral -> ATC", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:in_atc_class', 'ATC', atc_code, 'DrugCentral',
                    'struct2atc', 'native', 'native', 'asserted', '{PIN['dc']}', NULL FROM {dc('struct2atc')}""")
        if (DC / "omop_relationship.tsv").exists():
            rel = {"indication": "drugcentral:indication", "contraindication": "drugcentral:contraindication",
                   "off-label use": "drugcentral:off_label_use"}
            when = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in rel.items())
            ins("DrugCentral drug -> condition (label)", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, CASE relationship_name {when} END, 'SCT',
                    snomed_conceptid, 'DrugCentral', 'omop_relationship', relationship_name, 'native', 'asserted', '{PIN['dc']}',
                    json_object('umls_cui', umls_cui, 'concept_name', concept_name)
                FROM {dc('omop_relationship')} WHERE snomed_conceptid IS NOT NULL AND snomed_conceptid <> ''
                  AND relationship_name IN ({','.join(repr(k) for k in rel)})""")
        if (DC / "structures.tsv").exists():
            con.execute(f"INSERT INTO name_hint SELECT 'DRUGCENTRAL', id, name FROM {dc('structures')}")

    # --- UMLS: HPO phenotype -> SNOMED, the bridge from signs and symptoms to SNOMED findings --------------------
    # A shared UMLS CUI groups synonyms, and also near-synonyms: hand-checked 23 Sep 2026, links whose SNOMED name
    # differs from the HPO label were right 34 of 40 (85%, Wilson lower bound ~0.71 -- inadmissible) and wrong by
    # NARROWING (Polycythemia -> Polycythemia vera, Retinal hole -> Retinal round hole). Links whose SNOMED name equals
    # the HPO label were right 40 of 40 (Wilson lower bound 0.912 -- Tier 2). So only those load as edges, EDGE by edge
    # (a same-name term's other co-CUI targets are exactly the narrowings); the rest are written as candidates for a
    # person to cache/umls/hpo_snomed_candidates.tsv (UMLS-derived, licensed, not committed).
    if UMLS_HPO.exists():
        con.execute("""CREATE OR REPLACE MACRO nrm(x) AS
                       regexp_replace(replace(replace(lower(coalesce(x, '')), 'ae', 'e'), 'oe', 'e'), '[^a-z0-9]', '', 'g')""")
        con.execute(f"""CREATE TEMP TABLE umls_hp AS
            SELECT u.hpo_id, u.snomed_code, u.snomed_name, hp.name AS hp_name, c.pt AS au_name,
                   (nrm(hp.name) = nrm(c.pt) OR nrm(hp.name) = nrm(u.snomed_name)) AS same_name
            FROM read_csv('{UMLS_HPO}', delim='\t', header=true, all_varchar=true, quote='') u
            JOIN (SELECT code, any_value(name) AS name FROM name_hint WHERE vocab = 'HP' GROUP BY 1) hp ON hp.code = u.hpo_id
            JOIN cmp.concept c ON c.id = u.snomed_code
            WHERE u.snomed_code IS NOT NULL AND u.snomed_code <> ''""")
        ins("HPO phenotype -> SNOMED (UMLS, same name only)", f"""SELECT DISTINCT 'HP', hpo_id, 'hp:umls_snomed', 'SCT', snomed_code, 'UMLS',
                'UTS crosswalk HPO -> SNOMEDCT_US', 'shared CUI + same name', '2', 'asserted', '{PIN['umls']}',
                json_object('calibrated_on', 'hand check 40/40 same-name edges, 23 Sep 2026')
            FROM umls_hp WHERE same_name""")
        con.execute(f"""COPY (SELECT hpo_id, hp_name, snomed_code, au_name, snomed_name FROM umls_hp WHERE NOT same_name ORDER BY 1)
                        TO '{UMLS_HPO.parent / "hpo_snomed_candidates.tsv"}' (DELIMITER '\t', HEADER)""")
        log["HPO -> SNOMED candidates for a person (not edges)"] = con.execute("SELECT count(*) FROM umls_hp WHERE NOT same_name").fetchone()[0]

    # --- foreign SNOMED ids -> nearest ancestor the Australian release carries ------------------------------------
    # Runs after every family, so it catches foreign SCTIDs from any source (DrugCentral's US conditions, Athena's
    # LOINC targets in other extensions). Only the nearest level is kept; ties keep all.
    con.execute(f"CREATE TEMP VIEW CA AS SELECT * FROM read_csv('{a.vocab_dir}/CONCEPT_ANCESTOR.csv', delim='\t', header=true, all_varchar=true)")
    # an SCTID is "foreign" if neither SNOMED CT-AU nor an extension the graph loads (the LOINC Ontology) defines it
    ext_ids = (f"UNION SELECT id FROM read_csv('{LOINC_EXT / 'Terminology' / 'sct2_Concept_Snapshot_LO1010000_20260321.txt'}', "
               "delim='\\t', header=true, quote='', escape='', all_varchar=true)" if LOINC_EXT.exists() else "")
    con.execute(f"CREATE TEMP TABLE native_sct AS SELECT id FROM cmp.concept {ext_ids}")
    con.execute("""CREATE TEMP TABLE foreign_sct AS SELECT DISTINCT code FROM (SELECT s_code AS code FROM edge WHERE s_vocab = 'SCT'
                   UNION SELECT o_code FROM edge WHERE o_vocab = 'SCT') WHERE code NOT IN (SELECT id FROM native_sct)""")
    ins("foreign SNOMED -> nearest SNOMED CT-AU ancestor", f"""
        WITH anc AS (
            SELECT f.code, a.concept_code AS anc, CAST(ca.min_levels_of_separation AS INT) AS lvl
            FROM foreign_sct f JOIN C d ON d.vocabulary_id = 'SNOMED' AND d.concept_code = f.code
            JOIN CA ca ON ca.descendant_concept_id = d.concept_id AND ca.min_levels_of_separation <> '0'
            JOIN C a ON a.concept_id = ca.ancestor_concept_id AND a.vocabulary_id = 'SNOMED'
            WHERE a.concept_code IN (SELECT id FROM native_sct)),
        best AS (SELECT code, min(lvl) AS lvl FROM anc GROUP BY 1)
        SELECT DISTINCT 'SCT', anc.code, 'sct:au_nearest_ancestor', 'SCT', anc.anc, 'OMOP Athena', 'CONCEPT_ANCESTOR',
               'nearest ancestor in SNOMED CT-AU', 'native', 'asserted', '{PIN['athena']}', json_object('levels_up', anc.lvl)
        FROM anc JOIN best USING (code, lvl)""")
    log["foreign SNOMED ids (not in the AU release)"] = con.execute("SELECT count(*) FROM foreign_sct").fetchone()[0]

    # --- the contract ------------------------------------------------------------------------------------------------
    reg = json.load(open(REGISTER))
    preds = [(p["id"], p["subject"], p["object"], p["status"], p["category"], p.get("derivation"))
             for p in reg["predicates"] + reg["snomed_attributes"]]
    con.execute("CREATE TABLE predicate (id VARCHAR, subject VARCHAR[], object VARCHAR[], status VARCHAR, category VARCHAR, derivation VARCHAR)")
    con.executemany("INSERT INTO predicate VALUES (?, ?, ?, ?, ?, ?)", preds)
    bad = con.execute("""
        SELECT 'unregistered predicate' AS why, e.predicate, count(*) FROM edge e LEFT JOIN predicate p ON p.id = e.predicate
          WHERE p.id IS NULL GROUP BY 2
        UNION ALL SELECT 'predicate not loadable (' || p.status || ')', e.predicate, count(*) FROM edge e JOIN predicate p ON p.id = e.predicate
          WHERE p.status <> 'built' GROUP BY 1, 2
        UNION ALL SELECT 'subject vocabulary ' || e.s_vocab || ' not registered', e.predicate, count(*) FROM edge e JOIN predicate p ON p.id = e.predicate
          WHERE NOT list_contains(p.subject, e.s_vocab) GROUP BY 1, 2
        UNION ALL SELECT 'object vocabulary ' || coalesce(e.o_vocab, 'NULL') || ' not registered', e.predicate, count(*) FROM edge e
          JOIN predicate p ON p.id = e.predicate WHERE e.o_vocab IS NULL OR NOT list_contains(p.object, e.o_vocab) GROUP BY 1, 2
        UNION ALL SELECT 'no source (rule zero)', e.predicate, count(*) FROM edge e WHERE e.source IS NULL OR e.source = '' GROUP BY 2
        UNION ALL SELECT 'empty subject or object code', e.predicate, count(*) FROM edge e
          WHERE e.s_code IS NULL OR e.o_code IS NULL OR e.s_code = '' OR e.o_code = '' GROUP BY 2""").fetchall()
    if bad:
        print("\nREFUSED -- the build does not write a graph that breaks the register:", file=sys.stderr)
        for why, pred, n in bad:
            print(f"  {n:>9,}  {pred:<32} {why}", file=sys.stderr)
        con.close()
        GRAPH.unlink()
        return 1

    # --- nodes -------------------------------------------------------------------------------------------------------
    con.execute("""CREATE TEMP TABLE keys AS SELECT DISTINCT vocab, code FROM (
        SELECT s_vocab AS vocab, s_code AS code FROM edge UNION SELECT o_vocab, o_code FROM edge)""")
    con.execute("""INSERT INTO name_hint SELECT 'SCT', k.code, c.pt FROM keys k JOIN cmp.concept c ON c.id = k.code WHERE k.vocab = 'SCT'""")
    rev = " ".join(f"WHEN '{v}' THEN '{k}'" for k, v in OMOP_VOCAB.items() if v not in ("SCT",))
    con.execute(f"""INSERT INTO name_hint SELECT k.vocab, k.code, c.concept_name FROM keys k
        JOIN C c ON c.concept_code = k.code AND c.vocabulary_id = CASE k.vocab {rev} END
        WHERE k.vocab IN ('RXN', 'RXE', 'ATC', 'ICD10CM')""")
    con.execute("""INSERT INTO name_hint SELECT 'SCT', k.code, any_value(c.concept_name) FROM keys k
        JOIN C c ON c.concept_code = k.code AND c.vocabulary_id = 'SNOMED' WHERE k.vocab = 'SCT' GROUP BY 1, 2""")
    con.execute("""CREATE TABLE node AS SELECT k.vocab, k.code, k.vocab || ':' || k.code AS key,
                          (SELECT any_value(h.name) FROM name_hint h WHERE h.vocab = k.vocab AND h.code = k.code
                           AND h.name IS NOT NULL AND trim(h.name) <> '') AS name
                   FROM keys k""")
    con.execute("CREATE TABLE edge_final AS SELECT row_number() OVER () AS edge_id, * FROM edge")
    con.execute("DROP TABLE edge")
    con.execute("ALTER TABLE edge_final RENAME TO edge")
    con.execute("CREATE TABLE build_log (family VARCHAR, edges BIGINT)")
    con.executemany("INSERT INTO build_log VALUES (?, ?)", list(log.items()))

    n_edges = con.execute("SELECT count(*) FROM edge").fetchone()[0]
    n_nodes = con.execute("SELECT count(*) FROM node").fetchone()[0]
    unnamed = con.execute("SELECT vocab, count(*) FROM node WHERE name IS NULL GROUP BY 1 ORDER BY 2 DESC").fetchall()
    con.close()
    print(f"\ngraph: {n_nodes:,} nodes, {n_edges:,} edges -> {GRAPH}   (all edges validated against the register)")
    print("nodes without a name, by vocabulary:", unnamed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
