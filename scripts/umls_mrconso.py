#!/usr/bin/env python3
"""UMLS Metathesaurus (MRCONSO) -> the pairs of graph codes that share a UMLS concept (CUI), from the local file instead of
the per-code UTS API (1.7 h for 34,748 SNOMED codes; this is seconds for all of them).

Download (the UMLS licence holder's key, read from .env, never printed):
    scripts/umls_mrconso.py --download         # umls-2026AA-mrconso.zip, 513 MB -> cache/umls/2026AA/
    scripts/umls_mrconso.py                    # -> cache/umls/2026AA/mrconso.parquet and cache/umls/umls_shared_cui.parquet

Rules, each learned on an earlier bridge:
  - Sources by UMLS restriction level: 0 (no additional restrictions) and 9 (SNOMED CT, under the SNOMED affiliate licence
    Australia's membership covers). Levels 1-4 need their own agreements -- ICD-10-CM (4), ICD-10 and ICD-10-AM (3),
    MedDRA, CPT, MEDCIN, ICPC-2 PLUS (3), ORPHANET (1) -- and are left out; the build log says what they would add.
  - Suppressible and obsolete atoms (SUPPRESS <> 'N') are left out.
  - MeSH pairs only through its own heading (MH main heading, NM supplementary name). UMLS files many MeSH entry terms as
    concepts of their own, so an entry-term CUI paired a broad descriptor with a narrow concept (Leukoencephalopathies ->
    Vanishing white matter disease, Nodaviridae -> Alphanodavirus, terodiline -> terodiline hydrochloride): 25/30 on the
    first hand check, before this rule.
  - A shared CUI is synonymy judged by UMLS editors, not a map. `same_name` is true when the two codes share a name in that
    CUI (case, punctuation, word order and SNOMED's semantic tag set aside) -- the rule that held 40/40 for HPO -> SNOMED
    while differing names were right 34/40. build_edges.py loads same-name pairs as edges and writes the rest as candidates.
  - build_edges.py keeps only pairs where at least one code is already a graph node (so nothing arrives detached); this
    script writes every pair and does not read the graph.
UMLS content is licensed: everything written here stays in cache/umls/ (git-ignored) and is not redistributed.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import duckdb

REL = "2026AA"
DIR = Path("cache/umls") / REL
ZIP = DIR / f"umls-{REL}-mrconso.zip"
PARQUET = DIR / "mrconso.parquet"
PAIRS = Path("cache/umls/umls_shared_cui.parquet")
SAB = {"SNOMEDCT_US": "SCT", "LNC": "LOINC", "RXNORM": "RXN", "MSH": "MESH", "NCI": "NCIT", "HGNC": "HGNC", "OMIM": "OMIM",
       "FMA": "FMA", "HPO": "HP", "NCBI": "NCBITAXON", "ATC": "ATC"}
COLS = "CUI LAT TS LUI STT SUI ISPREF AUI SAUI SCUI SDUI SAB TTY CODE STR SRL SUPPRESS CVF X".split()


def download() -> None:
    sys.path.insert(0, "scripts")
    import umls_crosswalk
    key = umls_crosswalk.api_key()
    src = f"https://download.nlm.nih.gov/umls/kss/{REL}/umls-{REL}-mrconso.zip"
    DIR.mkdir(parents=True, exist_ok=True)
    t = time.time()
    try:
        with urllib.request.urlopen("https://uts-ws.nlm.nih.gov/download?" + urllib.parse.urlencode({"url": src, "apiKey": key}),
                                    timeout=120) as r, open(ZIP, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except urllib.error.HTTPError as e:
        sys.exit(f"UTS download refused (HTTP {e.code}); the URL holds the key and is not shown")
    print(f"{ZIP} {ZIP.stat().st_size:,} bytes in {time.time() - t:.0f} s")


def to_parquet(con) -> None:
    with zipfile.ZipFile(ZIP) as z:
        name = next(n for n in z.namelist() if n.endswith("MRCONSO.RRF"))
        z.extract(name, DIR)
    rrf = DIR / name
    spec = "{" + ",".join(f"'{k}':'VARCHAR'" for k in COLS) + "}"
    con.execute(f"""COPY (SELECT CUI, LAT, TS, ISPREF, SAB, TTY, CODE, STR, CAST(SRL AS INT) SRL, SUPPRESS
        FROM read_csv('{rrf}', delim='|', header=false, quote='', escape='', columns={spec}))
        TO '{PARQUET}' (FORMAT parquet, COMPRESSION zstd)""")
    shutil.rmtree(DIR / name.split("/")[0])        # the 2.3 GB RRF is not kept; the zip and the parquet are


def norm(s: str) -> str:
    s = re.sub(r"\s*\((disorder|finding|procedure|body structure|substance|organism|observable entity|qualifier value|"
               r"product|medicinal product|clinical drug|morphologic abnormality|cell|situation|regime/therapy|"
               r"physical object|specimen|assessment scale|record artifact|event)\)\s*$", "", (s or "").lower())
    return " ".join(sorted(re.findall(r"[a-z0-9]+", s)))


def pairs(con) -> None:
    con.execute("CREATE TEMP TABLE sab (sab VARCHAR, v VARCHAR)")
    con.executemany("INSERT INTO sab VALUES (?, ?)", list(SAB.items()))
    con.execute(f"""CREATE TEMP TABLE a AS SELECT m.CUI cui, s.v, m.CODE code, m.STR str
        FROM '{PARQUET}' m JOIN sab s ON s.sab = m.SAB
        WHERE m.SUPPRESS = 'N' AND m.SRL IN (0, 9) AND m.CODE NOT LIKE 'MTH%' AND m.CODE <> 'NOCODE'
          AND (m.SAB <> 'MSH' OR m.TTY IN ('MH', 'NM'))""")
    con.create_function("norm", norm, ["VARCHAR"], "VARCHAR")
    con.execute("CREATE TEMP TABLE an AS SELECT DISTINCT cui, v, code, norm(str) n FROM a")
    # each code's own preferred name in the CUI: the source's preferred term type first, then UMLS's preferred-atom flags
    con.execute(f"""CREATE TEMP TABLE pref AS SELECT m.CUI cui, s.v, m.CODE code,
            arg_min(m.STR, (CASE WHEN m.TTY IN ('PT', 'MH', 'PN', 'SCN', 'FN', 'LN', 'IN', 'SCD', 'SBD', 'NM', 'PEP', 'LA', 'LPN', 'PX')
                                 THEN 0 ELSE 1 END) * 4 + (CASE WHEN m.TS = 'P' THEN 0 ELSE 2 END) + (CASE WHEN m.ISPREF = 'Y' THEN 0 ELSE 1 END)) nm
        FROM '{PARQUET}' m JOIN sab s ON s.sab = m.SAB WHERE m.SUPPRESS = 'N' AND m.SRL IN (0, 9) GROUP BY 1, 2, 3""")
    con.execute(f"""COPY (
        WITH p AS (SELECT DISTINCT x.v sv, x.code sc, y.v ov, y.code oc, x.cui FROM (SELECT DISTINCT cui, v, code FROM an) x
                   JOIN (SELECT DISTINCT cui, v, code FROM an) y ON x.cui = y.cui AND x.v < y.v),
             p2 AS (SELECT * FROM p)
        SELECT p2.*, (SELECT min(s.n) FROM an s JOIN an o ON o.cui = s.cui AND o.v = p2.ov AND o.code = p2.oc AND o.n = s.n
                      WHERE s.cui = p2.cui AND s.v = p2.sv AND s.code = p2.sc) shared_name,
               ps.nm s_name, po.nm o_name
        FROM p2 JOIN pref ps ON ps.cui = p2.cui AND ps.v = p2.sv AND ps.code = p2.sc
                JOIN pref po ON po.cui = p2.cui AND po.v = p2.ov AND po.code = p2.oc
        ) TO '{PAIRS}.tmp' (FORMAT parquet)""")
    con.execute(f"COPY (SELECT *, shared_name IS NOT NULL same_name FROM read_parquet('{PAIRS}.tmp')) TO '{PAIRS}' (FORMAT parquet)")
    Path(f"{PAIRS}.tmp").unlink()
    print(con.execute(f"""SELECT count(*), count(*) FILTER (WHERE same_name) FROM '{PAIRS}'""").fetchone(), "pairs, same name")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    if a.download or not ZIP.exists():
        download()
    con = duckdb.connect()
    con.execute("SET threads=8")
    if not PARQUET.exists():
        to_parquet(con)
    pairs(con)
    return 0


if __name__ == "__main__":
    sys.exit(main())
