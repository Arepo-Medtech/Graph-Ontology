#!/usr/bin/env python3
"""SNOMED CT's maps to ICD-10 and ICD-10-CM, from the US Edition -> cache/snomed-us/extended_map_20260901.parquet.

The SNOMED CT to ICD-10 map (reference set 447562003, SNOMED International, released with the International Edition) is
not in the AU release, and the International Edition otherwise comes only through MLDS. NLM's US Edition carries it
unchanged (moduleId 449080006, SNOMED International's mapping module) beside NLM's own SNOMED CT to ICD-10-CM map
(6011000124106), and NLM gives the US Edition to UMLS licence holders:

    https://download.nlm.nih.gov/mlb/utsauth/USExt/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20260901T120000Z.zip
    (661 MB, fetched through the UTS download API with the key in .env -- never printed)

This keeps the active rows of those two reference sets from the Snapshot extended map file. Licensed content: it stays in
cache/snomed-us/ (git-ignored), not redistributed.

    .venv/bin/python scripts/snomed_us_maps.py            # seconds, once the zip is in cache/snomed-us/
"""
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

RELEASE = "20260901"
D = Path("cache/snomed-us")
ZIP = D / f"SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_{RELEASE}T120000Z.zip"
OUT = D / f"extended_map_{RELEASE}.parquet"
REFSETS = ("447562003", "6011000124106")


def main() -> int:
    if not ZIP.exists():
        sys.exit(f"missing {ZIP}: fetch the US Edition first (see the docstring)")
    with zipfile.ZipFile(ZIP) as z, tempfile.TemporaryDirectory() as tmp:
        name = next(n for n in z.namelist() if "/Snapshot/Refset/Map/der2_iisssccRefset_ExtendedMapSnapshot" in n)
        path = z.extract(name, tmp)
        duckdb.connect().execute(f"""COPY (SELECT * FROM read_csv('{path}', delim='\t', header=true, quote='', escape='', all_varchar=true)
            WHERE active = '1' AND refsetId IN {REFSETS}) TO '{OUT}' (FORMAT parquet)""")
    print(duckdb.connect().execute(f"SELECT refsetId, count(*) FROM '{OUT}' GROUP BY 1").fetchall())
    return 0


if __name__ == "__main__":
    sys.exit(main())
