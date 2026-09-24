#!/usr/bin/env python3
"""Completeness, measured from the source side: for the groups that matter in Australia, how many members carry each
edge they should, and -- for a seeded sample of those that do not -- why not.

Precision (the hand-checked tiers) cannot see an edge that is missing. This can. For every (group, expectation) cell:

  present         the member reaches what it should through admissible edges (rejected and inadmissible are not
                  followed). Identity edges are walked both ways; classification edges only forward, and once a walk has
                  classified (SNOMED -> ICD-10) it may only classify further (ICD-10 -> ICD-11), never widen back out.
  absent, sampled 50 per cell (seeded, so the same members every run) and each put in one of three classes:
    our_gap         a source we hold states it and the graph does not carry it: SeMRA's aggregated mappings, a UMLS
                    shared concept (including pairs held back because the names differ), or an edge held back by a hand
                    check (tier inadmissible). The gap is ours -- the fix is a load or a check.
    unknown         a source that covers the member for this kind of edge says nothing, or declines outright (SNOMED's
                    ICD-10 map: "cannot be classified with available data"). Recorded as unknown, never as "no".
    no_source_held  nothing we hold covers it: a gap-crossing for a person, or a source still to be obtained (named).

The only negatives in the graph stay the ones a source states outright; nothing here writes an edge.

    .venv/bin/python scripts/completeness.py                  # after graph_report.py; ~2 min; -> out/completeness.json
    .venv/bin/python scripts/completeness.py --set-baseline   # accept the current shares as the regression baseline

The baseline (reference/completeness_baseline.json: counts and shares only) is the guard: a cell whose present share
drops by more than half a percentage point is reported and the script exits 1. The evidence index it builds from SeMRA
and UMLS (cache/completeness/evidence.parquet) is licensed-derived and stays in cache/.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import duckdb


ONT_ROOT = os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES"))   # the licensed releases, read in place
GRAPH, CMP = Path("out/graph.duckdb"), Path("out/compendium.duckdb")
REGISTER = Path("reference/graph_predicates.json")
OUT, BASELINE = Path("out/completeness.json"), Path("reference/completeness_baseline.json")
EVID = Path("cache/completeness/evidence.parquet")
SEMRA = Path("cache/semra/m.parquet")
UMLS_PAIRS = Path("cache/umls/umls_shared_cui.parquet")
MONDO_OBO, HP_OBO, ORPHA_XML = Path("cache/mondo/mondo.obo"), Path("cache/hpo/hp.obo"), Path("cache/orphanet/en_product1.xml")
# SeMRA re-publishes older releases of sources we hold in current form; a row from one of these counts as stated only if
# the current release still states it -- otherwise it is superseded (the source now covers the member and says nothing)
CURRENT = {"Mondo Disease Ontology": "MONDO", "Orphanet Rare Disease Ontology": "ORPHA", "Human Phenotype Ontology": "HP"}
OBO_V = {"ICD10WHO": "ICD10WHO", "ICD10CM": "ICD10CM", "Orphanet": "ORPHA", "OMIM": "OMIM", "DOID": "DOID", "NCIT": "NCIT",
         "MESH": "MESH", "MSH": "MESH", "UMLS": "UMLS", "SCTID": "SCT", "SNOMEDCT_US": "SCT", "EFO": "EFO", "GARD": "GARD",
         "icd11.foundation": "ICD11", "ICD-10": "ICD10WHO", "ORPHA": "ORPHA"}
ORPHA_V = {"ICD-10": "ICD10WHO", "ICD-11": "ICD11MMS", "OMIM": "OMIM", "UMLS": "UMLS", "MeSH": "MESH", "MONDO": "MONDO", "GARD": "GARD"}
XMAP = Path("cache/snomed-us/extended_map_20260901.parquet")
LOINC_TABLE = Path(os.environ.get("LOINC_TABLE", os.path.join(ONT_ROOT, "Loinc_2.83/LoincTable/Loinc.csv")))
SAMPLE, DROP = 50, 0.005

# SeMRA prefix -> (graph vocabulary, how the graph writes the local id)
SEMRA_V = {"snomedct": "SCT", "mondo": "MONDO", "doid": "DOID", "efo": "EFO", "hp": "HP", "omim": "OMIM",
           "orphanet": "ORPHA", "orphanet.ordo": "ORPHA", "icd10": "ICD10WHO", "icd10cm": "ICD10CM", "icd11": "ICD11",
           "mesh": "MESH", "umls": "UMLS", "ncit": "NCIT", "ncbigene": "NCBIGENE", "hgnc": "HGNC", "chebi": "CHEBI",
           "rxnorm": "RXN", "loinc": "LOINC", "gard": "GARD", "drugcentral": "DRUGCENTRAL", "pubchem.compound": "PUBCHEM",
           "chembl.compound": "CHEMBL", "atc": "ATC", "ncbitaxon": "NCBITAXON", "uniprot": "UNIPROT", "unii": "UNII",
           "fma": "FMA", "uberon": "UBERON"}
KEEP_PREFIX = {"MONDO": "MONDO:", "HP": "HP:", "HGNC": "HGNC:"}
# predicates walked as classification (forward only) although the register files some of them as identity: they
# cross between classifications, and a walk that has classified must be able to take them
CLS_EXTRA = ("who:icd10_to_icd11", "who:icd11_to_icd10", "who:icd11_mms_foundation", "icd10:subdivision_of")
NOT_WALKED = ("sct:in_refset",)
# Orphanet's loose alignments: "narrower than" an ICD code is a classification (walked on by classification, e.g. through
# WHO's ICD-10 -> ICD-11 table); otherwise a narrower / broader / undecided alignment reaches a code but is not an identity
# to walk on from
ORPHA_CLS = "(predicate = 'orpha:xref' AND method = 'NTBT' AND o_vocab IN ('ICD10WHO', 'ICD11MMS'))"
LOOSE = f"(predicate = 'orpha:xref' AND method IN ('NTBT', 'BTNT', 'ND') AND NOT {ORPHA_CLS})"                     # a membership, not a meaning: every member would reach every other

PD = "Problem/Diagnosis reference set"
EDP = "Australian emergency department principal diagnosis reference set for ED funding"
GROUPS = {
    "Problem/Diagnosis": ("SCT", f"SELECT DISTINCT s_code FROM edge WHERE predicate = 'sct:in_refset' AND method = '{PD}'"),
    "Problem/Diagnosis disorders": ("SCT", f"""SELECT DISTINCT e.s_code FROM edge e JOIN cmp.concept c ON c.id = e.s_code
                                             WHERE e.predicate = 'sct:in_refset' AND e.method = '{PD}' AND c.tag = 'disorder'"""),
    "ED principal diagnosis": ("SCT", f"SELECT DISTINCT s_code FROM edge WHERE predicate = 'sct:in_refset' AND method = '{EDP}'"),
    "PBS-listed products": ("SCT", "SELECT DISTINCT s_code FROM edge WHERE predicate = 'pbs:lists'"),
    "PBS medicine ingredients": ("SCT", """WITH p AS (SELECT DISTINCT s_code c FROM edge WHERE predicate = 'pbs:lists'),
            d AS (SELECT c FROM p UNION SELECT e.o_code FROM edge e JOIN p ON e.s_code = p.c WHERE e.predicate IN ('sct:774160008', 'sct:999000011000168107')
                  UNION SELECT e2.o_code FROM edge e JOIN p ON e.s_code = p.c AND e.predicate = 'sct:999000011000168107'
                        JOIN edge e2 ON e2.s_code = e.o_code AND e2.predicate = 'sct:774160008'),
            d2 AS (SELECT c FROM d UNION SELECT e.o_code FROM edge e JOIN d ON e.s_code = d.c WHERE e.predicate = 'sct:116680003')
        SELECT DISTINCT e.o_code FROM edge e JOIN d2 ON e.s_code = d2.c WHERE e.predicate IN ('sct:127489000', 'sct:762949000')"""),
    "Common laboratory LOINC (top 2,000)": ("LOINC", "SELECT code FROM lab_top"),
    "HPO phenotypes in use": ("HP", "SELECT DISTINCT o_code FROM edge WHERE predicate = 'hpo:has_phenotype'"),
    "Orphanet disorders": ("ORPHA", "SELECT code FROM node WHERE vocab = 'ORPHA'"),
    "Orphanet disorders (disorder or subtype level)": ("ORPHA", """SELECT code FROM node WHERE vocab = 'ORPHA'
                                                                AND code IN (SELECT code FROM orpha_level WHERE level IN ('Disorder', 'Subtype of disorder'))"""),
    "MBS items": ("MBS", "SELECT code FROM node WHERE vocab = 'MBS'"),
}
DECLINE_ICD10 = f"SELECT DISTINCT referencedComponentId FROM '{XMAP}' WHERE refsetId = '447562003' AND coalesce(mapTarget, '') = ''"
DECLINE_ICD10CM = f"SELECT DISTINCT referencedComponentId FROM '{XMAP}' WHERE refsetId = '6011000124106' AND coalesce(mapTarget, '') = ''"
DISEASE_V = ("OMIM", "ORPHA")
# the ICD maps' source domain: clinical findings (and disorders), events, situations -- a procedure in an ED set is out of scope
ICD_SCOPE = "SELECT id FROM cmp.concept WHERE tag IN ('disorder', 'finding', 'event', 'situation')"
ORPHA_ACTIVE = "SELECT code FROM orpha_level WHERE active"          # an entry Orphanet has retired is not a member
MEDICINE = "SELECT id FROM cmp.concept WHERE tag NOT LIKE '%physical object%'"      # dressings and devices carry no ATC      # the vocabularies HPO annotates with phenotypes and genes
# (group, expectation, spec). target: reach a code of these vocabularies within `hops`. final: from a node reached
# through identity edges within `hops`, an edge with one of these predicates (dir out: the node is its subject).
CELLS = [
    ("Problem/Diagnosis", "ICD-10 (WHO)", {"target": ["ICD10WHO"], "hops": 2, "decline": DECLINE_ICD10, "applies": ICD_SCOPE}),
    ("Problem/Diagnosis", "ICD-11", {"target": ["ICD11", "ICD11MMS"], "hops": 4, "decline": DECLINE_ICD10, "applies": ICD_SCOPE}),
    ("Problem/Diagnosis", "ICD-10-CM", {"target": ["ICD10CM"], "hops": 2, "decline": DECLINE_ICD10CM, "applies": ICD_SCOPE}),
    ("Problem/Diagnosis disorders", "MONDO", {"target": ["MONDO"], "hops": 2}),
    ("Problem/Diagnosis disorders", "HPO phenotype", {"final": ["hpo:has_phenotype", "orpha:has_phenotype"], "dir": "out", "hops": 2,
                                                     "covers": DISEASE_V}),
    ("ED principal diagnosis", "ICD-10 (WHO)", {"target": ["ICD10WHO"], "hops": 2, "decline": DECLINE_ICD10, "applies": ICD_SCOPE}),
    ("ED principal diagnosis", "ICD-11", {"target": ["ICD11", "ICD11MMS"], "hops": 4, "decline": DECLINE_ICD10, "applies": ICD_SCOPE}),
    ("ED principal diagnosis", "CCSR category", {"target": ["CCSR"], "hops": 2, "decline": DECLINE_ICD10CM, "applies": ICD_SCOPE,
                                                 "covers": ("ICD10CM",), "covers_why": "reaches only an ICD-10-CM code CCSR does not classify (a subcategory whose last character is still to be chosen)"}),
    ("PBS-listed products", "ATC", {"target": ["ATC"], "hops": 1, "applies": MEDICINE}),
    ("PBS-listed products", "OMOP standard drug (RxNorm / RxNorm Extension)", {"target": ["RXN", "RXE"], "hops": 2, "applies": MEDICINE}),
    ("PBS medicine ingredients", "RxNorm ingredient", {"target": ["RXN"], "hops": 2}),
    ("PBS medicine ingredients", "DrugCentral", {"target": ["DRUGCENTRAL"], "hops": 2}),
    ("PBS medicine ingredients", "indication", {"final": ["drugcentral:indication", "medrt:may_treat"], "dir": "out", "hops": 2,
                                                "covers": ("DRUGCENTRAL",)}),
    ("PBS medicine ingredients", "mechanism / target", {"final": ["drugcentral:mechanism_target", "medrt:has_mechanism_of_action",
                                                                  "fda:pharmacologic_class"], "dir": "out", "hops": 2, "covers": ("DRUGCENTRAL",)}),
    # the LOINC cells carry coverage rules (loinc_sources): which source we hold states the link, and which covers the
    # member without stating it -- so an absent member is our gap, unknown, or no source, never a silent "no"
    ("PBS medicine ingredients", "drug-level laboratory test (LOINC)", {"final": ["loinc:part_xref"], "dir": "in", "hops": 2,
        "sources": [("LOINC part mapping names this substance (a LOINC test measures it)", "states", "pl_analyte_ext")],
        "not_held": "no LOINC part names this substance by the codes it reaches (RxNorm, ChEBI, UNII, PubChem)"}),
    ("Common laboratory LOINC (top 2,000)", "SNOMED CT", {"target": ["SCT"], "hops": 2,
        "sources": [("LOINC Extension: the term's official SNOMED CT identifier", "states", "lx_ident"),
                    ("Athena: LOINC -> SNOMED (Is a / Maps to)", "states", "ath_ls"),
                    ("LOINC maps only the term's component part to SNOMED CT, not the term", "covers", "part_sct"),
                    ("Athena holds the term and places it under no SNOMED concept; the LOINC Extension does not model it", "covers", "ath_loinc")],
        "not_held": "in neither Athena's LOINC nor the LOINC Extension"}),
    ("Common laboratory LOINC (top 2,000)", "AU preferred unit", {"final": ["loinc:au_preferred_unit"], "dir": "out", "hops": 0,
        "applies": f"SELECT LOINC_NUM FROM read_csv('{LOINC_TABLE}', header=true, all_varchar=true) WHERE SCALE_TYP = 'Qn'",   # a unit is a quantity's
        "sources": [("RCPA SPIA states the Australian preferred unit", "states", "rcpa_unit"),
                    ("RCPA SPIA lists the term with no unit", "covers", "rcpa_nounit")],
        "not_held": "not in the RCPA SPIA reporting sets"}),
    ("Common laboratory LOINC (top 2,000)", "analyte code (ChEBI, RxNorm, gene ...)", {"final": ["loinc:part_xref"], "dir": "out", "hops": 0,
        "sources": [("LOINC part mapping: the component part carries an analyte code", "states", "pl_analyte"),
                    ("LOINC decomposes the term, but its component part carries no analyte code", "covers", "pl_component")],
        "not_held": "LOINC links no component part for this term"}),
    ("Common laboratory LOINC (top 2,000)", "finding it is interpreted in", {"final": ["loinc:interpreted_in_finding"], "dir": "out", "hops": 0,
        "sources": [("the LOINC Extension models the term, but no SNOMED CT finding interprets its component at this specimen", "covers", "lx_ident")],
        "not_held": "not modelled in the LOINC Extension, the rule's input"}),
    ("HPO phenotypes in use", "SNOMED CT", {"target": ["SCT"], "hops": 2}),
    ("Orphanet disorders", "ICD-10 (WHO)", {"target": ["ICD10WHO"], "hops": 1, "covers": ("ORPHA",), "covers_why": "Orphanet's own alignments (product1) state none for this disorder"}),
    ("Orphanet disorders", "ICD-11", {"target": ["ICD11", "ICD11MMS"], "hops": 2, "covers": ("ORPHA",), "covers_why": "Orphanet's own alignments (product1) state none for this disorder"}),
    ("Orphanet disorders", "OMIM", {"target": ["OMIM"], "hops": 1, "covers": ("ORPHA",), "covers_why": "Orphanet's own alignments (product1) state none for this disorder"}),
    ("Orphanet disorders", "MONDO", {"target": ["MONDO"], "hops": 2}),
    ("Orphanet disorders", "SNOMED CT", {"target": ["SCT"], "hops": 2}),
    ("Orphanet disorders (disorder or subtype level)", "ICD-10 (WHO)", {"target": ["ICD10WHO"], "hops": 1, "covers": ("ORPHA",),
        "covers_why": "Orphanet's own alignments (product1) state none for this disorder"}),
    ("Orphanet disorders", "gene", {"final": ["hpo:gene_disease", "orpha:gene_disease"], "dir": "in", "hops": 0, "covers": ("ORPHA",),
                                    "covers_why": "Orphanet's gene file (product 6) states no gene for this disorder"}),
    ("Orphanet disorders", "HPO phenotype", {"final": ["hpo:has_phenotype", "orpha:has_phenotype"], "dir": "out", "hops": 0,
                                             "covers": ("ORPHA",), "covers_why": "Orphanet's phenotype file (product 4) states none for this disorder"}),
    ("MBS items", "SNOMED CT procedure", {"target": ["SCT"], "hops": 2,
                                          "not_held": "none published: candidate frames in reference/mbs_procedure_candidates.json"}),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(max(0.0, c - m), 3), round(min(1.0, c + m), 3))


def current_statements() -> list[tuple]:
    """What the current MONDO, HPO and Orphanet releases we hold state, as (vocab, code, vocab, code)."""
    out = []
    for path, own in ((MONDO_OBO, "MONDO"), (HP_OBO, "HP")):
        if not path.exists():
            continue
        cur, got, obsolete = None, [], set()      # an obsolete class's cross-references are not a current statement
        for line in open(path, encoding="utf-8"):
            if line.startswith("[Term]"):
                cur = None
            elif line.startswith("id: "):
                cur = line[4:].strip()
            elif line.startswith("is_obsolete: true") and cur:
                obsolete.add(cur)
            elif line.startswith("xref: ") and cur:
                ref = line[6:].split(" ")[0]
                pre, _, loc = ref.partition(":")
                if pre in OBO_V and loc:
                    got.append((own, cur, OBO_V[pre], ("MONDO:" + loc) if OBO_V[pre] == "MONDO" else loc))
        out += [r for r in got if r[1] not in obsolete]
    if ORPHA_XML.exists():
        import xml.etree.ElementTree as ET
        for d in ET.parse(ORPHA_XML).getroot().iter("Disorder"):
            oc = d.findtext("OrphaCode")
            for x in d.iter("ExternalReference"):
                src, ref = x.findtext("Source"), (x.findtext("Reference") or "").strip()
                if oc and src in ORPHA_V and ref:
                    v = ORPHA_V[src]
                    out.append(("ORPHA", oc, v, ("MONDO:" + ref.zfill(7)) if v == "MONDO" else ref))
                    if v == "ICD11MMS":
                        out.append(("ORPHA", oc, "ICD11", ref))
    return out


def loinc_sources(con) -> None:
    """The tables the LOINC coverage rules read: node keys ('VOCAB:code') for which a source we hold STATES the expected
    link (absent from the graph: our gap) or COVERS the member without stating it (unknown -- never 'no link'). Read from
    the releases themselves, not from the graph, so a loader that drops rows shows up as our gap."""
    sys.path.insert(0, str(Path(__file__).parent))
    import build_edges as be
    rd = lambda p, tab=False: (f"read_csv('{p}', delim='\t', header=true, all_varchar=true, quote='')" if tab
                               else f"read_csv('{p}', header=true, all_varchar=true)")
    xs = {"https://www.ebi.ac.uk/chebi": "CHEBI", "http://www.nlm.nih.gov/research/umls/rxnorm": "RXN", "http://pubchem.ncbi.nlm.nih.gov": "PUBCHEM",
          "http://fdasis.nlm.nih.gov": "UNII", "https://www.ncbi.nlm.nih.gov/taxonomy": "NCBITAXON", "https://www.ncbi.nlm.nih.gov/gene": "NCBIGENE",
          "http://www.genenames.org": "HGNC", "https://www.ncbi.nlm.nih.gov/clinvar": "CLINVAR"}      # as build_edges.py loads them
    xcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in xs.items())
    xlist = ",".join(repr(k) for k in xs)
    T = be.LOINC_EXT / "Terminology"
    links = f"SELECT LoincNumber, PartNumber, PartTypeName FROM {rd(be.LOINC_PARTLINK)}" + (
        f" UNION SELECT LoincNumber, PartNumber, PartTypeName FROM {rd(be.LOINC_PARTLINK_SUPP)} WHERE LinkTypeName = 'DetailedModel'"
        if be.LOINC_PARTLINK_SUPP.exists() else "")
    analyte = f"""SELECT pl.LoincNumber, pm.ExtCodeSystem, pm.ExtCodeId FROM ({links}) pl JOIN {rd(be.LOINC_PARTS)} pm ON pm.PartNumber = pl.PartNumber
                  WHERE pm.ExtCodeSystem IN ({xlist}) AND pl.PartTypeName IN ('COMPONENT', 'DIVISORS', 'GENE', 'CHALLENGE')"""
    tables = {
        "lx_ident": ([T], f"""SELECT 'LOINC:' || alternateIdentifier FROM {rd(T / 'sct2_Identifier_Snapshot_LO1010000_20260321.txt', True)}
                             WHERE active = '1' AND identifierSchemeId = '30051010000102'"""),
        "ath_loinc": ([be.VOCAB_DIR / "CONCEPT.csv"], f"SELECT 'LOINC:' || concept_code FROM {rd(be.VOCAB_DIR / 'CONCEPT.csv', True)} WHERE vocabulary_id = 'LOINC'"),
        "ath_ls": ([be.VOCAB_DIR / "CONCEPT_RELATIONSHIP.csv"], f"""SELECT 'LOINC:' || l.concept_code FROM {rd(be.VOCAB_DIR / 'CONCEPT_RELATIONSHIP.csv', True)} r
                   JOIN {rd(be.VOCAB_DIR / 'CONCEPT.csv', True)} l ON l.concept_id = r.concept_id_1 AND l.vocabulary_id = 'LOINC'
                   JOIN {rd(be.VOCAB_DIR / 'CONCEPT.csv', True)} s ON s.concept_id = r.concept_id_2 AND s.vocabulary_id = 'SNOMED'
                   WHERE r.relationship_id IN ('Is a', 'Maps to', 'Maps to value') AND coalesce(r.invalid_reason, '') = ''"""),
        "part_sct": ([be.LOINC_PARTLINK, be.LOINC_PARTS], f"""SELECT 'LOINC:' || pl.LoincNumber FROM {rd(be.LOINC_PARTLINK)} pl
                     JOIN {rd(be.LOINC_PARTS)} pm ON pm.PartNumber = pl.PartNumber AND pm.ExtCodeSystem = 'http://snomed.info/sct'
                     WHERE pl.PartTypeName = 'COMPONENT'"""),
        "pl_analyte": ([be.LOINC_PARTLINK, be.LOINC_PARTS], f"SELECT 'LOINC:' || LoincNumber FROM ({analyte})"),
        "pl_analyte_ext": ([be.LOINC_PARTLINK, be.LOINC_PARTS], f"""SELECT CASE ExtCodeSystem {xcase} END || ':' ||
                           CASE WHEN ExtCodeSystem = 'http://www.genenames.org' THEN ExtCodeId ELSE replace(ExtCodeId, 'CHEBI:', '') END FROM ({analyte})"""),
        "pl_component": ([be.LOINC_PARTLINK], f"SELECT 'LOINC:' || LoincNumber FROM {rd(be.LOINC_PARTLINK)} WHERE PartTypeName = 'COMPONENT'"),
    }
    for name, (need, sql) in tables.items():
        con.execute(f"CREATE OR REPLACE TEMP TABLE {name} AS SELECT DISTINCT k FROM ("
                    + (sql if all(p.exists() for p in need) else "SELECT NULL::VARCHAR WHERE false") + ") t(k)")
    rows = json.load(open(be.RCPA_UNITS))["rows"] if be.RCPA_UNITS.exists() else []
    unit = lambda x: (x.get("ucum") or "").strip() and (x.get("ucum") or "").strip().lower() != "no unit"
    for name, keep in (("rcpa_unit", True), ("rcpa_nounit", False)):
        con.execute(f"CREATE OR REPLACE TEMP TABLE {name} (k VARCHAR)")
        con.executemany(f"INSERT INTO {name} VALUES (?)", sorted({("LOINC:" + x["loinc"],) for x in rows if x.get("loinc") and bool(unit(x)) == keep}))


def build_evidence(con) -> None:
    """Pairs a source we hold states, both directions: SeMRA (43.9 M aggregated mappings) and every UMLS shared-concept
    pair, including the ones not loaded because the names differ."""
    EVID.parent.mkdir(parents=True, exist_ok=True)
    con.execute("CREATE TEMP TABLE pv (p VARCHAR, v VARCHAR)")
    con.executemany("INSERT INTO pv VALUES (?, ?)", list(SEMRA_V.items()))
    lid = lambda v, col: (f"CASE WHEN {v} IN ({','.join(repr(x) for x in KEEP_PREFIX)}) THEN {v} || ':' || split_part({col}, ':', 2) "
                          f"ELSE split_part({col}, ':', 2) END")
    con.execute(f"""CREATE TEMP TABLE ev AS SELECT a.v v1, {lid('a.v', 'm.s')} c1, b.v v2, {lid('b.v', 'm.o')} c2,
               'SeMRA: ' || m.ms src, m.p rel,
               m.j IN ('semapv:UnspecifiedMatching', 'semapv:ManualMappingCuration') AND m.ms NOT LIKE '%cbms2019%' stated
        FROM '{SEMRA}' m JOIN pv a ON a.p = m.sp JOIN pv b ON b.p = m.op WHERE a.v <> b.v""")
    # superseded: a row from an older release of a source we hold, which the current release no longer states
    con.execute("CREATE TEMP TABLE cur (v1 VARCHAR, c1 VARCHAR, v2 VARCHAR, c2 VARCHAR)")
    con.executemany("INSERT INTO cur VALUES (?, ?, ?, ?)", current_statements())
    con.execute("CREATE TEMP TABLE curb AS SELECT * FROM cur UNION SELECT v2, c2, v1, c1 FROM cur")
    con.execute("ALTER TABLE ev ADD COLUMN superseded BOOLEAN DEFAULT false")
    cs = " OR ".join(f"(src = 'SeMRA: {k}' AND (v1 = '{v}' OR v2 = '{v}'))" for k, v in CURRENT.items())
    con.execute(f"""UPDATE ev SET superseded = true, stated = false WHERE stated AND ({cs})
                    AND (v1, c1, v2, c2) NOT IN (SELECT v1, c1, v2, c2 FROM curb)""")
    if UMLS_PAIRS.exists():
        con.execute(f"""INSERT INTO ev SELECT sv, sc, ov, oc, CASE WHEN same_name THEN 'UMLS shared concept (same name)'
                        ELSE 'UMLS shared concept (names differ)' END, 'shared CUI', true, false FROM '{UMLS_PAIRS}'""")
    con.execute(f"""COPY (SELECT DISTINCT * FROM (SELECT v1, c1, v2, c2, src, rel, stated, superseded FROM ev UNION ALL SELECT v2, c2, v1, c1, src, rel, stated, superseded FROM ev))
                    TO '{EVID}' (FORMAT parquet)""")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set-baseline", action="store_true")
    ap.add_argument("--refresh-evidence", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    con = duckdb.connect()
    con.execute("SET threads=8")
    if a.refresh_evidence or not EVID.exists():
        build_evidence(con)
    con.execute(f"ATTACH '{GRAPH}' AS g (READ_ONLY)")
    con.execute(f"ATTACH '{CMP}' AS cmp (READ_ONLY)")
    con.execute("CREATE TEMP VIEW edge AS SELECT * FROM g.edge")
    con.execute("CREATE TEMP VIEW node AS SELECT * FROM g.node")
    con.execute(f"CREATE TEMP VIEW evidence AS SELECT * FROM '{EVID}'")
    reg = json.load(open(REGISTER))["predicates"]
    ident = [p["id"] for p in reg if p["category"] == "identity" and p["id"] not in CLS_EXTRA]
    cls = [p["id"] for p in reg if p["category"] == "classification" and p["id"] not in NOT_WALKED] + list(CLS_EXTRA)
    q = lambda xs: ",".join(repr(x) for x in xs)
    # the walk: admissible edges only, keyed 'VOCAB:code'
    con.execute(f"""CREATE TEMP TABLE walk AS
        SELECT s_vocab || ':' || s_code src, o_vocab || ':' || o_code dst, o_vocab dv,
               CASE WHEN {ORPHA_CLS} THEN 'cls' WHEN {LOOSE} THEN 'end' ELSE 'id' END kind FROM edge
            WHERE predicate IN ({q(ident)}) AND state <> 'rejected' AND tier <> 'inadmissible'
        UNION SELECT o_vocab || ':' || o_code, s_vocab || ':' || s_code, s_vocab, CASE WHEN {LOOSE} THEN 'end' ELSE 'id' END FROM edge
            WHERE predicate IN ({q(ident)}) AND state <> 'rejected' AND tier <> 'inadmissible' AND NOT {ORPHA_CLS}
        UNION SELECT s_vocab || ':' || s_code, o_vocab || ':' || o_code, o_vocab, 'cls' FROM edge
            WHERE predicate IN ({q(cls)}) AND state <> 'rejected' AND tier <> 'inadmissible'""")
    if LOINC_TABLE.exists():
        con.execute(f"""CREATE TEMP TABLE lab_top AS SELECT LOINC_NUM code FROM read_csv('{LOINC_TABLE}', header=true, all_varchar=true)
            WHERE CLASSTYPE = '1' AND STATUS = 'ACTIVE' AND TRY_CAST(COMMON_TEST_RANK AS INT) > 0
              AND LOINC_NUM IN (SELECT code FROM node WHERE vocab = 'LOINC')
            ORDER BY TRY_CAST(COMMON_TEST_RANK AS INT) LIMIT 2000""")
    else:
        con.execute("CREATE TEMP TABLE lab_top (code VARCHAR)")
    loinc_sources(con)
    # Orphanet's own status: an entry it has retired (deprecated, or non-rare in Europe) is not a member
    con.execute("CREATE TEMP TABLE orpha_level (code VARCHAR, level VARCHAR, active BOOLEAN)")
    if ORPHA_XML.exists():
        import xml.etree.ElementTree as ET
        con.executemany("INSERT INTO orpha_level VALUES (?, ?, ?)", [(d.findtext("OrphaCode"), d.findtext("DisorderGroup/Name"),
                        "Inactive" not in [f.findtext("Label") for f in d.findall("DisorderFlagList/DisorderFlag")])
                        for d in ET.parse(ORPHA_XML).getroot().iter("Disorder") if d.findtext("OrphaCode")])
    cells, flagged = [], []
    base = json.load(open(BASELINE)) if BASELINE.exists() else {}
    for group, exp, spec in CELLS:
        gv, gsql = GROUPS[group]
        con.execute(f"CREATE OR REPLACE TEMP TABLE m AS SELECT DISTINCT '{gv}:' || s_code AS k, s_code AS code FROM ({gsql}) t(s_code)")
        n_all = con.execute("SELECT count(*) FROM m").fetchone()[0]
        applies = spec.get("applies") or (ORPHA_ACTIVE if gv == "ORPHA" else None)
        if applies:
            con.execute(f"DELETE FROM m WHERE code NOT IN ({applies})")
        n = con.execute("SELECT count(*) FROM m").fetchone()[0]
        # breadth-first walk; st 0 = only identity so far, 1 = has classified
        con.execute("CREATE OR REPLACE TEMP TABLE vis AS SELECT k m, k node, 0 st, 0 hop FROM m")  # st 2: reached by a loose alignment
        con.execute("CREATE OR REPLACE TEMP TABLE fr AS SELECT * FROM vis")
        final = "final" in spec
        for h in range(1, spec["hops"] + 1):
            allowed = "w.kind IN ('id', 'end') AND fr.st = 0" if final else "(w.kind = 'cls' AND fr.st IN (0, 1) OR w.kind IN ('id', 'end') AND fr.st = 0)"
            con.execute(f"""CREATE OR REPLACE TEMP TABLE fr AS SELECT DISTINCT fr.m, w.dst node,
                    CASE WHEN w.kind = 'end' THEN 2 WHEN w.kind = 'cls' OR fr.st = 1 THEN 1 ELSE 0 END st, {h} hop
                FROM fr JOIN walk w ON w.src = fr.node WHERE {allowed}
                  AND NOT EXISTS (SELECT 1 FROM vis v WHERE v.m = fr.m AND v.node = w.dst)""")
            con.execute("INSERT INTO vis SELECT * FROM fr")
        if final:
            side, other = ("s_vocab || ':' || s_code", "o") if spec["dir"] == "out" else ("o_vocab || ':' || o_code", "s")
            con.execute(f"""CREATE OR REPLACE TEMP TABLE fe AS SELECT {side} node, state, tier FROM edge WHERE predicate IN ({q(spec['final'])})""")
            con.execute("""CREATE OR REPLACE TEMP TABLE hit AS SELECT DISTINCT v.m FROM vis v JOIN fe ON fe.node = v.node
                           WHERE fe.state <> 'rejected' AND fe.tier <> 'inadmissible'""")
        else:
            con.execute(f"""CREATE OR REPLACE TEMP TABLE hit AS SELECT DISTINCT m FROM vis
                            WHERE split_part(node, ':', 1) IN ({q(spec['target'])})""")
        present = con.execute("SELECT count(*) FROM hit").fetchone()[0]
        cid = f"{group} | {exp}"
        con.execute(f"""CREATE OR REPLACE TEMP TABLE smp AS SELECT k, code FROM m WHERE k NOT IN (SELECT m FROM hit)
                        ORDER BY hash(k || '{cid}') LIMIT {SAMPLE}""")
        # classify the sample
        rows = []
        for k, code in con.execute("SELECT k, code FROM smp ORDER BY k").fetchall():
            near = [x for (x,) in con.execute("SELECT DISTINCT node FROM vis WHERE m = ? AND st = 0 AND hop <= 1", [k]).fetchall()]
            cls_, why = None, []
            if final:
                held = con.execute(f"""SELECT DISTINCT {other}_vocab || ':' || {other}_code FROM edge WHERE predicate IN ({q(spec['final'])})
                        AND tier = 'inadmissible' AND state <> 'rejected' AND {side} IN (SELECT node FROM vis WHERE m = ?)""", [k]).fetchall()
                if held:
                    cls_, why = "our_gap", ["held back by a hand check (inadmissible family)"]
                elif spec.get("covers") and con.execute(f"""SELECT count(*) FROM vis WHERE m = ? AND split_part(node, ':', 1) IN ({q(spec['covers'])})""",
                                                        [k]).fetchone()[0]:
                    cls_, why = "unknown", [spec.get("covers_why", f"covered by a source for {', '.join(spec['covers'])}, which states nothing of this kind")]
            else:
                ev3 = con.execute(f"""SELECT DISTINCT src, stated, superseded FROM evidence WHERE v1 || ':' || c1 IN (SELECT unnest(?::VARCHAR[]))
                                      AND v2 IN ({q(spec['target'])})""", [near]).fetchall()
                ev = [(s_, st) for s_, st, sup in ev3 if not sup]
                sup = sorted(s_ for s_, _, sp in ev3 if sp)
                if any(st for _, st in ev):
                    cls_, why = "our_gap", sorted(s for s, st in ev if st)
                elif sup:
                    cls_, why = "unknown", [f"superseded: stated by an older release ({', '.join(sup)}); the current release we hold does not"]
                elif spec.get("covers") and con.execute(f"""SELECT count(*) FROM vis WHERE m = ? AND split_part(node, ':', 1) IN ({q(spec['covers'])})""",
                                                        [k]).fetchone()[0]:
                    cls_, why = "unknown", [spec.get("covers_why", f"covered by {', '.join(spec['covers'])}, which states nothing of this kind")]
                elif spec.get("decline") and con.execute(f"SELECT count(*) FROM ({spec['decline']}) d(c) WHERE c = ?", [code]).fetchone()[0]:
                    cls_, why = "unknown", ["the map's publisher declines: cannot be classified with available data"]
            if cls_ is None and spec.get("sources"):
                # coverage rules (the LOINC cells): the first source that states the link makes it our gap; one that covers
                # the member without stating it makes it unknown. Matched on the member and what identity reaches from it.
                nodes = [x for (x,) in con.execute("SELECT DISTINCT node FROM vis WHERE m = ? AND st = 0", [k]).fetchall()]
                for name, kind, table in spec["sources"]:
                    if con.execute(f"SELECT count(*) FROM {table} WHERE k IN (SELECT unnest(?::VARCHAR[]))", [nodes]).fetchone()[0]:
                        cls_, why = ("our_gap" if kind == "states" else "unknown"), [name]
                        break
            if cls_ is None:
                pred = sorted(s for s, st in ev if not st) if not final else []
                au = gv == "SCT" and group != "PBS-listed products" and con.execute("SELECT au_authored FROM cmp.concept WHERE id = ?", [code]).fetchone()
                reason = ("a SNOMED CT-AU extension concept: outside the international maps and sources" if au and au[0]
                          else spec.get("not_held", "no held source covers it"))
                cls_, why = "no_source_held", [reason] + [f"predicted only: {x}" for x in pred]
            name = con.execute("SELECT name FROM node WHERE key = ?", [k]).fetchone()
            rows.append({"code": code, "name": name[0] if name else None, "class": cls_, "evidence": why})
        tally = {c: sum(r["class"] == c for r in rows) for c in ("our_gap", "unknown", "no_source_held")}
        absent, s_n = n - present, len(rows)
        share = round(present / n, 4) if n else None
        cell = {"group": group, "expectation": exp, "members": n, "not_applicable": n_all - n, "present": present, "present_share": share,
                "absent": absent, "sample": s_n, "classes": tally,
                "our_gap_share_of_absent": {"point": round(tally["our_gap"] / s_n, 3) if s_n else None,
                                            "wilson_95": wilson(tally["our_gap"], s_n)},
                "estimated_absent_by_class": {c: round(absent * v / s_n) if s_n else 0 for c, v in tally.items()},
                "evidence_sources": _count(src for r in rows if r["class"] == "our_gap" for src in r["evidence"]),
                "no_source_reasons": _count(r["evidence"][0] for r in rows if r["class"] == "no_source_held"),
                "sample_rows": rows}
        b = base.get(cid)
        if b and share is not None and b["present_share"] - share > DROP:
            flagged.append(f"{cid}: present share {b['present_share']:.3f} -> {share:.3f}")
            cell["guard"] = "DROP"
        cells.append(cell)
        print(f"{cid:<78} {present:>7,}/{n:<7,} {share if share is not None else '-':>7}  gap {tally['our_gap']:>2} "
              f"unk {tally['unknown']:>2} none {tally['no_source_held']:>2}", flush=True)
    out = {"_note": "completeness from the source side (scripts/completeness.py); absent members sampled and classified, "
                    "unknown recorded as unknown", "seconds": round(time.time() - t0), "cells": cells, "guard": flagged}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    if a.set_baseline:
        BASELINE.write_text(json.dumps({f"{c['group']} | {c['expectation']}": {"members": c["members"], "present": c["present"],
                                        "present_share": c["present_share"]} for c in cells}, indent=1) + "\n")
        print(f"baseline written: {BASELINE}")
        if flagged:
            print("accepted as the new baseline:\n  " + "\n  ".join(flagged))
        return 0
    if flagged:
        print("GUARD -- present share dropped:\n  " + "\n  ".join(flagged), file=sys.stderr)
        return 1
    return 0


def _count(it) -> dict:
    d: dict = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    sys.exit(main())
