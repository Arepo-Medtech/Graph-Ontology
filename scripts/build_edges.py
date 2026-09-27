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


ONT_ROOT = os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES"))   # the licensed releases, read in place
CMP = Path("out/compendium.duckdb")
# the spine project's database and Athena vocabulary; on a machine without ~/code/spine, scripts/graph_inputs.py restore
# puts them under this repository's out/ (from ~/Documents/ONTOLOGIES/graph-inputs and the Athena zip)
_first = lambda *ps: next((p for p in ps if p.exists()), ps[0])
SPINE = _first(Path(os.path.expanduser("~/code/spine/out/spine.duckdb")), Path("out/spine.duckdb"))
VOCAB_DIR = _first(Path(os.path.expanduser("~/code/spine/out/omop-vocab/CONCEPT.csv")), Path("out/omop-vocab/CONCEPT.csv")).parent
GRAPH = Path("out/graph.duckdb")
LEDGER = Path("out/loader_ledger.json")                     # per-loader: rows available, excluded (why), loaded
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
UMLS_PAIRS = Path("cache/umls/umls_shared_cui.parquet")
DECISIONS = Path("reference/candidate_decisions.json")      # scripts/review_sheets.py: a person's decisions on the review queues
UMLS_CONSO = Path("cache/umls/2026AA/mrconso.parquet")   # scripts/umls_mrconso.py (licensed; not redistributed)
UMLS_REL = Path("cache/umls/umls_rel_edges.parquet")
WAVE2_MEMBERS = Path("cache/wave2/umls_disease_member_candidates.parquet")   # scripts/wave2_candidates.py (UMLS-derived: git-ignored)
WAVE2_UNII = Path("cache/wave2/unii_rxnorm_candidates.parquet")               # scripts/wave2_candidates.py (UMLS-derived: git-ignored)
UMLS_MRMAP, UMLS_AUI = Path("cache/umls/2026AA/mrmap_l0.parquet"), Path("cache/umls/2026AA/aui_l0.parquet")   # CCSR via UMLS Level 0          # scripts/umls_mrrel.py, UMLS 2026AA MRREL Level 0 (licensed)   # scripts/umls_mrconso.py, UMLS 2026AA MRCONSO (licensed; not redistributed)
UMLS_FMA_SCT, UMLS_RADLEX_CUI = Path("cache/umls/fma_sct.tsv"), Path("cache/umls/radlex_cui_sct.tsv")   # scripts/umls_crosswalk.py
LOINC_RSNA = Path(os.path.join(ONT_ROOT, "Loinc_2.83/AccessoryFiles/LoincRsnaRadiologyPlaybook/LoincRsnaRadiologyPlaybook.csv"))
RSNA_PLAYBOOK = Path(os.environ.get("RSNA_PLAYBOOK", os.path.join(ONT_ROOT, "complete-playbook-dev.csv")))
LOINC_PARTS = Path(os.path.join(ONT_ROOT, "Loinc_2.83/AccessoryFiles/PartFile/PartRelatedCodeMapping.csv"))
LOINC_PARTLINK = Path(os.path.join(ONT_ROOT, "Loinc_2.83/AccessoryFiles/PartFile/LoincPartLink_Primary.csv"))
LOINC_PARTLINK_SUPP = LOINC_PARTLINK.with_name("LoincPartLink_Supplementary.csv")
LOINC_ANSWERS = LOINC_PARTLINK.parent.parent / "AnswerFile" / "AnswerList.csv"   # answers with their SNOMED CT code
DC = Path("cache/drugcentral")
UMLS_HPO = Path("cache/umls/hpo_snomed.tsv")
PBS_BIND = Path("reference/pbs_indication_bindings.json")   # scripts/bind_indications.py
UNIT_PAIRS, THRESH_UNITS = Path("reference/loinc_unit_counterparts.json"), Path("reference/threshold_units.json")   # US <-> AU units
AU_RF2 = Path(os.environ.get("AU_RF2_SNAPSHOT", os.path.join(ONT_ROOT, "SnomedCT_Release_AU1000036_20260831/Snapshot")))
HGNC_SET = Path("cache/hgnc/hgnc_complete_set.txt")           # HGNC complete set, downloaded 24 Sep 2026 (CC0)
ORPHA_XML = Path("cache/orphanet/en_product1.xml")            # Orphadata product 1, 2026-06-23 (CC BY 4.0)
ORPHA_GENES = Path("cache/orphanet/en_product6.xml")          # Orphadata product 6 (genes), 2026-06-23, 22.6 MB (CC BY 4.0)
ORPHA_PHENO = Path("cache/orphanet/en_product4.xml")          # Orphadata product 4 (HPO phenotypes), 2026-06-23, 47.9 MB (CC BY 4.0)
SCT_US_XMAP = Path("cache/snomed-us/extended_map_20260901.parquet")   # scripts/snomed_us_maps.py: SNOMED -> ICD-10 / ICD-10-CM maps (licensed)
WHO_MAP = Path("cache/who-icd11")                             # WHO ICD-10 <-> ICD-11 mapping tables, release 2026-01 (CC BY-ND 3.0 IGO)
GENCC = Path("cache/gencc/gencc-submissions.tsv")                # GenCC gene-disease validity, all submitters (CC0)
MEDGEN_MAP = Path("cache/medgen/MedGenIDMappings.txt.gz")        # NCBI MedGen: concept -> source codes (public domain)
CHEBI_OBO = Path("cache/chebi/chebi.obo.gz")                     # ChEBI ontology release 255 (CC BY 4.0)
REACTOME = Path("cache/reactome")                             # Reactome v97: UniProt2Reactome, pathways, hierarchy (CC0)
RCPA_UNITS = Path("cache/rcpa/reporting_units.json")          # scripts/rcpa_units.py -- RCPA copyright, git-ignored
RCPA_UNITS_PIN = "RCPA SPIA RCPA_v20260831"
RCPA_ELEMENTS = Path("cache/rcpa/element_bindings.json")   # scripts/rcpa_elements.py: SNOMED + LOINC per report element
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
LOINC_EXT = Path(os.environ.get("LOINC_EXTENSION", os.path.join(ONT_ROOT, "SnomedCT_LOINCExtension_PRODUCTION_LO1010000_20260321T120000Z/Snapshot")))   # licensed; read in place
LOINC_TABLE = Path(os.environ.get("LOINC_TABLE", os.path.join(ONT_ROOT, "Loinc_2.83/LoincTable/Loinc.csv")))     # written by scripts/umls_hpo_crosswalk.py (licensed; not redistributed)

PIN = {"sct": "SNOMED CT-AU 20260831", "athena": "Athena v5.0 29-AUG-26", "pbs": "PBS schedule 4333",
       "loinc": "LOINC 2.82 (Athena)", "mondo": "MONDO releases/2026-09-01", "hpo": "HPO 2026-09-02",
       "dc": "DrugCentral 2023-11-01", "corpus": "reference/snomed_bindings.json", "umls": "UMLS current (UTS crosswalk)", "umls_rel": "UMLS 2026AA MRCONSO", "loinc_ext": "LOINC Extension 20260321", "loinc_table": "LOINC 2.83", "uberon": "Uberon v2026-06-23", "mbs": "MBS XML 20260801", "hgnc": "HGNC complete set 2026-09-24",
       "orphanet": "Orphadata product1 2026-06-23", "reactome": "Reactome v97", "gencc": "GenCC submissions 2026-09-13", "medgen": "MedGen ID mappings 2026-09-26", "chebi": "ChEBI 255 (2026-09-09)", "who": "WHO ICD-11 2026-01 mapping tables", "ccsr": "AHRQ CCSR for ICD-10-CM 2026 (UMLS 2026AA)",
       "sct_us": "SNOMED CT US Edition 20260901 (International 20260701 ICD-10 map)",
       "radlex": "RadLex 4.3", "rsna": "RSNA Radiology Playbook (complete-playbook-dev.csv, downloaded 24 Sep 2026)"}
OMOP_VOCAB = {"RxNorm": "RXN", "RxNorm Extension": "RXE", "AMT": "SCT", "SNOMED": "SCT", "ATC": "ATC", "ICD10CM": "ICD10CM"}
LOINC_AXIS = {"COMPONENT": "loinc:has_component", "PROPERTY": "loinc:has_property", "TIME": "loinc:has_time_aspect",
              "SYSTEM": "loinc:has_system", "SCALE": "loinc:has_scale", "METHOD": "loinc:has_method"}
EDGE_COLS = "s_vocab, s_code, predicate, o_vocab, o_code, source, source_locator, method, tier, state, pin, attrs"


def obo_terms(path: Path) -> list[dict]:
    """Minimal OBO reader: id, name, is_a, xref, obsolete. Enough for hierarchy, labels and cross-references."""
    terms, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line == "[Term]":
            cur = {"is_a": [], "xref": []}
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
            elif k == "xref":
                cur["xref"].append(v.split(" ")[0])
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
            "LOINC part links": LOINC_PARTLINK, "LOINC supplementary part links": LOINC_PARTLINK_SUPP, "LOINC/RSNA playbook": LOINC_RSNA, "RSNA playbook": RSNA_PLAYBOOK,
            "RadLex (scripts/radlex_prepare.py)": RADLEX_JSON, "RCPA units (scripts/rcpa_units.py)": RCPA_UNITS,
            "unit pairs": UNIT_PAIRS, "threshold units": THRESH_UNITS, "diagnostic accuracy": DX_ACC,
            "diagnostic accuracy bindings": DX_BIND, "diagnostic accuracy verification": DX_VER,
            "UMLS HPO -> SNOMED": UMLS_HPO, "UMLS SNOMED -> NCBI": UMLS_SCT_NCBI, "UMLS FMA -> SNOMED": UMLS_FMA_SCT,
            "UMLS RadLex CUI -> SNOMED": UMLS_RADLEX_CUI, "UMLS 2026AA shared-CUI pairs (scripts/umls_mrconso.py)": UMLS_PAIRS, "UMLS 2026AA MRCONSO": UMLS_CONSO,
            "UMLS 2026AA relationships (scripts/umls_mrrel.py)": UMLS_REL, "UMLS 2026AA MRMAP (CCSR)": UMLS_MRMAP,
            "SNOMED CT-AU RF2 refsets": AU_RF2 / "Refset", "HGNC": HGNC_SET, "Orphanet": ORPHA_XML,
            "Orphanet genes (product 6)": ORPHA_GENES, "Orphanet phenotypes (product 4)": ORPHA_PHENO,
            "Reactome": REACTOME / "UniProt2Reactome.txt", "WHO ICD-10 <-> ICD-11 tables": WHO_MAP / "10To11MapToOneCategory.txt",
            "SNOMED -> ICD-10 / ICD-10-CM maps (scripts/snomed_us_maps.py)": SCT_US_XMAP}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab-dir", default=str(VOCAB_DIR))
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
    # The loader ledger (workstream 1): for every loader, the rows its source offers, each filter in turn with its reason
    # and the rows it took out, and what loaded -- so a member the graph lacks can be told apart as never in the source,
    # or in it and excluded (and why). A loader is one of: 'source' (rows available -> exclusions -> loaded), 'derived'
    # (a rule over edges already loaded; it names the rule), or 'undeclared' (listed as such -- the ledger hides nothing).
    # Whatever is left between the rows kept and the edges loaded is named, never absorbed: rows collapsing into fewer
    # edges (duplicates, several rows naming one edge), or one row giving several edges.
    ledger, loaders = {}, []

    def account(label: str, available=None, excluded=(), derived: str | None = None, unit: str = "rows") -> None:
        e = ledger.setdefault(label, {"kind": "undeclared", "available": None, "excluded": [], "unit": unit})
        if derived:
            e.update(kind="derived", rule=derived)
        if available is not None:
            e.update(kind="source", available=int(available), unit=unit)
        e["excluded"] += [{"reason": r, "rows": int(n)} for r, n in excluded]

    def waterfall(src: str, keep, params=None) -> tuple[int, list]:
        """One pass over the source: its rows, then how many each filter (cumulatively, in order) keeps."""
        conds, cols = [], ["count(*)"]
        for _, c in keep:
            conds.append(f"({c})")
            cols.append(f"count(*) FILTER (WHERE {' AND '.join(conds)})")
        got = con.execute(f"SELECT {', '.join(cols)} FROM {src}", params or []).fetchone()
        return got[0], [(r, got[i] - got[i + 1]) for i, (r, _) in enumerate(keep)]

    def ins(label: str, sql: str, params=None, src: str | None = None, keep=(), derived: str | None = None, unit: str = "rows") -> None:
        if src:              # counted before the insert: a filter that asks "is this code in the graph yet" must not see its own edges
            n0, exc = waterfall(src, keep)
        before = con.execute("SELECT count(*) FROM edge").fetchone()[0]
        con.execute(f"INSERT INTO edge ({EDGE_COLS}) " + sql, params or [])
        log[label] = con.execute("SELECT count(*) FROM edge").fetchone()[0] - before
        loaders.append(label)
        if src:
            account(label, n0, exc, unit=unit)
        elif derived:
            account(label, derived=derived)
        print(f"  {label:<44} {log[label]:>10,}", flush=True)

    def ins_rows(label: str, rows: list[tuple], available=None, excluded=(), derived: str | None = None, unit: str = "rows") -> None:
        before = con.execute("SELECT count(*) FROM edge").fetchone()[0]
        if rows:
            con.executemany(f"INSERT INTO edge ({EDGE_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        log[label] = con.execute("SELECT count(*) FROM edge").fetchone()[0] - before
        loaders.append(label)
        if available is not None or excluded or derived:
            account(label, available, excluded, derived, unit)
        print(f"  {label:<44} {log[label]:>10,}", flush=True)

    vmap = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in OMOP_VOCAB.items())
    print("loading edges:")
    # --- SNOMED CT-AU: the whole relationship snapshot ------------------------------------------------------------
    ins("SNOMED CT-AU relationships", f"""SELECT 'SCT', src, 'sct:' || typ, 'SCT', dst, 'SNOMED CT-AU RF2', 'compendium rel',
            'native', 'native', 'asserted', '{PIN['sct']}', json_object('group', grp) FROM cmp.rel""", src="cmp.rel")
    # --- SNOMED CT concrete values: the numbers and strings a concept carries (AMT strengths, pack sizes, counts) ------
    # RF2's RelationshipConcreteValues give an attribute a literal ('#500', '"text"'), not a concept. A value is a property
    # of its concept, not a node -- "500" as a node would join every product that happens to share it -- so they go to
    # their own table, concrete_value, traced like an edge (the RF2 row id is the locator). graph_register.py registers
    # the attribute types (snomed_concrete_attributes), and the build refuses an unregistered one as it does for edges.
    con.execute("""CREATE TABLE concrete_value (s_vocab VARCHAR, s_code VARCHAR, predicate VARCHAR, datatype VARCHAR, value_num DOUBLE,
                   value_str VARCHAR, value_raw VARCHAR, grp INTEGER, source VARCHAR, source_locator VARCHAR, pin VARCHAR)""")
    lx_concepts = LOINC_EXT / "Terminology" / "sct2_Concept_Snapshot_LO1010000_20260321.txt"
    for lbl, f, sname, pin, cond in (
            ("SNOMED CT-AU concrete values (strengths, pack sizes, counts)",
             AU_RF2 / "Terminology" / f"sct2_RelationshipConcreteValues_Snapshot_AU1000036_{PIN['sct'].split()[-1]}.txt",
             "SNOMED CT-AU RF2", PIN["sct"], "sourceId IN (SELECT id FROM cmp.concept)"),
            ("SNOMED CT LOINC Extension concrete values", LOINC_EXT / "Terminology" / "sct2_RelationshipConcreteValues_Snapshot_LO1010000_20260321.txt",
             "SNOMED CT LOINC Extension", PIN["loinc_ext"],
             "sourceId IN (SELECT id FROM cmp.concept)" + (f" OR sourceId IN (SELECT id FROM read_csv('{lx_concepts}', delim='\t', header=true, "
                                                           "quote='', escape='', all_varchar=true) WHERE active = '1')" if lx_concepts.exists() else ""))):
        if not f.exists():
            continue
        rv = f"read_csv('{f}', delim='\t', header=true, quote='', escape='', all_varchar=true)"
        n0, exc = waterfall(rv, [("inactive row", "active = '1'"), ("concept not active in the release", cond)])
        before = con.execute("SELECT count(*) FROM concrete_value").fetchone()[0]
        con.execute(f"""INSERT INTO concrete_value SELECT 'SCT', sourceId, 'sct:' || typeId,
                CASE WHEN value LIKE '"%' THEN 'string' WHEN value LIKE '#%.%' THEN 'decimal' ELSE 'integer' END,
                CASE WHEN value LIKE '#%' THEN TRY_CAST(substr(value, 2) AS DOUBLE) END,
                CASE WHEN value LIKE '"%' THEN trim(value, '"') END, value, CAST(relationshipGroup AS INT), '{sname}',
                'sct2_RelationshipConcreteValues_Snapshot id ' || id, '{pin}'
            FROM {rv} WHERE active = '1' AND ({cond})""")
        log[lbl] = con.execute("SELECT count(*) FROM concrete_value").fetchone()[0] - before
        loaders.append(lbl)
        account(lbl, n0, exc, unit="concrete-value rows (to the concrete_value table, not edges)")
        print(f"  {lbl:<44} {log[lbl]:>10,}", flush=True)
    # --- SNOMED CT-AU's own maps and associations (the release's Refset/Map and Refset/Content) -----------------------
    ref = lambda sub, name: f"read_csv('{AU_RF2 / 'Refset' / sub / name}', delim='\t', header=true, quote='', escape='', all_varchar=true)"
    rel_ = PIN["sct"].split()[-1]
    if (AU_RF2 / "Refset").exists():
        ins("SNOMED CT -> ICD-O-3 (ICD-O simple map)", f"""SELECT DISTINCT 'SCT', referencedComponentId, 'sct:icdo_map', 'ICDO', mapTarget,
                'SNOMED CT-AU RF2', 'ICD-O simple map reference set 446608001', 'simple map', 'native', 'asserted', '{PIN['sct']}',
                json_object('axis', CASE WHEN mapTarget LIKE 'C%' THEN 'topography' ELSE 'morphology' END)
            FROM {ref('Map', f'der2_sRefset_SimpleMapSnapshot_AU1000036_{rel_}.txt')}
            WHERE active = '1' AND refsetId = '446608001' AND referencedComponentId IN (SELECT id FROM cmp.concept)""",
            src=f"{ref('Map', f'der2_sRefset_SimpleMapSnapshot_AU1000036_{rel_}.txt')} WHERE refsetId = '446608001'",
            keep=[("inactive member", "active = '1'"), ("concept not active in SNOMED CT-AU", "referencedComponentId IN (SELECT id FROM cmp.concept)")])
        ins("AMT product -> ARTG id (ARTG Id reference set)", f"""SELECT DISTINCT 'SCT', referencedComponentId, 'sct:artg_id', 'ARTG', mapTarget,
                'SNOMED CT-AU RF2', 'ARTG Id reference set 11000168105', 'simple map', 'native', 'asserted', '{PIN['sct']}', NULL
            FROM {ref('Map', f'der2_iRefset_SimpleMapSnapshot_AU1000036_{rel_}.txt')}
            WHERE active = '1' AND refsetId = '11000168105' AND referencedComponentId IN (SELECT id FROM cmp.concept)""",
            src=f"{ref('Map', f'der2_iRefset_SimpleMapSnapshot_AU1000036_{rel_}.txt')} WHERE refsetId = '11000168105'",
            keep=[("inactive member", "active = '1'"), ("concept not active in SNOMED CT-AU", "referencedComponentId IN (SELECT id FROM cmp.concept)")])
        ins("SNOMED anatomy structure -> entire / part (association refsets)", f"""SELECT DISTINCT 'SCT', referencedComponentId,
                CASE refsetId WHEN '734138000' THEN 'sct:anatomy_structure_entire' ELSE 'sct:anatomy_structure_part' END,
                'SCT', targetComponentId, 'SNOMED CT-AU RF2', 'association reference set ' || refsetId, 'association', 'native', 'asserted',
                '{PIN['sct']}', NULL
            FROM {ref('Content', f'der2_cRefset_AssociationSnapshot_AU1000036_{rel_}.txt')}
            WHERE active = '1' AND refsetId IN ('734138000', '734139008')""",
            src=f"{ref('Content', f'der2_cRefset_AssociationSnapshot_AU1000036_{rel_}.txt')} WHERE refsetId IN ('734138000', '734139008')",
            keep=[("inactive member", "active = '1'")])
        # membership of the AU release's simple reference sets: clinical subsets (Problem/Diagnosis, the emergency
        # department sets, RACS MALT procedures, allied health), foundation sets by hierarchy, AMT structure, the
        # medicines-regulation lists (each state's monitored Schedule 4 list, Schedule 8, Black Triangle, brand
        # consideration) and the RCPA / RANZCR requesting sets. A reference set is itself a SNOMED concept, so a membership
        # is an edge from the member to that concept; method names the set.
        ins("SNOMED CT-AU reference set membership", f"""SELECT 'SCT', r.referencedComponentId, 'sct:in_refset', 'SCT', r.refsetId,
                'SNOMED CT-AU RF2', 'simple reference set ' || r.refsetId, coalesce(n.pt, r.refsetId), 'native', 'asserted', '{PIN['sct']}', NULL
            FROM {ref('Content', f'der2_Refset_SimpleSnapshot_AU1000036_{rel_}.txt')} r LEFT JOIN cmp.concept n ON n.id = r.refsetId
            WHERE r.active = '1' AND r.referencedComponentId IN (SELECT id FROM cmp.concept)""",
            src=f"{ref('Content', f'der2_Refset_SimpleSnapshot_AU1000036_{rel_}.txt')} r",
            keep=[("inactive member", "r.active = '1'"), ("member not an active concept", "r.referencedComponentId IN (SELECT id FROM cmp.concept)")])
        log["SNOMED CT-AU reference set members not loaded (member not an active concept)"] = con.execute(f"""SELECT count(*)
            FROM {ref('Content', f'der2_Refset_SimpleSnapshot_AU1000036_{rel_}.txt')} WHERE active = '1'
              AND referencedComponentId NOT IN (SELECT id FROM cmp.concept)""").fetchone()[0]
        con.execute("INSERT INTO name_hint SELECT DISTINCT 'ICDO', o_code, 'ICD-O-3 ' || o_code FROM edge WHERE predicate = 'sct:icdo_map'")
        con.execute("INSERT INTO name_hint SELECT DISTINCT 'ARTG', o_code, 'ARTG ' || o_code FROM edge WHERE predicate = 'sct:artg_id'")

    # --- SNOMED CT's maps to ICD-10 (SNOMED International) and ICD-10-CM (NLM), as the US Edition ships them ----------
    # Complex maps: a concept can need several codes together (mapGroup), and within a group the first rule that holds
    # wins (mapPriority) -- TRUE, IFA <condition> (the patient's sex, age, or another SNOMED concept), OTHERWISE TRUE.
    # method names the rule kind, so a traversal that cannot evaluate a condition can leave conditional edges out; the
    # rule text, group, priority, advice and category ride in attrs. A row with no target (SNOMED: "cannot be classified
    # with available data") is not an edge. Source concepts must be active in SNOMED CT-AU; the US-extension concepts in
    # the file are not.
    if SCT_US_XMAP.exists():
        for refset, pred, vocab, what in (("447562003", "sct:icd10_map", "ICD10WHO", "SNOMED CT -> ICD-10 (SNOMED International map)"),
                                          ("6011000124106", "sct:icd10cm_map", "ICD10CM", "SNOMED CT -> ICD-10-CM (NLM map)")):
            ins(what, f"""SELECT 'SCT', m.referencedComponentId, '{pred}', '{vocab}', m.mapTarget, 'SNOMED CT US Edition (NLM)',
                    'extended map reference set {refset}',
                    CASE WHEN m.mapRule = 'TRUE' THEN 'unconditional' WHEN m.mapRule = 'OTHERWISE TRUE' THEN 'default, when no condition holds'
                         ELSE 'conditional' END, 'native', 'asserted', '{PIN['sct_us']}',
                    json_object('group', CAST(m.mapGroup AS INT), 'priority', CAST(m.mapPriority AS INT),
                                'rule', CASE WHEN m.mapRule NOT IN ('TRUE', 'OTHERWISE TRUE') THEN m.mapRule END,
                                'advice', m.mapAdvice, 'category', coalesce(n.pt, m.mapCategoryId))
                FROM '{SCT_US_XMAP}' m LEFT JOIN cmp.concept n ON n.id = m.mapCategoryId
                WHERE m.refsetId = '{refset}' AND coalesce(m.mapTarget, '') <> '' AND m.mapTarget NOT LIKE '%?%'
                  AND m.referencedComponentId IN (SELECT id FROM cmp.concept)""",
                src=f"'{SCT_US_XMAP}' m WHERE m.refsetId = '{refset}'",
                keep=[("no target: cannot be classified with available data", "coalesce(m.mapTarget, '') <> ''"),
                      ("partial code (loaded apart, as its subcategory)", "m.mapTarget NOT LIKE '%?%'"),
                      ("source concept not active in SNOMED CT-AU", "m.referencedComponentId IN (SELECT id FROM cmp.concept)")])
            for why, cond in (("no target: cannot be classified", "coalesce(mapTarget, '') = ''"),
                              ("source concept not active in SNOMED CT-AU", "referencedComponentId NOT IN (SELECT id FROM cmp.concept)")):
                log[f"{what}: rows not loaded, {why}"] = con.execute(f"""SELECT count(*) FROM '{SCT_US_XMAP}'
                    WHERE refsetId = '{refset}' AND {cond}""").fetchone()[0]
        # NLM's partial targets: 'S08.129?' names a code whose last character (for injuries, the episode of care) the
        # coder still has to choose. The concept certainly falls in the subcategory the published characters spell --
        # 'S08.129', or 'O32.4' for 'O32.4XX?' once the placeholder X's are dropped -- so it loads against that code, when
        # it is an ICD-10-CM code, as its own method; attrs.target_as_published keeps NLM's string.
        con.execute(f"""CREATE TEMP TABLE icd10cm_code AS SELECT DISTINCT concept_code c FROM C WHERE vocabulary_id = 'ICD10CM'""")
        con.execute(f"""CREATE TEMP TABLE xmap_partial AS SELECT m.*, rtrim(regexp_replace(rtrim(m.mapTarget, '?'), 'X+$', ''), '.') sub
            FROM '{SCT_US_XMAP}' m WHERE m.refsetId = '6011000124106' AND m.mapTarget LIKE '%?'""")
        ins("SNOMED CT -> ICD-10-CM subcategory (NLM map, partial code)", f"""SELECT 'SCT', m.referencedComponentId, 'sct:icd10cm_map', 'ICD10CM',
                m.sub, 'SNOMED CT US Edition (NLM)', 'extended map reference set 6011000124106',
                CASE WHEN m.mapRule = 'TRUE' THEN 'unconditional' WHEN m.mapRule = 'OTHERWISE TRUE' THEN 'default, when no condition holds'
                     ELSE 'conditional' END || ', partial code (subcategory)', 'native', 'asserted', '{PIN['sct_us']}',
                json_object('group', CAST(m.mapGroup AS INT), 'priority', CAST(m.mapPriority AS INT),
                            'rule', CASE WHEN m.mapRule NOT IN ('TRUE', 'OTHERWISE TRUE') THEN m.mapRule END,
                            'advice', m.mapAdvice, 'category', coalesce(n.pt, m.mapCategoryId), 'target_as_published', m.mapTarget)
            FROM xmap_partial m LEFT JOIN cmp.concept n ON n.id = m.mapCategoryId
            WHERE m.sub IN (SELECT c FROM icd10cm_code) AND m.referencedComponentId IN (SELECT id FROM cmp.concept)""",
            src="xmap_partial m", keep=[("subcategory not an ICD-10-CM code", "m.sub IN (SELECT c FROM icd10cm_code)"),
                                        ("source concept not active in SNOMED CT-AU", "m.referencedComponentId IN (SELECT id FROM cmp.concept)")])
        log["SNOMED CT -> ICD-10-CM (NLM map): partial codes not loaded, subcategory not an ICD-10-CM code"] = con.execute(
            "SELECT count(*) FROM xmap_partial WHERE sub NOT IN (SELECT c FROM icd10cm_code)").fetchone()[0]
        # ICD-10's optional fifth characters (WHO Volume 1: site in chapter XIII, open / closed in XIX -- M41.15, S36.00)
        # subdivide a four-character subcategory; T08.X0-style codes subdivide a three-character category. WHO's ICD-11
        # tables list only the parent, so each mapped fifth-character code gets an edge to its parent, kept only when the
        # parent is a code of WHO's own tables -- the step that carries these concepts on to ICD-11.
        if (WHO_MAP / "10To11MapToOneCategory.txt").exists():
            who10 = set()
            for f in ("10To11MapToOneCategory.txt", "10To11MapToMultipleCategories.txt"):
                rows_ = [l.rstrip("\r\n").split("\t") for l in open(WHO_MAP / f, encoding="utf-8-sig")]
                ic = [h.strip() for h in rows_[0]].index("icd10Code")
                who10 |= {r[ic].strip() for r in rows_[1:] if len(r) > ic}
            parent = lambda c: (re.match(r"^([A-Z]\d\d\.\d)\d$", c) or re.match(r"^([A-Z]\d\d)\.X\d$", c) or [None, None])[1]
            mapped = [c for (c,) in con.execute("SELECT DISTINCT o_code FROM edge WHERE predicate = 'sct:icd10_map'").fetchall()]
            lift = [(c, parent(c)) for c in mapped if c not in who10]
            ins_rows("ICD-10 fifth-character code -> its WHO parent", sorted(
                ("ICD10WHO", c, "icd10:subdivision_of", "ICD10WHO", p_, "WHO ICD-10 code structure", "10To11MapToOneCategory.txt (parent present)",
                 "fifth-character subdivision", "native", "asserted", PIN["who"], None) for c, p_ in lift if p_ and p_ in who10),
                available=len(lift), excluded=[("no parent in WHO's tables", sum(1 for c, p_ in lift if not (p_ and p_ in who10)))],
                unit="mapped ICD-10 codes absent from WHO's tables")
            log["ICD-10 mapped codes absent from WHO's tables, no parent there"] = sum(1 for c, p_ in lift if not (p_ and p_ in who10))


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
        LEFT JOIN cmp.omop_drug_check chk ON chk.product_id = o.product_id AND chk.source = 'omop_drug'""",
        src="cmp.omop_drug o WHERE o.standard_concept_id IS NOT NULL",
        keep=[("standard concept not in the Athena bundle", "CAST(o.standard_concept_id AS VARCHAR) IN (SELECT concept_id FROM cmap)")])
    ins("OMOP product -> standard drug (rejected)", f"""SELECT 'SCT', o.product_id, 'omop:maps_to', CASE m.vocabulary_id {vmap} END,
            m.concept_code, 'OMOP Athena', 'omop_drug.refused_standard_concept_id', 'Maps to', 'ungraded', 'rejected',
            '{PIN['athena']}', json_object('level', o.level, 'review', o.review_status)
        FROM cmp.omop_drug o JOIN cmap m ON m.concept_id = CAST(o.refused_standard_concept_id AS VARCHAR)""",
        src="cmp.omop_drug o WHERE o.refused_standard_concept_id IS NOT NULL",
        keep=[("refused concept not in the Athena bundle", "CAST(o.refused_standard_concept_id AS VARCHAR) IN (SELECT concept_id FROM cmap)")])
    ins("OMOP product -> standard drug (indirect)", f"""SELECT 'SCT', x.product_id, 'omop:maps_to_indirect', CASE m.vocabulary_id {vmap} END,
            m.concept_code, 'scripts/amt_indirect.py', 'omop_drug_indirect', x.route, 'ungraded', 'asserted', '{PIN['athena']}',
            json_object('level', x.level, 'via', x.via_product_id)
        FROM cmp.omop_drug_indirect x JOIN cmap m ON m.concept_id = CAST(x.standard_concept_id AS VARCHAR)""",
        src="cmp.omop_drug_indirect x WHERE x.standard_concept_id IS NOT NULL",
        keep=[("standard concept not in the Athena bundle", "CAST(x.standard_concept_id AS VARCHAR) IN (SELECT concept_id FROM cmap)")])

    # --- substance -> standard ingredient ---------------------------------------------------------------------------
    ins("substance -> standard ingredient", """SELECT 'SCT', substance_id, 'std_ingredient',
            CASE vocabulary WHEN 'RxNorm' THEN 'RXN' ELSE 'RXE' END, code, source, 'substance_standard_ingredient',
            split_part(source, ':', 1), CASE WHEN source LIKE 'route:%' THEN tier WHEN source = 'decision' THEN 'decision'
                                              ELSE 'ungraded' END,
            CASE WHEN state = 'asserted' THEN 'asserted' ELSE state END, '', json_object('check', "check")
        FROM cmp.substance_standard_ingredient""", src="cmp.substance_standard_ingredient")
    con.execute(f"UPDATE edge SET pin = '{PIN['athena']}' WHERE predicate = 'std_ingredient'")

    # --- ATC: PBS and OMOP as parallel edges -------------------------------------------------------------------------
    ins("product -> ATC (PBS and OMOP, parallel)", f"""SELECT 'SCT', product_id, 'in_atc_class', 'ATC', atc_code,
            CASE source WHEN 'pbs' THEN 'PBS item-atc' ELSE 'OMOP CONCEPT_ANCESTOR' END, 'product_atc',
            CASE source WHEN 'pbs' THEN 'native' ELSE 'omop ancestry' END, CASE source WHEN 'pbs' THEN 'native' ELSE 'ungraded' END,
            'asserted', CASE source WHEN 'pbs' THEN '{PIN['pbs']}' ELSE '{PIN['athena']}' END, json_object('atc_level', atc_level)
        FROM cmp.product_atc""", src="cmp.product_atc")

    # --- PBS: AMT -> item -> restriction -> indication ---------------------------------------------------------------
    rows = lambda f: f"(SELECT unnest(rows, recursive := true) FROM read_json_auto('{PBS}/{f}.json', maximum_object_size=300000000))"
    ins("AMT -> PBS item", f"""SELECT DISTINCT 'SCT', CAST(amt_code AS VARCHAR), 'pbs:lists', 'PBS_ITEM', split_part(li_item_id, '_', 1),
            'PBS API v3 amt-items', 'cache/pbs/amt-items.json', 'native', 'native', 'asserted', '{PIN['pbs']}',
            json_object('amt_level', concept_type_code) FROM {rows('amt-items')} WHERE amt_code IS NOT NULL""",
        src=rows('amt-items'), keep=[("no AMT code", "amt_code IS NOT NULL")])
    ins("PBS item -> restriction", f"""SELECT DISTINCT 'PBS_ITEM', pbs_code, 'pbs:has_restriction', 'PBS_RESTRICTION', res_code,
            'PBS API v3 item-restriction-relationships', 'cache/pbs/item-restriction-relationships.json', 'native', 'native',
            'asserted', '{PIN['pbs']}', json_object('benefit_type', benefit_type_code) FROM {rows('item-restriction-relationships')}""",
        src=rows('item-restriction-relationships'))
    con.execute(f"CREATE TEMP TABLE ind AS SELECT * FROM {rows('indications')}")
    ins("PBS restriction -> indication", f"""SELECT DISTINCT 'PBS_RESTRICTION', r.res_code, 'pbs:restricted_to', 'PBS_INDICATION',
            CAST(i.indication_prescribing_txt_id AS VARCHAR), 'PBS API v3 restriction-prescribing-text-relationships + indications',
            'cache/pbs/indications.json', 'native', 'native', 'asserted', '{PIN['pbs']}',
            json_object('severity', i.severity, 'episodicity', i.episodicity)
        FROM {rows('restriction-prescribing-text-relationships')} r
        JOIN ind i ON CAST(i.indication_prescribing_txt_id AS VARCHAR) = CAST(r.prescribing_text_id AS VARCHAR)""",
        src=f"{rows('restriction-prescribing-text-relationships')} r",
        keep=[("prescribing text is not an indication (a criterion, a note)",
               "CAST(r.prescribing_text_id AS VARCHAR) IN (SELECT CAST(indication_prescribing_txt_id AS VARCHAR) FROM ind)")])
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
            for r in pb if r.get("bound")],
            available=len(pb), excluded=[("not bound exactly: a candidate for a person (review queue pbs_indications)",
                                          sum(1 for r in pb if not r.get("bound")))], unit="indication texts")

    # --- corpus condition bindings ----------------------------------------------------------------------------------
    b = json.load(open(BINDINGS))["results"]
    ins_rows("corpus condition -> SNOMED", [("CORPUS", r["condition"], "corpus:binds_to", "SCT", r["snomed"]["concept_id"],
             "reference/snomed_bindings.json", r["condition"], r["snomed"].get("method"), "ungraded",
             "asserted", PIN["corpus"], json.dumps({"parent_verified": r["snomed"].get("parent_verified")}))
             for r in b if r.get("snomed")],
             available=len(b), excluded=[("not bound: a candidate (the binding review loop)", sum(1 for r in b if not r.get("snomed")))],
             unit="corpus conditions")
    con.executemany("INSERT INTO name_hint VALUES ('CORPUS', ?, ?)", [(r["condition"], r["condition"]) for r in b])

    # --- LOINC -------------------------------------------------------------------------------------------------------
    axis = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in LOINC_AXIS.items())
    ins("LOINC term -> axis part", f"""SELECT 'LOINC', code, CASE axis {axis} END, 'LOINC', part_code, 'LOINC via Athena',
            'spine.duckdb loinc_axis', 'native', 'native', 'asserted', '{PIN['loinc']}', NULL FROM sp.loinc_axis""", src="sp.loinc_axis")
    ins("LOINC question -> answer", f"""SELECT DISTINCT 'LOINC', question_code, 'loinc:has_answer', 'LOINC', answer_code, 'LOINC via Athena',
            'spine.duckdb loinc_answer', 'native', 'native', 'asserted', '{PIN['loinc']}', NULL FROM sp.loinc_answer""", src="sp.loinc_answer")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', code, concept_name FROM sp.loinc_omop")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', part_code, any_value(part_name) FROM sp.loinc_axis GROUP BY part_code")
    con.execute("INSERT INTO name_hint SELECT 'LOINC', answer_code, any_value(answer_name) FROM sp.loinc_answer GROUP BY answer_code")

    # --- LOINC -> SNOMED: the bridge out of LOINC's island (Athena places lab tests under SNOMED measurements) -----
    ins("LOINC -> SNOMED (Is a / Maps to)", f"""SELECT DISTINCT 'LOINC', l.concept_code,
            CASE r.relationship_id WHEN 'Is a' THEN 'loinc:is_a_snomed' ELSE 'loinc:maps_to_snomed' END, 'SCT', s.concept_code,
            'OMOP Athena', 'CONCEPT_RELATIONSHIP', r.relationship_id, 'ungraded', 'asserted', '{PIN['athena']}', NULL
        FROM CR r JOIN C l ON l.concept_id = r.concept_id_1 AND l.vocabulary_id = 'LOINC'
        JOIN C s ON s.concept_id = r.concept_id_2 AND s.vocabulary_id = 'SNOMED'
        WHERE r.relationship_id IN ('Is a', 'Maps to', 'Maps to value') AND (r.invalid_reason IS NULL OR r.invalid_reason = '')""",
        src="CR r JOIN C l ON l.concept_id = r.concept_id_1 AND l.vocabulary_id = 'LOINC'",
        keep=[("another relationship (not Is a / Maps to / Maps to value)", "r.relationship_id IN ('Is a', 'Maps to', 'Maps to value')"),
              ("relationship retired (invalid_reason)", "r.invalid_reason IS NULL OR r.invalid_reason = ''"),
              ("target not a SNOMED concept", "r.concept_id_2 IN (SELECT concept_id FROM C WHERE vocabulary_id = 'SNOMED')")],
        unit="Athena relationships from a LOINC concept")

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
            FROM {ext(T / 'sct2_Relationship_Snapshot_LO1010000_20260321.txt')} WHERE active = '1'""",
            src=ext(T / 'sct2_Relationship_Snapshot_LO1010000_20260321.txt'), keep=[("inactive relationship", "active = '1'")])
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
            WHERE i.active = '1' AND i.identifierSchemeId = '30051010000102'""",
            src=f"{ext(T / 'sct2_Identifier_Snapshot_LO1010000_20260321.txt')} i WHERE i.identifierSchemeId = '30051010000102'",
            keep=[("inactive identifier", "i.active = '1'")])
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
            rcpa_rows, skip_u = json.load(open(RCPA_UNITS))["rows"], collections.Counter()
            for x in rcpa_rows:
                ucum = (x["ucum"] or "").strip()
                if not ucum or ucum.lower() == "no unit":
                    skip_u["RCPA states no unit"] += 1
                    continue
                if (x["loinc"], ucum) in seen:
                    skip_u["the same code and unit in another RCPA set"] += 1
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
            ins_rows("LOINC -> Australian preferred unit (RCPA SPIA)", rows_u, available=len(rcpa_rows), excluded=sorted(skip_u.items()),
                     unit="RCPA SPIA rows")
        if UNIT_PAIRS.exists():
            def au_side(c):
                a, b = c["mass_loinc"] in rcpa_codes, c["molar_loinc"] in rcpa_codes
                return "both" if a and b else "mass" if a else "molar" if b else None
            ins_rows("LOINC mass <-> molar unit counterpart", [
                ("LOINC", c["mass_loinc"], "loinc:unit_counterpart", "LOINC", c["molar_loinc"], "LOINC 2.83 + PubChem",
                 "reference/loinc_unit_counterparts.json", "same axes, MCnc / SCnc", "native", "asserted", f"{PIN['loinc_table']}",
                 json.dumps({**{k: c[k] for k in ("factor_mg_per_dL_to_mmol_per_L", "molecular_weight", "pubchem_cid", "analyte_code",
                                                  "mass_unit_example", "molar_unit_example")}, "au_preferred": au_side(c)}))
                for c in json.load(open(UNIT_PAIRS))["counterparts"]], available=len(json.load(open(UNIT_PAIRS))["counterparts"]),
                unit="counterpart pairs (scripts/unit_reconcile.py)")
        if LOINC_TABLE.exists():
            # LOINC's own example unit (US convention) for every active term that states one -- the unit edge for the tens of
            # thousands of terms no RCPA set covers, clinical and survey terms among them. An example, not a rule: the
            # Australian preferred unit stays loinc:au_preferred_unit. "mg/dL;mg/L" is two example units, split.
            lt_ = f"read_csv('{LOINC_TABLE}', header=true, all_varchar=true)"
            ins("LOINC term -> example UCUM unit (LOINC)", f"""SELECT DISTINCT 'LOINC', LOINC_NUM, 'loinc:example_unit', 'UCUM', trim(u),
                    'LOINC 2.83', 'Loinc.csv EXAMPLE_UCUM_UNITS',
                    CASE WHEN contains(EXAMPLE_UCUM_UNITS, ';') THEN 'one of several example units' ELSE 'example unit' END,
                    'native', 'asserted', '{PIN['loinc_table']}', json_object('as_written', EXAMPLE_UCUM_UNITS)
                FROM (SELECT LOINC_NUM, STATUS, EXAMPLE_UCUM_UNITS, unnest(string_split(EXAMPLE_UCUM_UNITS, ';')) AS u FROM {lt_}
                      WHERE EXAMPLE_UCUM_UNITS IS NOT NULL) WHERE STATUS = 'ACTIVE' AND trim(u) <> ''""",
                src=f"{lt_} WHERE EXAMPLE_UCUM_UNITS IS NOT NULL", keep=[("LOINC term not active", "STATUS = 'ACTIVE'")],
                unit="LOINC terms that state an example unit")
        if RCPA_ELEMENTS.exists():
            # the SNOMED CT and LOINC codes the RCPA binds to the same data element of a structured cancer report
            # (scripts/rcpa_elements.py): the same report element, not the same concept -- a relation. One edge per pair,
            # the elements it binds in attrs; kept where the SNOMED code is active in SNOMED CT-AU.
            el = collections.defaultdict(list)
            el_rows = json.load(open(RCPA_ELEMENTS))["rows"]
            for x in el_rows:
                el[(x["loinc"], x["sct"])].append(x["element"])
            active = {r[0] for r in con.execute("SELECT id FROM cmp.concept WHERE id IN (SELECT unnest(?))", [[k[1] for k in el]]).fetchall()}
            ins_rows("LOINC <-> SNOMED CT bound to the same RCPA report element", [
                ("LOINC", l_, "rcpa:same_data_element", "SCT", s_, "RCPA SPIA", "anatomical pathology FHIR mappings", "same report data element",
                 "native", "asserted", RCPA_UNITS_PIN, json.dumps({"elements": sorted(set(v))}))
                for (l_, s_), v in sorted(el.items()) if s_ in active],
                available=len(el_rows), excluded=[("SNOMED code not active in SNOMED CT-AU", sum(len(v) for k, v in el.items() if k[1] not in active)),
                                                  ("the same pair on another report element (one edge, elements listed)",
                                                   sum(len(v) - 1 for k, v in el.items() if k[1] in active))],
                unit="RCPA element bindings (scripts/rcpa_elements.py)")

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
            WHERE t.tgt NOT IN (SELECT tgt FROM ix_refined)""",
            derived="LOINC observable (LOINC Extension) and a SNOMED finding's Interprets target share a Component; specimen at or below")

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
               OR (k.spec IS NULL AND EXISTS (SELECT 1 FROM ax_site_up su WHERE su.s = k.site AND su.n = '119297000'))""",
            derived="Athena's placement of a LOINC term under a SNOMED procedure that a finding Interprets; specimen agreeing")

    # --- MONDO -------------------------------------------------------------------------------------------------------
    if MONDO_OBO.exists():
        mt = obo_terms(MONDO_OBO)
        ins_rows("MONDO is-a", [("MONDO", t["id"], "mondo:is_a", "MONDO", p, "MONDO", "mondo.obo", "native", "native",
                                 "asserted", PIN["mondo"], None) for t in mt if t["id"].startswith("MONDO:") for p in t["is_a"]
                                if p.startswith("MONDO:")],
                 available=sum(len(t["is_a"]) for t in mt if t["id"].startswith("MONDO:")),
                 excluded=[("parent outside MONDO", sum(1 for t in mt if t["id"].startswith("MONDO:") for p in t["is_a"] if not p.startswith("MONDO:")))],
                 unit="is_a statements of MONDO classes")
        con.executemany("INSERT INTO name_hint VALUES ('MONDO', ?, ?)", [(t["id"], t.get("name")) for t in mt if t["id"].startswith("MONDO:")])
        con.executemany("INSERT INTO name_hint VALUES ('NCBITAXON', ?, ?)",      # the taxa MONDO cites carry their names in mondo.obo
                        [(t["id"].split(":", 1)[1], t.get("name")) for t in mt if t["id"].startswith("NCBITaxon:")])
        prefix = {"SCTID": "SCT", "ICD10CM": "ICD10CM", "OMIM": "OMIM", "Orphanet": "ORPHA",
                  # MONDO's other exact matches (MedDRA left out: MSSO-licensed)
                  "DOID": "DOID", "NCIT": "NCIT", "mesh": "MESH", "icd11.foundation": "ICD11", "EFO": "EFO", "UMLS": "UMLS",
                  "MEDGEN": "MEDGEN", "ICD10WHO": "ICD10WHO", "OMIMPS": "OMIMPS"}
        # an obsolete MONDO class keeps its mappings in the SSSOM file (1,790 of them carried 2,168 exact matches), and as
        # equivalences they joined a retired class to what replaced it -- found by scripts/consistency.py; only active
        # classes load
        live = {t["id"] for t in mt}
        ss_rows = list(csv.DictReader((l for l in open(MONDO_SSSOM) if not l.startswith("#")), delimiter="\t"))
        sssom_all = [r for r in ss_rows if r["predicate_id"] == "skos:exactMatch" and r["object_id"].split(":")[0] in prefix]
        ss_exc = [("not an exactMatch (broad, narrow, close, related)", sum(r["predicate_id"] != "skos:exactMatch" for r in ss_rows)),
                  ("exactMatch to a vocabulary not loaded (MedDRA: MSSO-licensed; others)",
                   sum(r["predicate_id"] == "skos:exactMatch" and r["object_id"].split(":")[0] not in prefix for r in ss_rows))]
        sssom = [r for r in sssom_all if r["subject_id"] in live]
        log["MONDO exactMatch: not loaded, obsolete MONDO class"] = len(sssom_all) - len(sssom)
        con.executemany("INSERT INTO name_hint VALUES (?, ?, ?)",
                        [("MONDO", r["subject_id"], r.get("subject_label")) for r in sssom] +
                        [(prefix[r["object_id"].split(":")[0]], r["object_id"].split(":", 1)[1], r.get("object_label")) for r in sssom
                         if prefix[r["object_id"].split(":")[0]] != "SCT"])   # SNOMED names come from the SNOMED CT-AU release
        ins_rows("MONDO exactMatch -> SNOMED / ICD-10-CM / OMIM / Orphanet / DOID / NCIT / MeSH / ICD-11 / EFO / UMLS / MedGen / ICD-10",
                 [("MONDO", r["subject_id"], "mondo:exact_match", prefix[r["object_id"].split(":")[0]], r["object_id"].split(":", 1)[1],
                   "MONDO SSSOM", "mondo.sssom.tsv", r.get("mapping_justification"), "ungraded", "asserted", PIN["mondo"], None)
                  for r in sssom], available=len(ss_rows), excluded=ss_exc + [("obsolete MONDO class", len(sssom_all) - len(sssom))],
                 unit="MONDO SSSOM rows")

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
        FROM m""", src="C s JOIN CR r ON r.concept_id_1 = s.concept_id WHERE s.vocabulary_id = 'ICD10CM'",
        keep=[("another relationship (not Maps to; 'Maps to value' means something else)", "r.relationship_id = 'Maps to'"),
              ("relationship retired (invalid_reason)", "r.invalid_reason IS NULL OR r.invalid_reason = ''"),
              ("target not a SNOMED concept", "r.concept_id_2 IN (SELECT concept_id FROM C WHERE vocabulary_id = 'SNOMED')")],
        unit="Athena relationships from an ICD-10-CM code")

    # --- HPO ---------------------------------------------------------------------------------------------------------
    if HP_OBO.exists():
        ht = obo_terms(HP_OBO)
        ins_rows("HPO is-a", [("HP", t["id"], "hp:is_a", "HP", p, "HPO", "hp.obo", "native", "native", "asserted", PIN["hpo"], None)
                              for t in ht if t["id"].startswith("HP:") for p in t["is_a"] if p.startswith("HP:")],
                 available=sum(len(t["is_a"]) for t in ht if t["id"].startswith("HP:")),
                 excluded=[("parent outside HPO", sum(1 for t in ht if t["id"].startswith("HP:") for p in t["is_a"] if not p.startswith("HP:")))],
                 unit="is_a statements of HPO terms")
        con.executemany("INSERT INTO name_hint VALUES ('HP', ?, ?)", [(t["id"], t.get("name")) for t in ht])
        hx = {"NCIT": "NCIT", "ORPHA": "ORPHA", "ICD-10": "ICD10WHO"}      # HPO's own xrefs (MedDRA left out: MSSO-licensed)
        ins_rows("HPO xref -> NCIT / Orphanet / ICD-10", sorted({("HP", t["id"], "hp:xref", hx[x.split(":")[0]], x.split(":", 1)[1], "HPO",
                                                                  "hp.obo xref", x.split(":")[0], "native", "asserted", PIN["hpo"], None)
                                                                 for t in ht if t["id"].startswith("HP:") for x in t["xref"]
                                                                 if x.split(":")[0] in hx}),
                 available=sum(len(t["xref"]) for t in ht if t["id"].startswith("HP:")),
                 excluded=[("xref to a vocabulary not loaded (MedDRA: MSSO-licensed; UMLS, SNOMED CT US, MeSH ... by other routes)",
                            sum(1 for t in ht if t["id"].startswith("HP:") for x in t["xref"] if x.split(":")[0] not in hx))],
                 unit="xref statements of HPO terms")
    if HPOA.exists():
        dbv = {"OMIM": "OMIM", "ORPHA": "ORPHA", "DECIPHER": "DECIPHER"}
        rows_h, names, n_h, skip_h = [], {}, 0, collections.Counter()
        for r in csv.DictReader((l for l in open(HPOA, encoding="utf-8") if not l.startswith("#")), delimiter="\t"):
            n_h += 1
            if r["aspect"] != "P":
                skip_h["not a phenotype annotation (inheritance, onset, clinical course)"] += 1
                continue
            v, code = r["database_id"].split(":", 1)
            if v not in dbv:
                skip_h[f"disease vocabulary not loaded"] += 1
                continue
            names[(dbv[v], code)] = r["disease_name"]
            rows_h.append((dbv[v], code, "hpo:lacks_phenotype" if r["qualifier"] == "NOT" else "hpo:has_phenotype", "HP", r["hpo_id"],
                           "HPO annotations", r["reference"], r["evidence"], "native", "asserted", PIN["hpo"],
                           json.dumps({k: r[k] for k in ("frequency", "onset", "sex", "modifier") if r[k]})))
        ins_rows("HPO disease -> phenotype (present / absent)", rows_h, available=n_h, excluded=sorted(skip_h.items()),
                 unit="phenotype.hpoa annotations")
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
                json_object('id_rxcui', identifier, 'id_class', id_class, 'lifted_via', via) FROM dc_rx""",
            src=f"(SELECT DISTINCT struct_id, identifier FROM {dc('identifier')} WHERE id_type = 'RXNORM') i",
            keep=[("RxNorm id not in the Athena bundle, or not liftable to a standard ingredient",
                   "(struct_id, identifier) IN (SELECT struct_id, identifier FROM dc_rx)")], unit="DrugCentral RXNORM identifiers")
        ins("DrugCentral -> SNOMED", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:snomed', 'SCT', identifier, 'DrugCentral',
                'identifier', 'SNOMEDCT_US', 'ungraded', 'asserted', '{PIN['dc']}', NULL FROM {dc('identifier')} WHERE id_type = 'SNOMEDCT_US'""",
            src=f"{dc('identifier')} WHERE id_type = 'SNOMEDCT_US'")
        dx = {"CHEBI": "CHEBI", "UNII": "UNII", "PUBCHEM_CID": "PUBCHEM", "ChEMBL_ID": "CHEMBL", "MESH_DESCRIPTOR_UI": "MESH",
              "MESH_SUPPLEMENTAL_RECORD_UI": "MESH", "UMLSCUI": "UMLS", "IUPHAR_LIGAND_ID": "IUPHAR", "KEGG_DRUG": "KEGG", "INN_ID": "INN"}
        dcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in dx.items())
        ins("DrugCentral -> ChEBI / UNII / PubChem / ChEMBL / MeSH / UMLS / IUPHAR / KEGG / INN", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id,
                'drugcentral:xref', CASE id_type {dcase} END, replace(identifier, 'CHEBI:', ''), 'DrugCentral', 'identifier', id_type,
                'native', 'asserted', '{PIN['dc']}', NULL
            FROM {dc('identifier')} WHERE id_type IN ({','.join(repr(k) for k in dx)}) AND trim(coalesce(identifier, '')) <> ''""",
            src=f"{dc('identifier')} WHERE id_type IN ({','.join(repr(k) for k in dx)})",
            keep=[("empty identifier", "trim(coalesce(identifier, '')) <> ''")])
        if (DC / "pharma_class.tsv").exists():
            # the FDA's own pharmacologic class indexing of approved labels (SPL), relayed by DrugCentral; its classes
            # are MED-RT concepts (N-codes), so this is a label-grade route to the same class nodes MED-RT reaches
            ins("DrugCentral drug -> FDA pharmacologic class (EPC, MoA, PE; MED-RT codes)", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id,
                    'fda:pharmacologic_class', 'MEDRT', class_code, 'FDA SPL pharmacologic class indexing (via DrugCentral)', 'pharma_class',
                    type, 'native', 'asserted', '{PIN['dc']}', json_object('class_type', type, 'class_name', name)
                FROM {dc('pharma_class')} WHERE source = 'FDA' AND type IN ('EPC', 'MoA', 'PE') AND class_code LIKE 'N%'""",
                src=f"{dc('pharma_class')} WHERE source = 'FDA'",
                keep=[("another class type (not EPC, MoA, PE)", "type IN ('EPC', 'MoA', 'PE')"), ("class code not a MED-RT N-code", "class_code LIKE 'N%'")])
            con.execute(f"""INSERT INTO name_hint SELECT 'MEDRT', class_code, any_value(name) FROM {dc('pharma_class')}
                            WHERE source = 'FDA' AND type IN ('EPC', 'MoA', 'PE') GROUP BY 2""")
        if (DC / "struct2atc.tsv").exists():
            ins("DrugCentral -> ATC", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:in_atc_class', 'ATC', atc_code, 'DrugCentral',
                    'struct2atc', 'native', 'native', 'asserted', '{PIN['dc']}', NULL FROM {dc('struct2atc')}""", src=dc('struct2atc'))
        if (DC / "omop_relationship.tsv").exists():
            rel = {"indication": "drugcentral:indication", "contraindication": "drugcentral:contraindication",
                   "off-label use": "drugcentral:off_label_use"}
            when = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in rel.items())
            ins("DrugCentral drug -> condition (label)", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, CASE relationship_name {when} END, 'SCT',
                    snomed_conceptid, 'DrugCentral', 'omop_relationship', relationship_name, 'native', 'asserted', '{PIN['dc']}',
                    json_object('umls_cui', umls_cui, 'concept_name', concept_name)
                FROM {dc('omop_relationship')} WHERE snomed_conceptid IS NOT NULL AND snomed_conceptid <> ''
                  AND relationship_name IN ({','.join(repr(k) for k in rel)})""", src=dc('omop_relationship'),
                keep=[("another relationship (not indication, contraindication, off-label use)", f"relationship_name IN ({','.join(repr(k) for k in rel)})"),
                      ("no SNOMED concept", "snomed_conceptid IS NOT NULL AND snomed_conceptid <> ''")])
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
                LEFT JOIN dc_wit w ON w.act_id = a.act_id AND a.moa = '1'""", src=dc('act_table_full'))
            ins("DrugCentral target -> protein component", f"""SELECT DISTINCT 'DC_TARGET', t.target_id, 'drugcentral:target_component',
                    'UNIPROT', c.accession, 'DrugCentral', 'td2tc + target_component', 'native', 'native', 'asserted', '{PIN['dc']}',
                    json_object('organism', c.organism, 'swissprot', c.swissprot)
                FROM {dc('td2tc')} t JOIN {dc('target_component')} c ON c.id = t.component_id
                WHERE c.accession IS NOT NULL AND c.accession <> ''""",
                src=f"{dc('td2tc')} t JOIN {dc('target_component')} c ON c.id = t.component_id",
                keep=[("no UniProt accession", "c.accession IS NOT NULL AND c.accession <> ''")])
            ins("protein -> gene (DrugCentral)", f"""SELECT DISTINCT 'UNIPROT', accession, 'uniprot:encoded_by', 'NCBIGENE', geneid,
                    'DrugCentral', 'target_component', 'native', 'native', 'asserted', '{PIN['dc']}',
                    json_object('gene_symbol', gene, 'organism', organism)
                FROM {dc('target_component')} WHERE geneid IS NOT NULL AND geneid <> '' AND accession IS NOT NULL AND accession <> ''
                  AND id IN (SELECT component_id FROM {dc('td2tc')})""",   # target proteins only, not DrugCentral's whole protein list
                src=f"{dc('target_component')} WHERE id IN (SELECT component_id FROM {dc('td2tc')})",
                keep=[("no NCBI Gene id", "geneid IS NOT NULL AND geneid <> ''"), ("no UniProt accession", "accession IS NOT NULL AND accession <> ''")])
            con.execute(f"""INSERT INTO name_hint SELECT 'DC_TARGET', id, name FROM {dc('target_dictionary')}""")
            con.execute(f"""INSERT INTO name_hint SELECT 'UNIPROT', accession, any_value(name) FROM {dc('target_component')} GROUP BY 2""")
            con.execute(f"""INSERT INTO name_hint SELECT 'NCBIGENE', geneid, any_value(gene) FROM {dc('target_component')}
                            WHERE geneid IS NOT NULL AND geneid <> '' GROUP BY 2""")

    # --- Medicare Benefits Schedule: items, groups, categories (no SNOMED map exists; candidates are not edges) ------
    if MBS_XML.exists():
        import xml.etree.ElementTree as ET
        mbs_all = [{c.tag: (c.text or "").strip() for c in d} for d in ET.parse(MBS_XML).getroot().iter("Data")]
        mbs = [m for m in mbs_all if not m.get("ItemEndDate")]
        ins_rows("MBS item -> group -> category", [
            ("MBS", m["ItemNum"], "mbs:in_group", "MBS_GROUP", f"{m['Category']}/{m['Group']}", "MBS XML", MBS_XML.name, "native", "native",
             "asserted", PIN["mbs"], json.dumps({"schedule_fee": m.get("ScheduleFee") or None, "benefit_100": m.get("Benefit100") or None,
                                               "item_type": m.get("ItemType"), "fee_type": m.get("FeeType"),
                                               "item_start": m.get("ItemStartDate"), "fee_start": m.get("FeeStartDate")}))
            for m in mbs] + sorted({("MBS_GROUP", f"{m['Category']}/{m['Group']}", "mbs:group_in_category", "MBS_CATEGORY", m["Category"],
                                     "MBS XML", MBS_XML.name, "native", "native", "asserted", PIN["mbs"], None) for m in mbs}),
                 available=len(mbs_all), excluded=[("item ended (ItemEndDate)", len(mbs_all) - len(mbs))],
                 unit="MBS items (the group -> category edges show as fanned out)")
        con.executemany("INSERT INTO name_hint VALUES ('MBS', ?, ?)",
                        [(m["ItemNum"], re.sub(r"\s+", " ", m["Description"])[:160]) for m in mbs])
        cat_names = {"1": "Professional attendances", "2": "Diagnostic procedures and investigations", "3": "Therapeutic procedures",
                     "4": "Oral and maxillofacial services", "5": "Diagnostic imaging services", "6": "Pathology services",
                     "7": "Cleft lip and cleft palate services", "8": "Miscellaneous services", "10": "Dental services"}
        con.executemany("INSERT INTO name_hint VALUES ('MBS_CATEGORY', ?, ?)", list(cat_names.items()))
        con.executemany("INSERT INTO name_hint VALUES ('MBS_GROUP', ?, ?)", sorted({(f"{m['Category']}/{m['Group']}", f"Group {m['Group']}") for m in mbs}))
        # PBS restrictions that require an MBS service say so by item number ("... the medical service as described in item
        # 14249 of the Medicare Benefits Schedule"): the only code-to-code link MBS has outside itself.
        res_path = PBS / "restrictions.json"
        if res_path.exists():
            live = {m["ItemNum"] for m in mbs}
            cite = re.compile(r"\bitems?\s+((?:\d{2,6}(?:\s*,\s*|\s+(?:and|or|to)\s+|\s*)?)+?)\s*of the Medicare Benefits Schedule", re.I)
            rows_c, n_cited, dead = [], 0, 0
            for r in json.load(open(res_path))["rows"]:
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (r.get("li_html_text") or "") + " " + (r.get("schedule_html_text") or "")))
                for item in sorted({n for mt in cite.finditer(text) for n in re.findall(r"\d+", mt.group(1))}):
                    n_cited += 1
                    if item not in live:
                        dead += 1
                        continue
                    rows_c.append(("PBS_RESTRICTION", r["res_code"], "pbs:cites_mbs_item", "MBS", item, "PBS Public API v3",
                                   "restrictions.json " + r["res_code"], "restriction text: item N of the Medicare Benefits Schedule",
                                   "native", "asserted", PIN["pbs"], None))
            ins_rows("PBS restriction -> MBS item it cites", rows_c, available=n_cited,
                     excluded=[("item number not an active MBS item", dead)], unit="MBS item numbers cited in PBS restriction text")

    # --- anatomy and organisms: Uberon, MONDO's locations and agents, SNOMED organism <-> NCBI Taxonomy ---------------
    if UBERON_OBO.exists():
        terms, cur = [], None
        for line in open(UBERON_OBO, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("["):
                cur = {"is_a": [], "part_of": [], "mesh": []} if line == "[Term]" else None
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
                elif k == "xref" and v_.startswith("MESH:"):
                    cur["mesh"].append(v_.split(" ")[0][5:])
        ub = [t for t in terms if t.get("id", "").startswith("UBERON:") and not t.get("obsolete")]
        ub_all = [t for t in terms if t.get("id", "").startswith("UBERON:")]
        ub_n = lambda ts, f=lambda o: True: sum(1 for t in ts for k in ("is_a", "part_of") for o in t[k] if f(o))
        ins_rows("Uberon is-a / part-of", [("UBERON", t["id"], pred, "UBERON", o, "Uberon", "uberon-basic.obo", "native", "native", "asserted",
                                             PIN["uberon"], None)
                                            for t in ub for pred, key in (("uberon:is_a", "is_a"), ("uberon:part_of", "part_of"))
                                            for o in t[key] if o.startswith("UBERON:")],
                 available=ub_n(ub_all), excluded=[("obsolete Uberon class", ub_n([t for t in ub_all if t.get("obsolete")])),
                                                   ("target outside Uberon (a CL cell type, a GO process ...)", ub_n(ub, lambda o: not o.startswith("UBERON:")))],
                 unit="is_a / part_of statements of Uberon classes")
        con.executemany("INSERT INTO name_hint VALUES ('UBERON', ?, ?)", [(t["id"], t.get("name")) for t in ub])
        # Uberon's own cross-references to MeSH descriptors: a database xref, which Uberon does not grade as an exact match.
        mesh_ok = lambda m: re.fullmatch(r"[DC]\d+", m) is not None
        n_mesh = sum(len(t["mesh"]) for t in ub_all)
        ins_rows("Uberon -> MeSH (xref)", [("UBERON", t["id"], "uberon:mesh_xref", "MESH", m, "Uberon", "uberon-basic.obo xref",
                                            "database cross-reference", "native", "asserted", PIN["uberon"], None)
                                           for t in ub for m in sorted(set(t["mesh"])) if mesh_ok(m)],
                 available=n_mesh, excluded=[("obsolete Uberon class", sum(len(t["mesh"]) for t in ub_all if t.get("obsolete"))),
                                             ("not a MeSH descriptor id", sum(1 for t in ub for m in t["mesh"] if not mesh_ok(m)))],
                 unit="MESH xrefs of Uberon classes")
    if UBERON_SSSOM.exists():
        ss = [r for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
              if r["object_id"].startswith("SCTID:") and r["subject_id"].startswith("UBERON:")]
        ins_rows("Uberon -> SNOMED body structure (narrowMatch)", [
            ("UBERON", r["subject_id"], "uberon:sct_narrow_match", "SCT", r["object_id"].split(":", 1)[1], "Uberon SSSOM", "uberon.sssom.tsv",
             r["predicate_id"], "ungraded", "asserted", PIN["uberon"], json.dumps({"mapping_justification": r.get("mapping_justification")}))
            for r in ss if r["predicate_id"] == "skos:narrowMatch"],
            available=len(ss), excluded=[("not a narrowMatch", sum(r["predicate_id"] != "skos:narrowMatch" for r in ss))],
            unit="Uberon SSSOM rows to SNOMED CT")
        ins_rows("Uberon -> NCI Thesaurus anatomy (narrowMatch)", [
            ("UBERON", r["subject_id"], "uberon:ncit_narrow_match", "NCIT", r["object_id"].split(":", 1)[1], "Uberon SSSOM", "uberon.sssom.tsv",
             r["predicate_id"], "native", "asserted", PIN["uberon"], None)
            for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
            if r["subject_id"].startswith("UBERON:") and r["object_id"].startswith("NCIT:") and r["predicate_id"] == "skos:narrowMatch"],
            available=len(un := [r for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
                                 if r["subject_id"].startswith("UBERON:") and r["object_id"].startswith("NCIT:")]),
            excluded=[("not a narrowMatch", sum(r["predicate_id"] != "skos:narrowMatch" for r in un))], unit="Uberon SSSOM rows to NCIt")
    if MONDO_OBO.exists():
        rows_m, cur, obs = [], None, False
        rows_g, rows_f, rows_x = [], [], []        # causal gene; phenotype feature; annotated xrefs beyond the exact matches
        skip_x, skip_g = collections.Counter(), collections.Counter()
        # MONDO says how each xref relates in its source annotation; the exact ones are the SSSOM file's (loaded apart)
        xmap = {"GARD": "GARD", "HP": "HP", "SCTID": "SCT", "ICD10CM": "ICD10CM", "NCIT": "NCIT", "MESH": "MESH", "Orphanet": "ORPHA",
                "OMIM": "OMIM", "DOID": "DOID", "ICDO": "ICDO"}
        for line in open(MONDO_OBO, encoding="utf-8"):
            line = line.rstrip("\n")
            if line == "[Term]" or (line.startswith("[") and line.endswith("]")):
                cur, obs = None, False
            elif line.startswith("id: "):
                cur = line[4:]
            elif line == "is_obsolete: true":
                obs = True
            elif line.startswith("relationship: ") and cur and cur.startswith("MONDO:") and not obs:
                parts = line[14:].split(" ")
                if parts[0] == "disease_has_location" and parts[1].startswith("UBERON:"):
                    rows_m.append(("MONDO", cur, "mondo:disease_has_location", "UBERON", parts[1]))
                elif parts[0] == "disease_has_infectious_agent" and parts[1].startswith("NCBITaxon:"):
                    rows_m.append(("MONDO", cur, "mondo:disease_has_infectious_agent", "NCBITAXON", parts[1].split(":", 1)[1]))
                elif parts[0] == "has_material_basis_in_germline_mutation_in":
                    g = parts[1]
                    if "/hgnc/" in g:
                        rows_g.append(("MONDO", cur, "mondo:germline_gene", "HGNC", "HGNC:" + g.rsplit("/", 1)[1], parts[0]))
                    elif "/ncbigene/" in g:          # MONDO's veterinary diseases (OMIA): a dog's KIT, not a human gene
                        skip_g["an NCBI Gene id: a non-human gene (OMIA veterinary disease); human genes are HGNC"] += 1
                elif parts[0] in ("disease_has_feature", "disease_has_major_feature", "has_characteristic") and parts[1].startswith("HP:"):
                    rows_f.append(("MONDO", cur, "mondo:has_feature", "HP", parts[1], parts[0]))
            elif line.startswith("xref: ") and cur and cur.startswith("MONDO:") and not obs:
                m_ = re.match(r"xref: ([A-Za-z0-9_.]+):(\S+)(?: \{(.*)\})?$", line)
                if not m_ or m_.group(1) not in xmap:
                    continue
                pre, code, how = m_.group(1), m_.group(2), set(re.findall(r'source="MONDO:([A-Za-z]+)', m_.group(3) or ""))
                v = xmap[pre]
                code = str(int(code)) if pre == "GARD" and code.isdigit() else ("HP:" + code) if pre == "HP" else code
                if how & {"equivalentTo", "obsoleteEquivalent", "obsoleteEquivalentObsolete", "ObsoleteEquivalent", "obsolete", "Obsolete"}:
                    skip_x["an exact match (SSSOM, loaded apart) or on a class MONDO is retiring"] += 1
                elif pre == "GARD" and "GARD" in how:
                    rows_x.append(("MONDO", cur, "mondo:gard_xref", v, code, "MONDO:GARD"))
                elif pre == "HP" and "otherHierarchy" in how:
                    rows_x.append(("MONDO", cur, "mondo:other_hierarchy", v, code, "MONDO:otherHierarchy"))
                elif "equivalentObsolete" in how:
                    rows_x.append(("MONDO", cur, "mondo:obsolete_equivalent", v, code, "MONDO:equivalentObsolete"))
                elif how & {"relatedTo", "mondoIsNarrowerThanSource", "mondoIsBroaderThanSource"} and v in ("SCT", "ICD10CM", "NCIT", "MESH"):
                    rows_x.append(("MONDO", cur, "mondo:related_xref", v, code, "MONDO:" + sorted(how & {"relatedTo", "mondoIsNarrowerThanSource",
                                                                                                          "mondoIsBroaderThanSource"})[0]))
                elif pre == "ICDO" and not how:
                    rows_x.append(("MONDO", cur, "mondo:icdo_xref", v, code, "unannotated ICD-O xref"))
                else:
                    skip_x["another annotation (a sibling, a finding, an alternative hierarchy)"] += 1
        ins_rows("MONDO disease -> location (Uberon) / infectious agent (NCBI Taxonomy)",
                 [r + ("MONDO", "mondo.obo", "native", "native", "asserted", PIN["mondo"], None) for r in sorted(set(rows_m))],
                 available=len(rows_m), unit="disease_has_location / disease_has_infectious_agent statements")
        ins_rows("MONDO disease -> causal gene (germline)", [r[:4] + (r[4], "MONDO", "mondo.obo relationship", r[5], "native", "asserted",
                                                                     PIN["mondo"], None) for r in sorted(set(rows_g))],
                 available=len(rows_g) + sum(skip_g.values()), excluded=sorted(skip_g.items()),
                 unit="has_material_basis_in_germline_mutation_in statements")
        ins_rows("MONDO disease -> HPO feature", [r[:5] + ("MONDO", "mondo.obo relationship", r[5], "native", "asserted", PIN["mondo"], None)
                                                  for r in sorted(set(rows_f))],
                 available=len(rows_f), unit="disease_has_feature / disease_has_major_feature / has_characteristic HP statements")
        ins_rows("MONDO disease -> GARD / HPO / related / obsolete / ICD-O (annotated xrefs)",
                 [r[:5] + ("MONDO", "mondo.obo xref", r[5], "native", "asserted", PIN["mondo"], None) for r in sorted(set(rows_x))],
                 available=len(rows_x) + sum(skip_x.values()), excluded=sorted(skip_x.items()),
                 unit="xrefs of live MONDO classes to GARD, HP, SNOMED, ICD-10-CM, NCIt, MeSH, Orphanet, OMIM, DOID, ICD-O")
    if LOINC_PARTS.exists():
        con.execute(f"CREATE TEMP VIEW lpm AS SELECT * FROM read_csv('{LOINC_PARTS}', header=true, all_varchar=true)")
        ins("SNOMED organism <-> NCBI Taxonomy (LOINC part asserts both)", f"""SELECT DISTINCT 'SCT', s.ExtCodeId, 'sct:ncbitaxon_equivalent',
                'NCBITAXON', t.ExtCodeId, 'LOINC 2.83 PartRelatedCodeMapping', 'part ' || s.PartNumber, 'LOINC part asserts both',
                'ungraded', 'asserted', '{PIN['loinc_table']}', json_object('loinc_part', s.PartNumber, 'part_name', s.PartName)
            FROM lpm s JOIN lpm t ON t.PartNumber = s.PartNumber AND t.ExtCodeSystem = 'https://www.ncbi.nlm.nih.gov/taxonomy'
                 AND t.Equivalence = 'equivalent'
            WHERE s.ExtCodeSystem = 'http://snomed.info/sct' AND s.Equivalence = 'equivalent'""",
            src="lpm s WHERE s.ExtCodeSystem = 'http://snomed.info/sct' AND s.Equivalence = 'equivalent'",
            keep=[("the part has no equivalent NCBI taxon", "s.PartNumber IN (SELECT PartNumber FROM lpm WHERE ExtCodeSystem = "
                   "'https://www.ncbi.nlm.nih.gov/taxonomy' AND Equivalence = 'equivalent')")], unit="LOINC parts equivalent to a SNOMED concept")
        con.execute("""INSERT INTO name_hint SELECT DISTINCT 'NCBITAXON', ExtCodeId, any_value(ExtCodeDisplayName) FROM lpm
                       WHERE ExtCodeSystem = 'https://www.ncbi.nlm.nih.gov/taxonomy' GROUP BY 2""")
    if LOINC_PARTS.exists() and LOINC_PARTLINK.exists():
        # term -> part links. lpl_primary: LoincPartLink_Primary (the six axes, plus the radiology and document-ontology
        # properties). lpl_enh: the analyte pieces LOINC's enriched linkages name beyond the axes -- SyntaxEnhancement's
        # analyte-core / numerator / divisor ("Urea nitrogen/Creatinine" -> urea nitrogen, creatinine) and
        # SemanticEnhancement's genes -- kept only where the term does not already link that part, so a simple term whose
        # core is its whole component gains nothing twice. Suffixes ("targeted mutation analysis") name no analyte.
        con.execute(f"""CREATE TEMP VIEW lpl_primary AS SELECT LoincNumber, PartNumber, PartTypeName, LinkTypeName, 'primary' AS f
            FROM read_csv('{LOINC_PARTLINK}', header=true, all_varchar=true)""")
        con.execute(f"""CREATE TEMP VIEW lpl_supp AS SELECT LoincNumber, PartNumber, PartTypeName, LinkTypeName, 'supplementary' AS f
            FROM read_csv('{LOINC_PARTLINK_SUPP}', header=true, all_varchar=true)
            WHERE LinkTypeName IN ('DetailedModel', 'SyntaxEnhancement', 'SemanticEnhancement') AND PartTypeName <> 'SUFFIX'"""
            if LOINC_PARTLINK_SUPP.exists() else
            "CREATE TEMP VIEW lpl_supp AS SELECT * FROM (SELECT ''::VARCHAR, ''::VARCHAR, ''::VARCHAR, ''::VARCHAR, ''::VARCHAR) "
            "t(LoincNumber, PartNumber, PartTypeName, LinkTypeName, f) WHERE false")
        con.execute("""CREATE TEMP VIEW lpl_enh AS SELECT e.* FROM lpl_supp e
            WHERE e.LinkTypeName IN ('SyntaxEnhancement', 'SemanticEnhancement')
              AND NOT EXISTS (SELECT 1 FROM lpl_primary p WHERE p.LoincNumber = e.LoincNumber AND p.PartNumber = e.PartNumber)
              AND NOT EXISTS (SELECT 1 FROM lpl_supp d WHERE d.LinkTypeName = 'DetailedModel' AND d.LoincNumber = e.LoincNumber
                              AND d.PartNumber = e.PartNumber)""")
        sct_links = ("(SELECT * FROM lpl_primary UNION ALL SELECT * FROM lpl_enh WHERE LinkTypeName = 'SyntaxEnhancement' "
                     "AND PartTypeName IN ('COMPONENT', 'DIVISOR', 'NUMERATOR'))")
        ins("LOINC term -> SNOMED via its component / system / method part", f"""SELECT DISTINCT 'LOINC', pl.LoincNumber, 'loinc:part_maps_to_sct',
                'SCT', pm.ExtCodeId, 'LOINC 2.83 part mapping', 'part ' || pl.PartNumber,
                CASE WHEN pl.f = 'primary' THEN pl.PartTypeName ELSE pl.LinkTypeName || ' ' || pl.PartTypeName END || ' ' || pm.Equivalence,
                'native', 'asserted', '{PIN['loinc_table']}',
                json_object('part_type', pl.PartTypeName, 'link_type', pl.LinkTypeName, 'part', pl.PartNumber, 'part_name', pm.PartName,
                            'equivalence', pm.Equivalence)
            FROM {sct_links} pl
            JOIN lpm pm ON pm.PartNumber = pl.PartNumber AND pm.ExtCodeSystem = 'http://snomed.info/sct'
            JOIN lx_loinc st ON st.LOINC_NUM = pl.LoincNumber AND st.STATUS = 'ACTIVE'
            WHERE pl.PartTypeName IN ('COMPONENT', 'SYSTEM', 'METHOD', 'DIVISOR', 'NUMERATOR') AND pm.PartName <> 'XXX'""",
            src=f"{sct_links} pl WHERE pl.PartTypeName IN ('COMPONENT', 'SYSTEM', 'METHOD', 'DIVISOR', 'NUMERATOR')",
            keep=[("the part has no SNOMED CT mapping", "pl.PartNumber IN (SELECT PartNumber FROM lpm WHERE ExtCodeSystem = 'http://snomed.info/sct' AND PartName <> 'XXX')"),
                  ("LOINC term not active", "pl.LoincNumber IN (SELECT LOINC_NUM FROM lx_loinc WHERE STATUS = 'ACTIVE')")],
            unit="LOINC term -> component / system / method part links, and analyte-core / numerator / divisor links")
    if LOINC_PARTS.exists() and LOINC_PARTLINK.exists():
        # what a lab test measures, in the analyte's own vocabularies: LOINC maps its component parts to ChEBI, RxNorm,
        # PubChem, UNII, NCBI Taxonomy, NCBI Gene, HGNC and ClinVar. RxNorm and NCBI Gene are vocabularies the drug and gene
        # sides already hold, so "serum vancomycin" meets vancomycin, and a genotype test its gene, with no matching at all.
        # Primary links (the term's own axis), DetailedModel links (the component decomposed), and the enriched analyte
        # links in lpl_enh: SyntaxEnhancement's analyte-core / numerator / divisor and SemanticEnhancement's genes, the only
        # route by which LOINC ties a genetic test to its gene parts. Search links are for finding terms, not for what a
        # term measures, and are not loaded.
        xs = {"https://www.ebi.ac.uk/chebi": "CHEBI", "http://www.nlm.nih.gov/research/umls/rxnorm": "RXN",
              "http://pubchem.ncbi.nlm.nih.gov": "PUBCHEM", "http://fdasis.nlm.nih.gov": "UNII",
              "https://www.ncbi.nlm.nih.gov/taxonomy": "NCBITAXON", "https://www.ncbi.nlm.nih.gov/gene": "NCBIGENE",
              "http://www.genenames.org": "HGNC", "https://www.ncbi.nlm.nih.gov/clinvar": "CLINVAR"}
        xcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in xs.items())
        links = ("SELECT LoincNumber, PartNumber, PartTypeName, LinkTypeName FROM lpl_primary"
                 " UNION SELECT LoincNumber, PartNumber, PartTypeName, LinkTypeName FROM lpl_supp WHERE LinkTypeName = 'DetailedModel'"
                 " UNION SELECT LoincNumber, PartNumber, PartTypeName, LinkTypeName FROM lpl_enh")
        ins("LOINC term -> analyte code (ChEBI / RxNorm / PubChem / UNII / taxon / gene / ClinVar)", f"""SELECT DISTINCT 'LOINC', pl.LoincNumber,
                'loinc:part_xref', CASE pm.ExtCodeSystem {xcase} END,
                CASE WHEN pm.ExtCodeSystem = 'http://www.genenames.org' THEN pm.ExtCodeId ELSE replace(pm.ExtCodeId, 'CHEBI:', '') END,
                'LOINC 2.83 part mapping', 'part ' || pl.PartNumber, pl.LinkTypeName || ' ' || pl.PartTypeName || ' ' || pm.Equivalence,
                'native', 'asserted', '{PIN['loinc_table']}',
                json_object('part_type', pl.PartTypeName, 'link_type', pl.LinkTypeName, 'part', pl.PartNumber, 'part_name', pm.PartName,
                            'equivalence', pm.Equivalence, 'ext_name', pm.ExtCodeDisplayName)
            FROM ({links}) pl JOIN lpm pm ON pm.PartNumber = pl.PartNumber
            JOIN lx_loinc st ON st.LOINC_NUM = pl.LoincNumber AND st.STATUS = 'ACTIVE'
            WHERE pm.ExtCodeSystem IN ({','.join(repr(k) for k in xs)}) AND pl.PartTypeName IN ('COMPONENT', 'DIVISORS', 'DIVISOR', 'NUMERATOR', 'GENE', 'CHALLENGE')""",
            src=f"({links}) pl WHERE pl.PartTypeName IN ('COMPONENT', 'DIVISORS', 'DIVISOR', 'NUMERATOR', 'GENE', 'CHALLENGE')",
            keep=[("the part has no code in an analyte vocabulary", f"pl.PartNumber IN (SELECT PartNumber FROM lpm WHERE ExtCodeSystem IN ({','.join(repr(k) for k in xs)}))"),
                  ("LOINC term not active", "pl.LoincNumber IN (SELECT LOINC_NUM FROM lx_loinc WHERE STATUS = 'ACTIVE')")],
            unit="LOINC term -> component / divisor / numerator / gene / challenge part links")
        con.execute(f"""INSERT INTO name_hint SELECT DISTINCT CASE ExtCodeSystem {xcase} END,
                CASE WHEN ExtCodeSystem = 'http://www.genenames.org' THEN ExtCodeId ELSE replace(ExtCodeId, 'CHEBI:', '') END,
                any_value(ExtCodeDisplayName) FROM lpm WHERE ExtCodeSystem IN ({','.join(repr(k) for k in xs if xs[k] not in ('RXN', 'NCBITAXON', 'NCBIGENE'))})
            GROUP BY 1, 2""")
        # the same mappings at the part itself: the part links above reach a code only through a term, so a part whose
        # terms are all inactive, and every part as a concept in its own right, stayed unlinked. Equivalence as LOINC states
        # it rides in method and attrs; relation, not identity: 'narrower' and 'wider' rows are not the same concept.
        pc = {**xs, "http://snomed.info/sct": "SCT", "http://www.radlex.org": "RADLEX"}
        pcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in pc.items())
        ins("LOINC part -> its code in another vocabulary", f"""SELECT DISTINCT 'LOINC', PartNumber, 'loinc:part_code', CASE ExtCodeSystem {pcase} END,
                CASE WHEN ExtCodeSystem = 'http://www.genenames.org' THEN ExtCodeId ELSE replace(ExtCodeId, 'CHEBI:', '') END,
                'LOINC 2.83 part mapping', 'PartRelatedCodeMapping', PartTypeName || ' ' || Equivalence, 'native', 'asserted', '{PIN['loinc_table']}',
                json_object('part_type', PartTypeName, 'part_name', PartName, 'equivalence', Equivalence, 'ext_name', ExtCodeDisplayName)
            FROM lpm WHERE ExtCodeSystem IN ({','.join(repr(k) for k in pc)}) AND PartName <> 'XXX'""",
            src="lpm", keep=[("target is not a graph vocabulary (a LOINC-to-LOINC row)", f"ExtCodeSystem IN ({','.join(repr(k) for k in pc)})"),
                             ("the unspecified part XXX", "PartName <> 'XXX'")],
            unit="PartRelatedCodeMapping rows")
        con.execute("INSERT INTO name_hint SELECT 'LOINC', PartNumber, any_value(PartName) FROM lpm GROUP BY 2")
    if LOINC_ANSWERS.exists():
        # LOINC's answer list gives some answers the SNOMED CT concept they are ("Small" LA8983-4 = 255507004 Small);
        # kept where that concept is active in SNOMED CT-AU.
        ans = f"read_csv('{LOINC_ANSWERS}', header=true, all_varchar=true)"
        ins("LOINC answer -> SNOMED CT (answer list external code)", f"""SELECT 'LOINC', AnswerStringId, 'loinc:answer_sct', 'SCT', ExtCodeId,
                'LOINC 2.83 AnswerList', 'AnswerList.csv', 'LOINC answer external code', 'native', 'asserted', '{PIN['loinc_table']}',
                json_object('answer', any_value(DisplayText), 'sct_name', any_value(ExtCodeDisplayName), 'answer_lists', count(DISTINCT AnswerListId))
            FROM {ans} WHERE ExtCodeSystem = 'http://snomed.info/sct' AND AnswerStringId IS NOT NULL
              AND ExtCodeId IN (SELECT id FROM cmp.concept) GROUP BY AnswerStringId, ExtCodeId""",
            src=f"(SELECT DISTINCT AnswerStringId, ExtCodeId, ExtCodeSystem FROM {ans} WHERE ExtCodeId IS NOT NULL)",
            keep=[("external code is not SNOMED CT", "ExtCodeSystem = 'http://snomed.info/sct'"),
                  ("SNOMED code not active in SNOMED CT-AU", "ExtCodeId IN (SELECT id FROM cmp.concept)")],
            unit="distinct answer -> external code pairs")
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
        ins_rows("SNOMED organism <-> NCBI Taxonomy (UMLS, same name)", rows_o, available=len(rows_o) + len(cands),
                 excluded=[("names differ: a candidate for a person (review queue organism_ncbi)", len(cands))], unit="UTS crosswalk rows")
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
        for lbl, pred, key in (("RadLex is-a", "radlex:is_a", "is_a"), ("RadLex part-of", "radlex:part_of", "part_of")):
            ins_rows(lbl, rsrc(pred, "RADLEX", key), available=sum(len(d[key]) for d in rl.values()),
                     excluded=[("target not a RadLex id", sum(1 for d in rl.values() for o in d[key] if not o.startswith("RID")))],
                     unit=f"RadLex {key} statements")
        ins_rows("RadLex -> FMA (ExternalRefID)", [("RADLEX", r, "radlex:fma_xref", "FMA", e[4:], "RadLex", "RadLex.owl ExternalRefID",
                                                    "native", "native", "asserted", PIN["radlex"], None)
                                                   for r, d in rl.items() for e in d["ext"] if e.startswith("FMA:")],
                 available=sum(len(d["ext"]) for d in rl.values()),
                 excluded=[("not an FMA id (UMLS CUIs feed the RadLex -> SNOMED routes below)",
                            sum(1 for d in rl.values() for e in d["ext"] if not e.startswith("FMA:")))], unit="RadLex ExternalRefIDs")
        ub_fma = [r for r in csv.DictReader((l for l in open(UBERON_SSSOM, encoding="utf-8") if not l.startswith("#")), delimiter="\t")
                  if r["subject_id"].startswith("UBERON:") and r["object_id"].startswith("FMA:")] if UBERON_SSSOM.exists() else []
        ins_rows("Uberon <-> FMA (cross-species exact match)", [
            ("UBERON", r["subject_id"], "uberon:fma_match", "FMA", r["object_id"][4:], "Uberon SSSOM", "uberon.sssom.tsv",
             r["predicate_id"], "native", "asserted", PIN["uberon"], None) for r in ub_fma], available=len(ub_fma),
            unit="Uberon SSSOM rows to FMA")
        ins("LOINC radiology term -> RadLex part (LOINC/RSNA playbook)", f"""SELECT DISTINCT 'LOINC', p.LoincNumber, 'loinc:radlex_part',
                'RADLEX', p.RID, 'LOINC 2.83 LoincRsnaRadiologyPlaybook', 'part ' || p.PartNumber, p.PartTypeName, 'native', 'asserted',
                '{PIN['loinc_table']}', json_object('part_type', p.PartTypeName, 'part', p.PartNumber, 'part_name', p.PartName)
            FROM read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p
            JOIN lx_loinc st ON st.LOINC_NUM = p.LoincNumber AND st.STATUS = 'ACTIVE' WHERE p.RID IS NOT NULL AND p.RID <> ''""",
            src=f"read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p",
            keep=[("no RadLex id", "p.RID IS NOT NULL AND p.RID <> ''"),
                  ("LOINC term not active", "p.LoincNumber IN (SELECT LOINC_NUM FROM lx_loinc WHERE STATUS = 'ACTIVE')")])
        ins("LOINC radiology term -> RSNA playbook procedure (RPID)", f"""SELECT DISTINCT 'LOINC', p.LoincNumber, 'loinc:rsna_rpid',
                'RPID', p.RPID, 'LOINC 2.83 LoincRsnaRadiologyPlaybook', 'RPID column', 'LOINC/RSNA harmonised', 'native', 'asserted',
                '{PIN['loinc_table']}', NULL
            FROM read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p
            JOIN lx_loinc st ON st.LOINC_NUM = p.LoincNumber AND st.STATUS = 'ACTIVE' WHERE p.RPID IS NOT NULL AND p.RPID <> ''""",
            src=f"read_csv('{LOINC_RSNA}', header=true, all_varchar=true) p",
            keep=[("no RSNA playbook id", "p.RPID IS NOT NULL AND p.RPID <> ''"),
                  ("LOINC term not active", "p.LoincNumber IN (SELECT LOINC_NUM FROM lx_loinc WHERE STATUS = 'ACTIVE')")])
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
                for r in live for c, rid in zip(cols[i0:], r["RIDS"].split("|")) if rid.startswith("RID") and c}),
                available=len(pb), excluded=[("playbook status neither ACTIVE nor TRIAL", len(pb) - len(live))],
                unit="playbook procedures (one edge per RadLex field: fanned out)")
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
        ins_rows("RadLex -> SNOMED CT body structure (three code routes)", sorted(rows_a.values()), excluded=sorted(dropped.items()),
                 derived="RadLex FMA / CUI -> Uberon or UMLS -> SNOMED CT; the SNOMED end must be an active body structure")
        for k, v in sorted(dropped.items()):
            log[f"RadLex -> SNOMED CT not loaded ({k})"] = v
        ins("LOINC radiology term -> SNOMED via its RadLex anatomy part", """SELECT DISTINCT 'LOINC', p.s_code, 'loinc:part_maps_to_sct',
                'SCT', a.o_code, 'LOINC 2.83 LoincRsnaRadiologyPlaybook + ' || a.source, 'part ' || json_extract_string(p.attrs, '$.part') || ' -> ' || p.o_code,
                'RadLex anatomy: ' || a.method, 'ungraded', 'asserted', a.pin,
                json_object('part_type', json_extract_string(p.attrs, '$.part_type'), 'part', json_extract_string(p.attrs, '$.part'),
                            'part_name', json_extract_string(p.attrs, '$.part_name'), 'rid', p.o_code, 'route', a.method)
            FROM edge p JOIN edge a ON a.predicate = 'radlex:anatomy_sct' AND a.s_code = p.o_code
            WHERE p.predicate = 'loinc:radlex_part' AND json_extract_string(p.attrs, '$.part_type') LIKE 'Rad.Anatomic Location.%'
              AND json_extract_string(p.attrs, '$.part_type') NOT LIKE '%Laterality%'""",
            derived="loinc:radlex_part (anatomic location, not laterality) -> radlex:anatomy_sct")
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
            WHERE split_part(disease_id, ':', 1) IN ('OMIM', 'ORPHA')""",
            src=f"read_csv('{HP_GENES}', delim='\t', header=true, all_varchar=true, quote='')",
            keep=[("disease vocabulary not loaded (not OMIM, Orphanet)", "split_part(disease_id, ':', 1) IN ('OMIM', 'ORPHA')")])
        con.execute(f"""INSERT INTO name_hint SELECT 'NCBIGENE', split_part(ncbi_gene_id, ':', 2), any_value(gene_symbol)
            FROM read_csv('{HP_GENES}', delim='\t', header=true, all_varchar=true, quote='') GROUP BY 2""")

    # --- HGNC: the human gene's official identity, joining NCBI Gene, UniProt and OMIM ------------------------------
    if HGNC_SET.exists():
        hg_all = list(csv.DictReader(open(HGNC_SET, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
        hg = [r for r in hg_all if r["status"] == "Approved"]
        # only genes something else in the graph already names (a disease gene, a drug target, a LOINC genotype test, a
        # Reactome participant): the other ~31,000 HGNC genes -- mostly non-coding RNAs and pseudogenes -- would each be a
        # detached cluster of their own ids, joining nothing
        present = {(v, c) for v, c in con.execute("""SELECT DISTINCT o_vocab, o_code FROM edge WHERE o_vocab IN ('NCBIGENE', 'UNIPROT', 'OMIM', 'HGNC')
                                                     UNION SELECT DISTINCT s_vocab, s_code FROM edge WHERE s_vocab IN ('NCBIGENE', 'UNIPROT', 'OMIM', 'HGNC')""").fetchall()}
        if (REACTOME / "UniProt2Reactome.txt").exists():
            present |= {("UNIPROT", l.split("\t", 1)[0]) for l in open(REACTOME / "UniProt2Reactome.txt", encoding="utf-8") if "\tHomo sapiens" in l}
        ids_of = lambda r: [("HGNC", r["hgnc_id"])] + [(vv, x.strip()) for col, vv in (("entrez_id", "NCBIGENE"), ("uniprot_ids", "UNIPROT"),
                                                                                    ("omim_id", "OMIM")) for x in filter(None, (r.get(col) or "").split("|"))]
        n_all = len(hg)
        hg = [r for r in hg if any(k in present for k in ids_of(r))]
        log["HGNC genes not loaded (no id shared with the rest of the graph)"] = n_all - len(hg)
        rows_g = []
        for r in hg:
            for col, vocab in (("entrez_id", "NCBIGENE"), ("uniprot_ids", "UNIPROT"), ("omim_id", "OMIM")):
                for v in filter(None, (r.get(col) or "").split("|")):
                    rows_g.append(("HGNC", r["hgnc_id"], "hgnc:xref", vocab, v.strip(), "HGNC", "hgnc_complete_set.txt " + col, col,
                                   "native", "asserted", PIN["hgnc"], None))
        ins_rows("HGNC gene -> NCBI Gene / UniProt / OMIM gene entry", sorted(set(rows_g)), available=len(hg_all),
                 excluded=[("not an approved symbol (entry withdrawn)", len(hg_all) - n_all),
                           ("no id shared with the rest of the graph", n_all - len(hg))],
                 unit="HGNC entries (one edge per NCBI Gene / UniProt / OMIM id: fanned out)")
        con.executemany("INSERT INTO name_hint VALUES ('HGNC', ?, ?)", [(r["hgnc_id"], r["symbol"]) for r in hg])
        con.executemany("INSERT INTO name_hint VALUES ('NCBIGENE', ?, ?)", [(r["entrez_id"], r["symbol"]) for r in hg if r.get("entrez_id")])
        # an HGNC gene names its OMIM gene entry and its proteins, where nothing else does (fallbacks: see the node stage)
        hgnc_names = [("OMIM", v.strip(), r["symbol"] + " (gene)") for r in hg for v in filter(None, (r.get("omim_id") or "").split("|"))] + \
                     [("UNIPROT", v.strip(), r["symbol"]) for r in hg for v in filter(None, (r.get("uniprot_ids") or "").split("|"))]

    # --- Orphanet's own alignments: each rare disease to ICD-10, ICD-11, OMIM, UMLS, MeSH, MONDO, GARD -------------
    # with Orphanet's relation (E exact, NTBT the ORPHAcode is narrower, BTNT broader, ND undecided) and validation.
    if ORPHA_XML.exists():
        import xml.etree.ElementTree as ET
        ov = {"ICD-10": "ICD10WHO", "ICD-11": "ICD11MMS", "OMIM": "OMIM", "UMLS": "UMLS", "MeSH": "MESH", "MONDO": "MONDO", "GARD": "GARD"}
        rows_o, names_o, level_o, n_x, skip_x = [], [], [], 0, collections.Counter()
        for d in ET.parse(ORPHA_XML).getroot().iter("Disorder"):
            oc = d.findtext("OrphaCode")
            if not oc:
                continue
            names_o.append((oc, d.findtext("Name")))
            flags = [f.findtext("Label") for f in d.findall("DisorderFlagList/DisorderFlag")]
            active = "Inactive" not in flags                              # Orphanet retires an entry (deprecated, non-rare ...)
            level_o.append((oc, d.findtext("DisorderGroup/Name"), active))  # Disorder / Group of disorders / Subtype of disorder
            for x in d.iter("ExternalReference"):
                src, ref_ = x.findtext("Source"), (x.findtext("Reference") or "").strip()
                n_x += 1
                if src not in ov or not ref_:
                    skip_x["no reference" if src in ov else "a vocabulary not loaded (MedDRA: MSSO-licensed)"] += 1
                    continue
                relx = (x.findtext("DisorderMappingRelation/Name") or "").split(" ")[0]
                rows_o.append(("ORPHA", oc, "orpha:xref", ov[src], ("MONDO:" + ref_.zfill(7)) if src == "MONDO" else ref_, "Orphanet",
                               "en_product1.xml ExternalReference", relx or "unqualified", "native", "asserted", PIN["orphanet"],
                               json.dumps({"relation": relx, "validation": x.findtext("DisorderMappingValidationStatus/Name"),
                                           "icd_relation": (x.findtext("DisorderMappingICDRelation/Name") or None),
                                           **({} if active else {"entry": "inactive: " + "; ".join(f for f in flags if f and f != "Inactive")})})))
        ins_rows("Orphanet disorder -> ICD-10 / ICD-11 / OMIM / UMLS / MeSH / MONDO / GARD (Orphanet's alignments)", sorted(set(rows_o)),
                 available=n_x, excluded=sorted(skip_x.items()), unit="Orphanet ExternalReferences")
        # an entry Orphanet has retired or folded into another says where it went: "Moved to" (the same disorder, now under
        # another code) is identity, like SNOMED's REPLACED BY; "Referred to" points the reader to a related entry.
        rows_s, n_s = [], 0
        for d in ET.parse(ORPHA_XML).getroot().iter("Disorder"):
            oc = d.findtext("OrphaCode")
            for a_ in d.findall("DisorderDisorderAssociationList/DisorderDisorderAssociation"):
                n_s += 1
                kind, tgt = a_.findtext("DisorderDisorderAssociationType/Name"), a_.findtext("TargetDisorder/OrphaCode")
                pred = {"Moved to": "orpha:moved_to", "Referred to": "orpha:referred_to"}.get(kind)
                if oc and tgt and pred:
                    rows_s.append(("ORPHA", oc, pred, "ORPHA", tgt, "Orphanet", "en_product1.xml DisorderDisorderAssociation", kind,
                                   "native", "asserted", PIN["orphanet"], None))
        ins_rows("Orphanet entry -> where it moved / is referred to", sorted(set(rows_s)), available=n_s,
                 excluded=[("another association type", n_s - len(rows_s))], unit="Orphanet DisorderDisorderAssociations")
        con.executemany("INSERT INTO name_hint VALUES ('ORPHA', ?, ?)", names_o)
        con.execute("CREATE TEMP TABLE orpha_level (code VARCHAR, level VARCHAR, active BOOLEAN)")
        con.executemany("INSERT INTO orpha_level VALUES (?, ?, ?)", sorted(set(level_o)))

    # --- Orphanet's own gene and phenotype files (products 6 and 4) ------------------------------------------------
    # HPO relays both, but without Orphanet's detail: the gene file says HOW a gene is involved (disease-causing germline
    # mutation, loss or gain of function, susceptibility factor, candidate gene tested, part of a fusion gene ...), with
    # Orphanet's validation status and sources; the phenotype file carries the frequency band, whether the sign is a
    # diagnostic criterion or pathognomonic, and exclusions ("Excluded (0%)": a stated absence, loaded as lacks_phenotype).
    # Gene links Orphanet has not yet assessed are counted, not loaded.
    if ORPHA_GENES.exists():
        import xml.etree.ElementTree as ET
        rows_g, names_g, skipped = [], [], {"not yet assessed": 0, "no HGNC id": 0}
        for d in ET.parse(ORPHA_GENES).getroot().iter("Disorder"):
            oc = d.findtext("OrphaCode")
            for a_ in d.iter("DisorderGeneAssociation"):
                g_ = a_.find("Gene")
                hg = next((x.findtext("Reference") for x in g_.iter("ExternalReference") if x.findtext("Source") == "HGNC"), None) if g_ is not None else None
                status = a_.findtext("DisorderGeneAssociationStatus/Name")
                if status != "Assessed":
                    skipped["not yet assessed"] += 1
                    continue
                if not hg:
                    skipped["no HGNC id"] += 1
                    continue
                names_g.append(("HGNC:" + hg, g_.findtext("Symbol")))
                rows_g.append(("HGNC", "HGNC:" + hg, "orpha:gene_disease", "ORPHA", oc, "Orphanet", "en_product6.xml DisorderGeneAssociation",
                               a_.findtext("DisorderGeneAssociationType/Name"), "native", "asserted", PIN["orphanet"],
                               json.dumps({"symbol": g_.findtext("Symbol"), "status": status, "validation": a_.findtext("SourceOfValidation")})))
        ins_rows("Orphanet gene -> disorder (product 6, with the kind of involvement)", sorted(set(rows_g)),
                 available=len(rows_g) + sum(skipped.values()), excluded=sorted(skipped.items()), unit="Orphanet gene associations")
        for k_, v_ in skipped.items():
            log[f"Orphanet gene -> disorder: not loaded, {k_}"] = v_
        con.executemany("INSERT INTO name_hint VALUES ('HGNC', ?, ?)", sorted(set(names_g)))
    if ORPHA_PHENO.exists():
        import xml.etree.ElementTree as ET
        rows_p, n_p, skip_p = [], 0, 0
        for st_ in ET.parse(ORPHA_PHENO).getroot().iter("HPODisorderSetStatus"):
            oc = st_.findtext("Disorder/OrphaCode")
            for a_ in st_.iter("HPODisorderAssociation"):
                hp_, fq = a_.findtext("HPO/HPOId"), a_.findtext("HPOFrequency/Name")
                n_p += 1
                if not (oc and hp_):
                    skip_p += 1
                    continue
                rows_p.append(("ORPHA", oc, "orpha:lacks_phenotype" if fq and fq.startswith("Excluded") else "orpha:has_phenotype", "HP", hp_,
                               "Orphanet", "en_product4.xml HPODisorderAssociation", fq or "frequency not stated", "native", "asserted",
                               PIN["orphanet"], json.dumps({"frequency": fq, "diagnostic_criteria": a_.findtext("DiagnosticCriteria/Name")})))
        ins_rows("Orphanet disorder -> HPO phenotype, with frequency (product 4)", sorted(set(rows_p)), available=n_p,
                 excluded=[("no ORPHAcode or HPO id", skip_p)], unit="Orphanet phenotype associations")

    # --- WHO's ICD-10 <-> ICD-11 mapping tables, and ICD-11's two identifiers ---------------------------------------
    # MMS codes (what is coded: Orphanet cites them) and foundation ids (what the entity is: MONDO cites them) are two
    # vocabularies here; WHO's tables carry both, so they also join them. Codes only -- WHO titles are not loaded.
    if (WHO_MAP / "10To11MapToOneCategory.txt").exists():
        # only rows touching an ICD code something else in the graph already names (Orphanet, MONDO, HPO): the rest of the
        # two classifications would be detached clusters joining nothing (counted in build_log, not loaded)
        seen = {(v, c) for v, c in con.execute("""SELECT DISTINCT o_vocab, o_code FROM edge WHERE o_vocab IN ('ICD10WHO', 'ICD11MMS', 'ICD11')""").fetchall()}
        touch = lambda *ks: any(k in seen for k in ks)
        wt = lambda f: [dict(zip([h.strip() for h in rows[0]], r)) for rows in [[l.rstrip("\n").split("\t") for l in open(WHO_MAP / f, encoding="utf-8-sig")]]
                        for r in rows[1:]]
        fid = lambda u: (u or "").rstrip("/").split("/entity/")[-1] if "/entity/" in (u or "") else None
        mid = lambda u: (u or "").split("/mms/")[-1].split("/")[0] if "/mms/" in (u or "") else None
        one = wt("10To11MapToOneCategory.txt")
        multi = wt("10To11MapToMultipleCategories.txt") if (WHO_MAP / "10To11MapToMultipleCategories.txt").exists() else []
        loc = lambda f: f"{f} (WHO release 2026-01)"
        rows_w, w_code, w_touch = {}, 0, 0
        for f, rs, how in (("10To11MapToOneCategory.txt", one, "one category"), ("10To11MapToMultipleCategories.txt", multi, "multiple categories")):
            for r in rs:
                c10, c11 = (r.get("icd10Code") or "").strip(), (r.get("icd11Code") or "").strip()
                f11 = fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI"))
                w_code += bool(c10 and c11)
                if c10 and c11 and touch(("ICD10WHO", c10), ("ICD11MMS", c11), ("ICD11", f11)):
                    w_touch += 1
                    rows_w.setdefault((c10, c11), ("ICD10WHO", c10, "who:icd10_to_icd11", "ICD11MMS", c11, "WHO", loc(f), how, "native", "asserted",
                                               PIN["who"], json.dumps({"icd11_foundation": fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI"))})))
        ins_rows("WHO ICD-10 -> ICD-11 (MMS) mapping table", sorted(rows_w.values()), available=len(one) + len(multi),
                 excluded=[("no ICD-10 or no ICD-11 code on the row", len(one) + len(multi) - w_code),
                           ("no code shared with the rest of the graph", w_code - w_touch)], unit="WHO 10To11 rows")
        back = wt("11To10MapToOneCategory.txt")
        ins_rows("WHO ICD-11 (MMS) -> ICD-10 mapping table", sorted({("ICD11MMS", r["icd11Code"].strip(), "who:icd11_to_icd10", "ICD10WHO",
                  r["icd10Code"].strip(), "WHO", loc("11To10MapToOneCategory.txt"), "one category", "native", "asserted", PIN["who"], None)
                  for r in back if (r.get("icd11Code") or "").strip() and (r.get("icd10Code") or "").strip()
                  and touch(("ICD11MMS", r["icd11Code"].strip()), ("ICD10WHO", r["icd10Code"].strip()))}),
                 available=len(back), excluded=[("no ICD-11 or no ICD-10 code on the row",
                                                 sum(not ((r.get("icd11Code") or "").strip() and (r.get("icd10Code") or "").strip()) for r in back)),
                                                ("no code shared with the rest of the graph", sum(bool((r.get("icd11Code") or "").strip() and (r.get("icd10Code") or "").strip())
                                                  and not touch(("ICD11MMS", r["icd11Code"].strip()), ("ICD10WHO", r["icd10Code"].strip())) for r in back))],
                 unit="WHO 11To10 rows")
        fnd = wt("foundation_11To10MapToOneCategory.txt") if (WHO_MAP / "foundation_11To10MapToOneCategory.txt").exists() else []
        ins_rows("WHO ICD-11 foundation entity -> ICD-10 mapping table", sorted({("ICD11", fid(r["Foundation URI"]), "who:icd11_to_icd10",
                  "ICD10WHO", r["icd10Code"].strip(), "WHO", loc("foundation_11To10MapToOneCategory.txt"), "foundation, one category", "native",
                  "asserted", PIN["who"], None) for r in fnd if fid(r.get("Foundation URI")) and (r.get("icd10Code") or "").strip()
                  and touch(("ICD11", fid(r["Foundation URI"])), ("ICD10WHO", r["icd10Code"].strip()))}),
                 available=len(fnd), excluded=[("no foundation id or no ICD-10 code on the row",
                                                sum(not (fid(r.get("Foundation URI")) and (r.get("icd10Code") or "").strip()) for r in fnd)),
                                               ("no code shared with the rest of the graph", sum(bool(fid(r.get("Foundation URI")) and (r.get("icd10Code") or "").strip())
                                                 and not touch(("ICD11", fid(r["Foundation URI"])), ("ICD10WHO", r["icd10Code"].strip())) for r in fnd))],
                 unit="WHO foundation 11To10 rows")
        # and the forward table, ICD-10 -> foundation entity, which the build had not read: the same test for a shared code
        fwd = wt("foundation_10To11MapToOneCategory.txt") if (WHO_MAP / "foundation_10To11MapToOneCategory.txt").exists() else []
        fk = lambda r: ((r.get("icd10Code") or "").strip(), fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI")))
        ins_rows("WHO ICD-10 -> ICD-11 foundation entity mapping table", sorted({("ICD10WHO", fk(r)[0], "who:icd10_to_icd11", "ICD11", fk(r)[1],
                  "WHO", loc("foundation_10To11MapToOneCategory.txt"), "foundation, one category", "native", "asserted", PIN["who"], None)
                  for r in fwd if all(fk(r)) and touch(("ICD10WHO", fk(r)[0]), ("ICD11", fk(r)[1]))}),
                 available=len(fwd), excluded=[("no ICD-10 code or no foundation id on the row", sum(not all(fk(r)) for r in fwd)),
                                               ("no code shared with the rest of the graph",
                                                sum(bool(all(fk(r))) and not touch(("ICD10WHO", fk(r)[0]), ("ICD11", fk(r)[1])) for r in fwd))],
                 unit="WHO foundation 10To11 rows")
        # an MMS code and the foundation entity it linearises (WHO states both on every row that has a code)
        mf = {(r["icd11Code"].strip(), fid(r["Foundation URI"])) for r in fnd if (r.get("icd11Code") or "").strip() and fid(r.get("Foundation URI"))}
        mf |= {(r["icd11Code"].strip(), fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI"))) for r in one + multi
               if (r.get("icd11Code") or "").strip() and fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI"))
               and mid(r.get("Linearization (releaseURI)") or r.get("Linearization (release) URI")) == fid(r.get("ICD-11 FoundationURI") or r.get("ICD-11 Foundation URI"))}
        now = {(v, c) for v, c in con.execute("""SELECT DISTINCT o_vocab, o_code FROM edge WHERE o_vocab IN ('ICD10WHO', 'ICD11MMS', 'ICD11')
                                                 UNION SELECT DISTINCT s_vocab, s_code FROM edge WHERE s_vocab IN ('ICD10WHO', 'ICD11MMS', 'ICD11')""").fetchall()}
        ins_rows("ICD-11 MMS code -> its foundation entity", sorted({("ICD11MMS", m_, "who:icd11_mms_foundation", "ICD11", f_, "WHO",
                  "mapping tables: icd11Code + Foundation URI", "stated on the same row", "native", "asserted", PIN["who"], None) for m_, f_ in mf
                  if ("ICD11MMS", m_) in now or ("ICD11", f_) in now}), available=len(mf),
                 excluded=[("neither code elsewhere in the graph", sum(1 for m_, f_ in mf if not (("ICD11MMS", m_) in now or ("ICD11", f_) in now)))],
                 unit="MMS code / foundation id pairs stated on the mapping rows")
        log["WHO mapping rows not loaded (no code shared with the rest of the graph)"] = (
            len({(r.get("icd10Code"), r.get("icd11Code")) for r in one + multi}) + len(back) + len(fnd) + len(mf)
            - sum(con.execute("SELECT count(*) FROM edge WHERE predicate LIKE 'who:%'").fetchone()))

    # --- Reactome: human protein -> pathway, and the pathway hierarchy ----------------------------------------------
    if (REACTOME / "UniProt2Reactome.txt").exists():
        hs_all = [l.rstrip("\n").split("\t") for l in open(REACTOME / "UniProt2Reactome.txt", encoding="utf-8")]
        hs = [r for r in hs_all if len(r) >= 6 and r[5] == "Homo sapiens"]
        ins_rows("UniProt protein -> Reactome pathway (human, lowest level)", sorted({
            ("UNIPROT", r[0], "reactome:participates_in", "REACTOME", r[1], "Reactome", "UniProt2Reactome.txt", r[4], "native", "asserted",
             PIN["reactome"], json.dumps({"evidence": r[4]})) for r in hs}), available=len(hs_all),
            excluded=[("not a human pathway", len(hs_all) - len(hs))], unit="UniProt2Reactome rows")
        if (REACTOME / "ChEBI2Reactome.txt").exists():
            # the small molecules Reactome places in its pathways (drugs among them): ChEBI -> pathway, human, lowest level
            ch_all = [l.rstrip("\n").split("\t") for l in open(REACTOME / "ChEBI2Reactome.txt", encoding="utf-8")]
            ch = [r for r in ch_all if len(r) >= 6 and r[5] == "Homo sapiens"]
            ins_rows("ChEBI chemical -> Reactome pathway (human, lowest level)", sorted({
                ("CHEBI", r[0], "reactome:participates_in", "REACTOME", r[1], "Reactome", "ChEBI2Reactome.txt", r[4], "native", "asserted",
                 PIN["reactome"], json.dumps({"evidence": r[4]})) for r in ch}), available=len(ch_all),
                excluded=[("not a human pathway", len(ch_all) - len(ch))], unit="ChEBI2Reactome rows")
        pw = {r[0]: r[1] for r in (l.rstrip("\n").split("\t") for l in open(REACTOME / "ReactomePathways.txt", encoding="utf-8"))
              if len(r) >= 3 and r[2] == "Homo sapiens"}
        ins_rows("Reactome pathway -> parent pathway (human)", sorted({
            ("REACTOME", c_, "reactome:part_of", "REACTOME", p_, "Reactome", "ReactomePathwaysRelation.txt", "native", "native", "asserted",
             PIN["reactome"], None)
            for p_, c_ in (l.rstrip("\n").split("\t") for l in open(REACTOME / "ReactomePathwaysRelation.txt", encoding="utf-8"))
            if p_ in pw and c_ in pw}), available=len(rr := [l.rstrip("\n").split("\t") for l in open(REACTOME / "ReactomePathwaysRelation.txt", encoding="utf-8")]),
            excluded=[("not a pair of human pathways", sum(1 for p_, c_ in rr if not (p_ in pw and c_ in pw)))], unit="pathway relation rows")
        con.executemany("INSERT INTO name_hint VALUES ('REACTOME', ?, ?)", list(pw.items()))

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
            FROM umls_hp WHERE same_name""", src=f"read_csv('{UMLS_HPO}', delim='\t', header=true, all_varchar=true, quote='') u",
            keep=[("no SNOMED code", "u.snomed_code IS NOT NULL AND u.snomed_code <> ''"),
                  ("SNOMED code not active in SNOMED CT-AU", "u.snomed_code IN (SELECT id FROM cmp.concept)"),
                  ("HPO term not in hp.obo", "u.hpo_id IN (SELECT code FROM name_hint WHERE vocab = 'HP')"),
                  ("names differ: a candidate for a person (review queue hpo_snomed)",
                   "(u.hpo_id, u.snomed_code) IN (SELECT hpo_id, snomed_code FROM umls_hp WHERE same_name)")], unit="UTS crosswalk rows")
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
        rows_lr, skip_lr = [], collections.Counter()
        for r in recs:
            b = bound.get(r["id"], {})
            if r["id"] not in verified:
                skip_lr["number not verified against the abstract"] += 1
                continue
            if not b.get("finding") or not b.get("diagnosis"):
                skip_lr["finding or diagnosis not bound to SNOMED CT exactly"] += 1
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
        ins_rows("finding -> diagnosis likelihood ratio (transcribed, verified)", rows_lr, available=len(recs),
                 excluded=sorted(skip_lr.items()) + [("bound, but the binding family has not earned a tier (held as candidates)", held)],
                 unit="transcribed likelihood-ratio records")
        log["likelihood-ratio records bound but held as candidates (family not admitted)"] = held
        print(f"  {'LR records held (binding family not admitted)':<44} {held:>10,}   admitted: {sorted(admitted)}", flush=True)

    # --- AHRQ CCSR: ICD-10-CM codes into clinical categories (UMLS relays AHRQ's map verbatim; Level 0, public domain) --
    if UMLS_MRMAP.exists():      # MRMAP's FROMID / TOID are its own row ids; the codes are FROMEXPR / TOEXPR
        ins("ICD-10-CM -> CCSR clinical category (AHRQ)", f"""SELECT DISTINCT 'ICD10CM', m.FROMEXPR, 'ccsr:category', 'CCSR', m.TOEXPR, 'AHRQ CCSR (via UMLS)',
                'MRMAP 2026AA CCSR_ICD10CM', m.RELA, 'native', 'asserted', '{PIN['ccsr']}',
                json_object('body_system', left(m.TOEXPR, 3))
            FROM '{UMLS_MRMAP}' m WHERE m.MAPSETSAB = 'CCSR_ICD10CM' AND m.FROMEXPR IS NOT NULL AND m.TOEXPR IS NOT NULL
              AND m.FROMEXPR IN (SELECT o_code FROM edge WHERE o_vocab = 'ICD10CM' UNION SELECT s_code FROM edge WHERE s_vocab = 'ICD10CM')""",
            src=f"'{UMLS_MRMAP}' m WHERE m.MAPSETSAB = 'CCSR_ICD10CM'",
            keep=[("no code on the row", "m.FROMEXPR IS NOT NULL AND m.TOEXPR IS NOT NULL"),
                  ("ICD-10-CM code not elsewhere in the graph", "m.FROMEXPR IN (SELECT o_code FROM edge WHERE o_vocab = 'ICD10CM' "
                                                               "UNION SELECT s_code FROM edge WHERE s_vocab = 'ICD10CM')")])
        con.execute(f"""INSERT INTO name_hint SELECT 'CCSR', CODE, any_value(STR) FROM '{UMLS_AUI}' WHERE SAB = 'CCSR_ICD10CM'
                        AND CODE IN (SELECT o_code FROM edge WHERE predicate = 'ccsr:category') GROUP BY 2""")

    # --- UMLS Metathesaurus: codes of two graph vocabularies under one CUI (UMLS 2026AA, the licence holder's copy) ---
    # Same-name pairs load (the HPO rule: the two sources share a name for the concept); pairs whose names differ are
    # candidates, counted here and kept in the parquet. SNOMED organism -> NCBI Taxonomy has its own UMLS loader above
    # and is not repeated. HPO -> SNOMED loads here too: the older per-code crosswalk (hp:umls_snomed) found 2,754
    # same-name pairs, the 2026AA concepts file 4,885 -- the completeness measure's largest held gap (docs/completeness.md).
    # Each vocabulary pair is tiered by its own hand check (graph_report.py).
    if UMLS_PAIRS.exists():
        own = "('NCBITAXON-SCT')"
        # last of the loaders: a pair loads only if one of its codes is already a node, so nothing arrives detached
        con.execute("""CREATE TEMP TABLE present AS SELECT DISTINCT s_vocab v, s_code c FROM edge UNION SELECT DISTINCT o_vocab, o_code FROM edge""")
        con.execute(f"""CREATE TEMP TABLE up AS SELECT u.* FROM '{UMLS_PAIRS}' u
                        WHERE (u.sv, u.sc) IN (SELECT v, c FROM present) OR (u.ov, u.oc) IN (SELECT v, c FROM present)""")
        n_up = lambda: con.execute("SELECT count(*) FROM up").fetchone()[0]
        up_all, up_steps = con.execute(f"SELECT count(*) FROM '{UMLS_PAIRS}'").fetchone()[0], []
        up_steps.append(("neither code a node the graph already holds", up_all - n_up()))
        up_n = n_up()
        # an OMIM GENE entry carries its diseases' names as synonyms, so a shared name pairs a disease with a gene
        # (Bardet-Biedl syndrome 1 -> the BBS1 gene entry). HGNC names the gene entries; they pair only with a gene.
        con.execute("""DELETE FROM up WHERE (('OMIM' = sv AND sc IN (SELECT o_code FROM edge WHERE predicate = 'hgnc:xref' AND o_vocab = 'OMIM')
                                               AND NOT (ov = 'HGNC' OR (ov = 'NCIT' AND o_name ILIKE '% Gene')))
                                          OR ('OMIM' = ov AND oc IN (SELECT o_code FROM edge WHERE predicate = 'hgnc:xref' AND o_vocab = 'OMIM')
                                               AND NOT (sv = 'HGNC' OR (sv = 'NCIT' AND s_name ILIKE '% Gene'))))""")
        up_steps.append(("an OMIM gene entry paired with a non-gene (it carries its diseases' names)", up_n - n_up()))
        # a SNOMED code joins only as an active SNOMED CT-AU concept (a US-only or retired code would be a node the AU
        # release does not have)
        log["UMLS shared CUI: pairs dropped, SNOMED code not active in SNOMED CT-AU"] = con.execute("""SELECT count(*) FROM up
            WHERE (sv = 'SCT' AND sc NOT IN (SELECT id FROM cmp.concept)) OR (ov = 'SCT' AND oc NOT IN (SELECT id FROM cmp.concept))""").fetchone()[0]
        con.execute("""DELETE FROM up WHERE (sv = 'SCT' AND sc NOT IN (SELECT id FROM cmp.concept)) OR (ov = 'SCT' AND oc NOT IN (SELECT id FROM cmp.concept))""")
        # Two more pair rules, from the equivalence-cluster check (scripts/consistency.py): an NCIt fusion gene
        # ("ETV6/PDGFRB Fusion Gene") is neither partner, though OMIM's gene entries list fusion names as synonyms; and an
        # OMIM susceptibility entry lists the phenotypes it predisposes to as synonyms ("Multiple system atrophy 1,
        # susceptibility to" -> "Orthostatic hypotension"), so it pairs only with a concept that is itself a susceptibility.
        log["UMLS shared CUI: pairs dropped, NCIt fusion gene with an OMIM gene entry"] = con.execute("""SELECT count(*) FROM up
            WHERE ((sv = 'NCIT' AND s_name ILIKE '%fusion gene%' AND ov = 'OMIM') OR (ov = 'NCIT' AND o_name ILIKE '%fusion gene%' AND sv = 'OMIM'))""").fetchone()[0]
        con.execute("""DELETE FROM up WHERE (sv = 'NCIT' AND s_name ILIKE '%fusion gene%' AND ov = 'OMIM')
                                         OR (ov = 'NCIT' AND o_name ILIKE '%fusion gene%' AND sv = 'OMIM')""")
        sus = """(sv = 'OMIM' AND s_name ILIKE '%susceptib%' AND o_name NOT ILIKE '%susceptib%')
                 OR (ov = 'OMIM' AND o_name ILIKE '%susceptib%' AND s_name NOT ILIKE '%susceptib%')"""
        log["UMLS shared CUI: pairs dropped, OMIM susceptibility entry with a non-susceptibility concept"] = con.execute(
            f"SELECT count(*) FROM up WHERE {sus}").fetchone()[0]
        con.execute(f"DELETE FROM up WHERE {sus}")
        up_steps += [(k.split(", ", 1)[1], log[k]) for k in ("UMLS shared CUI: pairs dropped, SNOMED code not active in SNOMED CT-AU",
                                                             "UMLS shared CUI: pairs dropped, NCIt fusion gene with an OMIM gene entry",
                                                             "UMLS shared CUI: pairs dropped, OMIM susceptibility entry with a non-susceptibility concept")]
        ins("UMLS shared CUI, same name (MRCONSO 2026AA)", f"""SELECT DISTINCT sv, sc, 'umls:shared_cui', ov, oc, 'UMLS', 'MRCONSO 2026AA CUI ' || cui,
                sv || '-' || ov || ' same name', 'ungraded', 'asserted', '{PIN['umls_rel']}',
                json_object('cui', cui, 'shared_name', shared_name)
            FROM up WHERE same_name AND sv || '-' || ov NOT IN {own}""", src="up",
            keep=[("SNOMED organism <-> NCBI Taxonomy: its own loader", f"sv || '-' || ov NOT IN {own}"),
                  ("names differ: candidates in cache/umls/umls_shared_cui.parquet", "same_name")], unit="UMLS shared-CUI pairs")
        account("UMLS shared CUI, same name (MRCONSO 2026AA)", available=up_all, excluded=up_steps, unit="UMLS shared-CUI pairs")
        log["UMLS shared CUI, names differ (candidates in cache/umls/umls_shared_cui.parquet, not edges)"] = con.execute(
            f"SELECT count(*) FROM up WHERE NOT same_name AND sv || '-' || ov NOT IN {own}").fetchone()[0]
        # The graph holds 29,234 UMLS concepts as nodes -- Orphanet's, MONDO's and DrugCentral's own cross-references
        # name them -- but nothing joined a CUI to the codes inside it, so Orphanet -> CUI stopped there (the measure's
        # second-largest held gap). Each CUI node now reaches its SNOMED CT-AU disorders and findings. Drugs are left
        # out: UMLS files a substance and SNOMED's "Product containing" it under one CUI, and DrugCentral links drugs to
        # SNOMED directly.
        if UMLS_CONSO.exists():
            ins("UMLS concept -> SNOMED CT disorder / finding in it (MRCONSO 2026AA)", f"""SELECT DISTINCT 'UMLS', m.CUI, 'umls:concept_member',
                    'SCT', m.CODE, 'UMLS', 'MRCONSO 2026AA SNOMEDCT_US atom', 'SNOMED CT atom in the concept', 'ungraded', 'asserted',
                    '{PIN['umls_rel']}', json_object('tty', any_value(m.TTY))
                FROM '{UMLS_CONSO}' m JOIN cmp.concept c ON c.id = m.CODE
                WHERE m.SAB = 'SNOMEDCT_US' AND m.SUPPRESS = 'N' AND c.tag IN ('disorder', 'finding')
                  AND m.CUI IN (SELECT c FROM present WHERE v = 'UMLS') GROUP BY m.CUI, m.CODE""",
                src=f"'{UMLS_CONSO}' m WHERE m.SAB = 'SNOMEDCT_US'",
                keep=[("suppressed atom", "m.SUPPRESS = 'N'"), ("CUI not a node the graph holds", "m.CUI IN (SELECT c FROM present WHERE v = 'UMLS')"),
                      ("not an active SNOMED CT-AU disorder or finding", "m.CODE IN (SELECT id FROM cmp.concept WHERE tag IN ('disorder', 'finding'))")],
                unit="MRCONSO SNOMEDCT_US atoms")
        # The same concepts' HPO, MeSH and NCIt atoms (Wave 2, scripts/wave2_candidates.py): pairs that pass the shared-name
        # gate and the graph does not already reach, for the families Ken confirmed on 27 Sep. OMIM stays held back (its
        # alternative titles let gene entries through: 7 of 30). graph_report.py earns each family's tier from its sheet.
        if WAVE2_MEMBERS.exists():
            ins("UMLS disease concept -> its HPO / MeSH / NCIt code (Wave 2, same name)", f"""SELECT DISTINCT 'UMLS', cui, 'umls:disease_member', v, code,
                    'UMLS', 'MRCONSO 2026AA ' || v || ' atom', 'atom in the concept, same name', 'ungraded', 'asserted', '{PIN['umls_rel']}',
                    json_object('matched_through', match_ttys, 'named_by', src)
                FROM '{WAVE2_MEMBERS}' WHERE gate AND NOT present AND v IN ('HP', 'MESH', 'NCIT')
                  AND cui IN (SELECT c FROM present WHERE v = 'UMLS')""",
                src=f"'{WAVE2_MEMBERS}' WHERE v IN ('HP', 'MESH', 'NCIT')",
                keep=[("names differ (the shared-name gate)", "gate"), ("the graph already reaches the pair", "NOT present"),
                      ("CUI not a node the graph holds", "cui IN (SELECT c FROM present WHERE v = 'UMLS')")],
                unit="Wave 2 candidate pairs (HPO, MeSH, NCIt)")
        # A chain rule (workstream 3): an Orphanet disorder with no ICD-10 code of its own, exactly aligned by Orphanet to a
        # UMLS concept or MONDO disease that holds a SNOMED CT concept, gets the ICD-10 code SNOMED International's map
        # classifies that concept to. Only where it can be right: Orphanet's disorder and subtype levels (a group given one
        # member's code was wrong 6 times in 27), and SNOMED maps with a single unconditional group (a concept needing two
        # codes together is misclassified by either alone). The two witnesses and the census are in graph_report.py.
        if UMLS_CONSO.exists() and SCT_US_XMAP.exists() and ORPHA_XML.exists():
            ins("Orphanet disorder -> ICD-10 via SNOMED CT's map (chain)", f"""WITH o2s AS (
                    SELECT DISTINCT x.s_code orpha, m.o_code sct, 'via SNOMED CT (UMLS concept)' via, x.o_code mid FROM edge x
                        JOIN edge m ON m.predicate = 'umls:concept_member' AND m.s_code = x.o_code
                        WHERE x.predicate = 'orpha:xref' AND x.o_vocab = 'UMLS' AND x.method = 'E'
                    UNION SELECT DISTINCT x.s_code, e.o_code, 'via SNOMED CT (MONDO)', x.o_code FROM edge x
                        JOIN edge e ON e.predicate = 'mondo:exact_match' AND e.s_code = x.o_code AND e.o_vocab = 'SCT'
                        WHERE x.predicate = 'orpha:xref' AND x.o_vocab = 'MONDO' AND x.method = 'E'),
                  single AS (SELECT s_code FROM edge WHERE predicate = 'sct:icd10_map' GROUP BY 1
                             HAVING max(CAST(attrs->>'group' AS INT)) = 1 AND bool_and(method = 'unconditional'))
                SELECT 'ORPHA', o.orpha, 'orpha:icd10_via_snomed', 'ICD10WHO', i.o_code, 'derived (Orphanet, UMLS / MONDO, SNOMED CT ICD-10 map)',
                       'orpha:xref E -> ' || CASE WHEN o.via LIKE '%UMLS%' THEN 'umls:concept_member' ELSE 'mondo:exact_match' END || ' -> sct:icd10_map',
                       o.via, 'ungraded', 'asserted', '{PIN['orphanet']}; {PIN['umls_rel']}; {PIN['sct_us']}',
                       json_object('intermediate', list(DISTINCT o.mid), 'snomed', list(DISTINCT o.sct))
                FROM o2s o JOIN edge i ON i.predicate = 'sct:icd10_map' AND i.s_code = o.sct AND i.s_code IN (SELECT s_code FROM single)
                JOIN orpha_level l ON l.code = o.orpha AND l.level IN ('Disorder', 'Subtype of disorder') AND l.active
                WHERE o.orpha NOT IN (SELECT s_code FROM edge WHERE predicate = 'orpha:xref' AND o_vocab = 'ICD10WHO')
                GROUP BY o.orpha, i.o_code, o.via""",
                derived="orpha:xref E -> umls:concept_member / mondo:exact_match -> sct:icd10_map (single unconditional group); "
                        "active Orphanet disorders and subtypes with no ICD-10 of their own")
        umls_names = con.execute("""SELECT sv, sc, any_value(s_name) FROM up WHERE same_name GROUP BY 1, 2
                                    UNION ALL SELECT ov, oc, any_value(o_name) FROM up WHERE same_name GROUP BY 1, 2""").fetchall()

    # --- UMLS relationships (MRREL Level 0): sources' own hierarchies, and MED-RT's drug knowledge ------------------
    if UMLS_REL.exists():
        con.execute("DROP TABLE IF EXISTS present")
        con.execute("""CREATE TEMP TABLE present AS SELECT DISTINCT s_vocab v, s_code c FROM edge UNION SELECT DISTINCT o_vocab, o_code FROM edge""")
        # a hierarchy is climbed upward from the nodes the graph already holds (their parents, the parents' parents ...);
        # children are not pulled in, so a broad concept does not bring thousands of nodes nothing else names
        con.execute(f"CREATE TEMP TABLE sp AS SELECT * FROM '{UMLS_REL}' WHERE predicate = 'umls:source_parent'")
        con.execute("CREATE TEMP TABLE reach AS SELECT v, c FROM present WHERE v IN ('MESH', 'NCIT', 'FMA', 'LOINC')")
        con.execute("CREATE TEMP TABLE sp_keep (s_vocab VARCHAR, s_code VARCHAR, o_vocab VARCHAR, o_code VARCHAR, sab VARCHAR, rela VARCHAR)")
        while True:
            n = con.execute("""INSERT INTO sp_keep SELECT DISTINCT s.s_vocab, s.s_code, s.o_vocab, s.o_code, s.sab, s.rela FROM sp s
                               JOIN reach r ON r.v = s.s_vocab AND r.c = s.s_code
                               WHERE (s.s_vocab, s.s_code, s.o_code) NOT IN (SELECT s_vocab, s_code, o_code FROM sp_keep)""").fetchone()[0]
            if not n:
                break
            con.execute("""INSERT INTO reach SELECT DISTINCT o_vocab, o_code FROM sp_keep WHERE (o_vocab, o_code) NOT IN (SELECT v, c FROM reach)""")
        ins("UMLS: a source's own hierarchy (MeSH tree, NCIt, FMA, LOINC parts)", f"""SELECT s_vocab, s_code, 'umls:source_parent', o_vocab,
                o_code, 'UMLS (' || sab || ')', 'MRREL 2026AA Level 0 PAR', sab || ' ' || rela, 'native', 'asserted', '{PIN['umls_rel']}', NULL FROM sp_keep""",
            src="sp", keep=[("not above a node the graph holds (a hierarchy is climbed up, never down)",
                             "(s_vocab, s_code, o_vocab, o_code, sab, rela) IN (SELECT * FROM sp_keep)")], unit="MRREL PAR rows")
        # MED-RT: the drug must already be a node; for treat / prevent / diagnose / contraindication the disease as well
        ins("UMLS: MED-RT drug -> disease (may treat, prevent, diagnose; contraindicated)", f"""SELECT DISTINCT s_vocab, s_code, predicate, o_vocab,
                o_code, 'UMLS (MED-RT)', 'MRREL 2026AA Level 0 ' || rela, how, 'ungraded', 'asserted', '{PIN['umls_rel']}',
                json_object('medrt_rela', rela, 'drug_cui', cui_s, 'other_cui', cui_o)
            FROM '{UMLS_REL}' WHERE sab = 'MED-RT' AND o_vocab <> 'MEDRT'
              AND (s_vocab, s_code) IN (SELECT v, c FROM present) AND (o_vocab, o_code) IN (SELECT v, c FROM present)""",
            src=f"'{UMLS_REL}' WHERE sab = 'MED-RT' AND o_vocab <> 'MEDRT'",
            keep=[("drug not a node the graph holds", "(s_vocab, s_code) IN (SELECT v, c FROM present)"),
                  ("disease not a node the graph holds", "(o_vocab, o_code) IN (SELECT v, c FROM present)")], unit="MRREL MED-RT rows")
        ins("UMLS: MED-RT drug -> mechanism of action / physiologic effect class", f"""SELECT DISTINCT s_vocab, s_code, predicate, o_vocab,
                o_code, 'UMLS (MED-RT)', 'MRREL 2026AA Level 0 ' || rela, how, 'ungraded', 'asserted', '{PIN['umls_rel']}',
                json_object('medrt_rela', rela, 'drug_cui', cui_s)
            FROM '{UMLS_REL}' WHERE sab = 'MED-RT' AND o_vocab = 'MEDRT' AND (s_vocab, s_code) IN (SELECT v, c FROM present)""",
            src=f"'{UMLS_REL}' WHERE sab = 'MED-RT' AND o_vocab = 'MEDRT'",
            keep=[("drug not a node the graph holds", "(s_vocab, s_code) IN (SELECT v, c FROM present)")], unit="MRREL MED-RT rows")
        con.execute(f"""INSERT INTO name_hint SELECT 'MEDRT', o_code, any_value(o_name) FROM '{UMLS_REL}' WHERE o_vocab = 'MEDRT' GROUP BY 2""")
        # a MED-RT mechanism / effect the FDA's label indexing also asserts for the same drug: two independent sources on one
        # fact. The method says so, and graph_report.py tiers corroborated and uncorroborated edges apart.
        con.execute("""UPDATE edge SET method = method || '; corroborated by FDA SPL'
            WHERE predicate IN ('medrt:has_mechanism_of_action', 'medrt:has_physiologic_effect')
              AND (s_code, o_code) IN (SELECT r.o_code, f.o_code FROM edge f JOIN edge r ON r.predicate = 'drugcentral:rxnorm' AND r.s_code = f.s_code
                                       WHERE f.predicate = 'fda:pharmacologic_class' AND f.method IN ('MoA', 'PE'))""")
        # Two more witnesses from DrugCentral, curated apart from MED-RT: its label indications (for may_treat, same drug
        # and the same SNOMED concept -- a MeSH disease through its same-name SNOMED concept) and its MeSH pharmacological
        # actions (for mechanism of action, same drug and the same class once wording is set aside: "Adrenergic
        # alpha2-Antagonists" = "Adrenergic alpha-2 Receptor Antagonists"). Corroborated edges are tiered apart.
        con.execute("""UPDATE edge SET method = method || '; corroborated by DrugCentral indication'
            WHERE predicate = 'medrt:may_treat' AND (s_code, o_vocab, o_code) IN (
                SELECT m.s_code, m.o_vocab, m.o_code FROM edge m
                JOIN edge r ON r.predicate = 'drugcentral:rxnorm' AND r.o_code = m.s_code
                JOIN edge i ON i.predicate = 'drugcentral:indication' AND i.s_code = r.s_code
                LEFT JOIN edge x ON m.o_vocab = 'MESH' AND x.predicate = 'umls:shared_cui' AND x.s_vocab = 'MESH' AND x.s_code = m.o_code AND x.o_vocab = 'SCT'
                WHERE m.predicate = 'medrt:may_treat' AND i.o_code = CASE WHEN m.o_vocab = 'SCT' THEN m.o_code ELSE x.o_code END)""")
        if (DC / "pharma_class.tsv").exists():
            stop = {"receptor", "receptors", "agents", "agent", "drugs", "drug", "of", "the", "and"}
            def class_key(v):
                v = re.sub(r"\s*\[(moa|pe|epc|cs)\]\s*$", "", (v or "").lower())
                v = re.sub(r"([a-z])(\d)", r"\1 \2", v)
                return " ".join(sorted({w[:-1] if w.endswith("s") and len(w) > 3 else w for w in re.findall(r"[a-z0-9]+", v)} - stop))
            con.create_function("class_key", class_key, ["VARCHAR"], "VARCHAR")
            con.execute(f"""CREATE TEMP TABLE mesh_pa AS SELECT DISTINCT struct_id dc, class_key(name) k FROM {dc('pharma_class')}
                            WHERE source = 'MeSH' AND type = 'PA'""")
            con.execute("""CREATE TEMP TABLE medrt_cls AS SELECT code, class_key(name) k FROM name_hint WHERE vocab = 'MEDRT' AND name IS NOT NULL""")
            con.execute("""UPDATE edge SET method = method || '; corroborated by MeSH pharmacological action (DrugCentral)'
                WHERE predicate = 'medrt:has_mechanism_of_action' AND method NOT LIKE '%corroborated%' AND (s_code, o_code) IN (
                    SELECT r.o_code, c.code FROM edge r JOIN mesh_pa p ON p.dc = r.s_code JOIN medrt_cls c ON c.k = p.k
                    WHERE r.predicate = 'drugcentral:rxnorm')""")

    # --- medicines: the hierarchies and cross-links the drug vocabularies already state ------------------------------
    # ATC, RxNorm, RxNorm Extension and MED-RT arrived as leaves joined to other vocabularies, with no structure of their
    # own. Each link below is asserted by the source named; Athena's are loaded only between nodes the graph already
    # holds, so its millions of rows add structure, not a second drug dictionary.
    con.execute("DROP TABLE IF EXISTS present")
    con.execute("""CREATE TEMP TABLE present AS SELECT DISTINCT s_vocab v, s_code c FROM edge UNION SELECT DISTINCT o_vocab, o_code FROM edge""")
    atc_json = PBS / "atc-codes.json"
    if atc_json.exists():
        atc_rows = json.load(open(atc_json))["rows"]
        ins_rows("ATC class -> parent class (PBS)", [("ATC", r["atc_code"], "atc:is_a", "ATC", r["atc_parent_code"], "PBS Public API v3",
                                                    "atc-codes.json", "PBS ATC level " + str(r["atc_level"]), "native", "asserted", PIN["pbs"], None)
                                                   for r in atc_rows if r.get("atc_parent_code")],
                 available=len(atc_rows), excluded=[("top level: no parent", sum(1 for r in atc_rows if not r.get("atc_parent_code")))],
                 unit="PBS ATC codes")
        con.executemany("INSERT INTO name_hint VALUES ('ATC', ?, ?)", [(r["atc_code"], r["atc_description"]) for r in atc_rows])
    ins("ATC class -> parent class (Athena)", """SELECT DISTINCT 'ATC', a.concept_code, 'atc:is_a', 'ATC', b.concept_code, 'OMOP Athena',
            'CONCEPT_RELATIONSHIP Is a', 'Athena ATC Is a', 'native', 'asserted', '""" + PIN["athena"] + """', NULL
        FROM CR r JOIN C a ON a.concept_id = r.concept_id_1 AND a.vocabulary_id = 'ATC' JOIN C b ON b.concept_id = r.concept_id_2 AND b.vocabulary_id = 'ATC'
        WHERE r.relationship_id = 'Is a' AND r.invalid_reason IS NULL""",
        src="CR r JOIN C a ON a.concept_id = r.concept_id_1 AND a.vocabulary_id = 'ATC' WHERE r.relationship_id = 'Is a'",
        keep=[("relationship retired", "r.invalid_reason IS NULL")], unit="Athena ATC Is a rows")
    # ATC -> RxNorm / RxNorm Extension: OHDSI's curated class assignment. Primary (the drug's own class, and the classes
    # above it) and secondary (a class the drug belongs to as one part of a combination, or through another indication)
    # are kept apart.
    atc_rel = {"ATC - RxNorm": "primary", "ATC - RxNorm pr lat": "primary", "ATC - RxNorm pr up": "primary",
               "Drug class of drug": "primary", "Maps to": "primary", "ATC - RxNorm sec lat": "secondary", "ATC - RxNorm sec up": "secondary"}
    rcase = " ".join(f"WHEN '{k}' THEN 'atc:rxnorm_{v}'" for k, v in atc_rel.items())
    atc_src = ("CR r JOIN C a ON a.concept_id = r.concept_id_1 AND a.vocabulary_id = 'ATC' JOIN C b ON b.concept_id = r.concept_id_2 "
               "AND b.vocabulary_id IN ('RxNorm', 'RxNorm Extension') WHERE r.relationship_id IN (" + ",".join(repr(k) for k in atc_rel) + ")")
    ins("ATC class -> RxNorm drug (Athena, primary / secondary)", f"""SELECT DISTINCT 'ATC', a.concept_code, CASE r.relationship_id {rcase} END,
            CASE b.vocabulary_id WHEN 'RxNorm' THEN 'RXN' ELSE 'RXE' END, b.concept_code, 'OMOP Athena', 'CONCEPT_RELATIONSHIP ' || r.relationship_id,
            r.relationship_id, 'native', 'asserted', '{PIN['athena']}', NULL
        FROM {atc_src} AND r.invalid_reason IS NULL
          AND ('ATC', a.concept_code) IN (SELECT v, c FROM present)
          AND (CASE b.vocabulary_id WHEN 'RxNorm' THEN 'RXN' ELSE 'RXE' END, b.concept_code) IN (SELECT v, c FROM present)""",
        src=atc_src, keep=[("relationship retired", "r.invalid_reason IS NULL"),
                           ("ATC class not a node the graph holds", "('ATC', a.concept_code) IN (SELECT v, c FROM present)"),
                           ("drug not a node the graph holds", "(CASE b.vocabulary_id WHEN 'RxNorm' THEN 'RXN' ELSE 'RXE' END, b.concept_code) IN (SELECT v, c FROM present)")],
        unit="Athena ATC -> RxNorm rows")
    # RxNorm Extension -> RxNorm: what an extension product is in RxNorm's own terms. One predicate per relationship.
    rxe_rel = {"Marketed form of": "rxe:marketed_form_of", "Tradename of": "rxe:tradename_of", "Box of": "rxe:box_of",
               "RxNorm has ing": "rxe:has_ingredient", "Quantified form of": "rxe:quantified_form_of", "Consists of": "rxe:consists_of",
               "RxNorm is a": "rxe:is_a"}
    xcase_ = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in rxe_rel.items())
    rxe_src = ("CR r JOIN C a ON a.concept_id = r.concept_id_1 AND a.vocabulary_id = 'RxNorm Extension' JOIN C b ON b.concept_id = r.concept_id_2 "
               "AND b.vocabulary_id = 'RxNorm' WHERE r.relationship_id IN (" + ",".join(repr(k) for k in rxe_rel) + ")")
    ins("RxNorm Extension -> RxNorm (Athena)", f"""SELECT DISTINCT 'RXE', a.concept_code, CASE r.relationship_id {xcase_} END, 'RXN', b.concept_code,
            'OMOP Athena', 'CONCEPT_RELATIONSHIP ' || r.relationship_id, r.relationship_id, 'native', 'asserted', '{PIN['athena']}', NULL
        FROM {rxe_src} AND r.invalid_reason IS NULL AND ('RXE', a.concept_code) IN (SELECT v, c FROM present)
          AND ('RXN', b.concept_code) IN (SELECT v, c FROM present)""",
        src=rxe_src, keep=[("relationship retired", "r.invalid_reason IS NULL"),
                           ("RxNorm Extension product not a node the graph holds", "('RXE', a.concept_code) IN (SELECT v, c FROM present)"),
                           ("RxNorm concept not a node the graph holds", "('RXN', b.concept_code) IN (SELECT v, c FROM present)")],
        unit="Athena RxNorm Extension -> RxNorm rows")
    # MeSH supplementary record -> the heading(s) it is indexed under, and MED-RT's class hierarchy: both are in UMLS
    # MRREL (Level 0, held), never in the derived relationship file. REL is the second atom's relation to the first.
    U2 = Path("cache/umls/2026AA")
    if (U2 / "mrrel_l0.parquet").exists() and (U2 / "aui_l0.parquet").exists():
        con.execute(f"CREATE TEMP VIEW ur AS SELECT * FROM '{U2 / 'mrrel_l0.parquet'}'")
        con.execute(f"CREATE TEMP VIEW ua AS SELECT * FROM '{U2 / 'aui_l0.parquet'}'")
        msh_src = "ur r JOIN ua d ON d.AUI = r.AUI1 JOIN ua s ON s.AUI = r.AUI2 WHERE r.SAB = 'MSH' AND r.RELA = 'mapped_to'"
        ins("MeSH supplementary record -> heading it is mapped to (UMLS)", f"""SELECT DISTINCT 'MESH', s.CODE, 'mesh:mapped_to', 'MESH', d.CODE,
                'UMLS (MSH)', 'MRREL 2026AA Level 0 mapped_to', 'MeSH heading mapped to', 'native', 'asserted', '{PIN['umls_rel']}', NULL
            FROM {msh_src} AND ('MESH', s.CODE) IN (SELECT v, c FROM present)""",
            src=msh_src, keep=[("supplementary record not a node the graph holds", "('MESH', s.CODE) IN (SELECT v, c FROM present)")],
            unit="MRREL MSH mapped_to rows")
        con.execute("""INSERT INTO name_hint SELECT 'MESH', d.CODE, any_value(d.STR) FROM ur r JOIN ua d ON d.AUI = r.AUI1
                       WHERE r.SAB = 'MSH' AND r.RELA = 'mapped_to' GROUP BY 2""")
        mrt_src = ("ur r JOIN ua c ON c.AUI = r.AUI1 JOIN ua p ON p.AUI = r.AUI2 WHERE r.SAB = 'MED-RT' AND r.REL = 'PAR' "
                   "AND c.CODE LIKE 'N%' AND p.CODE LIKE 'N%'")
        ins("MED-RT class -> parent class (UMLS)", f"""SELECT DISTINCT 'MEDRT', c.CODE, 'medrt:is_a', 'MEDRT', p.CODE, 'UMLS (MED-RT)',
                'MRREL 2026AA Level 0 PAR', 'MED-RT class hierarchy', 'native', 'asserted', '{PIN['umls_rel']}', NULL FROM {mrt_src}""",
            src="ur r JOIN ua c ON c.AUI = r.AUI1 JOIN ua p ON p.AUI = r.AUI2 WHERE r.SAB = 'MED-RT' AND r.REL = 'PAR' AND p.CODE LIKE 'N%'",
            keep=[("child is a MED-RT drug (an RxNorm code), not a class", "c.CODE LIKE 'N%'")], unit="MRREL MED-RT PAR rows")
        con.execute("""INSERT INTO name_hint SELECT 'MEDRT', CODE, any_value(STR) FROM ua WHERE SAB = 'MED-RT' AND CODE LIKE 'N%' GROUP BY 2""")

    # --- open sources joined in Wave 3: MedGen's concept mappings, GenCC gene-disease validity, ChEBI's own tree ------
    con.execute("DROP TABLE IF EXISTS present")
    con.execute("""CREATE TEMP TABLE present AS SELECT DISTINCT s_vocab v, s_code c FROM edge UNION SELECT DISTINCT o_vocab, o_code FROM edge""")
    if (DC / "pharma_class.tsv").exists():
        # DrugCentral's MeSH pharmacological actions (Wave 2 family 3): what NLM indexes each drug as doing or being used for
        # ('Anti-Bacterial Agents', 'Cholinesterase Inhibitors'). graph_report.py earns the tier from the MeSH stratum of
        # cache/wave2/drug_pharma_role_handcheck.json. DrugCentral's ChEBI roles are not loaded (ChEBI's own roles are).
        ins("DrugCentral drug -> MeSH pharmacological action (Wave 2)", f"""SELECT DISTINCT 'DRUGCENTRAL', struct_id, 'drugcentral:mesh_pharmacological_action',
                'MESH', class_code, 'DrugCentral', 'pharma_class.tsv MeSH PA', 'MeSH pharmacological action', 'ungraded', 'asserted', '{PIN['dc']}',
                json_object('class_name', name)
            FROM {dc('pharma_class')} WHERE source = 'MeSH' AND type = 'PA' AND class_code IS NOT NULL""",
            src=f"{dc('pharma_class')} WHERE source = 'MeSH'", keep=[("not a pharmacological action (PA) row", "type = 'PA'")],
            unit="DrugCentral pharma_class MeSH rows")
        con.execute(f"INSERT INTO name_hint SELECT 'MESH', class_code, any_value(name) FROM {dc('pharma_class')} WHERE source = 'MeSH' GROUP BY 2")
    # UNII substance <-> RxNorm ingredient sharing a UMLS concept and a name (Wave 2 family 2), for pairs with one end
    # already in the graph and not already reached. Ken's rule, 27 Sep: an RxNorm "X extract" is the same ingredient as
    # the UNII for X. graph_report.py earns the tier from cache/wave2/unii_rxnorm_handcheck.json.
    if WAVE2_UNII.exists():
        un_keep = "(('UNII', unii) IN (SELECT v, c FROM present) OR ('RXN', rxcui) IN (SELECT v, c FROM present))"
        ins("UNII substance <-> RxNorm ingredient (UMLS shared concept, same name; Wave 2)", f"""SELECT DISTINCT 'UNII', unii, 'umls:unii_rxnorm', 'RXN', rxcui,
                'UMLS', 'MRCONSO 2026AA MTHSPL SU + RXNORM ' || tty, 'shared CUI, same name', 'ungraded', 'asserted', '{PIN['umls_rel']}',
                json_object('cui', cui, 'rxnorm_tty', tty)
            FROM '{WAVE2_UNII}' WHERE gate AND NOT present AND {un_keep}""",
            src=f"'{WAVE2_UNII}'", keep=[("names differ (the shared-name gate)", "gate"), ("the graph already reaches the pair", "NOT present"),
                                         ("neither the UNII nor the RxNorm ingredient is a node the graph holds", un_keep)],
            unit="Wave 2 UNII <-> RxNorm candidate pairs")
    if MEDGEN_MAP.exists():
        # MedGen groups each condition's codes from the sources it integrates. Loaded for the MedGen concepts the graph already
        # holds (MONDO's exact matches); MedGen's own UID is the node key, the UMLS CUI (or CN id) only joins the rows.
        mg = f"read_csv('{MEDGEN_MAP}', delim='|', header=false, skip=1, all_varchar=true, quote='')"
        con.execute(f"CREATE TEMP TABLE mg_uid AS SELECT column0 cui, column2 uid FROM {mg} WHERE column3 = 'MedGen'")
        mv = {"HPO": "HP", "OMIM": "OMIM", "Orphanet": "ORPHA", "MONDO": "MONDO", "SNOMEDCT_US": "SCT", "MeSH": "MESH", "GARD": "GARD"}
        mcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in mv.items())
        mg_src = f"{mg} m JOIN mg_uid u ON u.cui = m.column0 WHERE m.column3 <> 'MedGen'"
        ins("MedGen concept -> its codes in HPO, OMIM, Orphanet, MONDO, SNOMED, MeSH, GARD", f"""SELECT DISTINCT 'MEDGEN', u.uid, 'medgen:xref',
                CASE m.column3 {mcase} END, CASE WHEN m.column3 = 'Orphanet' THEN replace(m.column2, 'Orphanet_', '') ELSE m.column2 END,
                'NCBI MedGen', 'MedGenIDMappings.txt', 'MedGen concept groups ' || m.column3, 'native', 'asserted', '{PIN['medgen']}', NULL
            FROM {mg_src} AND m.column3 IN ({','.join(repr(k) for k in mv)}) AND ('MEDGEN', u.uid) IN (SELECT v, c FROM present)
              AND (m.column3 <> 'SNOMEDCT_US' OR m.column2 IN (SELECT id FROM cmp.concept))""",
            src=mg_src, keep=[("a source the graph does not hold (OMIM allelic variants, included entries, phenotypic series)",
                               f"m.column3 IN ({','.join(repr(k) for k in mv)})"),
                              ("MedGen concept not a node the graph holds", "('MEDGEN', u.uid) IN (SELECT v, c FROM present)"),
                              ("SNOMED code not active in SNOMED CT-AU", "m.column3 <> 'SNOMEDCT_US' OR m.column2 IN (SELECT id FROM cmp.concept)")],
            unit="MedGenIDMappings rows")
    if GENCC.exists():
        # GenCC: each submitter's gene-disease validity call (ClinGen, PanelApp Australia, Orphanet, G2P, laboratories ...), one
        # edge per gene, disease and submitter; the classification is the method. Disputed, refuted and "no known disease
        # relationship" calls are claims AGAINST the link and are not loaded as links.
        gc = f"read_csv('{GENCC}', delim='\t', header=true, all_varchar=true, quote='\"')"
        neg = "('Disputed Evidence', 'Refuted Evidence', 'No Known Disease Relationship')"
        ins("GenCC gene -> disease validity (per submitter)", f"""SELECT 'HGNC', gene_curie, 'gencc:gene_disease', 'MONDO', disease_curie, 'GenCC',
                'gencc-submissions.tsv ' || any_value(submitter_title), any_value(classification_title), 'native', 'asserted', '{PIN['gencc']}',
                json_object('submitter', any_value(submitter_title), 'classification', any_value(classification_title),
                            'mode_of_inheritance', any_value(moi_title), 'submitted_as', any_value(submitted_as_disease_id),
                            'submissions', count(*))
            FROM {gc} WHERE classification_title NOT IN {neg} AND gene_curie LIKE 'HGNC:%' AND disease_curie LIKE 'MONDO:%'
            GROUP BY gene_curie, disease_curie, submitter_curie""",
            src=f"{gc}", keep=[("a claim against the link (disputed, refuted, no known relationship)", f"classification_title NOT IN {neg}"),
                               ("gene or disease not HGNC / MONDO", "gene_curie LIKE 'HGNC:%' AND disease_curie LIKE 'MONDO:%'")],
            unit="GenCC submissions")
        con.execute(f"INSERT INTO name_hint SELECT 'HGNC', gene_curie, any_value(gene_symbol) FROM {gc} GROUP BY 2")
        con.execute(f"INSERT INTO name_hint SELECT 'MONDO', disease_curie, any_value(disease_title) FROM {gc} GROUP BY 2")
    if CHEBI_OBO.exists():
        # ChEBI's own is-a tree, climbed upward from the ChEBI entities the graph already holds (never down: a class does not
        # pull in the thousands of chemicals under it), and each entity's roles (RO:0000087 has role: 'antibacterial drug').
        import gzip
        terms, cur = {}, None
        for line in gzip.open(CHEBI_OBO, "rt", encoding="utf-8"):
            line = line.rstrip("\n")
            if line == "[Term]":
                cur = {"is_a": [], "role": []}
            elif line.startswith("["):
                cur = None
            elif cur is not None and line.startswith("id: CHEBI:"):
                cur["id"] = line[10:]
                terms[cur["id"]] = cur
            elif cur is not None and line.startswith("name: "):
                cur["name"] = line[6:]
            elif cur is not None and line.startswith("is_a: CHEBI:"):
                cur["is_a"].append(line[12:].split(" ")[0])
            elif cur is not None and line.startswith("relationship: RO:0000087 CHEBI:"):
                cur["role"].append(line.split("CHEBI:", 1)[1].split(" ")[0])
            elif cur is not None and line == "is_obsolete: true":
                cur["obsolete"] = True
        live = {k for k, t in terms.items() if not t.get("obsolete")}
        held = {c for (v, c) in con.execute("SELECT v, c FROM present WHERE v = 'CHEBI'").fetchall()} & live
        role_rows = sorted({(c, r) for c in held for r in terms[c]["role"] if r in live})
        seen, todo, isa = set(), set(held) | {r for _, r in role_rows}, set()
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            seen.add(c)
            for p_ in terms[c]["is_a"]:
                if p_ in live:
                    isa.add((c, p_))
                    todo.add(p_)
        ins_rows("ChEBI entity -> role (has role)", [("CHEBI", c, "chebi:has_role", "CHEBI", r, "ChEBI", "chebi.obo RO:0000087", "has role",
                                                       "native", "asserted", PIN["chebi"], None) for c, r in role_rows],
                 available=len(role_rows), unit="has-role statements of ChEBI entities the graph holds")
        ins_rows("ChEBI entity -> parent (is a), upward from the graph's entities", [("CHEBI", c, "chebi:is_a", "CHEBI", p_, "ChEBI", "chebi.obo is_a",
                                                       "native", "native", "asserted", PIN["chebi"], None) for c, p_ in sorted(isa)],
                 available=len(isa), unit="is_a statements above the graph's ChEBI entities")
        con.executemany("INSERT INTO name_hint VALUES ('CHEBI', ?, ?)", [(c, terms[c].get("name")) for c in seen if terms[c].get("name")])

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
    if (AU_RF2 / "Refset").exists():
        # a retired SCTID the AU release still describes: SNOMED's own historical association (REPLACED BY, SAME AS,
        # POSSIBLY EQUIVALENT TO ...) and the AU substance map, to an active concept -- the release's answer, not a guess
        ins("retired SNOMED -> current (historical association)", f"""SELECT DISTINCT 'SCT', a.referencedComponentId, 'sct:historical_association',
                'SCT', a.targetComponentId, 'SNOMED CT-AU RF2', 'association reference set ' || a.refsetId, t.pt, 'native', 'asserted',
                '{PIN['sct']}', json_object('association', t.pt)
            FROM {ref('Content', f'der2_cRefset_AssociationSnapshot_AU1000036_{rel_}.txt')} a
            JOIN cmp.concept t ON t.id = a.refsetId
            WHERE a.active = '1' AND a.refsetId NOT IN ('734138000', '734139008')
              AND a.referencedComponentId IN (SELECT code FROM foreign_sct) AND a.targetComponentId IN (SELECT id FROM native_sct)
            UNION SELECT DISTINCT 'SCT', m.referencedComponentId, 'sct:historical_association', 'SCT', m.targetSnomedCtSubstance,
                'SNOMED CT-AU RF2', 'Substance to SNOMED CT-AU mapping reference set 281000036105', 'Substance map: ' || t.pt, 'native',
                'asserted', '{PIN['sct']}', json_object('association', 'substance map ' || lower(t.pt))
            FROM {ref('Map', f'der2_csRefset_AttributeValueMapSnapshot_AU1000036_{rel_}.txt')} m JOIN cmp.concept t ON t.id = m.mapType
            WHERE m.active = '1' AND m.referencedComponentId IN (SELECT code FROM foreign_sct)
              AND m.targetSnomedCtSubstance IN (SELECT id FROM native_sct)""",
            derived="SNOMED ids any loader brought that the AU release does not carry, resolved by its historical associations "
                    "and the substance map")
        # the release still carries the retired concepts' descriptions: name them from it
        con.execute(f"""INSERT INTO name_hint SELECT 'SCT', d.conceptId, any_value(d.term) FROM {ref('../Terminology', f'sct2_Description_Snapshot-en-au_AU1000036_{rel_}.txt')} d
            WHERE d.active = '1' AND d.conceptId IN (SELECT code FROM foreign_sct) AND d.typeId = '900000000000003001' GROUP BY 2""")
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
        FROM anc JOIN best USING (code, lvl)""", derived="foreign SNOMED ids -> their nearest ancestor in SNOMED CT-AU (Athena CONCEPT_ANCESTOR)")
    log["foreign SNOMED ids (not in the AU release)"] = con.execute("SELECT count(*) FROM foreign_sct").fetchone()[0]

    # --- the contract ------------------------------------------------------------------------------------------------
    # --- decisions a person made on the review queues (reference/candidate_decisions.json, scripts/review_sheets.py) --
    # An accepted candidate is an edge a person vouches for: tier 'decision', method naming the reviewer and date. A
    # rejection or "none of these" is counted, not loaded -- it only keeps the subject out of the next review sheet.
    if DECISIONS.exists():
        dq = json.load(open(DECISIONS))
        qp = {q: v["predicate"] for q, v in dq.get("queues", {}).items()}
        acc = [d for d in dq.get("decisions", []) if d["decision"] == "accept" and d.get("object")]
        rows_d = [(d["subject"]["vocab"], d["subject"]["code"], qp[d["queue"]], d["object"]["vocab"], d["object"]["code"], "reviewer",
                   "reference/candidate_decisions.json", f"confirmed by {d['reviewer']} {d['date']}", "decision", "asserted",
                   "reference/candidate_decisions.json", json.dumps({"queue": d["queue"], **({"note": d["note"]} if d.get("note") else {})}))
                  for d in acc]
        active_sct = {c for (c,) in con.execute("SELECT id FROM cmp.concept").fetchall()} if rows_d else set()
        keep_d = [r for r in rows_d if r[3] != "SCT" or r[4] in active_sct]
        ins_rows("Decisions by a person on the review queues (accepted)", keep_d, available=len(dq.get("decisions", [])),
                 excluded=[(f"{k_} (recorded, not an edge)", sum(d["decision"] == k_ for d in dq.get("decisions", []))) for k_ in ("reject", "none")]
                          + [("SNOMED CT concept no longer active", len(rows_d) - len(keep_d))], unit="decisions")
        log["Decisions by a person: not loaded, SNOMED CT concept no longer active"] = len(rows_d) - len(keep_d)
        for k_ in ("reject", "none"):
            log[f"Decisions by a person: {k_} (recorded, not an edge)"] = sum(d["decision"] == k_ for d in dq.get("decisions", []))

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
    # concrete values answer to the register too: their attribute types are snomed_concrete_attributes
    con.execute("CREATE TEMP TABLE cpred (id VARCHAR, status VARCHAR)")
    con.executemany("INSERT INTO cpred VALUES (?, ?)", [(p["id"], p["status"]) for p in reg.get("snomed_concrete_attributes", [])])
    bad += con.execute("""
        SELECT 'unregistered concrete attribute', v.predicate, count(*) FROM concrete_value v LEFT JOIN cpred p ON p.id = v.predicate
          WHERE p.id IS NULL GROUP BY 2
        UNION ALL SELECT 'concrete attribute not loadable (' || p.status || ')', v.predicate, count(*) FROM concrete_value v
          JOIN cpred p ON p.id = v.predicate WHERE p.status <> 'built' GROUP BY 1, 2
        UNION ALL SELECT 'concrete value unreadable', predicate, count(*) FROM concrete_value
          WHERE (datatype <> 'string' AND value_num IS NULL) OR (datatype = 'string' AND value_str IS NULL) GROUP BY 2
        UNION ALL SELECT 'concrete value with no source (rule zero)', predicate, count(*) FROM concrete_value
          WHERE source IS NULL OR source = '' GROUP BY 2""").fetchall()
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
    conso = Path("cache/umls/2026AA/mrconso.parquet")
    if conso.exists():           # any still-unnamed node of a UMLS source vocabulary: that source's preferred atom (level 0 / SNOMED)
        con.execute(f"""INSERT INTO name_hint SELECT k.vocab, k.code, arg_min(m.STR, CASE WHEN m.TTY IN ('MH', 'NM', 'PT', 'PN', 'SCN', 'IN', 'LN', 'LPN', 'LA')
                            THEN 0 ELSE 1 END) FROM keys k
            JOIN '{conso}' m ON m.CODE = k.code AND m.SUPPRESS = 'N' AND m.SRL IN (0, 9) AND m.SAB = CASE k.vocab WHEN 'MESH' THEN 'MSH' WHEN 'NCIT' THEN 'NCI'
                 WHEN 'OMIM' THEN 'OMIM' WHEN 'FMA' THEN 'FMA' WHEN 'LOINC' THEN 'LNC' WHEN 'HGNC' THEN 'HGNC' WHEN 'RXN' THEN 'RXNORM' ELSE NULL END
            WHERE (k.vocab, k.code) NOT IN (SELECT vocab, code FROM name_hint WHERE name IS NOT NULL AND trim(name) <> '' AND name <> vocab || ':' || code)
            GROUP BY 1, 2""")
    if UMLS_PAIRS.exists():      # a UMLS name only where no source of the node's own vocabulary names it
        con.execute("CREATE TEMP TABLE umls_names (vocab VARCHAR, code VARCHAR, name VARCHAR)")
        con.executemany("INSERT INTO umls_names VALUES (?, ?, ?)", umls_names)
        con.execute("""INSERT INTO name_hint SELECT DISTINCT u.vocab, u.code, u.name FROM umls_names u
                       WHERE (u.vocab, u.code) NOT IN (SELECT vocab, code FROM name_hint WHERE name IS NOT NULL AND trim(name) <> ''
                                                         AND name <> vocab || ':' || code)""")
    if HGNC_SET.exists():
        con.execute("CREATE TEMP TABLE hgnc_names (vocab VARCHAR, code VARCHAR, name VARCHAR)")
        con.executemany("INSERT INTO hgnc_names VALUES (?, ?, ?)", hgnc_names)
        con.execute("""INSERT INTO name_hint SELECT DISTINCT h.vocab, h.code, h.name FROM hgnc_names h
                       WHERE (h.vocab, h.code) NOT IN (SELECT vocab, code FROM name_hint WHERE name IS NOT NULL AND trim(name) <> '')""")
    con.execute("""INSERT INTO name_hint SELECT vocab, code, vocab || ':' || code FROM keys
                   WHERE vocab IN ('CHEBI', 'UNII', 'PUBCHEM', 'CHEMBL', 'MESH', 'UMLS', 'IUPHAR', 'KEGG', 'INN', 'HGNC', 'CLINVAR', 'MEDGEN',
                                   'ICD11', 'ICD10WHO', 'OMIMPS', 'EFO', 'DOID', 'NCIT', 'ICD11MMS', 'GARD', 'UNIPROT')
                     AND (vocab, code) NOT IN (SELECT vocab, code FROM name_hint WHERE name IS NOT NULL AND trim(name) <> '')""")   # an identifier with no loaded label is named by itself
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
    # the ledger, balanced: the rows the filters kept against the edges loaded, and any difference named
    out_l = []
    for label in dict.fromkeys(loaders):
        e = dict(ledger.get(label, {"kind": "undeclared", "available": None, "excluded": [], "unit": "rows"}))
        e["loaded"], e["excluded"] = log.get(label, 0), [x for x in e["excluded"] if x["rows"]]
        if e["kind"] == "source":
            kept = e["available"] - sum(x["rows"] for x in e["excluded"])
            if kept > e["loaded"]:
                e["excluded"].append({"reason": "collapsed into fewer edges (duplicate rows, or several rows naming one edge)",
                                      "rows": kept - e["loaded"]})
            elif kept < e["loaded"]:
                e["fanned_out"] = e["loaded"] - kept          # one source row gives several edges (a row's several targets)
        out_l.append({"loader": label, **e})
    con.execute("""CREATE TABLE loader_ledger (loader VARCHAR, kind VARCHAR, unit VARCHAR, available BIGINT, loaded BIGINT,
                   fanned_out BIGINT, reason VARCHAR, rows BIGINT)""")
    con.executemany("INSERT INTO loader_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(e["loader"], e["kind"], e["unit"], e["available"], e["loaded"], e.get("fanned_out"), x["reason"], x["rows"])
                     for e in out_l for x in (e["excluded"] or [{"reason": None, "rows": None}])])
    kinds = collections.Counter(e["kind"] for e in out_l)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps({"_note": "Per-loader ledger (scripts/build_edges.py): source rows available, each exclusion with its "
                                           "reason, edges loaded. 'derived' loaders are rules over edges already loaded.",
                                  "loaders": len(out_l), "by_kind": dict(kinds), "ledger": out_l}, indent=1) + "\n")
    print(f"\nledger: {len(out_l)} loaders -- {kinds['source']} with source rows, {kinds['derived']} derived, "
          f"{kinds['undeclared']} undeclared -> {LEDGER}")

    n_edges = con.execute("SELECT count(*) FROM edge").fetchone()[0]
    n_nodes = con.execute("SELECT count(*) FROM node").fetchone()[0]
    unnamed = con.execute("SELECT vocab, count(*) FROM node WHERE name IS NULL GROUP BY 1 ORDER BY 2 DESC").fetchall()
    n_vals = con.execute("SELECT count(*) FROM concrete_value").fetchone()[0]
    con.close()
    print(f"\ngraph: {n_nodes:,} nodes, {n_edges:,} edges, {n_vals:,} concrete values -> {GRAPH}   (all validated against the register)")
    print("nodes without a name, by vocabulary:", unnamed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
