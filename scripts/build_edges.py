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
    MONDO          is-a, and exactMatch to SNOMED / ICD-10-CM / OMIM / Orphanet
    ICD-10-CM      every code -> SNOMED (OMOP Maps to); also the second path that scores MONDO
    HPO            is-a, disease -> phenotype (present / absent) with frequency, onset, sex, and gene -> disease
    DrugCentral    drug -> RxNorm / SNOMED / ATC, indication / contraindication / off-label use, and
                   drug -> target (mechanism / measured activity) -> protein -> gene  (if extracted)

Writes out/graph.duckdb. Pins recorded on every edge.

    scripts/build_edges.py [--vocab-dir ~/code/spine/out/omop-vocab]
"""
from __future__ import annotations

import argparse
import collections
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
HP_GENES = Path("cache/hpo/genes_to_disease.txt")   # HPO release v2026-09-01, 1.5 MB
MBS_XML = Path("cache/mbs/MBS-XML-20260801.XML")          # MBS Online, Department of Health
UBERON_OBO, UBERON_SSSOM = Path("cache/uberon/uberon-basic.obo"), Path("cache/uberon/uberon.sssom.tsv")   # Uberon v2026-06-23
UMLS_SCT_NCBI = Path("cache/umls/sct_ncbi.tsv")          # scripts/umls_crosswalk.py SNOMEDCT_US -> NCBI (licensed; not redistributed)
RADLEX_JSON = Path("cache/radlex/radlex_classes.json")   # scripts/radlex_prepare.py, from RadLex 4.3 (RSNA; read in place)
UMLS_FMA_SCT, UMLS_RADLEX_CUI = Path("cache/umls/fma_sct.tsv"), Path("cache/umls/radlex_cui_sct.tsv")   # scripts/umls_crosswalk.py
LOINC_RSNA = Path(os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/AccessoryFiles/LoincRsnaRadiologyPlaybook/LoincRsnaRadiologyPlaybook.csv"))
RSNA_PLAYBOOK = Path(os.environ.get("RSNA_PLAYBOOK", os.path.expanduser("~/Documents/ONTOLOGIES/complete-playbook-dev.csv")))
LOINC_PARTS = Path(os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/AccessoryFiles/PartFile/PartRelatedCodeMapping.csv"))
LOINC_PARTLINK = Path(os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/AccessoryFiles/PartFile/LoincPartLink_Primary.csv"))
DC = Path("cache/drugcentral")
UMLS_HPO = Path("cache/umls/hpo_snomed.tsv")
PBS_BIND = Path("reference/pbs_indication_bindings.json")   # scripts/bind_indications.py
UNIT_PAIRS, THRESH_UNITS = Path("reference/loinc_unit_counterparts.json"), Path("reference/threshold_units.json")   # US <-> AU units
RCPA_UNITS = Path("cache/rcpa/reporting_units.json")          # scripts/rcpa_units.py -- RCPA copyright, git-ignored
RCPA_UNITS_PIN = "RCPA SPIA RCPA_v20260831"
UCUM_PREFIX = {"k": 1e3, "h": 1e2, "da": 1e1, "": 1.0, "d": 1e-1, "c": 1e-2, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}


def ucum_malformed(u: str) -> list:
    """Ways a unit string breaks UCUM (reported, not silently fixed): '[IU]mL' (no operator), a typographic apostrophe,
    'KU' (K is not a UCUM prefix), 'mmHg' for mm[Hg], a bare 'IU' for [IU]."""
    import re as _re
    probs = []
    if _re.search(r"\][A-Za-z]", u or ""):
        probs.append("missing operator after a bracketed unit")
    if "\u2019" in (u or ""):
        probs.append("typographic apostrophe")
    if _re.search(r"(^|/)KU", u or ""):
        probs.append("'K' is not a UCUM prefix")
    if "mmHg" in (u or ""):
        probs.append("mmHg for mm[Hg]")
    if _re.search(r"(^|[^\[])IU", u or ""):
        probs.append("IU without brackets")
    return probs


def _ucum_norm(u: str) -> str:
    """Spelling-level normalisation for COMPARISON only: annotations dropped ({creat}), malformed forms repaired, titre / titer,
    [IU] / U, mmHg = mm[Hg], mosm = mmol for osmolality."""
    import re as _re
    u = (u or "").strip().replace("\u2019", "'").replace(" ", "")
    u = _re.sub(r"\](?=[A-Za-z])", "]/", u)
    u = _re.sub(r"(^|/)KU", r"\1kU", u)
    u = _re.sub(r"(^|[^\[])IU", r"\1[IU]", u)
    u = _re.sub(r"\{[^}]*\}", "", u).replace("[IU]", "U").replace("mmHg", "mm[Hg]").replace("mosm", "mmol")
    return u or "{titre}"


ARBITRARY = ("[arb'U]", "[IU]", "U", "[beth'U]", "[APL'U]", "[GPL'U]", "[MPL'U]")
COUNT = {"10*9/L": 1e9, "10*12/L": 1e12, "10*6/L": 1e6, "10*3/uL": 1e9, "10*6/uL": 1e12, "/uL": 1e6, "/L": 1.0, "/mm3": 1e6}
FRACTION = {"%": 0.01, "L/L": 1.0, "/1": 1.0, "{ratio}": 1.0, "": 1.0}


def ucum_scale(us: str, au: str):
    """Factor taking a value in `us` to `au` when they differ only in scale: metric prefix (g/dL -> g/L = 10), a count per
    volume (/uL -> 10*9/L = 0.001), a fraction (% -> L/L = 0.01). None otherwise."""
    import re as _re
    nu, na = _ucum_norm(us), _ucum_norm(au)
    cu, ca = COUNT.get(_re.sub(r"\{[^}]*\}", "", us.replace(" ", ""))), COUNT.get(_re.sub(r"\{[^}]*\}", "", au.replace(" ", "")))
    if cu and ca:
        return round(cu / ca, 12)
    if us.strip() in FRACTION and au.strip() in FRACTION and us.strip() != au.strip() and "{ratio}" not in (us, au):
        return round(FRACTION[us.strip()] / FRACTION[au.strip()], 9)
    def parse(u):
        parts = u.split("/")
        if len(parts) != 2:
            return None
        out = []
        for p_ in parts:
            m = _re.fullmatch(r"(da|[khdcmunpf]?)(g|mol|L|U)", p_.strip())
            if not m:
                return None
            out.append((UCUM_PREFIX[m.group(1)], m.group(2)))
        return out
    a, b = parse(nu), parse(na)
    if not a or not b or a[0][1] != b[0][1] or a[1][1] != b[1][1]:
        return None
    return round((a[0][0] / a[1][0]) / (b[0][0] / b[1][0]), 9)


def unit_difference(us_examples: str | None, au: str):
    """Compare LOINC's example unit(s) (US convention; may list several, 'mg/dL;g/L') with the Australian preferred unit:
    ('none' | 'spelling' | 'scale' | 'arbitrary' | 'kind' | 'no US example', factor). 'arbitrary': assay-specific units
    (arbitrary, international, Bethesda) that no factor converts."""
    import re as _re
    if not us_examples:
        return "no US example", None
    ex = [x.strip() for x in us_examples.split(";") if x.strip()]
    if au in ex:
        return "none", 1.0
    if any(_ucum_norm(x) == _ucum_norm(au) for x in ex):
        return "spelling", 1.0
    for x in ex:
        f = ucum_scale(x, au)
        if f is not None:
            return "scale", f
    stem = lambda u: _re.split(r"/", _ucum_norm(u).replace("[arb'U]", "U").replace("[beth'U]", "U"))[0].lstrip("kmun")
    if any(stem(x) in ("U", "") for x in ex) and stem(au) in ("U", ""):
        return "arbitrary", None
    return "kind", None
DX_ACC, DX_BIND, DX_VER = (Path("reference/diagnostic_accuracy.json"), Path("reference/diagnostic_accuracy_bindings.json"),
                           Path("reference/diagnostic_accuracy_verification.json"))   # finding -> diagnosis LRs
LOINC_EXT = Path(os.environ.get("LOINC_EXTENSION", os.path.expanduser(
    "~/Documents/ONTOLOGIES/SnomedCT_LOINCExtension_PRODUCTION_LO1010000_20260321T120000Z/Snapshot")))   # licensed; read in place
LOINC_TABLE = Path(os.environ.get("LOINC_TABLE", os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/LoincTable/Loinc.csv")))     # written by scripts/umls_hpo_crosswalk.py (licensed; not redistributed)

PIN = {"sct": "SNOMED CT-AU 20260831", "athena": "Athena v5.0 29-AUG-26", "pbs": "PBS schedule 4333",
       "loinc": "LOINC 2.82 (Athena)", "mondo": "MONDO releases/2026-09-01", "hpo": "HPO 2026-09-02",
       "dc": "DrugCentral 2023-11-01", "corpus": "reference/snomed_bindings.json", "umls": "UMLS current (UTS crosswalk)", "loinc_ext": "LOINC Extension 20260321", "loinc_table": "LOINC 2.83", "uberon": "Uberon v2026-06-23", "mbs": "MBS XML 20260801",
       "radlex": "RadLex 4.3", "rsna": "RSNA Radiology Playbook (complete-playbook-dev.csv, downloaded 24 Sep 2026)"}
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


def sources(vocab_dir: str) -> dict[str, Path]:
    """Every input a full build reads. The loaders below skip a source that is absent, so without this check a deleted
    folder (24 Sep 2026: the unpacked LOINC, RadLex and SNOMED releases) would rebuild a smaller graph without failing."""
    return {"compendium": CMP, "spine": SPINE, "Athena CONCEPT": Path(vocab_dir) / "CONCEPT.csv",
            "Athena CONCEPT_RELATIONSHIP": Path(vocab_dir) / "CONCEPT_RELATIONSHIP.csv", "PBS cache": PBS,
            "snomed bindings": BINDINGS, "MONDO obo": MONDO_OBO, "MONDO sssom": MONDO_SSSOM, "HPO obo": HP_OBO,
            "HPO annotations": HPOA, "HPO genes": HP_GENES, "MBS XML": MBS_XML, "Uberon obo": UBERON_OBO,
            "Uberon sssom": UBERON_SSSOM, "DrugCentral": DC, "PBS indication bindings": PBS_BIND,
            "LOINC Extension": LOINC_EXT, "LOINC table": LOINC_TABLE, "LOINC part mapping": LOINC_PARTS,
            "LOINC part links": LOINC_PARTLINK, "LOINC/RSNA playbook": LOINC_RSNA, "RSNA playbook": RSNA_PLAYBOOK,
            "RadLex (scripts/radlex_prepare.py)": RADLEX_JSON, "RCPA units (scripts/rcpa_units.py)": RCPA_UNITS,
            "unit pairs": UNIT_PAIRS, "threshold units": THRESH_UNITS, "diagnostic accuracy": DX_ACC,
            "diagnostic accuracy bindings": DX_BIND, "diagnostic accuracy verification": DX_VER,
            "UMLS HPO -> SNOMED": UMLS_HPO, "UMLS SNOMED -> NCBI": UMLS_SCT_NCBI, "UMLS FMA -> SNOMED": UMLS_FMA_SCT,
            "UMLS RadLex CUI -> SNOMED": UMLS_RADLEX_CUI}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=os.path.expanduser("~/code/spine/out/omop-vocab"))
    ap.add_argument("--allow-missing", action="append", default=[], metavar="NAME",
                    help="build without this source (repeatable; 'all' for any) -- the build log names each one skipped")
    a = ap.parse_args()
    missing = {k: v for k, v in sources(a.vocab_dir).items() if not v.exists()}
    refused = {k: v for k, v in missing.items() if "all" not in a.allow_missing and k not in a.allow_missing}
    if refused:
        print("REFUSED -- sources missing (restore them, or pass --allow-missing NAME to build without one on purpose):",
              file=sys.stderr)
        for k, v in refused.items():
            print(f"  {k:<36} {v}", file=sys.stderr)
        return 1
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

        # --- US <-> Australian units ---------------------------------------------------------------------------------
        # The Australian preferred unit per LOINC code (RCPA SPIA reporting sets, scripts/rcpa_units.py) against LOINC's own
        # example unit (the US convention); and the mass (MCnc) <-> molar (SCnc) counterpart pairs (scripts/unit_reconcile.py),
        # each marked with which side Australia reports.
        rcpa_codes = set()
        if RCPA_UNITS.exists():
            ex = dict(con.execute("SELECT LOINC_NUM, EXAMPLE_UCUM_UNITS FROM read_csv(?, header=true, all_varchar=true)", [str(LOINC_TABLE)]).fetchall())
            seen, rows_u = set(), []
            for x in json.load(open(RCPA_UNITS))["rows"]:
                ucum = (x["ucum"] or "").strip()
                if not ucum or ucum.lower() == "no unit" or (x["loinc"], ucum) in seen:
                    continue
                seen.add((x["loinc"], ucum))
                rcpa_codes.add(x["loinc"])
                us = (ex.get(x["loinc"]) or "").strip() or None
                diff, f = unit_difference(us, ucum)
                rows_u.append(("LOINC", x["loinc"], "loinc:au_preferred_unit", "UCUM", ucum, "RCPA SPIA", f"{x['set']} / {x['rcpa_term']}",
                               "RCPA preferred unit", "native", "asserted", RCPA_UNITS_PIN,
                               json.dumps({"au_display": x["unit"], "us_example_ucum": us, "difference": diff,
                                           "rcpa_ucum_malformed": ucum_malformed(ucum) or None,
                                           "differs_from_us_example": diff in ("scale", "kind"),
                                           "factor_us_example_to_au": f, "rcpa_property": x["property"]})))
            ins_rows("LOINC -> Australian preferred unit (RCPA SPIA)", rows_u)
        if UNIT_PAIRS.exists():
            def au_side(c):
                a, b = c["mass_loinc"] in rcpa_codes, c["molar_loinc"] in rcpa_codes
                return "both" if a and b else "mass" if a else "molar" if b else None
            ins_rows("LOINC mass <-> molar unit counterpart", [
                ("LOINC", c["mass_loinc"], "loinc:unit_counterpart", "LOINC", c["molar_loinc"], "LOINC 2.83 + PubChem",
                 "reference/loinc_unit_counterparts.json", "same axes, MCnc / SCnc", "native", "asserted", f"{PIN['loinc_table']}",
                 json.dumps({**{k: c[k] for k in ("factor_mg_per_dL_to_mmol_per_L", "molecular_weight", "pubchem_cid", "analyte_code",
                                                  "mass_unit_example", "molar_unit_example")}, "au_preferred": au_side(c)}))
                for c in json.load(open(UNIT_PAIRS))["counterparts"]])

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
        con.executemany("INSERT INTO name_hint VALUES ('MONDO', ?, ?)", [(t["id"], t.get("name")) for t in mt if t["id"].startswith("MONDO:")])
        con.executemany("INSERT INTO name_hint VALUES ('NCBITAXON', ?, ?)",      # the taxa MONDO cites carry their names in mondo.obo
                        [(t["id"].split(":", 1)[1], t.get("name")) for t in mt if t["id"].startswith("NCBITaxon:")])
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

    # --- ICD-10-CM -> SNOMED, every code (reference/icd10cm_handcheck.json) -----------------------------------------
    # OMOP's 'Maps to' from all 98,290 mapped ICD-10-CM codes -- diseases, symptoms (R), injuries (S, T), external causes
    # (V-Y), health factors (Z) -- where the first build loaded only MONDO's 1,968. A combination code maps to 2-4 concepts
    # that TOGETHER are its meaning (diabetes with retinopathy -> both); `targets_of_code` says how many, so no single
    # target is read as the whole. 'Maps to value' ("history of" style pairs) means something else and is not loaded.
    ins("ICD-10-CM -> SNOMED (all codes)", f"""
        WITH m AS (SELECT s.concept_code AS icd, coalesce(s.invalid_reason, '') AS icd_invalid, t.concept_code AS sct
                   FROM C s JOIN CR r ON r.concept_id_1 = s.concept_id AND r.relationship_id = 'Maps to'
                        AND (r.invalid_reason IS NULL OR r.invalid_reason = '')
                   JOIN C t ON t.concept_id = r.concept_id_2 AND t.vocabulary_id = 'SNOMED'
                   WHERE s.vocabulary_id = 'ICD10CM')
        SELECT DISTINCT 'ICD10CM', icd, 'icd10cm:maps_to', 'SCT', sct, 'OMOP Athena', 'CONCEPT_RELATIONSHIP', 'Maps to',
               'ungraded', 'asserted', '{PIN['athena']}',
               json_object('targets_of_code', count(*) OVER (PARTITION BY icd), 'icd_deprecated', icd_invalid = 'D')
        FROM m""")

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
        # --- how a drug works: drug -> target -> protein -> gene (DrugCentral's activity tables) -------------------
        # Mechanism (moa = 1: the target the drug's effect is attributed to) and measured activity (a Ki, an IC50 --
        # binding, not a reason to prescribe) are two predicates. Every edge keeps its act_id, so it traces to the row
        # and through it to ChEMBL / the label / the paper (act_source, moa_source, their URLs, PMID or DOI).
        if (DC / "act_table_full.tsv").exists():
            con.execute(f"""CREATE TEMP TABLE dc_ref AS SELECT id, pmid, doi, url FROM {dc('reference')}""")
            # ChEMBL as a second witness for mechanisms DrugCentral did not take from ChEMBL (scripts/chembl_moa_witness.py)
            wit = Path("cache/chembl/moa_witness.tsv")
            wit_src = (f"read_csv('{wit}', delim='\\t', header=true, all_varchar=true, quote='')" if wit.exists()
                       else "(SELECT NULL AS act_id, NULL AS verdict)")
            con.execute(f"CREATE TEMP TABLE dc_wit AS SELECT act_id, verdict FROM {wit_src}")
            ins("DrugCentral drug -> target (mechanism / activity)", f"""SELECT 'DRUGCENTRAL', a.struct_id,
                    CASE WHEN a.moa = '1' THEN 'drugcentral:mechanism_target' ELSE 'drugcentral:bioactivity' END,
                    'DC_TARGET', a.target_id, 'DrugCentral', 'act_table_full act_id=' || a.act_id,
                    CASE WHEN a.moa = '1' THEN coalesce(a.moa_source, 'unstated') ELSE coalesce(a.act_source, 'unstated') END,
                    'native', 'asserted', '{PIN['dc']}',
                    json_object('action_type', a.action_type, 'organism', a.organism, 'act_type', a.act_type,
                                'act_value', a.act_value, 'act_unit', a.act_unit, 'relation', a.relation,
                                'act_source', a.act_source, 'act_source_url', a.act_source_url,
                                'moa_source', a.moa_source, 'moa_source_url', a.moa_source_url,
                                'act_pmid', ra.pmid, 'act_doi', ra.doi, 'moa_pmid', rm.pmid, 'moa_doi', rm.doi,
                                'first_in_class', a.first_in_class, 'tdl', a.tdl, 'chembl_witness', w.verdict)
                FROM {dc('act_table_full')} a LEFT JOIN dc_ref ra ON ra.id = a.act_ref_id LEFT JOIN dc_ref rm ON rm.id = a.moa_ref_id
                LEFT JOIN dc_wit w ON w.act_id = a.act_id AND a.moa = '1'""")
            ins("DrugCentral target -> protein component", f"""SELECT DISTINCT 'DC_TARGET', t.target_id, 'drugcentral:target_component',
                    'UNIPROT', c.accession, 'DrugCentral', 'td2tc + target_component', 'native', 'native', 'asserted', '{PIN['dc']}',
                    json_object('organism', c.organism, 'swissprot', c.swissprot)
                FROM {dc('td2tc')} t JOIN {dc('target_component')} c ON c.id = t.component_id
                WHERE c.accession IS NOT NULL AND c.accession <> ''""")
            ins("protein -> gene (DrugCentral)", f"""SELECT DISTINCT 'UNIPROT', accession, 'uniprot:encoded_by', 'NCBIGENE', geneid,
                    'DrugCentral', 'target_component', 'native', 'native', 'asserted', '{PIN['dc']}',
                    json_object('gene_symbol', gene, 'organism', organism)
                FROM {dc('target_component')} WHERE geneid IS NOT NULL AND geneid <> '' AND accession IS NOT NULL AND accession <> ''
                  AND id IN (SELECT component_id FROM {dc('td2tc')})""")   # target proteins only, not DrugCentral's whole protein list
            con.execute(f"""INSERT INTO name_hint SELECT 'DC_TARGET', id, name FROM {dc('target_dictionary')}""")
            con.execute(f"""INSERT INTO name_hint SELECT 'UNIPROT', accession, any_value(name) FROM {dc('target_component')} GROUP BY 2""")
            con.execute(f"""INSERT INTO name_hint SELECT 'NCBIGENE', geneid, any_value(gene) FROM {dc('target_component')}
                            WHERE geneid IS NOT NULL AND geneid <> '' GROUP BY 2""")

    # --- Medicare Benefits Schedule: items, groups, categories (no SNOMED map exists; candidates are not edges) ------
    if MBS_XML.exists():
        import xml.etree.ElementTree as ET
        mbs = [{c.tag: (c.text or "").strip() for c in d} for d in ET.parse(MBS_XML).getroot().iter("Data")]
        mbs = [m for m in mbs if not m.get("ItemEndDate")]
        ins_rows("MBS item -> group -> category", [
            ("MBS", m["ItemNum"], "mbs:in_group", "MBS_GROUP", f"{m['Category']}/{m['Group']}", "MBS XML", MBS_XML.name, "native", "native",
             "asserted", PIN["mbs"], json.dumps({"schedule_fee": m.get("ScheduleFee") or None, "benefit_100": m.get("Benefit100") or None,
                                               "item_type": m.get("ItemType"), "fee_type": m.get("FeeType"),
                                               "item_start": m.get("ItemStartDate"), "fee_start": m.get("FeeStartDate")}))
            for m in mbs] + sorted({("MBS_GROUP", f"{m['Category']}/{m['Group']}", "mbs:group_in_category", "MBS_CATEGORY", m["Category"],
                                     "MBS XML", MBS_XML.name, "native", "native", "asserted", PIN["mbs"], None) for m in mbs}))
        con.executemany("INSERT INTO name_hint VALUES ('MBS', ?, ?)",
                        [(m["ItemNum"], re.sub(r"\s+", " ", m["Description"])[:160]) for m in mbs])
        cat_names = {"1": "Professional attendances", "2": "Diagnostic procedures and investigations", "3": "Therapeutic procedures",
                     "4": "Oral and maxillofacial services", "5": "Diagnostic imaging services", "6": "Pathology services",
                     "7": "Cleft lip and cleft palate services", "8": "Miscellaneous services", "10": "Dental services"}
        con.executemany("INSERT INTO name_hint VALUES ('MBS_CATEGORY', ?, ?)", list(cat_names.items()))
        con.executemany("INSERT INTO name_hint VALUES ('MBS_GROUP', ?, ?)", sorted({(f"{m['Category']}/{m['Group']}", f"Group {m['Group']}") for m in mbs}))

    # --- anatomy and organisms: Uberon, MONDO's locations and agents, SNOMED organism <-> NCBI Taxonomy ---------------
    if UBERON_OBO.exists():
        terms, cur = [], None
        for line in open(UBERON_OBO, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("["):
                cur = {"is_a": [], "part_of": []} if line == "[Term]" else None
                if cur is not None:
                    terms.append(cur)
            elif cur is not None and ": " in line:
                k, v_ = line.split(": ", 1)
                if k == "id":
                    cur["id"] = v_
                elif k == "name":
                    cur["name"] = v_
                elif k == "is_a":
                    cur["is_a"].append(v_.split(" ")[0])
                elif k == "relationship" and v_.startswith("part_of "):
                    cur["part_of"].append(v_.split(" ")[1])
                elif k == "is_obsolete" and v_.strip() == "true":
                    cur["obsolete"] = True
        ub = [t for t in terms if t.get("id", "").startswith("UBERON:") and not t.get("obsolete")]
        ins_rows("Uberon is-a / part-of", [("UBERON", t["id"], pred, "UBERON", o, "Uberon", "uberon-basic.obo", "native", "native", "asserted",
                                             PIN["uberon"], None)
                                            for t in ub for pred, key in (("uberon:is_a", "is_a"), ("uberon:part_of", "part_of"))
                                            for o in t[key] if o.startswith("UBERON:")])
        con.executemany("INSERT INTO name_hint VALUES ('UBERON', ?, ?)", [(t["id"], t.get("name")) for t in ub])
    if UBERON_SSSOM.exists():
        ss = [r for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
              if r["object_id"].startswith("SCTID:") and r["subject_id"].startswith("UBERON:")]
        ins_rows("Uberon -> SNOMED body structure (narrowMatch)", [
            ("UBERON", r["subject_id"], "uberon:sct_narrow_match", "SCT", r["object_id"].split(":", 1)[1], "Uberon SSSOM", "uberon.sssom.tsv",
             r["predicate_id"], "ungraded", "asserted", PIN["uberon"], json.dumps({"mapping_justification": r.get("mapping_justification")}))
            for r in ss if r["predicate_id"] == "skos:narrowMatch"])
    if MONDO_OBO.exists():
        rows_m, cur = [], None
        for line in open(MONDO_OBO, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("id: "):
                cur = line[4:]
            elif line.startswith("relationship: ") and cur and cur.startswith("MONDO:"):
                parts = line[14:].split(" ")
                if parts[0] == "disease_has_location" and parts[1].startswith("UBERON:"):
                    rows_m.append(("MONDO", cur, "mondo:disease_has_location", "UBERON", parts[1]))
                elif parts[0] == "disease_has_infectious_agent" and parts[1].startswith("NCBITaxon:"):
                    rows_m.append(("MONDO", cur, "mondo:disease_has_infectious_agent", "NCBITAXON", parts[1].split(":", 1)[1]))
        ins_rows("MONDO disease -> location (Uberon) / infectious agent (NCBI Taxonomy)",
                 [r + ("MONDO", "mondo.obo", "native", "native", "asserted", PIN["mondo"], None) for r in sorted(set(rows_m))])
    if LOINC_PARTS.exists():
        con.execute(f"CREATE TEMP VIEW lpm AS SELECT * FROM read_csv('{LOINC_PARTS}', header=true, all_varchar=true)")
        ins("SNOMED organism <-> NCBI Taxonomy (LOINC part asserts both)", f"""SELECT DISTINCT 'SCT', s.ExtCodeId, 'sct:ncbitaxon_equivalent',
                'NCBITAXON', t.ExtCodeId, 'LOINC 2.83 PartRelatedCodeMapping', 'part ' || s.PartNumber, 'LOINC part asserts both',
                'ungraded', 'asserted', '{PIN['loinc_table']}', json_object('loinc_part', s.PartNumber, 'part_name', s.PartName)
            FROM lpm s JOIN lpm t ON t.PartNumber = s.PartNumber AND t.ExtCodeSystem = 'https://www.ncbi.nlm.nih.gov/taxonomy'
                 AND t.Equivalence = 'equivalent'
            WHERE s.ExtCodeSystem = 'http://snomed.info/sct' AND s.Equivalence = 'equivalent'""")
        con.execute("""INSERT INTO name_hint SELECT DISTINCT 'NCBITAXON', ExtCodeId, any_value(ExtCodeDisplayName) FROM lpm
                       WHERE ExtCodeSystem = 'https://www.ncbi.nlm.nih.gov/taxonomy' GROUP BY 2""")
    if LOINC_PARTS.exists() and LOINC_PARTLINK.exists():
        ins("LOINC term -> SNOMED via its component / system / method part", f"""SELECT DISTINCT 'LOINC', pl.LoincNumber, 'loinc:part_maps_to_sct',
                'SCT', pm.ExtCodeId, 'LOINC 2.83 part mapping', 'part ' || pl.PartNumber, pl.PartTypeName || ' ' || pm.Equivalence,
                'native', 'asserted', '{PIN['loinc_table']}',
                json_object('part_type', pl.PartTypeName, 'part', pl.PartNumber, 'part_name', pm.PartName, 'equivalence', pm.Equivalence)
            FROM read_csv('{LOINC_PARTLINK}', header=true, all_varchar=true) pl
            JOIN lpm pm ON pm.PartNumber = pl.PartNumber AND pm.ExtCodeSystem = 'http://snomed.info/sct'
            JOIN lx_loinc st ON st.LOINC_NUM = pl.LoincNumber AND st.STATUS = 'ACTIVE'
            WHERE pl.PartTypeName IN ('COMPONENT', 'SYSTEM', 'METHOD') AND pm.PartName <> 'XXX'""")
    if UMLS_SCT_NCBI.exists():
        # UMLS shared CUI, admitted where the NCBI name equals the SNOMED preferred term -- as written, or once rank words are
        # set aside ("Salmonella species" = Salmonella, "Order Strigiformes" = Strigiformes). Truly different names (renamed
        # taxa, and some errors: family Anatidae -> the genus Aythya) are candidates for a person, not edges.
        ranks = re.compile(r"^(kingdom|subkingdom|phylum|subphylum|division|superclass|class|subclass|infraclass|superorder|order|"
                           r"suborder|infraorder|superfamily|family|subfamily|tribe|genus|subgenus|section|species) ")
        def tnorm(x):
            x = re.sub(r"\s*\((organism)\)$", "", (x or "").lower().strip())
            x = ranks.sub("", re.sub(r"\s+-\s+.*$", "", x))
            x = re.sub(r"\s+(species|sp\.?|spp\.?)$", "", x).replace(" ss. ", " subsp. ").replace("[", "").replace("]", "")
            return re.sub(r"\s+", " ", x).strip()
        pts = dict(con.execute("SELECT id, pt FROM cmp.concept WHERE id IN (SELECT source_code FROM read_csv(?, delim='\t', header=true, all_varchar=true, quote=''))",
                               [str(UMLS_SCT_NCBI)]).fetchall())
        rows_o, cands = [], []
        for r in csv.DictReader(open(UMLS_SCT_NCBI, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            sname = pts.get(r["source_code"]) or ""
            if sname.lower().strip() == r["target_name"].lower().strip():
                how = "UMLS shared CUI, same name"
            elif tnorm(sname) == tnorm(r["target_name"]):
                how = "UMLS shared CUI, same name after rank words"
            else:
                cands.append((r["source_code"], sname, r["target_code"], r["target_name"]))
                continue
            rows_o.append(("SCT", r["source_code"], "sct:ncbitaxon_equivalent", "NCBITAXON", r["target_code"], "UMLS",
                           "UTS crosswalk SNOMEDCT_US -> NCBI", how, "ungraded", "asserted", PIN["umls"],
                           json.dumps({"ncbi_name": r["target_name"]})))
            con.execute("INSERT INTO name_hint VALUES ('NCBITAXON', ?, ?)", [r["target_code"], r["target_name"]])
        ins_rows("SNOMED organism <-> NCBI Taxonomy (UMLS, same name)", rows_o)
        with open(UMLS_SCT_NCBI.with_name("sct_ncbi_candidates.tsv"), "w", encoding="utf-8") as fh:
            fh.write("sct\tsct_name\tncbi_taxon\tncbi_name\n")
            fh.writelines("\t".join(x) + "\n" for x in cands)
        log["SNOMED organism <-> NCBI Taxonomy candidates (different names; cache/umls/)"] = len(cands)

    # --- radiology: LOINC and the RSNA playbook -> RadLex -> FMA -> SNOMED CT body structure ----------------------
    # LOINC codes its radiology terms' parts to RadLex (the LOINC/RSNA Radiology Playbook) and to nothing in SNOMED CT.
    # RadLex carries FMA ids and some UMLS CUIs, so three code routes reach a SNOMED body structure, kept apart by method:
    # FMA -> Uberon -> SNOMED (Uberon's own maps), FMA -> SNOMED (UMLS shared CUI), RadLex's CUI -> SNOMED (UMLS atoms).
    # Each is tiered by its own hand check (graph_report.py); they witness one another through SNOMED's is-a, since
    # Uberon maps to "Entire kidney" and UMLS to "Structure of kidney" -- one structure, two SNOMED forms.
    if RADLEX_JSON.exists() and LOINC_RSNA.exists():
        rl = json.load(open(RADLEX_JSON))
        con.executemany("INSERT INTO name_hint VALUES ('RADLEX', ?, ?)", [(r, d.get("name")) for r, d in rl.items()])
        rsrc = lambda pred, o_vocab, key: [("RADLEX", r, pred, o_vocab, o, "RadLex", "RadLex.owl", "native", "native", "asserted",
                                            PIN["radlex"], None) for r, d in rl.items() for o in d[key] if o.startswith("RID")]
        ins_rows("RadLex is-a", rsrc("radlex:is_a", "RADLEX", "is_a"))
        ins_rows("RadLex part-of", rsrc("radlex:part_of", "RADLEX", "part_of"))
        ins_rows("RadLex -> FMA (ExternalRefID)", [("RADLEX", r, "radlex:fma_xref", "FMA", e[4:], "RadLex", "RadLex.owl ExternalRefID",
                                                    "native", "native", "asserted", PIN["radlex"], None)
                                                   for r, d in rl.items() for e in d["ext"] if e.startswith("FMA:")])
        ub_fma = [r for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
                  if r["subject_id"].startswith("UBERON:") and r["object_id"].startswith("FMA:")] if UBERON_SSSOM.exists() else []
        ins_rows("Uberon <-> FMA (cross-species exact match)", [
            ("UBERON", r["subject_id"], "uberon:fma_match", "FMA", r["object_id"][4:], "Uberon SSSOM", "uberon.sssom.tsv",
             r["predicate_id"], "native", "asserted", PIN["uberon"], None) for r in ub_fma])
        ins("LOINC radiology term -> RadLex part (LOINC/RSNA playbook)", f"""SELECT DISTINCT 'LOINC', p.LoincNumber, 'loinc:radlex_part',
                'RADLEX', p.RID, 'LOINC 2.83 LoincRsnaRadiologyPlaybook', 'part ' || p.PartNumber, p.PartTypeName, 'native', 'asserted',
                '{PIN['loinc_table']}', json_object('part_type', p.PartTypeName, 'part', p.PartNumber, 'part_name', p.PartName)
            FROM read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p
            JOIN lx_loinc st ON st.LOINC_NUM = p.LoincNumber AND st.STATUS = 'ACTIVE' WHERE p.RID IS NOT NULL AND p.RID <> ''""")
        ins("LOINC radiology term -> RSNA playbook procedure (RPID)", f"""SELECT DISTINCT 'LOINC', p.LoincNumber, 'loinc:rsna_rpid',
                'RPID', p.RPID, 'LOINC 2.83 LoincRsnaRadiologyPlaybook', 'RPID column', 'LOINC/RSNA harmonised', 'native', 'asserted',
                '{PIN['loinc_table']}', NULL
            FROM read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p
            JOIN lx_loinc st ON st.LOINC_NUM = p.LoincNumber AND st.STATUS = 'ACTIVE' WHERE p.RPID IS NOT NULL AND p.RPID <> ''""")
        if RSNA_PLAYBOOK.exists():
            pb = list(csv.DictReader(open(RSNA_PLAYBOOK, encoding="utf-8")))
            cols = list(pb[0].keys())
            i0 = cols.index("MODALITY")                         # RIDS holds one RID (or 0) per column from MODALITY onward
            live = [r for r in pb if r["STATUS"] in ("ACTIVE", "TRIAL")]
            con.executemany("INSERT INTO name_hint VALUES ('RPID', ?, ?)", [(r["RPID"], r["LONG_NAME"].strip() or r["AUTOMATED_LONG_NAME"].strip().lower() or None)
                                                                          for r in pb])
            ins_rows("RSNA playbook procedure -> RadLex part", sorted({
                ("RPID", r["RPID"], "rsna:radlex_part", "RADLEX", rid, "RSNA Radiology Playbook", RSNA_PLAYBOOK.name + " RIDS", c,
                 "native", "asserted", PIN["rsna"], json.dumps({"field": c, "status": r["STATUS"]}))
                for r in live for c, rid in zip(cols[i0:], r["RIDS"].split("|")) if rid.startswith("RID") and c}))
        act = dict(con.execute("SELECT id, tag FROM cmp.concept").fetchall())
        fma_ub = collections.defaultdict(set)
        for r in ub_fma:
            fma_ub[r["object_id"][4:]].add(r["subject_id"])
        ub_sct = collections.defaultdict(set)
        for s_, o_ in con.execute("SELECT s_code, o_code FROM edge WHERE predicate = 'uberon:sct_narrow_match'").fetchall():
            ub_sct[s_].add(o_)
        def umls(p):
            d = collections.defaultdict(set)
            if p.exists():
                for r in csv.DictReader(open(p, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
                    d[r["source_code"]].add(r["target_code"])
            return d
        fma_sct, cui_sct = umls(UMLS_FMA_SCT), umls(UMLS_RADLEX_CUI)
        rows_a, dropped = {}, collections.Counter()
        def add(rid, sct, method, source, locator, pin, attrs):
            if act.get(sct) != "body structure":
                dropped[f"{method}: {'not active in SNOMED CT-AU' if sct not in act else 'not a body structure'}"] += 1
                return
            rows_a.setdefault((rid, sct, method), ("RADLEX", rid, "radlex:anatomy_sct", "SCT", sct, source, locator, method,
                                                   "ungraded", "asserted", pin, json.dumps(attrs)))
        for rid, d in rl.items():
            for e in d["ext"]:
                if e.startswith("FMA:"):
                    for u in sorted(fma_ub.get(e[4:], ())):
                        for sct in sorted(ub_sct.get(u, ())):
                            add(rid, sct, "FMA -> Uberon -> SNOMED CT", "RadLex + Uberon SSSOM", "ExternalRefID; crossSpeciesExactMatch; narrowMatch",
                                PIN["uberon"], {"fma": e[4:], "uberon": u})
                    for sct in sorted(fma_sct.get(e[4:], ())):
                        add(rid, sct, "FMA -> UMLS shared CUI", "RadLex + UMLS", "ExternalRefID; UTS crosswalk FMA -> SNOMEDCT_US",
                            PIN["umls"], {"fma": e[4:]})
                elif e.startswith("UMLS:"):
                    for sct in sorted(cui_sct.get(e[5:], ())):
                        add(rid, sct, "RadLex CUI -> UMLS atoms", "RadLex + UMLS", "ExternalRefID; UTS CUI atoms SNOMEDCT_US",
                            PIN["umls"], {"cui": e[5:]})
        ins_rows("RadLex -> SNOMED CT body structure (three code routes)", sorted(rows_a.values()))
        for k, v in sorted(dropped.items()):
            log[f"RadLex -> SNOMED CT not loaded ({k})"] = v
        ins("LOINC radiology term -> SNOMED via its RadLex anatomy part", """SELECT DISTINCT 'LOINC', p.s_code, 'loinc:part_maps_to_sct',
                'SCT', a.o_code, 'LOINC 2.83 LoincRsnaRadiologyPlaybook + ' || a.source, 'part ' || json_extract_string(p.attrs, '$.part') || ' -> ' || p.o_code,
                'RadLex anatomy: ' || a.method, 'ungraded', 'asserted', a.pin,
                json_object('part_type', json_extract_string(p.attrs, '$.part_type'), 'part', json_extract_string(p.attrs, '$.part'),
                            'part_name', json_extract_string(p.attrs, '$.part_name'), 'rid', p.o_code, 'route', a.method)
            FROM edge p JOIN edge a ON a.predicate = 'radlex:anatomy_sct' AND a.s_code = p.o_code
            WHERE p.predicate = 'loinc:radlex_part' AND json_extract_string(p.attrs, '$.part_type') LIKE 'Rad.Anatomic Location.%'
              AND json_extract_string(p.attrs, '$.part_type') NOT LIKE '%Laterality%'""")
        # playbook anatomy with no code route at all (head, neck, hand...): name-matched SNOMED body structures are
        # candidates for a person, never edges -- a gap-crossing by name. RadLex- and SNOMED-derived: cache/, not committed.
        bridged = {r for (r, _, _) in rows_a}
        used = {r for (r,) in con.execute("""SELECT DISTINCT o_code FROM edge WHERE predicate IN ('loinc:radlex_part', 'rsna:radlex_part')
                 AND (json_extract_string(attrs, '$.part_type') LIKE 'Rad.Anatomic Location.%' AND json_extract_string(attrs, '$.part_type') NOT LIKE '%Laterality%'
                      OR json_extract_string(attrs, '$.field') LIKE 'BODY_REGION%' OR json_extract_string(attrs, '$.field') LIKE 'ANATOMIC_FOCUS%')""").fetchall()}
        bnorm = lambda x: re.sub(r"\s+", " ", re.sub(r"^(entire |structure of |bone structure of )|( structure| region structure)$", "",
                                                         re.sub(r"\s*\(body structure\)$", "", (x or "").lower().strip()))).strip()
        by_name = collections.defaultdict(set)
        for i, pt in con.execute("SELECT id, pt FROM cmp.concept WHERE tag = 'body structure'").fetchall():
            by_name[bnorm(pt)].add((i, pt))
        cands = [(r, rl[r].get("name") or "", i, pt) for r in sorted(used - bridged) if r in rl
                 for i, pt in sorted({x for n in [rl[r].get("name")] + rl[r]["syn"] if n for x in by_name.get(bnorm(n), ())})]
        with open(RADLEX_JSON.with_name("radlex_sct_candidates.tsv"), "w", encoding="utf-8") as fh:
            fh.write("rid\tradlex_name\tsct\tsct_name\n")
            fh.writelines("\t".join(x) + "\n" for x in cands)
        log["RadLex anatomy with no code route (playbook)"] = len(used - bridged)
        log["RadLex anatomy candidates by name (cache/radlex/, not edges)"] = len({c[0] for c in cands})

    # --- genes -> diseases (HPO genes_to_disease, the release hp.obo came from) --------------------------------------
    if HP_GENES.exists():
        ins("HPO gene -> disease (OMIM, Orphanet)", f"""SELECT DISTINCT 'NCBIGENE', split_part(ncbi_gene_id, ':', 2), 'hpo:gene_disease',
                split_part(disease_id, ':', 1), split_part(disease_id, ':', 2), 'HPO', 'genes_to_disease.txt',
                association_type, 'native', 'asserted', '{PIN['hpo']}',
                json_object('association_type', association_type, 'gene_symbol', gene_symbol, 'upstream', source)
            FROM read_csv('{HP_GENES}', delim='\t', header=true, all_varchar=true, quote='')
            WHERE split_part(disease_id, ':', 1) IN ('OMIM', 'ORPHA')""")
        con.execute(f"""INSERT INTO name_hint SELECT 'NCBIGENE', split_part(ncbi_gene_id, ':', 2), any_value(gene_symbol)
            FROM read_csv('{HP_GENES}', delim='\t', header=true, all_varchar=true, quote='') GROUP BY 2""")

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

    # --- finding -> diagnosis likelihood ratios (reference/diagnostic_accuracy.json) ----------------------------------
    # Numbers transcribed from diagnostic-accuracy review abstracts (PMID per edge), verified against the cached abstract;
    # finding and diagnosis bound to SNOMED CT-AU by exact term. Only records whose number verified AND whose finding and
    # diagnosis both bound become edges; the rest stay candidates in the reference files. Every edge is a clinical-safety
    # edge, so it enters corrected_pending_attestation.
    if DX_ACC.exists() and DX_BIND.exists():
        recs = json.load(open(DX_ACC))["records"]
        bound = {x["id"]: x for x in json.load(open(DX_BIND))["results"]}
        ver_doc = json.load(open(DX_VER)) if DX_VER.exists() else {"rows": [], "binding_review": {}}
        verified = {x["id"] for x in ver_doc["rows"] if x["verified"]}
        # a binding family (bedside findings; tests, scores and prognosis) enters the graph only once its first-pass binding
        # precision has earned a tier: >= 30 read and a Wilson lower bound >= 0.80. Otherwise its records stay candidates.
        def wilson_lo(k, n, z=1.96):
            if not n:
                return 0.0
            p = k / n
            return (p + z * z / (2 * n) - z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / (1 + z * z / n)
        admitted = {fam for fam, v in ver_doc.get("binding_review", {}).items() if isinstance(v, dict) and v.get("distinct_bindings_read", 0) >= 30
                    and wilson_lo(v["distinct_bindings_read"] - v["read_as_wrong"], v["distinct_bindings_read"]) >= 0.80}
        family = lambda r: "finding" if r.get("kind", "finding") == "finding" else "test_score_prognosis"
        units = ({x["id"]: {k: v for k, v in x.items() if k not in ("id", "pmid")} for x in json.load(open(THRESH_UNITS))["thresholds"]}
                 if THRESH_UNITS.exists() else {})
        held = 0
        rows_lr = []
        for r in recs:
            b = bound.get(r["id"], {})
            if r["id"] not in verified or not b.get("finding") or not b.get("diagnosis"):
                continue
            if family(r) not in admitted:       # bound, but its family's binding has not earned a tier: a candidate for a person
                held += 1
                continue
            kind = r.get("kind", "finding")
            ranged = r.get("lr_range") is not None and r.get("lr") is None
            derived = r.get("lr") is None and not ranged
            if derived:
                s_, p_ = r["sens"], r["spec"]
                lr = s_ / (1 - p_) if r["when"] == "present" else (1 - s_) / p_
            else:
                lr = r.get("lr")
            pred = {"finding": "finding_lr_if_" + r["when"], "test": "test_result_lr", "score": "score_result_lr",
                    "prognosis": "finding_lr_for_outcome"}[kind]
            rows_lr.append(("SCT", b["finding"]["concept_id"], pred, "SCT", b["diagnosis"]["concept_id"],
                            "PubMed abstract (diagnostic-accuracy review)", f"PMID:{r['pmid']} record={r['id']}",
                            "LR range across studies" if ranged else "LR derived from pooled sensitivity and specificity" if derived else "LR as reported",
                            "ungraded", "corrected_pending_attestation", "reference/diagnostic_accuracy.json",
                            json.dumps({"lr": None if lr is None else round(lr, 3), "lr_ci": None if derived else r.get("lr_ci"),
                                        "lr_range": r.get("lr_range"), "derived": derived, "kind": kind, "result": r.get("result"), "when": r["when"],
                                        "sens": r.get("sens"), "sens_ci": r.get("sens_ci"), "spec": r.get("spec"), "spec_ci": r.get("spec_ci"),
                                        "population": r["population"], "setting": r["setting"], "pmid": r["pmid"],
                                        "finding_text": r["finding_text"], "diagnosis_text": r["diagnosis_text"],
                                        "units": units.get(r["id"])})))
        ins_rows("finding -> diagnosis likelihood ratio (transcribed, verified)", rows_lr)
        log["likelihood-ratio records bound but held as candidates (family not admitted)"] = held
        print(f"  {'LR records held (binding family not admitted)':<44} {held:>10,}   admitted: {sorted(admitted)}", flush=True)

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
    con.execute("INSERT INTO name_hint SELECT vocab, code, code FROM keys WHERE vocab = 'UCUM'")   # a unit is named by its UCUM code
    con.execute("INSERT INTO name_hint SELECT vocab, code, 'FMA:' || code FROM keys WHERE vocab = 'FMA'")   # FMA itself is not loaded
    con.execute("""CREATE TABLE node AS SELECT k.vocab, k.code, k.vocab || ':' || k.code AS key,
                          (SELECT any_value(h.name) FROM name_hint h WHERE h.vocab = k.vocab AND h.code = k.code
                           AND h.name IS NOT NULL AND trim(h.name) <> '') AS name
                   FROM keys k""")
    con.execute("CREATE TABLE edge_final AS SELECT row_number() OVER () AS edge_id, * FROM edge")
    con.execute("DROP TABLE edge")
    con.execute("ALTER TABLE edge_final RENAME TO edge")
    for k in missing:
        log[f"SOURCE MISSING (built without it on purpose): {k}"] = 0
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
