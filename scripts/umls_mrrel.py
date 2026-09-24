#!/usr/bin/env python3
"""UMLS relationships (MRREL, Level 0 subset 2026AA) -> edges for build_edges.py.

Two kinds, kept apart because they rest on different evidence:

  1. A source's OWN hierarchy, relayed by UMLS: the MeSH tree, NCI Thesaurus is-a, FMA is-a, and LOINC's part hierarchy
     (vocabularies the graph holds without their hierarchy). The only UMLS step is atom -> the source's own code, which is
     bookkeeping, so these are native assertions of that source (`umls:source_parent`, child -> parent).
  2. MED-RT (the VA's medication reference terminology, public domain): may_treat, may_prevent, may_diagnose,
     contraindicated with a disease, mechanism of action, physiologic effect. MED-RT asserts them between its own concepts;
     reaching the graph's RxNorm ingredient and SNOMED / MeSH disease codes takes a shared-CUI step on each side, so these
     are tiered by hand check and witnessed against DrugCentral (graph_report.py). Mechanism and physiologic-effect classes
     stay MED-RT's own codes (vocabulary MEDRT).

UMLS writes a relationship as "the second atom to the first": a row (disease, may_treat, drug) means the drug may treat
the disease; a PAR row (child, PAR, parent) names the parent second. Levels 1-4 sources are not in the Level 0 subset.

    scripts/umls_mrrel.py --download   # umls-2026AA-metathesaurus-level0.zip, 2.0 GB, with the key in .env (never printed)
    scripts/umls_mrrel.py              # extract MRREL/MRCONSO/MRSAB/MRMAP to parquet (raw RRF deleted), then the edges
                                       # -> cache/umls/umls_rel_edges.parquet (needs cache/umls/2026AA/mrconso.parquet too)

UMLS-derived: cache/umls/ only (git-ignored), not redistributed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import duckdb

RELEASE = "2026AA"
D = Path("cache/umls") / RELEASE
ZIP = D / f"umls-{RELEASE}-metathesaurus-level0.zip"
REL, AUI, CONSO = D / "mrrel_l0.parquet", D / "aui_l0.parquet", D / "mrconso.parquet"
OUT = Path("cache/umls/umls_rel_edges.parquet")
HIER = {"MSH": "MESH", "NCI": "NCIT", "FMA": "FMA", "LNC": "LOINC"}
MEDRT = {"may_treat": "medrt:may_treat", "may_prevent": "medrt:may_prevent", "may_diagnose": "medrt:may_diagnose",
         "contraindicated_with_disease": "medrt:contraindicated_with", "has_mechanism_of_action": "medrt:has_mechanism_of_action",
         "has_physiologic_effect": "medrt:has_physiologic_effect"}
CLASS_RELA = ("has_mechanism_of_action", "has_physiologic_effect")


def download() -> None:
    sys.path.insert(0, "scripts")
    import umls_crosswalk
    src = f"https://download.nlm.nih.gov/umls/kss/{RELEASE}/umls-{RELEASE}-metathesaurus-level0.zip"
    D.mkdir(parents=True, exist_ok=True)
    t = time.time()
    try:
        with urllib.request.urlopen("https://uts-ws.nlm.nih.gov/download?" + urllib.parse.urlencode({"url": src, "apiKey": umls_crosswalk.api_key()}),
                                    timeout=180) as r, open(ZIP, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 22)
    except urllib.error.HTTPError as e:
        sys.exit(f"UTS download refused (HTTP {e.code}); the URL holds the key and is not shown")
    print(f"{ZIP} {ZIP.stat().st_size:,} bytes in {time.time() - t:.0f} s")


def extract(con) -> None:
    tmp = D / "l0"
    with zipfile.ZipFile(ZIP) as z:
        for name in z.namelist():
            if name.split("/")[-1] in ("MRREL.RRF", "MRCONSO.RRF", "MRSAB.RRF", "MRMAP.RRF"):
                z.extract(name, tmp)
    m = next(tmp.rglob("MRREL.RRF")).parent
    spec = lambda cols: "{" + ",".join(f"'{k}':'VARCHAR'" for k in cols) + "}"
    rd = lambda f, cols: f"read_csv('{m / f}', delim='|', header=false, quote='', escape='', columns={spec(cols.split())})"
    con.execute(f"""COPY (SELECT CUI1, AUI1, STYPE1, REL, CUI2, AUI2, STYPE2, RELA, SAB, DIR, SUPPRESS FROM
        {rd('MRREL.RRF', 'CUI1 AUI1 STYPE1 REL CUI2 AUI2 STYPE2 RELA RUI SRUI SAB SL RG DIR SUPPRESS CVF X')}) TO '{REL}' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"""COPY (SELECT AUI, CUI, SAB, TTY, CODE, STR, SUPPRESS FROM
        {rd('MRCONSO.RRF', 'CUI LAT TS LUI STT SUI ISPREF AUI SAUI SCUI SDUI SAB TTY CODE STR SRL SUPPRESS CVF X')}) TO '{AUI}' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"""COPY (SELECT RSAB, VSAB, SON, SRL, CURVER, SVER FROM
        {rd('MRSAB.RRF', 'VCUI RCUI VSAB RSAB SON SF SVER VSTART VEND IMETA RMETA SLC SCC SRL TFR CFR CXTY TTYL ATNL LAT CENC CURVER SABIN SSN SCIT X')})
        TO '{D / "mrsab_l0.parquet"}' (FORMAT parquet)""")
    con.execute(f"""COPY (SELECT * EXCLUDE (X) FROM {rd('MRMAP.RRF', 'MAPSETCUI MAPSETSAB MAPSUBSETID MAPRANK MAPID MAPSID FROMID FROMSID FROMEXPR FROMTYPE FROMRULE FROMRES REL RELA TOID TOSID TOEXPR TOTYPE TORULE TORES MAPRULE MAPRES MAPTYPE MAPATN MAPATV CVF X')})
        TO '{D / "mrmap_l0.parquet"}' (FORMAT parquet, COMPRESSION zstd)""")
    shutil.rmtree(tmp)                       # the RRF files (3.2 GB) are not kept; the zip and the parquet are


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    if a.download or (not REL.exists() and not ZIP.exists()):
        download()
    if not REL.exists() or not AUI.exists():
        extract(duckdb.connect())
    for p in (REL, AUI, CONSO):
        if not p.exists():
            sys.exit(f"missing {p}: run the Level 0 extraction first (docs/multigraph-build.md)")
    con = duckdb.connect()
    con.execute("SET threads=8")
    hcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in HIER.items())
    # 1. source hierarchies: (child, PAR, parent)
    con.execute(f"""CREATE TEMP TABLE hier AS
        SELECT DISTINCT CASE r.SAB {hcase} END s_vocab, c.CODE s_code, 'umls:source_parent' predicate, CASE r.SAB {hcase} END o_vocab,
               p.CODE o_code, r.SAB sab, coalesce(r.RELA, 'PAR') rela, r.CUI1 cui_s, r.CUI2 cui_o, 'source hierarchy' how
        FROM '{REL}' r JOIN '{AUI}' c ON c.AUI = r.AUI1 AND c.SAB = r.SAB AND c.SUPPRESS = 'N'
                       JOIN '{AUI}' p ON p.AUI = r.AUI2 AND p.SAB = r.SAB AND p.SUPPRESS = 'N'
        WHERE r.REL = 'PAR' AND r.SAB IN ({','.join(repr(k) for k in HIER)}) AND r.SUPPRESS = 'N'
          AND c.CODE <> p.CODE AND c.CODE NOT LIKE 'MTH%' AND p.CODE NOT LIKE 'MTH%'
          AND (r.SAB <> 'MSH' OR (c.TTY IN ('MH', 'NM') AND p.TTY IN ('MH', 'NM')))""")
    # 2. MED-RT: row (first, RELA, second) = second RELA first, and the drug is the second atom for every RELA kept here
    #    ("Soft Tissue Infections | may_treat | amikacin"; "Nucleic Acid Synthesis Inhibitors | has_mechanism_of_action | fidaxomicin")
    rel_in = ",".join(repr(k) for k in MEDRT)
    con.execute(f"""CREATE TEMP TABLE medrt AS SELECT r.RELA rela, r.CUI2 drug_cui, r.CUI1 other_cui, a1.CODE other_medrt_code,
               a1.STR other_name, a2.STR drug_name
        FROM '{REL}' r JOIN '{AUI}' a1 ON a1.AUI = r.AUI1 JOIN '{AUI}' a2 ON a2.AUI = r.AUI2
        WHERE r.SAB = 'MED-RT' AND r.SUPPRESS = 'N' AND r.RELA IN ({rel_in})""")
    # a CUI's graph codes: RxNorm ingredients for drugs; SNOMED CT (level 9, the affiliate licence) and MeSH headings for
    # diseases -- from the full MRCONSO, since Level 0 carries no SNOMED atoms
    con.execute(f"""CREATE TEMP TABLE cui_code AS SELECT DISTINCT CUI cui, CASE SAB WHEN 'RXNORM' THEN 'RXN' WHEN 'SNOMEDCT_US' THEN 'SCT'
                        ELSE 'MESH' END v, CODE code
        FROM '{CONSO}' WHERE SUPPRESS = 'N' AND SRL IN (0, 9) AND ((SAB = 'RXNORM' AND TTY IN ('IN', 'PIN'))
             OR (SAB = 'SNOMEDCT_US' AND TTY = 'PT') OR (SAB = 'MSH' AND TTY IN ('MH', 'NM')))""")
    mcase = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in MEDRT.items())
    con.execute(f"""CREATE TEMP TABLE med AS
        SELECT DISTINCT 'RXN' s_vocab, d.code s_code, CASE m.rela {mcase} END predicate, o.v o_vocab, o.code o_code, 'MED-RT' sab,
               m.rela, m.drug_cui cui_s, m.other_cui cui_o, 'MED-RT, both ends through a shared CUI' how
        FROM medrt m JOIN cui_code d ON d.cui = m.drug_cui AND d.v = 'RXN' JOIN cui_code o ON o.cui = m.other_cui AND o.v IN ('SCT', 'MESH')
        WHERE m.rela NOT IN {CLASS_RELA}
        UNION
        SELECT DISTINCT 'RXN', d.code, CASE m.rela {mcase} END, 'MEDRT', m.other_medrt_code, 'MED-RT', m.rela, m.drug_cui, m.other_cui,
               'MED-RT, drug through a shared CUI'
        FROM medrt m JOIN cui_code d ON d.cui = m.drug_cui AND d.v = 'RXN' WHERE m.rela IN {CLASS_RELA}""")
    con.execute(f"""CREATE TEMP TABLE names AS SELECT DISTINCT 'MEDRT' v, other_medrt_code code, any_value(other_name) nm
                    FROM medrt WHERE rela IN {CLASS_RELA} GROUP BY 1, 2""")
    con.execute(f"""COPY (SELECT h.*, NULL::VARCHAR o_name FROM hier h UNION ALL
                          SELECT m.*, n.nm FROM med m LEFT JOIN names n ON n.v = m.o_vocab AND n.code = m.o_code)
                    TO '{OUT}' (FORMAT parquet)""")
    print(con.execute(f"SELECT predicate, sab, count(*) FROM '{OUT}' GROUP BY 1, 2 ORDER BY 3 DESC").fetchall())
    return 0


if __name__ == "__main__":
    sys.exit(main())
